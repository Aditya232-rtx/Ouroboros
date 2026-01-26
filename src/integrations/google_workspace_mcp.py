"""
Ouroboros AI - Google Workspace MCP Integration
Google Docs creation and management for security reports
"""

import logging
from typing import Dict, Any, Optional, List
from pathlib import Path

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from config.settings import settings

logger = logging.getLogger(__name__)


class GoogleWorkspaceClient:
    """
    Google Workspace client for creating and managing Google Docs.
    Per 02_AGENT_SPECIFICATIONS: Auto-updating reports for live status.
    """
    
    SCOPES = [
        'https://www.googleapis.com/auth/documents',
        'https://www.googleapis.com/auth/drive'
    ]
    
    def __init__(self):
        """Initialize Google Workspace client"""
        self.docs_service = None
        self.drive_service = None
        
        if settings.google_service_account_file:
            self._initialize_services()
    
    def _initialize_services(self):
        """Initialize Google Docs and Drive services"""
        try:
            creds = service_account.Credentials.from_service_account_file(
                str(settings.google_service_account_file),
                scopes=self.SCOPES
            )
            
            self.docs_service = build('docs', 'v1', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            
            logger.info("Google Workspace services initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Google Workspace: {e}")
    
    def create_document(
        self, 
        title: str,
        content: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Create a new Google Doc.
        
        Args:
            title: Document title
            content: Optional initial content
        
        Returns:
            {doc_id, doc_url}
        """
        if not self.docs_service:
            raise ValueError("Google Docs service not initialized")
        
        logger.info(f"Creating Google Doc: {title}")
        
        try:
            # Create document
            doc = self.docs_service.documents().create(
                body={'title': title}
            ).execute()
            
            doc_id = doc.get('documentId')
            doc_url = f"https://docs.google.com/document/d/{doc_id}/edit"
            
            # Add initial content if provided
            if content:
                self.update_document(doc_id, content)
            
            logger.info(f"Created document: {doc_url}")
            
            return {
                "doc_id": doc_id,
                "doc_url": doc_url
            }
        
        except HttpError as e:
            logger.error(f"Failed to create document: {e}")
            raise
    
    def update_document(
        self, 
        doc_id: str, 
        content: str
    ):
        """
        Update document content.
        
        Args:
            doc_id: Document ID
            content: New content to append
        """
        if not self.docs_service:
            raise ValueError("Google Docs service not initialized")
        
        logger.info(f"Updating document {doc_id}")
        
        try:
            requests = [{
                'insertText': {
                    'location': {'index': 1},
                    'text': content
                }
            }]
            
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Document updated: {doc_id}")
        
        except HttpError as e:
            logger.error(f"Failed to update document: {e}")
            raise
    
    def update_section(
        self,
        doc_id: str,
        section_heading: str,
        content: str
    ):
        """
        Update specific section of the document.
        Uses replaceAllText with strict matching for placeholders like [SECTION_NAME].
        """
        if not self.docs_service:
            raise ValueError("Google Docs service not initialized")
        
        logger.info(f"Updating section '{section_heading}' in {doc_id}")
        
        try:
            requests = [{
                'replaceAllText': {
                    'containsText': {
                        'text': f"[{section_heading}]",
                        'matchCase': True
                    },
                    'replaceText': content
                }
            }]
            
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()
            
            logger.info(f"Updated section '{section_heading}'")
            
        except HttpError as e:
            logger.error(f"Failed to update section: {e}")
            raise
    
    def share_document(
        self, 
        doc_id: str,
        email: str,
        role: str = "reader"  # reader|commenter|writer
    ):
        """
        Share document with a user.
        
        Args:
            doc_id: Document ID
            email: Email address to share with
            role: Permission level
        """
        if not self.drive_service:
            raise ValueError("Google Drive service not initialized")
        
        logger.info(f"Sharing document {doc_id} with {email}")
        
        try:
            permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }
            
            self.drive_service.permissions().create(
                fileId=doc_id,
                body=permission,
                sendNotificationEmail=True
            ).execute()
            
            logger.info(f"Document shared with {email}")
        
        except HttpError as e:
            logger.error(f"Failed to share document: {e}")
            raise


# Global instance
google_workspace_client = GoogleWorkspaceClient()
