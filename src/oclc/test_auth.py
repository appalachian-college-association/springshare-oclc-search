# src/oclc/test_auth.py
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import json
from datetime import datetime

def test_oclc_auth():
    """
    Test OCLC authentication and token retrieval.
    Saves successful token response to a json file for inspection.
    
    This function uses pytest assertions and returns None for compatibility.
    """
    # Get the project root directory (3 levels up from this file)
    current_file = Path(__file__).resolve()
    project_root = current_file.parent.parent.parent
    
    # Add project root to Python path
    if str(project_root) not in sys.path:
        sys.path.insert(0, str(project_root))
    
    # Load environment variables from project root
    env_file = project_root / '.env'
    if env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()  # Try to load from current directory
    
    # Assert environment variables exist
    oclc_key = os.getenv('OCLC_KEY')
    oclc_secret = os.getenv('OCLC_SECRET')
    
    assert oclc_key is not None, "OCLC_KEY not found in environment variables"
    assert oclc_secret is not None, "OCLC_SECRET not found in environment variables"
    
    # Import and initialize auth handler
    from src.oclc.auth import OCLCAuth
    
    auth_handler = OCLCAuth()
    assert auth_handler is not None, "Failed to initialize OCLCAuth handler"
    
    # Test the authorization header creation
    auth_header = auth_handler.get_authorization_header()
    assert auth_header.startswith("Basic "), "Authorization header should start with 'Basic '"
    
    # Attempt to get token
    token = auth_handler.get_token()
    
    # Assert token is valid
    assert token is not None, "No token returned from OCLC"
    assert 'access_token' in token, "Token response missing access_token"
    assert token['access_token'], "Access token is empty"
    assert 'token_type' in token, "Token response missing token_type"
    assert 'expires_in' in token, "Token response missing expires_in"
    
    # Test the get_valid_token method
    valid_token = auth_handler.get_valid_token()
    assert valid_token is not None, "get_valid_token() returned None"
    assert isinstance(valid_token, str), "Valid token should be a string"
    assert len(valid_token) > 0, "Valid token should not be empty"
    
    # Save token details to file for inspection (in project root)
    token_info = {
        "access_token_preview": token['access_token'][:20] + "..." if len(token['access_token']) > 20 else token['access_token'],
        "retrieved_at": datetime.now().isoformat(),
        "token_type": token.get('token_type', 'bearer'),
        "expires_in": token.get('expires_in', 'unknown'),
        "scope": token.get('scope', 'unknown'),
        "test_status": "PASSED"
    }
        
    output_file = project_root / 'token_test_results.json'
    with open(output_file, 'w') as f:
        json.dump(token_info, f, indent=2)
    
    # If we get here, all assertions passed - the test succeeded
    # No return statement needed for pytest

def main():
    """
    Main function for running the test directly (not through pytest)
    This preserves the original behavior when running the file directly
    """
    print("🔐 Testing OCLC Authentication...")
    print("=" * 50)
    
    try:
        test_oclc_auth()
        print("✅ Authentication test completed successfully!")
        success = True
    except AssertionError as e:
        print(f"❌ Test assertion failed: {e}")
        success = False
    except Exception as e:
        print(f"❌ Error testing authentication: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        success = False
    
    print("=" * 50)
    if success:
        print("✅ All checks passed!")
    else:
        print("❌ Test failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    print("\nPress Enter to exit...")
    input()