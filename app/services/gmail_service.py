"""
Gmail service for Gmail API integration.
"""
import base64
import json
from datetime import datetime
from email.utils import parsedate_to_datetime

from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.core.config import settings
from app.services.auth_service import AuthService
from app.utils.logger import get_logger

logger = get_logger(__name__)

class GmailService:
    """Service for Gmail API operations."""
    
    SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']
    
    @staticmethod
    def get_credentials(user_id: int) -> Credentials | None:
        """Get OAuth2 credentials for a user."""
        logger.debug(f'Getting credentials for user [user_id={user_id}]')
        tokens = AuthService.get_tokens(user_id)
        if not tokens:
            logger.warning(f'No tokens found for user [user_id={user_id}]')
            return None
        
        creds = Credentials(
            token=tokens['access_token'],
            refresh_token=tokens['refresh_token'],
            token_uri='https://oauth2.googleapis.com/token',
            client_id=settings.GMAIL_CLIENT_ID,
            client_secret=settings.GMAIL_CLIENT_SECRET
        )
        
        return creds
    
    @staticmethod
    def get_service(user_id: int):
        """Get Gmail API service instance for a user."""
        logger.debug(f'Getting Gmail service for user [user_id={user_id}]')
        creds = GmailService.get_credentials(user_id)
        if not creds:
            logger.error(f'No credentials available for user [user_id={user_id}]')
            raise ValueError("No credentials available for user")
        
        # Token expiration is handled automatically by Google's Credentials library
        # when making API calls - no proactive checking needed
        
        return build('gmail', 'v1', credentials=creds)
    
    @staticmethod
    def fetch_emails(user_id: int, max_results: int = 50) -> list[dict]:
        """
        Fetch recent emails from Gmail.
        
        Args:
            user_id: User ID
            max_results: Maximum number of emails to fetch
            
        Returns:
            List of email dictionaries with fields: id, subject, sender, recipient, body, received_at
        """
        try:
            logger.info(f'Fetching emails from Gmail API [user_id={user_id}] [max_results={max_results}]')
            service = GmailService.get_service(user_id)
            
            # List messages
            results = service.users().messages().list(
                userId='me',
                maxResults=max_results
            ).execute()
            
            messages = results.get('messages', [])
            logger.info(f'Gmail API returned {len(messages)} messages [user_id={user_id}]')
            emails = []
            skipped_count = 0
            
            for msg in messages:
                try:
                    # Get message details
                    message = service.users().messages().get(
                        userId='me',
                        id=msg['id'],
                        format='full'
                    ).execute()
                    
                    # Extract headers
                    headers = {h['name']: h['value'] for h in message['payload'].get('headers', [])}
                    subject = headers.get('Subject', '')
                    sender = headers.get('From', '')
                    recipient = headers.get('To', '')
                    
                    # Extract body
                    body = GmailService._extract_body(message['payload'])
                    
                    # Get date
                    date_str = headers.get('Date', '')
                    received_at = GmailService._parse_date(date_str)
                    
                    emails.append({
                        'gmail_message_id': msg['id'],
                        'subject': subject,
                        'sender': sender,
                        'recipient': recipient,
                        'body': body,
                        'received_at': received_at
                    })
                except Exception as e:
                    # Skip messages that can't be parsed
                    skipped_count += 1
                    logger.warning(f'Skipped message {msg.get("id", "unknown")} due to parsing error [user_id={user_id}]: {str(e)}')
                    continue
            
            logger.info(f'Gmail email fetch completed: {len(emails)} emails parsed, {skipped_count} skipped [user_id={user_id}]')
            return emails
            
        except HttpError as error:
            logger.error(f'Gmail API error [user_id={user_id}]: {str(error)}', exc_info=True)
            raise Exception(f"Gmail API error: {error}")
    
    @staticmethod
    def _extract_body(payload: dict) -> str:
        """Extract email body from Gmail API payload."""
        body = ""
        
        if 'parts' in payload:
            for part in payload['parts']:
                if part['mimeType'] == 'text/plain':
                    data = part['body'].get('data')
                    if data:
                        body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
                elif part['mimeType'] == 'text/html':
                    # Prefer plain text, but use HTML if no plain text
                    if not body:
                        data = part['body'].get('data')
                        if data:
                            body += base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        else:
            # Single part message
            if payload['mimeType'] == 'text/plain':
                data = payload['body'].get('data')
                if data:
                    body = base64.urlsafe_b64decode(data).decode('utf-8', errors='ignore')
        
        return body
    
    @staticmethod
    def _parse_date(date_str: str) -> str:
        """Parse email date string to ISO format."""
        try:
            dt = parsedate_to_datetime(date_str)
            return dt.isoformat()
        except Exception:
            return datetime.now().isoformat()
