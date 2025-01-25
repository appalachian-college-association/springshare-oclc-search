# API Documentation

## Endpoints

### GET /search

Searches OCLC Discovery API and returns formatted results.

#### Query Parameters

- `q` (required): Search query string
  - Max length: 500 characters
  - Max words: 20
- `page`: Page number (default: 1)
- `perpage`: Results per page (default: 10, max: 50)
- `sort`: Sort order
  - Options: library, recency, bestMatch, creator, publicationDateAsc, publicationDateDesc, mostWidelyHeld, title
  - Default: bestMatch

#### Example Request

```
GET /search?q=python programming&page=1&perpage=10&sort=bestMatch
```

#### Response Format

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

### JSONP Support

The API supports JSONP requests by including a callback parameter:
```
GET /search?q=python&callback=myCallback
```

Response will be wrapped in the callback function:
```javascript
myCallback({
    "total_results": 100,
    "results": [...]
})
```

### Library Detection

The API determines which library catalog to search based on the request's referrer header. Configure library mappings in environment variables.