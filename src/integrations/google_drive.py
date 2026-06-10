import os
import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from config.settings import settings

SCOPES = ['https://www.googleapis.com/auth/drive.file']

class GoogleDriveClient:
    def __init__(self):
        self.creds = None
        self.service = None
        self._authenticate()

    def _authenticate(self):
        """Authenticates using the Service Account file defined in settings."""
        try:
            if not os.path.exists(settings.google_service_account_file):
                print(f"Error: Google Service Account file not found at {settings.google_service_account_file}")
                return

            self.creds = Credentials.from_service_account_file(
                settings.google_service_account_file, scopes=SCOPES
            )
            self.service = build('drive', 'v3', credentials=self.creds)
            print("Google Drive Service authenticated successfully.")
        except Exception as e:
            print(f"Failed to authenticate with Google Drive: {e}")

    def upload_file(self, file_path: str, mime_type: str = 'application/pdf', parent_id: str = None):
        """
        Uploads a file to Google Drive.
        
        Args:
            file_path: Absolute path to the file to upload.
            mime_type: MIME type of the file.
            parent_id: ID of the folder to upload to. Defaults to settings.google_docs_folder_id.
        
        Returns:
            dict: The file metadata (id, name, webViewLink) or None if failed.
        """
        if not self.service:
            print("Google Drive service is not initialized.")
            return None

        if not parent_id:
            parent_id = settings.google_docs_folder_id

        file_name = os.path.basename(file_path)
        file_metadata = {
            'name': file_name,
            'parents': [parent_id] if parent_id else []
        }
        
        try:
            media = MediaFileUpload(file_path, mimetype=mime_type)
            file = self.service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, name, webViewLink'
            ).execute()
            
            print(f"File ID: {file.get('id')} uploaded successfully.")
            return file
        except Exception as e:
            print(f"An error occurred while uploading file: {e}")
            return None

# Singleton instance
drive_client = GoogleDriveClient()
