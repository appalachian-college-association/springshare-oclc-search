# Save this as test_search.py
import os
from dotenv import load_dotenv

# Load environment variables before importing the search function
load_dotenv()

# Add debug print to verify env vars are loaded
print(f"OCLC_KEY present: {'OCLC_KEY' in os.environ}")
print(f"OCLC_SECRET present: {'OCLC_SECRET' in os.environ}")

from src.oclc.discovery import search_worldcat

def test_direct_search():
    try:
        result = search_worldcat("python", 1, 10)
        print("Search Results:", result)
    except Exception as e:
        print(f"Error during search: {str(e)}")

if __name__ == "__main__":
    test_direct_search()