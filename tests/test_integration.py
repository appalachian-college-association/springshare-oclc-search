# tests/test_integration.py
from flask.testing import FlaskClient
import pytest
import os
from dotenv import load_dotenv

# Load environment variables before importing app
load_dotenv()

from src.app import app

@pytest.fixture
def client():
    """Create test client"""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

# In test_integration.py
def test_health_endpoint(client: FlaskClient):
    """Test health check endpoint"""
    response = client.get('/health')
    assert response.status_code == 200
    data = response.get_json()
    assert data['status'] == 'healthy'

def test_search_endpoint(client: FlaskClient):
    """Test basic search functionality"""
    response = client.get('/search?q=python&page=1&perpage=10')
    assert response.status_code == 200
    data = response.get_json()
    assert 'results' in data
    assert 'total_results' in data
    assert isinstance(data['results'], list)

def test_empty_query(client: FlaskClient):
    """Test empty query handling"""
    response = client.get('/search?q=')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_pagination_validation(client: FlaskClient):
    """Test pagination parameter validation"""
    # Test valid pagination
    response = client.get('/search?q=test&page=1&perpage=10')
    assert response.status_code == 200

    # Test invalid page number
    response = client.get('/search?q=test&page=0')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data
    assert 'page' in data['error'].lower()

    # Test invalid page format
    response = client.get('/search?q=test&page=abc')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

    # Test too large perpage
    response = client.get('/search?q=test&perpage=1000')
    assert response.status_code == 400
    data = response.get_json()
    assert 'error' in data

def test_query_sanitization(client: FlaskClient):
    """Test handling of special characters in query"""
    test_queries = [
        ('C++ programming', 200),
        ('Python & Django', 200),
        ('search/retrieve', 200), 
        ('test@example.com', 200),
        ('SELECT * FROM users', 200),  # SQL injection attempt
        ('"><script>alert(1)</script>', 200),  # XSS attempt
        ('a' * 1000, 400)  # Too long query
    ]
    
    for query, expected_status in test_queries:
        response = client.get(f'/search?q={query}')
        assert response.status_code == expected_status
        data = response.get_json()
        if expected_status == 200:
            assert 'results' in data
        else:
            assert 'error' in data

def test_response_format(client: FlaskClient):
    """Test response matches Springshare requirements"""
    response = client.get('/search?q=python')
    assert response.status_code == 200
    data = response.get_json()
    
    # Required fields
    assert 'total_results' in data
    assert 'results' in data
    assert isinstance(data['results'], list)
    assert 'perpage' in data
    
    # Optional fields
    if 'sort' in data:
        assert 'field' in data['sort']
        assert 'dir' in data['sort']
    
    # Result format
    if data['results']:
        result = data['results'][0]
        assert 'url' in result
        assert 'title' in result

def test_library_handling(client: FlaskClient):
    """Test library symbol handling"""
    # Test with no referrer
    response = client.get('/search?q=test')
    assert response.status_code == 200
    
    # Test with mapped referrer
    headers = {'Referer': 'https://libguides.johnsonu.edu/somelib'}
    response = client.get('/search?q=test', headers=headers)
    assert response.status_code == 200
    
    # Test with unmapped referrer
    headers = {'Referer': 'https://unknown.edu/lib'}
    response = client.get('/search?q=test', headers=headers)
    assert response.status_code == 200

def test_error_handling(client: FlaskClient):
    """Test error handling scenarios"""
    # Test malformed request
    response = client.get('/search')
    assert response.status_code == 400
    
    # Test invalid parameters
    response = client.get('/search?q=test&page=-1')
    assert response.status_code == 400
    
    # Test with invalid sort
    response = client.get('/search?q=test&sort=invalid')
    assert response.status_code == 400

def test_url_character_replacement():
    """Test URL character replacement with config"""
    from src.config import Config
    from src.springshare.formatter import process_title_for_url
    
    # Test with default config
    config = Config()
    assert process_title_for_url("Book - With Dash", config) == "Book With Dash"
    
    # Test with custom config
    os.environ['URL_REPLACE_CHARS'] = '["+", "@"]'
    config = Config()
    #assert process_title_for_url("Book & Records", config) == "Book Records"
    assert process_title_for_url("Data + Analysis", config) == "Data Analysis"

def test_long_title_processing():
    """Test URL processing of long titles"""
    from src.config import Config
    from src.springshare.formatter import process_title_for_url
    import logging

    # Set up logging to see the values
    logging.basicConfig(level=logging.DEBUG)
    logger = logging.getLogger(__name__)
    
    config = Config()
    
    # Test with title longer than 20 words
    long_title = "Homeric Vocabularies Greek and English Word Lists for the Study of Homer By William Bishop Owen Ph.D. and Edgar Johnson Goodspeed Ph.D. Chicago The University of Chicago Press 1906 Pp viii 62 50 cents net"
    processed = process_title_for_url(long_title, config)

    # Log the original and processed values
    logger.debug(f"Original title: {long_title}")
    logger.debug(f"Processed title: {processed}")
    
    # Count words in processed title
    word_count = len(processed.split())
    logger.debug(f"Word count: {word_count}")
    
    # Get the first 20 words of original and processed
    original_words = long_title.split()[:20]
    processed_words = processed.split()
    
    logger.debug(f"Original first 20 words: {original_words}")
    logger.debug(f"Processed words: {processed_words}")

    assert word_count <= 20, f"Processed title has {word_count} words, expected 20 or fewer"
    
    # Compare word by word
    for i, (orig, proc) in enumerate(zip(original_words, processed_words)):
        assert orig == proc, f"Mismatch at word {i}: expected '{orig}' but got '{proc}'"