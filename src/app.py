# app.py
from flask import Flask, jsonify, request
from src.oclc.discovery import search_worldcat, MAX_QUERY_LENGTH
from dotenv import load_dotenv
import logging
import os
import traceback

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Load environment variables
load_dotenv()

# Verify environment variables are loaded
logger.info("Checking environment variables:")
logger.info(f"DEFAULT_SITE: {os.getenv('DEFAULT_SITE')}")
logger.info(f"SITE_MAPPINGS: {os.getenv('SITE_MAPPINGS')}")

@app.route('/test-config')
def test_config():
    from src.config import Config
    config = Config()
    return jsonify({
        'default_site': config.DEFAULT_SITE,
        'site_mappings': config.SITE_MAPPINGS
    })

@app.route('/search', methods=['GET'])
def search():
    """Handle search requests from Springshare"""
    try:
        # Log request details
        logger.info("Raw query string: %s", request.query_string.decode('utf-8'))
        logger.info("Request args: %s", request.args)
        logger.info("Referrer header: %s", request.referrer)
        
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
            limit = int(request.args.get('perpage', 10))
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
        
        logger.info(
            "Processing search - query: %s, page: %s, limit: %s, referrer: %s",
            query, page, limit, request.referrer
        )
        
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
            logger.error("Search error: %s", results['error'])
            return jsonify(results), results.get('status_code', 400)
            
        return jsonify(results)

    except Exception as e:
        logger.error("Error processing search request:")
        logger.error(traceback.format_exc())  # Log full traceback
        return jsonify({
            "error": str(e),
            "total_results": 0,
            "results": []
        }), 500
    
# Health check
@app.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200

if __name__ == '__main__':
    # Log startup information
    logger.info("Starting Flask application...")
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)