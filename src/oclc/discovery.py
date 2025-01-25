# discovery.py
import logging
from typing import Dict, Optional
import requests
from urllib.parse import quote, unquote_plus
import re
from src.oclc.auth import OCLCAuth
from ..config import Config
from ..springshare.formatter import format_results

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize OCLC auth handler and config
auth_handler = OCLCAuth()
config = Config()

# Constants
MAX_QUERY_LENGTH = 500  # Maximum length for search queries
VALID_SORT_OPTIONS = ['library', 'recency', 'bestMatch', 'creator', 
                     'publicationDateAsc', 'publicationDateDesc', 
                     'mostWidelyHeld', 'title']

# In discovery.py, update the get_library_symbol function:

def get_library_symbol(referrer: str = None) -> str:
    """Get OCLC symbol based on referrer URL"""
    try:
        config = Config()
        
        if not referrer:
            logger.info(f"No referrer provided - using default library symbol: {config.DEFAULT_LIBRARY}")
            return config.DEFAULT_LIBRARY
            
        logger.info(f"Checking mappings for referrer: {referrer}")
        
        # Check each domain in library mappings
        for domain, symbol in config.LIBRARY_MAPPINGS.items():
            if domain.lower() in referrer.lower():
                logger.info(f"✓ Found matching library symbol: {symbol} for domain: {domain}")
                return symbol
                
        logger.info(f"No matching domain found - using default library: {config.DEFAULT_LIBRARY}")
        return config.DEFAULT_LIBRARY
        
    except Exception as e:
        logger.error(f"Error getting library symbol: {str(e)}")
        return config.DEFAULT_LIBRARY
    
def sanitize_query(query: str) -> str:
    """
    Sanitize and normalize the search query.
    - Enforces character limits
    - Normalizes whitespace
    - Preserves quoted phrases
    - Removes unsafe characters
    
    Args:
        query: Raw search query string
    Returns:
        Sanitized query string
    Raises:
        ValueError: If query is empty or too long after sanitization
    """
    try:
        # Check raw query length - OCLC has a general limit around 500 chars
        MAX_QUERY_LENGTH = 500  # OCLC API limit
        MAX_QUERY_WORDS = 20   # OCLC title query word limit
        
        if len(query) > MAX_QUERY_LENGTH:
            logger.warning(f"Query exceeds {MAX_QUERY_LENGTH} characters, will be truncated")
            query = query[:MAX_QUERY_LENGTH]
            
        # URL decode and strip
        query = unquote_plus(query)
        query = query.strip()
        
        # Convert + to space
        query = query.replace('+', ' ')
        
        # Preserve quoted phrases
        quoted_phrases = re.findall(r'"[^"]+"', query)
        temp_query = re.sub(r'"[^"]+"', 'QUOTED_PHRASE', query)
        
        # Clean query while preserving some special characters
        temp_query = re.sub(r'[^\w\s\-\'äëïöüáéíóúàèìòùâêîôûãñõ@\./+]', ' ', temp_query)
        
        # Replace quoted phrases
        for phrase in quoted_phrases:
            temp_query = temp_query.replace('QUOTED_PHRASE', phrase, 1)
        
        # Normalize whitespace
        temp_query = ' '.join(temp_query.split())
        
        # Limit number of words
        words = temp_query.split()
        if len(words) > MAX_QUERY_WORDS:
            logger.warning(f"Query exceeds {MAX_QUERY_WORDS} words, truncating")
            temp_query = ' '.join(words[:MAX_QUERY_WORDS])
        
        if not temp_query:
            raise ValueError("Query is empty after sanitization")
            
        logger.debug(f"Sanitized query: '{temp_query}'")
        return temp_query
        
    except Exception as e:
        logger.error(f"Error sanitizing query: {str(e)}")
        raise
def validate_pagination(page: int, limit: int) -> tuple[int, int]:
    """Validate and adjust pagination parameters"""
    try:
        # Validate page number
        if not isinstance(page, int) or page < 1:
            raise ValueError("Page number must be a positive integer")
            
        # Validate and adjust limit
        if limit is None:
            limit = config.DEFAULT_RESULTS_PER_PAGE
        elif not isinstance(limit, int) or limit < 1:
            raise ValueError("Results per page must be a positive integer")
        elif limit > config.MAX_RESULTS_PER_PAGE:
            raise ValueError(f"Results per page cannot exceed {config.MAX_RESULTS_PER_PAGE}")
            
        return page, limit
        
    except (TypeError, ValueError) as e:
        logger.error(f"Pagination validation error: {str(e)}")
        raise

def validate_sort(sort: str) -> bool:
    """Validate sort parameter"""
    if sort and sort not in VALID_SORT_OPTIONS:
        raise ValueError(f"Invalid sort option. Must be one of: {', '.join(VALID_SORT_OPTIONS)}")
    return True

# discovery.py - updated search_worldcat function

def search_worldcat(query: str, page: int = 1, limit: int = None, referrer: str = None, sort: str = None) -> Dict:
    """Search WorldCat using OCLC Discovery API"""
    try:
        # Input validation
        if not query or not query.strip():
            return {
                "error": "Search query cannot be empty",
                "total_results": 0,
                "results": []
            }
            
        # Validate sort if provided
        if sort:
            validate_sort(sort)
            
        # Sanitize query
        try:
            cleaned_query = sanitize_query(query)
        except ValueError as e:
            return {
                "error": str(e),
                "total_results": 0,
                "results": []
            }
            
        # Validate pagination
        try:
            validated_page, validated_limit = validate_pagination(page, limit)
        except ValueError as e:
            return {
                "error": str(e),
                "total_results": 0,
                "results": []
            }
            
        # Calculate offset
        offset = ((validated_page - 1) * validated_limit) + 1
        
        # Get access token
        access_token = auth_handler.get_valid_token()
        if not access_token:
            return {
                "error": "Authentication failed",
                "total_results": 0,
                "results": []
            }
            
        # Get library symbol
        library_symbol = get_library_symbol(referrer)
        logger.info(f"Using library symbol: {library_symbol}")
        
        # Build request parameters
        params = {
            "q": cleaned_query,
            "offset": offset,
            "limit": validated_limit,
            "heldBySymbol": library_symbol,
            "dbIds":"638",
            "orderBy": sort if sort else "bestMatch"
        }
        
        # Make request
        response = auth_handler.session.get(
            f"{config.OCLC_BASE_URL}/search/brief-bibs",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json"
            },
            params=params,
            timeout=30
        )
        
        response.raise_for_status()
        
        # Format results
        results = response.json()
        formatted_results = format_results(results, library_symbol)  # Pass library_symbol here
        
        # Add debug info
        formatted_results['debug_info'] = {
            'library_symbol': library_symbol,
            'referrer': referrer,
            'raw_params': params
        }
        
        return formatted_results

    except requests.exceptions.RequestException as e:
        logger.error("Search request failed: %s", str(e))
        return {
            "error": "Search request failed",
            "total_results": 0,
            "results": []
        }
    except Exception as e:
        logger.error("Unexpected error: %s", str(e))
        return {
            "error": "An unexpected error occurred",
            "total_results": 0,
            "results": []
        }