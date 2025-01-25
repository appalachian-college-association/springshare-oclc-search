import os
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class OCLCAuth:
    """Handles OCLC authentication with improved token management"""
    
    def __init__(self):
        """Initialize authentication handler with retry strategy"""
        self.key = os.environ.get('OCLC_KEY')
        self.secret = os.environ.get('OCLC_SECRET')
        
        if not self.key or not self.secret:
            raise ValueError("OCLC credentials not found in environment variables")
            
        self.token_url = 'https://oauth.oclc.org/token'
        self.scope = ['WorldCatDiscoveryAPI:view_brief_bib']
        
        # Initialize token storage
        self._token = None
        self._token_expiry = None
        
        # Configure session with retry strategy
        self.session = self._create_session()
        
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        retry_strategy = Retry(
            total=3,  # number of retries
            backoff_factor=1,  # wait 1, 2, 4 seconds between retries
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session = requests.Session()
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        
        return session
        
    def get_authorization_header(self) -> str:
        """Create Base64 encoded authorization header"""
        credentials = f"{self.key}:{self.secret}"
        encoded_credentials = base64.b64encode(credentials.encode('utf-8')).decode('utf-8')
        return f"Basic {encoded_credentials}"
        
    def _is_token_valid(self) -> bool:
        """Check if current token is valid and not near expiration"""
        if not self._token or not self._token_expiry:
            return False
        return datetime.now() < self._token_expiry
        
    def get_token(self) -> Optional[Dict]:
        """Get an OAuth2 token using client credentials flow with caching"""
        try:
            # Return cached token if valid
            if self._is_token_valid():
                logger.debug("Using cached token")
                return self._token
                
            logger.info("Requesting new token")
            response = self.session.post(
                self.token_url,
                headers={
                    'Authorization': self.get_authorization_header(),
                    'Content-Type': 'application/x-www-form-urlencoded'
                },
                data={
                    'grant_type': 'client_credentials',
                    'scope': ' '.join(self.scope)
                },
                timeout=10
            )
            
            response.raise_for_status()
            token_data = response.json()
            
            # Cache token and set expiry
            self._token = token_data
            # Set expiry 5 minutes before actual expiration
            self._token_expiry = datetime.now() + timedelta(seconds=token_data['expires_in'] - 300)
            
            logger.info("Successfully obtained new token")
            return token_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error getting token: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response text: {e.response.text}")
                
            # Return cached token if available, even if expired
            if self._token:
                logger.warning("Using expired cached token due to refresh failure")
                return self._token
                
            logger.error("No cached token available")
            return None
            
    def get_valid_token(self) -> Optional[str]:
        """Get valid access token string or None"""
        token_data = self.get_token()
        if token_data and 'access_token' in token_data:
            return token_data['access_token']
        return None