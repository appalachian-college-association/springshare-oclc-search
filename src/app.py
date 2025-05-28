# app.py
from flask import Flask, jsonify, request, Response
import json
from src.oclc.discovery import search_worldcat, MAX_QUERY_LENGTH
from src.config import Config
import structlog
import logging
from flask_talisman import Talisman
from flask_cors import CORS
import os

# Configure structured logging
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.format_exc_info,
        structlog.processors.JSONRenderer()
    ]
)
logger = structlog.get_logger()

# Initialize Flask app with config
flask_app = Flask(__name__)
try:
    config = Config()
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Failed to initialize configuration: {str(e)}")
    raise

# Configure Talisman based on environment
is_development = os.environ.get('ENV', 'production').lower() == 'development'
Talisman(
    flask_app,
    force_https=not is_development,
    content_security_policy=None
)
CORS(flask_app)

@flask_app.route('/search', methods=['GET'])
def search():
    """Handle search requests from Springshare"""
    try:
        callback = request.args.get('callback')
        
        # Get and validate query
        query = request.args.get('q', '').strip()
        if not query:
            error_response = {
                "error": "No search query provided",
                "total_results": 0,
                "results": []
            }
            return wrap_response(error_response, callback, 400)
            
        # Check query length
        if len(query) > MAX_QUERY_LENGTH:
            error_response = {
                "error": f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters",
                "total_results": 0,
                "results": []
            }
            return wrap_response(error_response, callback, 400)
            
        # Get and validate pagination
        try:
            page = int(request.args.get('page', 1))
            if page < 1:
                error_response = {
                    "error": "Page number must be greater than 0",
                    "total results": 0,
                    "results": []
                }
                return wrap_response(error_response, callback, 400)
                
            limit = int(request.args.get('perpage', config.DEFAULT_RESULTS_PER_PAGE))
            if limit < 1 or limit > config.MAX_RESULTS_PER_PAGE:
                error_response = {
                    "error": f"Results per page must be between 1 and {config.MAX_RESULTS_PER_PAGE}",
                    "total_results": 0,
                    "results": []
                }
                return wrap_response(error_response, callback, 400)
                
        except ValueError:
            error_response = {
                "error": "Invalid pagination parameters",
                "total_results": 0,
                "results": []
            }
            return wrap_response(error_response, callback, 400)
            
        # Get sort parameter
        sort = request.args.get('sort')
        
        # Perform search
        results, status_code = search_worldcat(
            query=query,
            page=page,
            limit=limit,
            referrer=request.referrer,
            sort=sort
        )
        
        # Check for errors in results
        if "error" in results:
            logger.error("search_error", error=results['error'])
            return wrap_response(results, callback, status_code or 400)
            
        return wrap_response(results, callback, status_code or 200)

    except Exception as e:
        logger.exception("search_failed", error=str(e))
        error_response = {
            "error": "Internal server error",
            "total_results": 0,
            "results": []
        }
        return wrap_response(error_response, callback, 500)

def wrap_response (data: dict, callback: str = None, status: int = 200):
    """Wrap response in JSONP callback if provided"""
    if callback:
        jsonp = f"{callback}({json.dumps(data)})"
        return Response(
            jsonp,
            status=status,
            mimetype='application/javascript'
        )
    return jsonify(data), status

# Health check endpoint
@flask_app.route('/health')
def health():
    """Health check endpoint"""
    callback = request.args.get('callback')
    try:
        response = {
            "status": "healthy",
            "env": os.environ.get('ENV', 'production')
        }
        return wrap_response(response, callback, 200)
    except Exception as e:
        logger.error("health_check_failed", error=str(e))
        error_response = {
            "status": "unhealthy",
            "error": str(e)
        }
        return wrap_response(error_response, callback, 500)

# Add root route for testing
@flask_app.route('/')
def index():
    return jsonify({"message": "API is running"}), 200

# Create app variable for Gunicorn
app = flask_app

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    debug = is_development
    flask_app.run(host='0.0.0.0', port=port, debug=debug)