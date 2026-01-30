import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

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

def get_authenticated_service(client_secrets_path: Path, token_path: Path):
    creds = None

    if token_path.exists():
        creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(client_secrets_path),
                SCOPES,
            )

            # WSL-safe: start local server but DO NOT try to open browser
            creds = flow.run_local_server(
                host="localhost",
                port=0,
                open_browser=False
            )

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
    parser = argparse.ArgumentParser(description="Upload Project S final_short.mp4 to YouTube using final_metadata.json.")
    parser.add_argument("--video", required=True, help="Path to queued video file (.mp4)")
    parser.add_argument("--meta", required=True, help="Path to queued metadata file (.json)")
    parser.add_argument("--client-secrets", default="secrets/client_secret.json",
                        help="Path to OAuth client secrets JSON (downloaded from Google Cloud Console).")
    parser.add_argument("--token", default="secrets/token.json", help="Path to saved OAuth token JSON.")
    parser.add_argument("--privacy", default="public", choices=["public", "unlisted", "private"], help="Upload privacy status.")
    args = parser.parse_args()

    video_path = Path(args.video).resolve()
    meta_path = Path(args.meta).resolve()

    if not meta_path.exists():
        raise FileNotFoundError(f"final_metadata.json not found: {meta_path}")
    if not video_path.exists():
        raise FileNotFoundError(f"final_short.mp4 not found: {video_path}")

    raw = load_json(meta_path)

    if "metadata" not in raw:
        raise RuntimeError(f"'metadata' object missing in {meta_path}")

    meta = raw["metadata"]

    # Validate required fields (fail loud, no silent fallback)
    required = ["title", "language", "made_for_kids"]
    missing = [k for k in required if k not in meta]
    if missing:
        raise RuntimeError(f"Metadata missing required fields: {missing} in {meta_path}")

    if "description_lines" not in meta or not isinstance(meta["description_lines"], list):
        raise RuntimeError("metadata.description_lines must be a list")

    title = str(meta["title"]).strip()
    description = "\n".join(line.strip() for line in meta["description_lines"])

    tags = meta.get("tags") or []
    if not isinstance(tags, list):
        raise RuntimeError("tags must be a list in final_metadata.json")
    
    language = meta.get("language", "en")
    made_for_kids = bool(meta.get("made_for_kids", False))

    print("[meta] title:", title)
    print("[meta] tags:", tags)
    print("[meta] privacy:", args.privacy)

    script_root = Path(__file__).resolve().parents[2]
    client_secrets_path = (script_root / args.client_secrets).resolve()
    token_path = (script_root / args.token).resolve()

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
