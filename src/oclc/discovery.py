# discovery.py
from typing import Dict, Optional
import requests
from urllib.parse import unquote_plus
import re
import structlog
import time
from .auth import OCLCAuth
from ..config import Config
from ..springshare.formatter import format_results
from requests.exceptions import Timeout, RequestException

logger = structlog.get_logger()

# Initialize OCLC auth handler and config
auth_handler = OCLCAuth()
config = Config()

# Constants
MAX_QUERY_LENGTH = 500
VALID_SORT_OPTIONS = ['library', 'recency', 'bestMatch', 'creator', 
                     'publicationDateAsc', 'publicationDateDesc', 
                     'mostWidelyHeld', 'title']

def map_springshare_sort(sort_param: Optional[str]) -> Optional[str]:
    """
    Map Springshare sort parameter to OCLC format
    
    Args:
        sort_param: Sort parameter from Springshare (e.g. 'relevancy_desc')
        
    Returns:
        Mapped OCLC sort parameter or None for default
        
    Raises:
        ValueError: If sort parameter is invalid
    """
    if not sort_param or sort_param == '_':
        return 'bestMatch'  # Default sort
    
    # Handle Springshare's relevancy_desc format
    if sort_param == 'relevancy_desc':
        return 'bestMatch'
        
    # Split into field and direction
    try:
        field, direction = sort_param.split('_')
    except ValueError:
        raise ValueError(f"Invalid sort format: {sort_param}")
        
    # Define complete mapping of Springshare to OCLC sort options
    sort_mappings = {
        'relevancy': {
            'desc': 'bestMatch'  # Only desc is valid for relevancy
        },
        'title': {
            'asc': 'title',
            'desc': 'title desc'
        },
        'date': {
            'asc': 'publicationDateAsc',
            'desc': 'publicationDateDesc'
        },
        'library': {
            'asc': 'library'  # Only asc is valid for library
        },
        'creator': {
            'asc': 'creator'  # Only asc is valid for creator
        },
        'popularity': {
            'desc': 'mostWidelyHeld'  # Only desc is valid for popularity
        }
    }
    
    # Validate field exists in mappings
    if field not in sort_mappings:
        raise ValueError(
            f"Invalid sort field '{field}'. Valid options: {', '.join(sort_mappings.keys())}")
            
    # Validate direction exists for field
    if direction not in sort_mappings[field]:
        valid_dirs = list(sort_mappings[field].keys())
        raise ValueError(
            f"Invalid direction '{direction}' for field '{field}'. Valid directions: {', '.join(valid_dirs)}")
            
    return sort_mappings[field][direction]

def get_library_symbol(referrer: str = None, timeout: int =5) -> str:
    """Get OCLC symbol based on referrer URL"""
    try:
        if not referrer:
            return config.DEFAULT_LIBRARY

        start_time = time.time()    
        for domain, symbol in config.LIBRARY_MAPPINGS.items():
            if time.time() - start_time > timeout:
                logger.warning("library_symbol_lookup_timeout")
                return config.DEFAULT_LIBRARY
            
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
            raise ValueError(f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters")
                        
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
    """
    Validate and adjust pagination parameters
    
    Args:
        page: Requested page number (1-based)
        limit: Number of results per page
        
    Returns:
        Tuple of (validated_page, validated_limit)
        
    Raises:
        ValueError: If parameters are invalid
    """
    try:
        # Convert to int if string
        try:
            page = int(page)
            if limit is not None:
                limit = int(limit)
        except (TypeError, ValueError):
            raise ValueError("Page and limit must be valid integers")

        # Validate page
        if page < 1:
            raise ValueError("Page number must be greater than 0")
            
        # Set and validate limit
        if limit is None:
            limit = config.DEFAULT_RESULTS_PER_PAGE
        elif limit < 1:
            raise ValueError("Results per page must be greater than 0")
        elif limit > config.MAX_RESULTS_PER_PAGE:
            raise ValueError(f"Results per page cannot exceed {config.MAX_RESULTS_PER_PAGE}")
            
        # Validate maximum offset
        max_offset = 10000  # OCLC's maximum offset
        calculated_offset = ((page - 1) * limit) + 1
        if calculated_offset > max_offset:
            raise ValueError(f"Requested page exceeds maximum offset of {max_offset}")
            
        return page, limit
        
    except (TypeError, ValueError) as e:
        logger.error("pagination_validation_error", error=str(e))
        raise

def calculate_offset(page: int, limit: int) -> int:
    """
    Calculate offset for OCLC API pagination
    
    Args:
        page: Validated page number
        limit: Validated results per page
        
    Returns:
        Calculated offset for OCLC API
    """
    return ((page - 1) * limit) + 1

def validate_sort(sort: str) -> bool:
    """Validate sort parameter"""
    try:
        mapped_sort = map_springshare_sort(sort)
        if mapped_sort and mapped_sort not in VALID_SORT_OPTIONS:
            raise ValueError(
                f"Invalid sort option. Must be one of: {', '.join(VALID_SORT_OPTIONS)}")
        return True
    except ValueError as e:
        raise ValueError(str(e))

def search_worldcat(query: str, page: int = 1, limit: int = None, referrer: str = None, sort: str = None) -> tuple[Dict, int]:
    """Search WorldCat using OCLC Discovery API"""
    try:
        # Input validation
        if not query or not query.strip():
            return {
                "error": "Search query cannot be empty",
                "total_results": 0,
                "results": []
            }, 400
  
        # Validate sort if provided
        try:
            if sort:
                validate_sort(sort)
        except ValueError as e:
            return {
                "error": str(e),
                "total_results": 0,
                "results": []
            }, 400
            
        # Sanitize query
        try:
            cleaned_query = sanitize_query(query)
        except ValueError as e:
            return {
                "error": str(e),
                "total_results": 0,
                "results": []
            }, 400
            
        # Validate pagination
        try:
            validated_page, validated_limit = validate_pagination(page, limit)
            offset = calculate_offset(validated_page, validated_limit)
        except ValueError as e:
            return {
                "error": str(e),
                "total_results": 0,
                "results": []
            }, 400
            
        # Calculate offset
        offset = ((validated_page - 1) * validated_limit) + 1
        
        # Get access token
        access_token = auth_handler.get_valid_token()
        if not access_token:
            return {
                "error": "Authentication failed",
                "total_results": 0,
                "results": []
            }, 401
            
        # Get library symbol
        library_symbol = get_library_symbol(referrer)
        
        # Map Springshare sort to OCLC format
        mapped_sort = map_springshare_sort(sort) if sort else None

        # Build request parameters        
        params = {
            "q": cleaned_query,
            "offset": offset,
            "limit": validated_limit,
            "heldBySymbol": library_symbol,
            "dbIds": "638",
            "orderBy": mapped_sort if mapped_sort else "bestMatch"
        }

        # Log pagination details for debugging
        logger.debug("pagination_details", 
                    page=validated_page,
                    limit=validated_limit,
                    offset=offset)
        
        # Make request with explicit timeout
        try:
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

        except Timeout:
            logger.error("request_timeout")
            return {
                "error": "Request timed out",
                "total_results": 0,
                "results": []
            }, 503
        
        except RequestException as e:
            logger.error("request_failed", error=str(e))
            return {
                "error": f"Request failed: {str(e)}",
                "total_results": 0,
                "results": []
            }, 503
        
        # Format results
        results = response.json()
        formatted_results = format_results(results, library_symbol)
        
        return formatted_results, 200

    except requests.exceptions.RequestException as e:
        logger.error("search_request_failed", error=str(e))
        return {
            "error": "Search request failed",
            "total_results": 0,
            "results": []
        }, 503

    except Exception as e:
        logger.error("search_error", error=str(e))
        return {
            "error": "An unexpected error occurred",
            "total_results": 0,
            "results": []
        }, 500
