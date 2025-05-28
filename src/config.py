# config.py
import os
import json
import logging
from typing import Dict, List
from google.cloud import secretmanager
from functools import lru_cache

logger = logging.getLogger(__name__)

class Config:
    """Configuration management for both local and Cloud Run environments"""
    
    def __init__(self):
        # Environment & project settings
        self.ENV = os.getenv('ENV', 'production')
        self.PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT')

        # Ensure PORT is always an integer
        try:
            self.PORT = int(os.getenv('PORT', '8080'))
        except ValueError:
            self.PORT = 8080
            logger.warning("Invalid PORT value, using default 8080")

        # Load secrets first
        if self.ENV == 'production' and self.PROJECT_ID:
            self._load_secrets()
        else:
            self._load_local_secrets()

        # Load standard configuration
        self._load_configuration()

    def _load_configuration(self):
        """Load all non-secret configuration values"""
        try:
            # Results settings - strip any comments and whitespace
            max_results = os.getenv('MAX_RESULTS_PER_PAGE', '50').split('#')[0].strip()
            default_results = os.getenv('DEFAULT_RESULTS_PER_PAGE', '10').split('#')[0].strip()

            self.MAX_RESULTS_PER_PAGE = int(max_results)
            self.DEFAULT_RESULTS_PER_PAGE = int(default_results)

            logger.info(f"Results settings loaded: max={self.MAX_RESULTS_PER_PAGE}, default={self.DEFAULT_RESULTS_PER_PAGE}")

            # Default values
            self._default_library = os.getenv('DEFAULT_LIBRARY', 'SZH')
            self._default_site = os.getenv('DEFAULT_SITE', 'worldcat')
            self._oclc_base_url = os.getenv('OCLC_BASE_URL', 'https://discovery.api.oclc.org/worldcat-org-ci')

            logger.info("Default values loaded successfully")

            # Load mapping configurations
            self._url_replace_chars = self._load_json_config(
                'URL_REPLACE_CHARS',
                default=['-', '–', '—', '―']
            )
            self._library_mappings = self._load_json_config(
                'LIBRARY_MAPPINGS',
                default={}
            )
            self._site_mappings = self._load_json_config(
                'SITE_MAPPINGS',
                default={}
            )

            logger.info("Mapping configurations loaded successfully")

        except ValueError as e:
            logger.error(f"Configuration error parsing integer values: {str(e)}")
            self.MAX_RESULTS_PER_PAGE = 50
            self.DEFAULT_RESULTS_PER_PAGE = 10

        except Exception as e:
            logger.error(f"Unexpected error in configuration: {str(e)}")
            raise

    @lru_cache()
    def _get_secret(self, secret_id: str) -> str:
        """Retrieve secret from Secret Manager"""
        try:
            client = secretmanager.SecretManagerServiceClient()
            name = f"projects/{self.PROJECT_ID}/secrets/{secret_id}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("UTF-8")
        except Exception as e:
            logger.error(f"Error accessing secret {secret_id}")
            return None

    def _load_secrets(self):
        """Load secrets from Google Cloud Secret Manager"""
        self.OCLC_KEY = self._get_secret('OCLC_KEY')
        self.OCLC_SECRET = self._get_secret('OCLC_SECRET')

    def _load_local_secrets(self):
        """Load secrets from local environment"""
        self.OCLC_KEY = os.getenv('OCLC_KEY')
        self.OCLC_SECRET = os.getenv('OCLC_SECRET')

        missing = []
        if not self.OCLC_KEY:
            missing.append('OCLC_KEY')
        if not self.OCLC_SECRET:
            missing.append('OCLC_SECRET')

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")
        
        logger.info("Local secrets loaded successfully")

    def _load_json_config(self, env_var: str, default: Dict = None) -> Dict:
        """
        Load and parse JSON configuration from environment variables
        
        Args:
            env_var: Name of environment variable
            default: Default value if env var is not set or invalid
        Returns:
            Parsed configuration or default value
        """
        try:
            value = os.getenv(env_var)
            if not value:
                return default if default is not None else {}
            return json.loads(value)
        except json.JSONDecodeError as e:
            logger.warning(f"Invalid JSON in {env_var}, using default")
            return default if default is not None else {}

    # Properties
    @property
    def URL_REPLACE_CHARS(self) -> List[str]:
        return self._url_replace_chars

    @property
    def LIBRARY_MAPPINGS(self) -> Dict[str, str]:
        return self._library_mappings

    @property
    def SITE_MAPPINGS(self) -> Dict[str, str]:
        return self._site_mappings
        
    @property
    def DEFAULT_SITE(self) -> str:
        return self._default_site
        
    @property
    def DEFAULT_LIBRARY(self) -> str:
        return self._default_library
        
    @property 
    def OCLC_BASE_URL(self) -> str:
        return self._oclc_base_url