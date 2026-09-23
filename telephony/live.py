"""Stateful, provider-independent coordinator for live inbound calls."""

from __future__ import annotations

from collections.abc import Iterable

from agents.intake import (
    FarmerIntakeDraft,
    apply_draft_to_listing,
    extract_farmer_details,
    next_follow_up,
)
from agents.models import DialogueLine, SimulationResult, SimulationScenario, SpeakerType
from db.database import PostgresStore
from orchestration.workflow import execute_scenario

from .contracts import (
    AudioInput,
    CallSession,
    CallStatus,
    SpeechToText,
    SynthesizedSpeech,
    TextToSpeech,
)

COMPLETION_MESSAGES = {
    "mr-IN": "धन्यवाद. तुमची माहिती नोंदवली आहे. तात्पुरती शिफारस तयार केली आहे.",
    "pa-IN": "ਧੰਨਵਾਦ। ਤੁਹਾਡੀ ਜਾਣਕਾਰੀ ਦਰਜ ਕਰ ਲਈ ਗਈ ਹੈ ਅਤੇ ਅਸਥਾਈ ਸਿਫਾਰਸ਼ ਤਿਆਰ ਹੈ।",
    "ta-IN": "நன்றி. உங்கள் தகவல் பதிவு செய்யப்பட்டது. தற்காலிக பரிந்துரை தயாராக உள்ளது.",
    "te-IN": "ధన్యవాదాలు. మీ వివరాలు నమోదు చేశాము. తాత్కాలిక సిఫార్సు సిద్ధంగా ఉంది.",
}
DEFAULT_COMPLETION_MESSAGE = "Thank you. Your information has been recorded."
INTAKE_RETRY_LIMIT = 6
INTAKE_FAILURE_MESSAGE = (
    "Sorry, I could not capture the required sale details. Please call again later."
)


class LiveCallCoordinator:
    """Collects a free-form spoken listing, then runs the ordinary workflow.

    Scenario data supplies a known farmer profile, markets, and simulated buyers
    for local evaluation.  Speech facts replace only explicitly captured listing
    fields; this prevents an uncertain transcript from overwriting fixture data.
    """

    def __init__(
        self,
        scenarios: Iterable[SimulationScenario],
        speech_to_text: SpeechToText,
        text_to_speech: TextToSpeech,
        store: PostgresStore | None = None,
    ) -> None:
        self._scenarios = {scenario.id: scenario for scenario in scenarios}
        self._speech_to_text = speech_to_text
        self._text_to_speech = text_to_speech
        self._store = store
        self._sessions: dict[str, CallSession] = {}
        self._results: dict[str, SimulationResult] = {}

    async def start_call(
        self, call_id: str, caller_reference: str, scenario_id: str
    ) -> tuple[CallSession, SynthesizedSpeech]:
        scenario = self._scenario(scenario_id)
        if call_id in self._sessions:
            raise ValueError(f"Call {call_id} already exists.")

        session = CallSession(
            call_id=call_id,
            scenario_id=scenario.id,
            caller_reference=caller_reference,
            preferred_language=scenario.farmer.preferred_language,
            intake_draft=FarmerIntakeDraft(village=scenario.farmer.location.village).model_dump(
                mode="json"
            ),
            status=CallStatus.CONNECTED,
        )
        self._sessions[call_id] = session
        session.events.append("Received inbound call.")
        prompt = await self._ask_next_follow_up(session, scenario)
        self._persist(session)
        return session, prompt

    async def accept_recording(
        self, call_id: str, audio: AudioInput
    ) -> tuple[CallSession, SynthesizedSpeech]:
        session = self._session(call_id)
        scenario = self._scenario(session.scenario_id)
        if session.status is not CallStatus.CONNECTED:
            raise ValueError(
                f"Call {call_id} cannot accept another recording in state {session.status}."
            )

        transcript = await self._speech_to_text.transcribe(
            audio,
            language_hint=scenario.farmer.preferred_language,
        )
        session.dialogue.append(
            DialogueLine(
                speaker=SpeakerType.FARMER,
                text=transcript.text,
                english_translation=transcript.text,
                language=transcript.language,
                speaker_id=scenario.farmer.id,
                metadata={
                    "audio_reference": audio.audio_reference,
                    "transcription_confidence": transcript.confidence,
                },
            )
        )
        session.events.append("Transcribed caller response.")
        before = FarmerIntakeDraft.model_validate(session.intake_draft)
        if transcript.confidence >= 0.5:
            draft = extract_farmer_details(transcript.text, before)
            session.intake_draft = draft.model_dump(mode="json")
            session.events.append("Extracted deterministic farmer-intake facts.")
        else:
            draft = before
            session.events.append("Requested a retry because transcription confidence was too low.")

        if prompt := await self._ask_next_follow_up(session, scenario):
            self._persist(session)
            return session, prompt

        session.status = CallStatus.INTAKE_COMPLETE
        session.events.append("Completed live speech intake.")
        listing = apply_draft_to_listing(scenario.listing, draft)
        location = scenario.farmer.location.model_copy(update={"village": draft.village})
        live_scenario = scenario.model_copy(
            update={
                "listing": listing,
                "farmer": scenario.farmer.model_copy(update={"location": location}),
            }
        )
        result = await execute_scenario(live_scenario)
        self._results[call_id] = result
        session.status = CallStatus.COMPLETED
        session.events.append("Completed the negotiation workflow.")
        completion_message = COMPLETION_MESSAGES.get(
            session.preferred_language, DEFAULT_COMPLETION_MESSAGE
        )
        prompt = await self._text_to_speech.synthesize(
            completion_message,
            language=session.preferred_language,
        )
        if self._store:
            self._store.save_result(live_scenario, result)
        self._persist(session, result)
        return session, prompt

    def get_session(self, call_id: str) -> CallSession:
        return self._session(call_id)

    def get_result(self, call_id: str) -> SimulationResult | None:
        return self._results.get(call_id)

    async def _ask_next_follow_up(
        self, session: CallSession, scenario: SimulationScenario
    ) -> SynthesizedSpeech | None:
        draft = FarmerIntakeDraft.model_validate(session.intake_draft)
        question = next_follow_up(draft, scenario.farmer.preferred_language)
        if question is None:
            return None
        if session.follow_up_attempts >= INTAKE_RETRY_LIMIT:
            session.status = CallStatus.FAILED
            session.events.append("Ended intake after the retry limit was reached.")
            return await self._text_to_speech.synthesize(
                INTAKE_FAILURE_MESSAGE,
                language=scenario.farmer.preferred_language,
            )
        session.follow_up_attempts += 1
        line = DialogueLine(
            speaker=SpeakerType.INTAKE_AGENT,
            speaker_id="intake-agent",
            language=scenario.farmer.preferred_language,
            text=question,
            english_translation=question,
            metadata={
                "action": "collect_missing_field",
                "missing_fields": draft.missing_required_fields(),
            },
        )
        session.dialogue.append(line)
        session.events.append("Synthesized a targeted intake follow-up.")
        return await self._text_to_speech.synthesize(question, language=line.language)

    def _scenario(self, scenario_id: str) -> SimulationScenario:
        try:
            return self._scenarios[scenario_id]
        except KeyError as exc:
            raise ValueError(f"Unknown voice scenario: {scenario_id}") from exc

    def _session(self, call_id: str) -> CallSession:
        try:
            return self._sessions[call_id]
        except KeyError as exc:
            raise ValueError(f"Unknown call: {call_id}") from exc

    def _persist(self, session: CallSession, result: SimulationResult | None = None) -> None:
        if self._store:
            self._store.save_voice_call(session, result)
