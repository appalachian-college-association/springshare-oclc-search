# API Documentation

## Endpoints

### GET /search

Searches OCLC Discovery API and returns formatted results compatible with Springshare LibApps custom search sources.

#### Query Parameters

- `q` (required): Search query string
  - Max length: 500 characters
  - Max words: 20
- `page`: Page number (default: 1)
- `perpage`: Results per page (default: 10, max: 50)
- `sort`: Sort order
  - Options: library, recency, bestMatch, creator, publicationDateAsc, publicationDateDesc, mostWidelyHeld, title
  - Default: bestMatch
- `callback` (required for JSONP): Callback function name for JSONP response wrapping

#### Example Requests

**Standard JSONP Request (Required for Springshare integration):**
```
GET /search?q=python programming&page=1&perpage=10&sort=bestMatch&callback=callback123456
```

**Direct JSON Request (for testing only):**
```
GET /search?q=python programming&page=1&perpage=10&sort=bestMatch
```

#### Response Formats

**JSONP Response (Standard - for Springshare):**
When a `callback` parameter is provided, the response is wrapped in the specified callback function:

```javascript
callback123456({
    "total_results": 100,
    "perpage": 10,
    "sort": {
        "field": "bestMatch",
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
    "results": [
        {
            "title": "Book Title",
            "ocn": "12345678",
            "url": "https://site.on.worldcat.org/search?queryString=ti:Book+Title",
            "author": "Author Name",
            "date": "2024",
            "publisher": "Publisher Name",
            "identifier": "9781234567890",
            "format": "Book"
        }
    ]
});
```

**JSON Response (Testing only):**
When no `callback` parameter is provided, returns standard JSON:

```json
{
    "total_results": 100,
    "perpage": 10,
    "sort": {
        "field": "bestMatch",
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
    "results": [
        {
            "title": "Book Title",
            "ocn": "12345678",
            "url": "https://site.on.worldcat.org/search?queryString=ti:Book+Title",
            "author": "Author Name",
            "date": "2024",
            "publisher": "Publisher Name",
            "identifier": "9781234567890",
            "format": "Book"
        }
    ]
}
```

#### Error Responses

**JSONP Error Response:**
```javascript
callback123456({
    "error": "Error message",
    "total_results": 0,
    "results": []
});
```

**JSON Error Response:**
```json
{
    "error": "Error message",
    "total_results": 0,
    "results": []
}
```

Common error scenarios:
- Empty query
- Query exceeds length limits
- Invalid pagination parameters
- Authentication failure

## Implementation Notes

### JSONP Requirement for Springshare

**Important:** Springshare LibApps custom search sources require JSONP responses. Always include the `callback` parameter in your requests when integrating with LibApps.

The API automatically detects the presence of a `callback` parameter and formats the response accordingly:
- **With callback:** Returns JSONP with `Content-Type: application/javascript`
- **Without callback:** Returns JSON with `Content-Type: application/json`

### Library Detection

The API determines which library catalog to search based on the request's referrer header. Configure library mappings in environment variables:

```bash
LIBRARY_MAPPINGS={"libguides.your-library.edu":"your-oclc-symbol"}
SITE_MAPPINGS={"your-oclc-symbol":"your-discovery-sitename"}
```

### Sort Parameter Mapping

The API automatically maps Springshare sort parameters to OCLC format:

| Springshare Format | OCLC API Format |
|-------------------|-----------------|
| `relevancy_desc` | `bestMatch` |
| `title_asc` | `title` |
| `date_desc` | `publicationDateDesc` |
| `date_asc` | `publicationDateAsc` |
| `creator_asc` | `creator` |
| `library_asc` | `library` |
| `popularity_desc` | `mostWidelyHeld` |

### URL Generation

The API generates WorldCat Discovery URLs using:
1. Configured discovery site mapping
2. Title processing (first 20 words, special character replacement)
3. Proper URL encoding for search queries