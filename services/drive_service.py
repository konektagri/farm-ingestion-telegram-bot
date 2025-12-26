"""Google Drive service with retry logic and folder caching."""
import os
import ssl
import logging
from typing import Optional, Tuple, Dict
from dataclasses import dataclass

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

from utils.retry import retry

logger = logging.getLogger(__name__)

# Configuration
SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = 'secret/service_account.json'

# Exceptions that should trigger a retry
RETRYABLE_EXCEPTIONS = (HttpError, ConnectionError, ssl.SSLError, OSError, TimeoutError)


@dataclass
class UploadResult:
    """Result of a file upload operation."""
    success: bool
    file_id: Optional[str] = None
    web_link: Optional[str] = None
    error: Optional[str] = None


class DriveService:
    """
    Google Drive service with retry logic, folder caching, and batch operations.
    
    Uses singleton pattern to maintain a single Drive connection.
    """
    
    _instance: Optional['DriveService'] = None
    
    def __new__(cls) -> 'DriveService':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._parent_folder_id = os.getenv('PARENT_FOLDER_ID')
        self._impersonated_email = os.getenv('IMPERSONATED_USER_EMAIL')
        self._service = None
        self._folder_cache: Dict[str, str] = {}  # path -> folder_id cache
        self._initialized = True
        
        # Initialize service
        self._init_service()
    
    def _init_service(self):
        """Initialize the Google Drive API service."""
        if not self._parent_folder_id:
            raise ValueError("❌ PARENT_FOLDER_ID is missing in .env file.")
        if not self._impersonated_email:
            raise ValueError("❌ IMPERSONATED_USER_EMAIL is missing in .env file.")
        if not os.path.exists(SERVICE_ACCOUNT_FILE):
            raise ValueError(f"❌ {SERVICE_ACCOUNT_FILE} not found.")
        
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE,
            scopes=SCOPES
        )
        delegated_creds = creds.with_subject(self._impersonated_email)
        self._service = build('drive', 'v3', credentials=delegated_creds)
        logger.info("Google Drive service initialized successfully")
    
    @property
    def parent_folder_id(self) -> str:
        """Get the parent folder ID."""
        return self._parent_folder_id
    
    @retry(max_attempts=3, backoff_base=2.0, exceptions=RETRYABLE_EXCEPTIONS)
    def _get_or_create_folder(self, folder_name: str, parent_id: str) -> str:
        """
        Check if folder exists inside parent, if not create it.
        
        Args:
            folder_name: Name of the folder to find/create
            parent_id: ID of the parent folder
            
        Returns:
            Folder ID
        """
        # Check cache first
        cache_key = f"{parent_id}/{folder_name}"
        if cache_key in self._folder_cache:
            return self._folder_cache[cache_key]
        
        try:
            query = (
                f"name='{folder_name}' and '{parent_id}' in parents and "
                f"mimeType='application/vnd.google-apps.folder' and trashed=false"
            )
            results = self._service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                self._folder_cache[cache_key] = folder_id
                return folder_id
            
            # Create folder
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = self._service.files().create(
                body=file_metadata,
                fields='id',
                supportsAllDrives=True
            ).execute()
            
            folder_id = folder.get('id')
            self._folder_cache[cache_key] = folder_id
            logger.info(f"Created folder: {folder_name}")
            return folder_id
            
        except HttpError as e:
            logger.error(f"Error finding/creating folder '{folder_name}': {e}")
            raise
    
    def create_folder_path(self, folder_path: str) -> str:
        """
        Create entire folder path with caching for efficiency.
        
        Args:
            folder_path: Nested folder path (e.g., "2025-12-23/Phnom_Penh/Farm-01")
            
        Returns:
            Final folder ID
        """
        folder_parts = folder_path.split('/')
        current_parent_id = self._parent_folder_id
        
        for folder_name in folder_parts:
            current_parent_id = self._get_or_create_folder(folder_name, current_parent_id)
        
        return current_parent_id
    
    def upload_file(self, file_path: str, folder_path: str) -> UploadResult:
        """
        Upload a file to Google Drive with retry logic.
        
        Args:
            file_path: Local path to the file
            folder_path: Nested folder path on Drive
            
        Returns:
            UploadResult with success status and file info
        """
        try:
            logger.info(f"Starting upload: {file_path} -> {folder_path}")
            
            # Check if file exists
            if not os.path.exists(file_path):
                error_msg = f"File not found: {file_path}"
                logger.error(error_msg)
                return UploadResult(success=False, error=error_msg)
            
            folder_id = self.create_folder_path(folder_path)
            logger.info(f"Folder ID obtained: {folder_id}")
            
            file_metadata = {
                'name': os.path.basename(file_path),
                'parents': [folder_id]
            }
            
            media = MediaFileUpload(file_path, resumable=True)
            
            file = self._service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id, webViewLink',
                supportsAllDrives=True
            ).execute()
            
            logger.info(f"Upload successful: {file.get('id')}")
            return UploadResult(
                success=True,
                file_id=file.get('id'),
                web_link=file.get('webViewLink')
            )
            
        except HttpError as e:
            logger.error(f"Drive upload HttpError: {e.resp.status} - {e.error_details}")
            return UploadResult(success=False, error=f"HttpError {e.resp.status}: {str(e)}")
        except Exception as e:
            logger.error(f"Drive upload error: {type(e).__name__}: {e}", exc_info=True)
            return UploadResult(success=False, error=str(e))
    
    @retry(max_attempts=3, backoff_base=2.0, exceptions=RETRYABLE_EXCEPTIONS)
    def upload_csv(self, csv_file_path: str) -> UploadResult:
        """
        Upload CSV file to a 'Surveys' folder, updating if exists.
        
        Args:
            csv_file_path: Path to the CSV file
            
        Returns:
            UploadResult with success status and file info
        """
        try:
            if not os.path.exists(csv_file_path):
                return UploadResult(success=False, error=f"CSV file not found: {csv_file_path}")
            
            # Create or get 'Surveys' folder
            folder_id = self._get_or_create_folder('Surveys', self._parent_folder_id)
            
            # Check if file already exists
            filename = os.path.basename(csv_file_path)
            query = f"name='{filename}' and '{folder_id}' in parents and trashed=false"
            results = self._service.files().list(
                q=query,
                spaces='drive',
                fields='files(id, name)',
                supportsAllDrives=True,
                includeItemsFromAllDrives=True
            ).execute()
            
            existing_files = results.get('files', [])
            media = MediaFileUpload(csv_file_path, mimetype='text/csv', resumable=True)
            
            if existing_files:
                # Update existing file
                file_id = existing_files[0]['id']
                file = self._service.files().update(
                    fileId=file_id,
                    media_body=media,
                    fields='id, webViewLink',
                    supportsAllDrives=True
                ).execute()
                logger.info(f"Updated CSV file in Google Drive: {filename}")
            else:
                # Create new file
                file_metadata = {
                    'name': filename,
                    'parents': [folder_id],
                    'mimeType': 'text/csv'
                }
                file = self._service.files().create(
                    body=file_metadata,
                    media_body=media,
                    fields='id, webViewLink',
                    supportsAllDrives=True
                ).execute()
                logger.info(f"Uploaded new CSV file to Google Drive: {filename}")
            
            return UploadResult(
                success=True,
                file_id=file.get('id'),
                web_link=file.get('webViewLink')
            )
            
        except Exception as e:
            logger.error(f"CSV Drive upload error: {e}")
            return UploadResult(success=False, error=str(e))
    
    def clear_folder_cache(self):
        """Clear the folder ID cache."""
        self._folder_cache.clear()
        logger.info("Folder cache cleared")


# Convenience function for backward compatibility
def get_drive_service() -> DriveService:
    """Get the singleton DriveService instance."""
    return DriveService()
