from collections import deque
from pathlib import Path

from fastapi.testclient import TestClient
from twilio.request_validator import RequestValidator

from agents.models import DialogueLine, SpeakerType
from data.scenarios import load_scenarios
from telephony.contracts import AudioInput, SynthesizedSpeech, TranscriptionResult
from telephony.live import LiveCallCoordinator
from telephony.settings import VoiceSettings
from telephony.webhook_routes import InMemoryAudioStore, create_app

CATALOG = Path(__file__).parents[1] / "data" / "scenarios.json"


class StubSpeechToText:
    def __init__(self, lines: list[DialogueLine]) -> None:
        self._lines = deque(lines)

    async def transcribe(
        self, audio: AudioInput, *, language_hint: str | None = None
    ) -> TranscriptionResult:
        line = self._lines.popleft()
        return TranscriptionResult(text=line.text, language=line.language, confidence=0.9)


class StubTextToSpeech:
    def __init__(self) -> None:
        self.count = 0

    async def synthesize(self, text: str, *, language: str) -> SynthesizedSpeech:
        self.count += 1
        return SynthesizedSpeech(
            clip_id=f"webhook-clip-{self.count}",
            text=text,
            language=language,
            audio_reference=f"memory://webhook/{self.count}",
            content=b"audio-bytes",
        )


async def fake_recording_fetcher(url: str, settings: VoiceSettings) -> AudioInput:
    return AudioInput(audio_reference=url, content=b"recording")


def test_twilio_webhook_flow_replays_all_intake_turns() -> None:
    scenario = load_scenarios(CATALOG)[0]
    farmer_lines = [line for line in scenario.intake_dialogue if line.speaker is SpeakerType.FARMER]
    coordinator = LiveCallCoordinator(
        [scenario],
        StubSpeechToText(farmer_lines),
        StubTextToSpeech(),
    )
    settings = VoiceSettings(
        public_base_url="https://voice.example.test",
        twilio_account_sid="AC-test",
        twilio_auth_token="test-token",
        sarvam_api_key="sarvam-test",
        default_scenario_id=scenario.id,
        validate_twilio_requests=False,
    )
    app = create_app(
        settings=settings,
        coordinator=coordinator,
        audio_store=InMemoryAudioStore(),
        recording_fetcher=fake_recording_fetcher,
    )
    client = TestClient(app)

    response = client.post("/twilio/voice", data={"CallSid": "CA-webhook", "From": "+910"})
    assert response.status_code == 200
    assert "<Record" in response.text

    for _ in farmer_lines:
        response = client.post(
            "/twilio/recording",
            data={"CallSid": "CA-webhook", "RecordingUrl": "https://recording.example.test/1"},
        )
        assert response.status_code == 200
        if "<Hangup" in response.text:
            break

    assert "<Hangup" in response.text
    assert coordinator.get_session("CA-webhook").status.value == "completed"


def test_twilio_webhook_rejects_unsigned_requests_by_default() -> None:
    scenario = load_scenarios(CATALOG)[0]
    coordinator = LiveCallCoordinator(
        [scenario],
        StubSpeechToText([]),
        StubTextToSpeech(),
    )
    settings = VoiceSettings(
        public_base_url="https://voice.example.test",
        twilio_account_sid="AC-test",
        twilio_auth_token="test-token",
        sarvam_api_key="sarvam-test",
        default_scenario_id=scenario.id,
    )
    app = create_app(settings=settings, coordinator=coordinator)
    client = TestClient(app)
    form = {"CallSid": "CA-signed", "From": "+910"}

    unsigned = client.post("/twilio/voice", data=form)
    assert unsigned.status_code == 403

    signature = RequestValidator(settings.twilio_auth_token).compute_signature(
        "https://voice.example.test/twilio/voice", form
    )
    signed = client.post(
        "/twilio/voice",
        data=form,
        headers={"X-Twilio-Signature": signature},
    )
    assert signed.status_code == 200
