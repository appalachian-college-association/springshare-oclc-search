# tests/conftest.py - Simplified for cross-platform compatibility
import os
from dotenv import load_dotenv
import pytest

# Load environment variables first
load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '.env'))

def pytest_configure(config):
    """Configure pytest markers and settings"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires real API credentials)"
    )

def pytest_collection_modifyitems(config, items):
    """Modify test collection to handle integration tests"""
    # Skip integration tests by default unless explicitly requested
    if not config.getoption("--run-integration"):
        skip_integration = pytest.mark.skip(reason="Integration tests skipped (use --run-integration to run)")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)

def pytest_addoption(parser):
    """Add custom command line options"""
    parser.addoption(
        "--run-integration",
        action="store_true", 
        default=False,
        help="Run integration tests that require real API calls"
    )

def pytest_sessionstart(session):
    """Verify test environment setup"""
    required_vars = ['OCLC_KEY', 'OCLC_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        pytest.exit(f"Missing required environment variables: {', '.join(missing_vars)}")

@pytest.fixture
def app():
    """Create application instance for testing"""
    from src.app import app
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    return app

@pytest.fixture
def client(app):
    """Create test client"""
    return app.test_client()