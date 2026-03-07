import os
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json

SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]
CREDENTIALS_FILE = "agentgpt/keys/client_secret.json"
TOKEN_FILE = "agentgpt/keys/youtube_token.pickle"

def get_authenticated_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        # Check if credentials file is for desktop or web
        with open(CREDENTIALS_FILE, 'r') as f:
            cred_data = json.load(f)
        if 'installed' in cred_data:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=8888)
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        else:
            print("⚠️  Your credentials are for a web application. Please:")
            print("1. Go to Google Cloud Console")
            print("2. Create new OAuth 2.0 Client ID")
            print("3. Choose 'Desktop application' (not 'Web application')")
            print("4. Download and replace client_secret.json")
            raise Exception("Web app credentials not supported for this flow. Please use desktop app credentials.")
    return build("youtube", "v3", credentials=creds)

def upload_video(video_path, title, description, tags=None, category="22", privacy="public"):
    youtube = get_authenticated_service()
    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags or [],
            "categoryId": category
        },
        "status": {
            "privacyStatus": privacy
        }
    }
    media = MediaFileUpload(video_path, chunksize=-1, resumable=True, mimetype="video/*")
    request = youtube.videos().insert(part="snippet,status", body=body, media_body=media)
    response = request.execute()
    return response 