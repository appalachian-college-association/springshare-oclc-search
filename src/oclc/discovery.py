# discovery.py
from typing import Dict, Optional
import requests
from urllib.parse import unquote_plus
import re
import structlog
from .auth import OCLCAuth
from ..config import Config
from ..springshare.formatter import format_results

logger = structlog.get_logger()

# Initialize OCLC auth handler and config
auth_handler = OCLCAuth()
config = Config()

# Constants
MAX_QUERY_LENGTH = 500
VALID_SORT_OPTIONS = ['library', 'recency', 'bestMatch', 'creator', 
                     'publicationDateAsc', 'publicationDateDesc', 
                     'mostWidelyHeld', 'title']

def get_library_symbol(referrer: str = None) -> str:
    """Get OCLC symbol based on referrer URL"""
    try:
        if not referrer:
            return config.DEFAULT_LIBRARY
            
        for domain, symbol in config.LIBRARY_MAPPINGS.items():
            if domain.lower() in referrer.lower():
                return symbol
                
        return config.DEFAULT_LIBRARY
        
    except Exception as e:
        logger.error("library_symbol_error", error=str(e))
        return config.DEFAULT_LIBRARY
    
def sanitize_query(query: str) -> str:
    """Sanitize and normalize search query"""
    try:
        if len(query) > MAX_QUERY_LENGTH:
            query = query[:MAX_QUERY_LENGTH]
            
        query = unquote_plus(query).strip()
        query = query.replace('+', ' ')
        
        # Preserve quoted phrases
        quoted_phrases = re.findall(r'"[^"]+"', query)
        temp_query = re.sub(r'"[^"]+"', 'QUOTED_PHRASE', query)
        
        # Clean query
        temp_query = re.sub(r'[^\w\s\-\'äëïöüáéíóúàèìòùâêîôûãñõ@\./+]', ' ', temp_query)
        
        # Replace quoted phrases
        for phrase in quoted_phrases:
            temp_query = temp_query.replace('QUOTED_PHRASE', phrase, 1)
        
        # Normalize whitespace
        temp_query = ' '.join(temp_query.split())
        
        if not temp_query:
            raise ValueError("Query is empty after sanitization")
            
        return temp_query
        
    except Exception as e:
        logger.error("query_sanitization_error", error=str(e))
        raise

def validate_pagination(page: int, limit: int) -> tuple[int, int]:
    """Validate and adjust pagination parameters"""
    try:
        if not isinstance(page, int) or page < 1:
            raise ValueError("Page number must be a positive integer")
            
        if limit is None:
            limit = config.DEFAULT_RESULTS_PER_PAGE
        elif not isinstance(limit, int) or limit < 1:
            raise ValueError("Results per page must be a positive integer")
        elif limit > config.MAX_RESULTS_PER_PAGE:
            raise ValueError(f"Results per page cannot exceed {config.MAX_RESULTS_PER_PAGE}")
            
        return page, limit
        
    except (TypeError, ValueError) as e:
        logger.error("pagination_validation_error", error=str(e))
        raise

def validate_sort(sort: str) -> bool:
    """Validate sort parameter"""
    if sort and sort not in VALID_SORT_OPTIONS:
        raise ValueError(f"Invalid sort option. Must be one of: {', '.join(VALID_SORT_OPTIONS)}")
    return True

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
        
        # Build request parameters
        params = {
            "q": cleaned_query,
            "offset": offset,
            "limit": validated_limit,
            "heldBySymbol": library_symbol,
            "dbIds": "638",
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
        formatted_results = format_results(results, library_symbol)
        
        return formatted_results

    except requests.exceptions.RequestException as e:
        logger.error("search_request_failed", error=str(e))
        return {
            "error": "Search request failed",
            "total_results": 0,
            "results": []
        }
    except Exception as e:
        logger.error("search_error", error=str(e))
        return {
            "error": "An unexpected error occurred",
            "total_results": 0,
            "results": []
        }
