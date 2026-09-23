import asyncio
import base64
from types import SimpleNamespace

from telephony.contracts import AudioInput
from telephony.sarvam import SarvamSpeechToText, SarvamTextToSpeech


class StubSpeechClient:
    def transcribe(self, **kwargs: object) -> SimpleNamespace:
        file = kwargs["file"]
        assert file.read() == b"caller-audio"
        return SimpleNamespace(
            transcript="नमस्कार",
            language_code="mr-IN",
            language_probability=0.93,
        )


class StubTextClient:
    def convert(self, **kwargs: object) -> SimpleNamespace:
        assert kwargs["model"] == "bulbul:v3"
        assert kwargs["speech_sample_rate"] == 8000
        return SimpleNamespace(audios=[base64.b64encode(b"wav-audio").decode()])


def test_sarvam_adapters_use_documented_response_shapes() -> None:
    client = SimpleNamespace(
        speech_to_text=StubSpeechClient(),
        text_to_speech=StubTextClient(),
    )
    transcription = asyncio.run(
        SarvamSpeechToText("key", client=client).transcribe(
            AudioInput(audio_reference="memory://caller", content=b"caller-audio"),
            language_hint="mr-IN",
        )
    )
    speech = asyncio.run(
        SarvamTextToSpeech("key", client=client).synthesize("नमस्कार", language="mr-IN")
    )

    assert transcription.text == "नमस्कार"
    assert transcription.language == "mr-IN"
    assert transcription.confidence == 0.93
    assert speech.content == b"wav-audio"
