from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    GROQ_API_KEY: str
    GROQ_MODEL: str
    GITHUB_TOKEN: str = ""  # Optional for public repos, avoids rate limits if provided

    IGNORE_PATTERNS: list[str] = [
        "lock", ".svg", ".png", "vendor/", "node_modules/", 
        "dist/", "build/", "coverage/", ".min.js", ".min.css"
    ]

    class Config:
        env_file = ".env"

settings = Settings()