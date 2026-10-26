import re
import httpx
from fastapi import HTTPException
from app.config import settings
from app.config import settings

def is_boilerplate(file_path: str) -> bool:
    return any(pattern in file_path for pattern in settings.IGNORE_PATTERNS)

def parse_github_pr_url(url: str):
    pattern = r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)"
    match = re.match(pattern, url)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid GitHub PR URL format.")
    return match.groups()

async def fetch_and_sanitize_diff(pr_url: str) -> str:
    owner, repo, pull_number = parse_github_pr_url(pr_url)
    api_url = f"https://api.github.com/repos/{owner}/{repo}/pulls/{pull_number}"
    
    headers = {
        "Accept": "application/vnd.github.v3.diff",
        "User-Agent": "FastAPI-PR-Walkthrough"
    }
    if settings.GITHUB_TOKEN:
        headers["Authorization"] = f"token {settings.GITHUB_TOKEN}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(api_url, headers=headers)
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch diff from GitHub.")
        raw_diff = response.text

    # Sanitize boilerplate and strip git headers
    sanitized_chunks = []
    current_file_diff = []
    skip_file = False
    file_name = ""

    for line in raw_diff.splitlines():
        if line.startswith("diff --git"):
            if current_file_diff and not skip_file:
                sanitized_chunks.append(f"File: {file_name}\n" + "\n".join(current_file_diff))

            parts = line.split(" b/")
            file_name = parts[-1] if len(parts) > 1 else "Unknown"

            current_file_diff = []
            skip_file = is_boilerplate(file_name)

        elif not skip_file:
            if line.startswith("index ") or line.startswith("--- a/") or line.startswith("+++ b/") or line.startswith("@@ "):
                continue
            current_file_diff.append(line)

    if current_file_diff and not skip_file:
        sanitized_chunks.append(f"File: {file_name}\n" + "\n".join(current_file_diff))

    return "\n\n".join(sanitized_chunks)