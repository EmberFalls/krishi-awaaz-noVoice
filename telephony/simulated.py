"""Deterministic local substitutes for voice providers.

These classes do not create audio. They let the call flow be tested without a
phone number, paid API credentials, or network access.
"""

from __future__ import annotations

from collections import deque
from collections.abc import Iterable

from agents.models import DialogueLine

from .contracts import AudioInput, SynthesizedSpeech, TranscriptionResult


class ScriptedSpeechToText:
    """Returns queued farmer utterances as if they had been transcribed."""

    def __init__(self, farmer_lines: Iterable[DialogueLine]) -> None:
        self._farmer_lines = deque(farmer_lines)

    async def transcribe(
        self, audio: AudioInput, *, language_hint: str | None = None
    ) -> TranscriptionResult:
        if not self._farmer_lines:
            raise RuntimeError(f"No scripted caller response remains for {audio.audio_reference}.")

        line = self._farmer_lines.popleft()
        return TranscriptionResult(text=line.text, language=line.language, confidence=1.0)


class CapturingTextToSpeech:
    """Records synthesis requests while returning deterministic fake clip IDs."""

    def __init__(self) -> None:
        self.clips: list[SynthesizedSpeech] = []

    async def synthesize(self, text: str, *, language: str) -> SynthesizedSpeech:
        index = len(self.clips) + 1
        clip = SynthesizedSpeech(
            clip_id=f"simulated-tts-{index}",
            text=text,
            language=language,
            audio_reference=f"simulated://tts/{index}",
            content=b"simulated-audio",
        )
        self.clips.append(clip)
        return clip
