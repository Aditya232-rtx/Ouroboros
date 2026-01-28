import sys
import os
from pathlib import Path

# Setup Path
sys.path.append(str(Path(__file__).parent.parent))

from config.settings import settings
from src.integrations.google_workspace_mcp import GoogleWorkspaceMCP

print(f"Current Working Directory: {os.getcwd()}")
print(f"Settings google_service_account_file: '{settings.google_service_account_file}'")

if settings.google_service_account_file:
    path = Path(settings.google_service_account_file)
    print(f"Abs Path: {path.absolute()}")
    print(f"Exists: {path.exists()}")
else:
    print("❌ Setting is empty!")

print("\nAttempting Reference Initialization...")
try:
    mcp = GoogleWorkspaceMCP()
    if mcp.docs_service and mcp.drive_service:
        print("✅ Services Initialized!")
        
        # Verify Identity
        try:
            creds = mcp.docs_service._http.credentials
            print(f"🆔 Authenticated as: {creds.service_account_email}")
        except Exception as e:
            print(f"⚠️ Could not verify identity details: {e}")
        
        # Test 1: List Files (Already verified working)
        # Test 2: Create in Folder
        folder_id = settings.google_docs_folder_id
        print(f"\n2. Attempting to create Doc in Shared Folder: {folder_id}")
        
        try:
            file_metadata = {
                'name': 'Ouroboros Debug Doc (Drive API)',
                'mimeType': 'application/vnd.google-apps.document',
                'parents': [folder_id]
            }
            if not folder_id:
                print("⚠️  No Folder ID in settings! Creating in root...")
                del file_metadata['parents']
                
            doc = mcp.drive_service.files().create(body=file_metadata).execute()
            print(f"✅ Document Created via Drive API! ID: {doc.get('id')}")
            print(f"URL: https://docs.google.com/document/d/{doc.get('id')}/edit")
        except Exception as e:
            print(f"❌ Drive API Creation Failed: {e}")
            
            print("\n3. Retrying Docs API (Root Create)...")
            try:
                result = mcp.create_document(title="Ouroboros Debug Docs API")
                print(f"✅ Success via Docs API")
            except Exception as e2:
                 print(f"❌ Docs API Failed: {e2}")

    else:
        print("❌ Service NOT Initialized")
except Exception as e:
    print(f"❌ Exception during operation: {e}")
