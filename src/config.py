# config.py
import os
import json
import logging
from typing import Dict, List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Config:
    """Base configuration"""
    def __init__(self):
        # Flask settings
        self.FLASK_ENV = os.getenv('FLASK_ENV', 'production')
        self.PORT = int(os.getenv('PORT', 5000))
        
        # OCLC API settings
        self.OCLC_BASE_URL = os.getenv('OCLC_BASE_URL', 'https://discovery.api.oclc.org/worldcat-org-ci')
        self.OCLC_KEY = os.getenv('OCLC_KEY')
        self.OCLC_SECRET = os.getenv('OCLC_SECRET')
        
        # Results settings
        self.MAX_RESULTS_PER_PAGE = int(os.getenv('MAX_RESULTS_PER_PAGE', '50'))
        self.DEFAULT_RESULTS_PER_PAGE = int(os.getenv('DEFAULT_RESULTS_PER_PAGE', '10'))
        
        # URL Processing settings
        self._url_replace_chars = self._load_url_replace_chars()
        
        # Library settings
        self._library_mappings = self._load_library_mappings()
        self.DEFAULT_LIBRARY = os.getenv('DEFAULT_LIBRARY', 'SZH')
        
        # Site settings
        self._site_mappings = self._load_site_mappings()
        self._default_site = os.getenv('DEFAULT_SITE', 'worldcat')
        
        logger.info(f"Initialized Config with URL replace chars: {self._url_replace_chars}")
        
    def _load_url_replace_chars(self) -> List[str]:
        """Load characters to be replaced with spaces in URLs"""
        # Default characters if none specified
        default_chars = ['-', '–', '—', '―']
        
        try:
            # Get from environment variable as JSON array
            chars_str = os.getenv('URL_REPLACE_CHARS')
            if not chars_str:
                logger.info("Using default URL replace characters")
                return default_chars
                
            chars_list = json.loads(chars_str)
            if not isinstance(chars_list, list):
                logger.warning("URL_REPLACE_CHARS must be a JSON array, using defaults")
                return default_chars
                
            logger.info(f"Loaded custom URL replace characters: {chars_list}")
            return chars_list
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse URL_REPLACE_CHARS: {e}")
            return default_chars
            
    def _load_library_mappings(self) -> Dict[str, str]:
        """Load and validate library mappings from environment"""
        mappings_str = os.getenv('LIBRARY_MAPPINGS', '{}')
        try:
            mappings = json.loads(mappings_str)
            logger.info(f"Loaded raw LIBRARY_MAPPINGS: {mappings}")
            return mappings
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LIBRARY_MAPPINGS: {e}")
            return {}
            
    def _load_site_mappings(self) -> Dict[str, str]:
        """Load and validate site mappings from environment"""
        mappings_str = os.getenv('SITE_MAPPINGS', '{}')
        try:
            mappings = json.loads(mappings_str)
            logger.info(f"Loaded raw SITE_MAPPINGS: {mappings}")
            return mappings
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse SITE_MAPPINGS: {e}")
            return {}

    @property
    def URL_REPLACE_CHARS(self) -> List[str]:
        """Get characters to be replaced in URLs"""
        return self._url_replace_chars

    @property
    def LIBRARY_MAPPINGS(self) -> Dict[str, str]:
        """Get library mappings dictionary"""
        return self._library_mappings

    @property
    def SITE_MAPPINGS(self) -> Dict[str, str]:
        """Get site mappings dictionary"""
        return self._site_mappings

    @property
    def DEFAULT_SITE(self) -> str:
        """Get default discovery site"""
        return self._default_site