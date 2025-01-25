# tests/conftest.py
import pytest
import os
from dotenv import load_dotenv

@pytest.fixture(autouse=True)
def load_env():
    """Load environment variables before each test"""
    load_dotenv()
    
    # Verify required env vars
    assert 'OCLC_KEY' in os.environ, "OCLC_KEY not found in environment"
    assert 'OCLC_SECRET' in os.environ, "OCLC_SECRET not found in environment"