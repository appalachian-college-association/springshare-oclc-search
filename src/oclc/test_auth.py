# src/oclc/test_auth.py
import os
from dotenv import load_dotenv
from .auth import OCLCAuth
import json
from datetime import datetime

def test_oclc_auth():
    """
    Test OCLC authentication and token retrieval.
    Saves successful token response to a json file for inspection.
    """
    # Load environment variables
    load_dotenv()
    
    try:
        # Initialize auth handler
        auth_handler = OCLCAuth()
        
        # Attempt to get token
        token = auth_handler.get_token()

        assert token and 'access_token' in token,  "✗ Failed to retrieve valid token"
        
        print("✓ Successfully retrieved access token")
            
        # Save token details to file for inspection
        token_info = {
            "access_token": token['access_token'],
            "retrieved_at": datetime.now().isoformat(),
            "token_type": token.get('token_type', 'bearer'),
            "expires_in": token.get('expires_in', 'unknown')
        }
            
        with open('token_test_results.json', 'w') as f:
            json.dump(token_info, f, indent=2)
            print("✓ Token details saved to token_test_results.json")
                
    except Exception as e:
        assert False, f"✗ Error testing authentication: {str(e)}"

if __name__ == "__main__":
    success = test_oclc_auth()
    if success:
        print("\nAuthentication test completed successfully!")
    else:
        print("\nAuthentication test failed!")
