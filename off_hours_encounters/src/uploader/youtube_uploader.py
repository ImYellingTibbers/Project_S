import argparse
import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials


SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]


def load_json(path: Path) -> Dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def sanitize_title(title: str, max_len: int = 70) -> str:
    # Remove newlines, collapse whitespace
    title = re.sub(r"\s+", " ", title).strip()
    if len(title) <= max_len:
        return title
    # Simple truncate without breaking words too badly
    return title[: max_len - 1].rstrip() + "…"


def safe_join_lines(lines: List[str]) -> str:
    # Keep as short lines (good for Shorts), strip empties
    cleaned = [re.sub(r"\s+", " ", (ln or "").strip()) for ln in lines]
    cleaned = [ln for ln in cleaned if ln]
    return "\n".join(cleaned).strip()


def build_fallback_title(idea_data: Dict[str, Any]) -> str:
    # Prefer winner idea; turn into a hook-ish title
    winner = (idea_data.get("data") or {}).get("winner") or {}
    idea = winner.get("idea") or "Short Horror Story"
    # If the winner idea is long, extract something usable
    # e.g., "In a decrepit hotel room, ..." -> "The Hotel Room That Changes"
    idea = re.sub(r"^In\s+a\s+|^In\s+an\s+", "", idea, flags=re.IGNORECASE)
    idea = re.sub(r"^During\s+|^While\s+", "", idea, flags=re.IGNORECASE)
    idea = idea.strip().rstrip(".")
    # Keep it short and title-ish
    return sanitize_title(idea, max_len=70)


def get_metadata_from_idea_json(idea_json: Dict[str, Any]) -> Tuple[str, str, List[str], str, bool]:
    """
    Returns: title, description, tags, language, made_for_kids
    """
    data = idea_json.get("data") or {}

    youtube = data.get("youtube") or {}
    title = youtube.get("title")
    if not title:
        title = build_fallback_title(idea_json)

    # Description: use description_lines if available; else use a minimal fallback
    desc_lines = youtube.get("description_lines")
    if isinstance(desc_lines, list) and desc_lines:
        description = safe_join_lines(desc_lines)
    else:
        # fallback: short + safe
        winner = data.get("winner") or {}
        reason = winner.get("reason") or ""
        base = "Short horror story."
        if reason:
            base = f"{base}\n{sanitize_title(reason, max_len=120)}"
        description = base

    # Hardcode #shorts regardless
    if "#shorts" not in description.lower():
        description = (description + "\n\n#shorts").strip()

    tags = youtube.get("tags")
    if not isinstance(tags, list):
        tags = []
    # Clean tags: remove hashtags, dedupe, limit count
    cleaned_tags = []
    seen = set()
    for t in tags:
        if not isinstance(t, str):
            continue
        t2 = t.strip()
        if not t2:
            continue
        t2 = t2.lstrip("#").strip()
        # YouTube tags are best without commas/line breaks
        t2 = re.sub(r"[\r\n,]+", " ", t2).strip()
        key = t2.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned_tags.append(t2)
        if len(cleaned_tags) >= 25:
            break

    language = youtube.get("language") or "en"
    made_for_kids = bool(youtube.get("made_for_kids", False))

    return sanitize_title(title), description, cleaned_tags, language, made_for_kids


def get_authenticated_service(client_secrets_path: Path, token_path: Path):
    creds = None
    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets_path), SCOPES)
            creds = flow.run_local_server(port=0)
        token_path.parent.mkdir(parents=True, exist_ok=True)
        token_path.write_text(creds.to_json(), encoding="utf-8")

    return build("youtube", "v3", credentials=creds)


def upload_video(youtube, video_path: Path, title: str, description: str, tags: List[str], language: str,
                 made_for_kids: bool, privacy_status: str) -> str:
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags if tags else None,
            "defaultLanguage": language,
            "defaultAudioLanguage": language,
            "categoryId": "24",  # Entertainment
        },
        "status": {
            "privacyStatus": privacy_status,  # public|unlisted|private
            "selfDeclaredMadeForKids": made_for_kids,
        },
    }

    # Remove None fields cleanly
    if body["snippet"].get("tags") is None:
        del body["snippet"]["tags"]

    media = MediaFileUpload(str(video_path), chunksize=-1, resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=body,
        media_body=media,
        notifySubscribers=False,
    )

    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            pct = int(status.progress() * 100)
            print(f"[upload] {pct}%")

    return response["id"]


def main():
    parser = argparse.ArgumentParser(description="Upload Project S final_short.mp4 to YouTube using idea.json metadata.")
    parser.add_argument("--run", required=True, help=r"Path to run folder, e.g. Project_S_v0.5.1\runs\20260104_123923__horror_shorts")
    parser.add_argument("--client-secrets", default="secrets/client_secret.json",
                        help="Path to OAuth client secrets JSON (downloaded from Google Cloud Console).")
    parser.add_argument("--token", default="secrets/token.json", help="Path to saved OAuth token JSON.")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"], help="Upload privacy status.")
    args = parser.parse_args()

    run_dir = Path(args.run).resolve()
    idea_path = run_dir / "idea.json"
    video_path = run_dir / "render" / "final_short.mp4"

    if not idea_path.exists():
        raise FileNotFoundError(f"idea.json not found: {idea_path}")
    if not video_path.exists():
        raise FileNotFoundError(f"final_short.mp4 not found: {video_path}")

    idea_json = load_json(idea_path)
    title, description, tags, language, made_for_kids = get_metadata_from_idea_json(idea_json)

    print("[meta] title:", title)
    print("[meta] tags:", tags)
    print("[meta] privacy:", args.privacy)

    client_secrets_path = Path(args.client_secrets).resolve()
    token_path = Path(args.token).resolve()

    if not client_secrets_path.exists():
        raise FileNotFoundError(
            f"Client secrets not found: {client_secrets_path}\n"
            "Create OAuth client in Google Cloud Console (Desktop app) and download JSON."
        )

    youtube = get_authenticated_service(client_secrets_path, token_path)

    try:
        video_id = upload_video(
            youtube=youtube,
            video_path=video_path,
            title=title,
            description=description,
            tags=tags,
            language=language,
            made_for_kids=made_for_kids,
            privacy_status=args.privacy,
        )
        print(f"[done] Uploaded video id: {video_id}")
        print(f"[done] URL: https://www.youtube.com/watch?v={video_id}")
    except HttpError as e:
        # Print useful API error details
        print("[error] HttpError:", e)
        raise


if __name__ == "__main__":
    main()
