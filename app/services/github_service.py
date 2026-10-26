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
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN}"

    async with httpx.AsyncClient(follow_redirects=True) as client:
        response = await client.get(api_url, headers=headers)
        if response.status_code != 200:
            if response.status_code == 403:
                detail = "GitHub API rate limit exceeded or access forbidden. Verify your GITHUB_TOKEN on Render."
            elif response.status_code == 404:
                detail = "PR not found. Ensure the repository is public or your GITHUB_TOKEN has private repo access."
            else:
                detail = f"Failed to fetch diff from GitHub (HTTP {response.status_code})."
            raise HTTPException(status_code=response.status_code, detail=detail)
            
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

            file_match = re.search(r"b/(.+)$", line)
            file_name = file_match.group(1) if file_match else "Unknown"

            current_file_diff = []
            skip_file = is_boilerplate(file_name)

        elif not skip_file:
            if line.startswith(("index ", "--- a/", "+++ b/", "@@ ")):
                continue
            current_file_diff.append(line)

    if current_file_diff and not skip_file:
        sanitized_chunks.append(f"File: {file_name}\n" + "\n".join(current_file_diff))

    sanitized_diff = "\n\n".join(sanitized_chunks)
    if not sanitized_diff.strip():
        raise HTTPException(
            status_code=400, 
            detail="No relevant code changes found in this PR after filtering lockfiles and build assets."
        )

    return sanitized_diff