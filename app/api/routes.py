from fastapi import APIRouter
from app.schemas.walkthrough import PRRequest, WalkthroughResponse
from app.services.github_service import fetch_and_sanitize_diff
from app.services.llm_service import generate_walkthrough_script
from app.services.tts_service import synthesize_audio

router = APIRouter()

@router.post("/generate-walkthrough", response_model=WalkthroughResponse)
async def create_walkthrough(payload: PRRequest):
    # Step 1: Ingestion & Sanitization
    sanitized_diff = await fetch_and_sanitize_diff(str(payload.pr_url))

    # Step 2: AI Script Generation
    script_steps = await generate_walkthrough_script(sanitized_diff)

    # Step 3: Audio & Timestamp Synthesis
    audio_b64, vtt_timestamps = await synthesize_audio(script_steps)

    return WalkthroughResponse(
        raw_diff=sanitized_diff,
        audio_base64=audio_b64,
        vtt_timestamps=vtt_timestamps,
        script=script_steps
    )