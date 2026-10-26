import base64
import edge_tts
from app.schemas.walkthrough import ExplanationStep

async def synthesize_audio(steps: list[ExplanationStep]) -> tuple[str, str]:
    full_script = " ".join([step.explanation for step in steps])
    voice = "en-US-GuyNeural"

    communicate = edge_tts.Communicate(full_script, voice)
    audio_data = bytearray()
    vtt_data = []

    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            audio_data.extend(chunk["data"])
        elif chunk["type"] == "WordBoundary":
            vtt_data.append(
                f"{chunk['offset']}ms -> {chunk['duration']}ms: {chunk['text']}"
            )

    audio_b64 = base64.b64encode(audio_data).decode("utf-8")
    vtt_timestamps = "\n".join(vtt_data)

    return audio_b64, vtt_timestamps