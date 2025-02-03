# app.py
from flask import Flask, jsonify, request
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
app = Flask(__name__)
config = Config()

# Security middleware
Talisman(app, force_https=True)
CORS(app)

@app.route('/search', methods=['GET'])
def search():
    """Handle search requests from Springshare"""
    try:
        # Get and validate query
        query = request.args.get('q', '').strip()
        if not query:
            return jsonify({
                "error": "No search query provided",
                "total_results": 0,
                "results": []
            }), 400
            
        if len(query) > MAX_QUERY_LENGTH:
            return jsonify({
                "error": f"Query exceeds maximum length of {MAX_QUERY_LENGTH} characters",
                "total_results": 0,
                "results": []
            }), 400
            
        # Get and validate pagination
        try:
            page = int(request.args.get('page', 1))
            if page < 1:
                raise ValueError("Page number must be greater than 0")
        except ValueError:
            return jsonify({
                "error": "Invalid page number",
                "total_results": 0,
                "results": []
            }), 400
            
        try:
            limit = int(request.args.get('perpage', config.DEFAULT_RESULTS_PER_PAGE))
            if limit < 1:
                raise ValueError("Results per page must be greater than 0")
        except ValueError:
            return jsonify({
                "error": "Invalid results per page value",
                "total_results": 0,
                "results": []
            }), 400
            
        # Get sort parameter
        sort = request.args.get('sort')
        
        # Perform search
        results = search_worldcat(
            query=query,
            page=page,
            limit=limit,
            referrer=request.referrer,
            sort=sort
        )
        
        # Check if there was an error
        if "error" in results:
            logger.error("search_error", error=results['error'])
            return jsonify(results), results.get('status_code', 400)
            
        return jsonify(results)

    except Exception as e:
        logger.exception("search_failed", error=str(e))
        return jsonify({
            "error": "Internal server error",
            "total_results": 0,
            "results": []
        }), 500
    
# Health check endpoint
@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)
