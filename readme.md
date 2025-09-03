# OCLC Discovery API Integration for LibGuides

A Flask application that enables library catalog searching within LibGuides using OCLC's Discovery API.

## Features

- **Real-time catalog searching** within LibGuides interface
- **Multi-library support** with configurable library mappings
- **Token-based authentication** with OCLC Discovery APIs
- **Configurable results formatting** to match LibGuides presentation
- **JSONP support** for cross-origin requests

## Requirements

- Python 3.11+
- OCLC Discovery API credentials
- Environment variables configured (see `sample.env`)
- Client system capable of:
  - Making JSONP requests with callback parameter
  - Handling JSON responses with:
    - `total_results` count
    - `perpage` value
    - `results` array containing formatted citations
    - `sort` options

## Quick Start

1. **Clone the repository**
   ```bash
   git clone [repository-url]
   cd [repository-name]
   ```

2. **Configure environment**
   ```bash
   cp sample.env .env
   # Edit .env with your OCLC API credentials and library settings
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Run tests**
   ```bash
   pytest
   ```

5. **Start the development server**
   ```bash
   flask run
   ```

## Configuration

Create a `.env` file based on `sample.env` and configure the following:

### OCLC API Settings
- `OCLC_KEY` - Your OCLC Discovery API key
- `OCLC_SECRET` - Your OCLC Discovery API secret
- `OCLC_BASE_URL` - OCLC Discovery API base URL

### Library Configuration
- `DEFAULT_LIBRARY` - Default OCLC library symbol
- `LIBRARY_MAPPINGS` - JSON mapping of domains to library symbols
- `DEFAULT_SITE` - Default Discovery site name
- `SITE_MAPPINGS` - JSON mapping of library symbols to site names

### Results Settings
- `MAX_RESULTS_PER_PAGE` - Maximum results per page (API limit: 50)
- `DEFAULT_RESULTS_PER_PAGE` - Default results per page (Springshare default: 10)

## Usage

The application exposes a search endpoint that accepts requests from LibGuides and returns formatted results from OCLC's Discovery API. 

For detailed endpoint specifications, request/response examples, and integration instructions, see [API_DOCUMENTATION.md](API_DOCUMENTATION.md).

## Known LibGuides Limitations

Springshare Support has confirmed that the following display issues with custom search sources (like this OCLC Discovery integration) are scheduled for a future update:

- **Sort checkmark display** - Sort indicators may not display correctly
- **Pagination functionality** - Page navigation may not work as expected  
- **Search term display** - Search terms may not appear in the header after searches

There is no release timeline available yet. Monitor the [Springshare Blog](https://blog.springshare.com) and [Lounge Release Notes](https://ask.springshare.com/libguides/faq/1235) for updates.

### Temporary Workaround

To hide the sort checkmark until the official fix is released, add this CSS to your LibGuides Admin > Look & Feel > Custom JS/CSS:

```css
/* Hide the Sort checkmark on the LibGuides Search page */
#s-lg-srch-cols .s-srch-sorter .fa-fw {
  display: none;
}
```

## Development

### Project Structure
```
├── src/
│   ├── oclc/
│   │   ├── discovery.py # OCLC API integration
│   │   └── auth.py      # OCLC API authentication
│   ├── springshare/
│   │   └── formatter.py # JSONP formatter
│   ├── app.py          # Main Flask application
│   └── config.py       # Configuration management
├── tests/              # Test suite
├── requirements.txt    # Python dependencies
├── sample.env          # Environment template
└── README.md
```

### Environment Variables
For development, credentials are managed in `.env` files.

**Note**: The `sample.env` file does not include OCLC credentials, but they have been verified for this project.

### Testing
```bash
# Run all tests
pytest

# Run with coverage
pytest --cov

# Run specific test file
pytest tests/test_discovery.py
```

## License

MIT - See [LICENSE](LICENSE) file for details.

## Support

For issues related to:
- **OCLC API integration** - Check the API documentation or OCLC Developer Network
- **LibGuides integration** - Contact Springshare Support
- **This application** - Open an issue in the GitHub repository