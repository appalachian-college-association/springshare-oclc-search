# tests/test_main.py - Consolidated test suite
import pytest
import requests
import json
import os
from dotenv import load_dotenv
from flask.testing import FlaskClient
from urllib.parse import urlencode
from unittest.mock import patch
import requests_mock

# Load environment variables
load_dotenv()

# Import after loading env vars
from src.oclc.discovery import search_worldcat, config
from src.app import app

@pytest.fixture
def client():
    """Create a test client for Flask."""
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client

@pytest.fixture
def mock_oclc_success():
    """Mock successful OCLC API responses"""
    with requests_mock.Mocker() as m:
        # Mock token endpoint
        m.post('https://oauth.oclc.org/token', json={
            'access_token': 'test-token',
            'expires_in': 3600,
            'token_type': 'bearer'
        })
        
        # Mock search endpoint
        m.get(
            f"{config.OCLC_BASE_URL}/search/brief-bibs",
            json={
                "numberOfRecords": 2,
                "briefRecords": [
                    {
                        "title": "Python Programming",
                        "oclcNumber": "123456", 
                        "creator": "Test Author",
                        "date": "2024",
                        "generalFormat": "Book",
                        "publisher": "Test Publisher",
                        "isbns": ["9781234567890"]
                    }
                ]
            }
        )
        yield m

# =============================================================================
# UNIT TESTS - Fast tests with mocked dependencies
# =============================================================================

class TestAuthentication:
    """Test authentication functionality"""
    
    def test_token_retrieval(self, mock_oclc_success):
        """Test successful token retrieval"""
        from src.oclc.auth import OCLCAuth
        auth = OCLCAuth()
        token = auth.get_valid_token()
        assert token == 'test-token'

class TestSearchValidation:
    """Test search parameter validation"""
    
    @pytest.mark.parametrize("query,expected_status", [
        ("", 400),  # Empty query
        ("python", 200),  # Valid query
        ("a" * 501, 400),  # Too long query
    ])
    def test_query_validation(self, client, mock_oclc_success, query, expected_status):
        """Test query validation"""
        response = client.get(f'/search?q={query}')
        assert response.status_code == expected_status

    @pytest.mark.parametrize("page,perpage,expected_status", [
        (1, 10, 200),  # Valid pagination
        (0, 10, 400),  # Invalid page
        (1, 0, 400),   # Invalid perpage
        (1, 100, 400), # Perpage too large
    ])
    def test_pagination_validation(self, client, mock_oclc_success, page, perpage, expected_status):
        """Test pagination parameter validation"""
        response = client.get(f'/search?q=test&page={page}&perpage={perpage}')
        assert response.status_code == expected_status

    @pytest.mark.parametrize("sort,expected_status", [
        ("relevancy_desc", 200),  # Valid sort
        ("title_asc", 200),       # Valid sort
        ("invalid_sort", 400),    # Invalid sort
    ])
    def test_sort_validation(self, client, mock_oclc_success, sort, expected_status):
        """Test sort parameter validation"""
        response = client.get(f'/search?q=test&sort={sort}')
        assert response.status_code == expected_status

class TestResponseFormat:
    """Test response formatting"""
    
    def test_json_response_format(self, client, mock_oclc_success):
        """Test JSON response format"""
        response = client.get('/search?q=python')
        assert response.status_code == 200
        data = response.get_json()
        
        # Required fields
        required_fields = ['total_results', 'results', 'perpage', 'sort', 'sort_options']
        for field in required_fields:
            assert field in data
        
        # Result format
        if data['results']:
            result = data['results'][0]
            required_result_fields = ['title', 'url', 'author', 'date', 'format']
            for field in required_result_fields:
                assert field in result

    @pytest.mark.parametrize("callback", [
        "validCallback123", 
        "cb_with_underscores", 
        "longCallbackName12345"
    ])
    def test_jsonp_response(self, client, mock_oclc_success, callback):
        """Test JSONP response format"""
        response = client.get(f'/search?q=python&callback={callback}')
        assert response.status_code == 200
        assert response.headers['content-type'] == 'application/javascript; charset=utf-8'
        
        # Check JSONP format
        response_text = response.get_data(as_text=True)
        assert response_text.startswith(f'{callback}(')
        assert response_text.endswith(')')

class TestErrorHandling:
    """Test error handling scenarios"""
    
    def test_api_timeout(self, client):
        """Test API timeout handling"""
        with patch('src.oclc.discovery.auth_handler.session.get', 
                  side_effect=requests.exceptions.Timeout):
            response = client.get('/search?q=python')
            assert response.status_code == 503
            data = response.get_json()
            assert 'error' in data
            assert 'timed out' in data['error'].lower()

    def test_authentication_failure(self, client):
        """Test authentication failure handling"""
        with patch('src.oclc.auth.OCLCAuth.get_valid_token', return_value=None):
            response = client.get('/search?q=python')
            assert response.status_code == 401
            data = response.get_json()
            assert 'error' in data
            assert 'authentication' in data['error'].lower()

class TestQuerySanitization:
    """Test query sanitization"""
    
    @pytest.mark.parametrize("malicious_query", [
        "<script>alert('xss')</script>",
        "SELECT * FROM users",
        "' OR 1=1 --"
    ])
    def test_malicious_query_handling(self, client, mock_oclc_success, malicious_query):
        """Test handling of potentially malicious queries"""
        response = client.get(f'/search?q={malicious_query}')
        # Should either sanitize and return results or return error
        assert response.status_code in [200, 400, 403, 503]

# =============================================================================
# INTEGRATION TESTS - Tests with real API calls (marked for optional execution)
# =============================================================================

@pytest.mark.integration
class TestRealAPIIntegration:
    """Integration tests with real OCLC API - only run when explicitly requested"""
    
    def test_real_search_safe_output(self):
        """Test real API search with safe output (no Unicode printing)"""
        try:
            result, status_code = search_worldcat("python", 1, 5)
            
            # Test structure without printing full response
            assert isinstance(result, dict)
            assert 'results' in result
            assert 'total_results' in result
            assert status_code == 200
            
            # Safe logging of basic info
            print(f"[OK] Search successful: {result['total_results']} results found")
            print(f"[OK] Returned {len(result['results'])} items")
            
        except Exception as e:
            pytest.fail(f"Real API test failed: {str(e)}")

    def test_real_authentication(self):
        """Test real authentication"""
        try:
            from src.oclc.auth import OCLCAuth
            auth = OCLCAuth()
            token = auth.get_valid_token()
            
            assert token is not None
            assert len(token) > 10  # Basic token validation
            print("[OK] Authentication successful")
            
        except Exception as e:
            pytest.fail(f"Authentication test failed: {str(e)}")

# =============================================================================
# CONFIGURATION TESTS
# =============================================================================

class TestConfiguration:
    """Test configuration handling"""
    
    def test_url_character_replacement(self):
        """Test URL character replacement"""
        from src.config import Config
        from src.springshare.formatter import process_title_for_url
        
        config = Config()
        
        # Test basic replacement
        result = process_title_for_url("Book - With Dash", config)
        assert result == "Book With Dash"
        
        # Test word limit
        long_title = " ".join([f"word{i}" for i in range(25)])
        result = process_title_for_url(long_title, config)
        assert len(result.split()) <= 20

    def test_library_symbol_mapping(self):
        """Test library symbol mapping"""
        from src.oclc.discovery import get_library_symbol
        
        # Test with mapped referrer
        symbol = get_library_symbol("https://libguides.johnsonu.edu/test")
        assert symbol == "SZH"  # Based on your config
        
        # Test with unmapped referrer
        symbol = get_library_symbol("https://unknown.edu/test")
        assert symbol == "SZH"  # Should use default

# =============================================================================
# HEALTH CHECK TESTS
# =============================================================================

class TestHealthCheck:
    """Test application health endpoints"""
    
    def test_health_endpoint(self, client):
        """Test health check endpoint"""
        response = client.get('/health')
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get('/')
        assert response.status_code == 200
        data = response.get_json()
        assert 'message' in data