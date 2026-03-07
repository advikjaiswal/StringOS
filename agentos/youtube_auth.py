from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# Define the required OAuth scope for uploading to YouTube
SCOPES = ["https://www.googleapis.com/auth/youtube.upload"]

# Path to your OAuth 2.0 client secrets JSON file
CLIENT_SECRETS_FILE = "/Users/advikjaiswal/Downloads/client_secret_30745657033-flio7aq5hi9qfrhpsfgetukpl760q8ad.apps.googleusercontent.com.json"

# Run the OAuth flow to get credentials
flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
credentials = flow.run_local_server(port=8080)

# Build the YouTube API client
youtube = build("youtube", "v3", credentials=credentials)

# Now you can use the 'youtube' object to interact with the YouTube Data API 