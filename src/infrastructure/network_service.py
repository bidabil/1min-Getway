import uuid
from flask import make_response

def handle_options_request():
    """
    Handles CORS (Cross-Origin Resource Sharing) preflight requests.
    Ensures web-based clients like TypingMind or browser extensions can connect.
    """
    response = make_response()
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')
    
    # Unique ID even for OPTIONS requests to improve traceability
    response.headers['X-Request-ID'] = f"opt-{uuid.uuid4()}"
    
    # 204 No Content is the standard success code for OPTIONS
    return response, 204

def set_response_headers(response):
    """
    Applies standard security and tracking headers to JSON responses.
    """
    response.headers['Content-Type'] = 'application/json'
    response.headers['Access-Control-Allow-Origin'] = '*'
    
    # Unique Request ID to correlate logs with client-side issues
    request_id = str(uuid.uuid4())
    response.headers['X-Request-ID'] = request_id
    
    # Allows client-side apps to read the X-Request-ID for debugging
    response.headers['Access-Control-Expose-Headers'] = 'X-Request-ID'
    
    return response