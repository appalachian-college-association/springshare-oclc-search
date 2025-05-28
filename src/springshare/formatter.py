from typing import Dict, List, Optional
from urllib.parse import quote
import logging
import re
from ..config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def process_title_for_url(title: str, config: Config) -> str:
    """
    Process title for URL construction:
    1. Replace configured characters with spaces
    2. Collapse multiple spaces into single spaces
    3. Strip leading/trailing whitespace
    4. Limit to first 20 words
    
    Args:
        title: Original title string
        config: Config object containing URL processing settings
    Returns:
        Processed title string suitable for URL construction
    """
    logger.debug(f"Input title: {title}")

    if not title:
        return ""
        
    # Get characters to replace from config
    replace_chars = config.URL_REPLACE_CHARS
    logger.debug(f"Characters to replace: {replace_chars}")
    
    # Replace configured characters with space
    processed_title = title
    for char in replace_chars:
        if char in processed_title:
            logger.debug(f"Replacing '{char}' with space")
            processed_title = processed_title.replace(char, ' ')
    
    logger.debug(f"After character replacement: {processed_title}")
        
    # Collapse multiple spaces and strip
    processed_title = ' '.join(processed_title.split())
    logger.debug(f"After space normalization: {processed_title}")
    
    # Limit to first 20 words by splitting on spaces and joining first 20
    words = processed_title.split()
    if len(words) > 20:
        logger.debug(f"Title has {len(words)} words, truncating to 20")
        processed_title = ' '.join(words[:20])
        logger.debug(f"After truncation: {processed_title}")
    
    return processed_title

def get_discovery_site(library_symbol: str, config: Config) -> str:
    """Get discovery site name for library symbol"""
    if not library_symbol:
        logger.warning("No library symbol provided, using default site")
        return config.DEFAULT_SITE
        
    site = config.SITE_MAPPINGS.get(library_symbol)
    logger.info(f"Mapping library symbol '{library_symbol}' to site: {site or config.DEFAULT_SITE}")
    
    if not site:
        logger.warning(f"No site mapping found for symbol '{library_symbol}', using default site")
        return config.DEFAULT_SITE
        
    return site

def get_identifier(item: Dict) -> Optional[str]:
    """
    Get ISBN or ISSN from item, preferring ISBN
    """
    # Try to get ISBNs first
    isbns = item.get('isbns', [])
    if isbns and len(isbns) > 0:
        return isbns[0]  # Return first ISBN
        
    # Fall back to ISSN if no ISBN
    issns = item.get('issns', [])
    if issns and len(issns) > 0:
        return issns[0]  # Return first ISSN
        
    return None

def format_worldcat_url(title: str, site: str, config: Config) -> str:
    """
    Format WorldCat URL with encoded processed title.
    Original title is preserved in the response JSON.
    
    Args:
        title: Original title string
        site: Discovery site name
        config: Config object containing URL processing settings
    Returns:
        Formatted WorldCat URL string
    """
    processed_title = process_title_for_url(title, config)
    encoded_title = quote(f'ti:{processed_title}')
    url = f"https://{site}.on.worldcat.org/search?queryString={encoded_title}"
    logger.debug(f"Formatted URL: {url}")
    return url

def format_results(results: Dict, library_symbol: str = None) -> Dict:
    """
    Format OCLC API response into Springshare-compatible format
    Args:
        results: Raw JSON response from OCLC API
        library_symbol: OCLC symbol for the library
     Returns:
        Dict containing formatted search results matching Springshare requirements
    """
    try:
        config = Config()
        total_results = results.get('numberOfRecords', 0)
        items = results.get('briefRecords', [])
        limit = min(len(items), config.DEFAULT_RESULTS_PER_PAGE)

        # Get discovery site for URL formatting
        site = get_discovery_site(library_symbol, config)

        formatted_response = {
            "total_results": total_results,
            "perpage": limit,
            "sort": {
                "field": "relevancy",
                "dir": "desc"
            },
            "sort_options": [
                {
                    "field": "relevancy",
                    "dir": "desc",
                    "label": "Most Relevant"
                },
                {
                    "field": "title",
                    "dir": "asc", 
                    "label": "Title A-Z"
                }
            ],
            "results": []
        }

        for item in items[:limit]:
            identifier = get_identifier(item)
            title = item.get('title', '')
            oclc_number = item.get('oclcNumber', '')
            
            formatted_item = {
                "title": title,
                "ocn": oclc_number,
                "url": format_worldcat_url(title, site, config),
                "author": item.get('creator', ''),
                "date": item.get('date', ''),
                "publisher": item.get('publisher', ''),
                "identifier": identifier if identifier else '',
                "format": item.get('generalFormat', '')
            }
            formatted_response["results"].append(formatted_item)

        return formatted_response

    except Exception as e:
        logger.error(f"Error formatting results: {str(e)}", exc_info=True)
        return {
            "total_results": 0,
            "perpage": config.DEFAULT_RESULTS_PER_PAGE,
            "results": []
        }