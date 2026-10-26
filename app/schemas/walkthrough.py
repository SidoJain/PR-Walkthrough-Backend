from pydantic import BaseModel, HttpUrl

class PRRequest(BaseModel):
    pr_url: HttpUrl

class ExplanationStep(BaseModel):
    line_number: int
    explanation: str

class WalkthroughResponse(BaseModel):
    raw_diff: str
    audio_base64: str
    vtt_timestamps: str
    script: list[ExplanationStep]