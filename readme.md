# OCLC Discovery API Integration for LibGuides

A Flask application that enables library catalog searching in LibGuides using OCLC's Discovery API.

## Features
- Real-time catalog searching within LibGuides
- Multi-library support with configurable mappings
- Token-based authentication with OCLC APIs
- Configurable results formatting

## Requirements
- Python 3.11+
- OCLC Discovery API credentials
- Environment variables configured per sample.env
- Client system capable of:
  - Making JSONP requests with callback parameter
  - Handling JSON responses with:
    - total_results count
    - perpage value
    - results array containing formatted citations
    - sort options

## Setup
1. Clone repository
2. Create .env file from sample.env
3. Install dependencies: `pip install -r requirements.txt`
4. Run tests: `pytest`
5. Start server: `flask run`

## Configuration
Set environment variables in .env:
- OCLC API credentials
- Library mappings
- Discovery site settings

## Usage
The application exposes a search endpoint that accepts requests and returns formatted results from OCLC's Discovery API. See API_DOCUMENTATION.md for detailed endpoint specifications and example requests/responses.

## License
MIT - See LICENSE file