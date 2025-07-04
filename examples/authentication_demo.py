"""
Authentication Demo for APIFlask
================================

This example demonstrates how to use APIFlask's authentication functions,
including HTTPBasicAuth and HTTPTokenAuth.

Run with: python authentication_demo.py
Test with: Use the provided curl commands in comments
"""

from apiflask import APIFlask, Schema, abort, HTTPBasicAuth, HTTPTokenAuth
from apiflask.fields import String, Boolean, DateTime, Integer
from apiflask.validators import Length
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import secrets

app = APIFlask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'

# Initialize authentication handlers
basic_auth = HTTPBasicAuth(description='Basic authentication with username and password')
token_auth = HTTPTokenAuth(scheme='Bearer', description='Bearer token authentication')
api_key_auth = HTTPTokenAuth(
    scheme='ApiKey', 
    header='X-API-Key',
    description='API Key authentication via custom header'
)

# Mock database for users and tokens
users_db = {
    'admin': {
        'password_hash': generate_password_hash('secret'),
        'role': 'admin',
        'active': True
    },
    'user': {
        'password_hash': generate_password_hash('password'),
        'role': 'user',
        'active': True
    },
    'inactive_user': {
        'password_hash': generate_password_hash('password'),
        'role': 'user',
        'active': False
    }
}

# Mock token storage
tokens_db = {}
api_keys_db = {
    'demo-api-key-123': {'username': 'admin', 'name': 'Demo API Key'}
}


# Schemas
class LoginSchema(Schema):
    username = String(required=True, validate=Length(1, 64))
    password = String(required=True, validate=Length(1, 128))


class TokenSchema(Schema):
    access_token = String()
    token_type = String()
    expires_in = Integer()
    expires_at = DateTime()


class UserProfileSchema(Schema):
    username = String()
    role = String()
    active = Boolean()


class ApiKeySchema(Schema):
    api_key = String()
    name = String()


# Basic Auth verify callback
@basic_auth.verify_password
def verify_password(username, password):
    """Verify username and password for basic auth."""
    if username in users_db:
        user = users_db[username]
        if check_password_hash(user['password_hash'], password):
            if user['active']:
                return username
            else:
                # User exists but is inactive
                abort(403, message='User account is inactive')
    return None


# Token Auth verify callback
@token_auth.verify_token
def verify_token(token):
    """Verify bearer token."""
    if token in tokens_db:
        token_data = tokens_db[token]
        if datetime.utcnow() < token_data['expires_at']:
            return token_data['username']
        else:
            # Token expired
            abort(401, message='Token has expired')
    return None


# API Key Auth verify callback
@api_key_auth.verify_token
def verify_api_key(api_key):
    """Verify API key from custom header."""
    if api_key in api_keys_db:
        return api_keys_db[api_key]['username']
    return None


# Custom error handlers for different auth methods
@basic_auth.error_processor
def basic_auth_error(error):
    """Custom error handler for basic auth."""
    return {
        'code': error.status_code,
        'message': error.message,
        'auth_method': 'basic',
        'hint': 'Use valid username and password in Basic Auth header'
    }, error.status_code, {'WWW-Authenticate': 'Basic realm="Login Required"'}


@token_auth.error_processor
def token_auth_error(error):
    """Custom error handler for token auth."""
    return {
        'code': error.status_code,
        'message': error.message,
        'auth_method': 'bearer',
        'hint': 'Include valid Bearer token in Authorization header'
    }, error.status_code


@api_key_auth.error_processor
def api_key_auth_error(error):
    """Custom error handler for API key auth."""
    return {
        'code': error.status_code,
        'message': error.message,
        'auth_method': 'api_key',
        'hint': 'Include valid API key in X-API-Key header'
    }, error.status_code


# Routes
@app.get('/')
def index():
    """Public endpoint - no authentication required."""
    return {
        'message': 'Welcome to APIFlask Authentication Demo',
        'endpoints': {
            'public': '/',
            'login': '/login',
            'basic_auth_protected': '/basic-protected',
            'token_protected': '/token-protected',
            'api_key_protected': '/api-key-protected',
            'admin_only': '/admin-only',
            'current_user': '/me'
        }
    }


@app.post('/login')
@app.input(LoginSchema)
@app.output(TokenSchema)
def login(json_data):
    """
    Login endpoint to get Bearer token.
    
    Example:
    curl -X POST http://localhost:5000/login \
         -H "Content-Type: application/json" \
         -d '{"username": "admin", "password": "secret"}'
    """
    username = json_data['username']
    password = json_data['password']
    
    if username not in users_db:
        abort(401, message='Invalid username or password')
    
    user = users_db[username]
    if not check_password_hash(user['password_hash'], password):
        abort(401, message='Invalid username or password')
    
    if not user['active']:
        abort(403, message='User account is inactive')
    
    # Generate token
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=1)
    
    tokens_db[token] = {
        'username': username,
        'expires_at': expires_at
    }
    
    return {
        'access_token': token,
        'token_type': 'Bearer',
        'expires_in': 3600,
        'expires_at': expires_at
    }


@app.get('/basic-protected')
@app.auth_required(basic_auth)
@app.output(UserProfileSchema)
def basic_protected():
    """
    Endpoint protected by HTTP Basic Authentication.
    
    Example:
    curl http://localhost:5000/basic-protected \
         -u admin:secret
    """
    username = basic_auth.current_user
    user = users_db[username]
    return {
        'username': username,
        'role': user['role'],
        'active': user['active']
    }


@app.get('/token-protected')
@app.auth_required(token_auth)
def token_protected():
    """
    Endpoint protected by Bearer token authentication.
    
    Example:
    # First get a token from /login, then:
    curl http://localhost:5000/token-protected \
         -H "Authorization: Bearer YOUR_TOKEN_HERE"
    """
    return {
        'message': 'You accessed a token-protected endpoint',
        'user': token_auth.current_user
    }


@app.get('/api-key-protected')
@app.auth_required(api_key_auth)
def api_key_protected():
    """
    Endpoint protected by API Key authentication.
    
    Example:
    curl http://localhost:5000/api-key-protected \
         -H "X-API-Key: demo-api-key-123"
    """
    return {
        'message': 'You accessed an API key protected endpoint',
        'user': api_key_auth.current_user,
        'api_key_info': api_keys_db.get(api_key_auth.token)
    }


@app.get('/admin-only')
@app.auth_required(token_auth)
def admin_only():
    """
    Endpoint that requires admin role.
    
    Example:
    # Login as admin first, then:
    curl http://localhost:5000/admin-only \
         -H "Authorization: Bearer YOUR_ADMIN_TOKEN"
    """
    username = token_auth.current_user
    user = users_db[username]
    
    if user['role'] != 'admin':
        abort(403, message='Admin access required')
    
    return {
        'message': 'Welcome admin!',
        'admin_data': 'Secret admin information'
    }


@app.get('/me')
@app.auth_required(token_auth)
@app.output(UserProfileSchema)
def get_current_user():
    """
    Get current authenticated user's profile.
    
    Example:
    curl http://localhost:5000/me \
         -H "Authorization: Bearer YOUR_TOKEN_HERE"
    """
    username = token_auth.current_user
    user = users_db[username]
    return {
        'username': username,
        'role': user['role'],
        'active': user['active']
    }


@app.post('/logout')
@app.auth_required(token_auth)
@app.output({}, status_code=204)
def logout():
    """
    Logout by invalidating the current token.
    
    Example:
    curl -X POST http://localhost:5000/logout \
         -H "Authorization: Bearer YOUR_TOKEN_HERE"
    """
    # Get the token from the request
    token = token_auth.token
    if token in tokens_db:
        del tokens_db[token]
    return ''


@app.post('/api-keys')
@app.auth_required(token_auth)
@app.input({'name': String(required=True)})
@app.output(ApiKeySchema)
def create_api_key(json_data):
    """
    Create a new API key (admin only).
    
    Example:
    curl -X POST http://localhost:5000/api-keys \
         -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
         -H "Content-Type: application/json" \
         -d '{"name": "My New API Key"}'
    """
    username = token_auth.current_user
    user = users_db[username]
    
    if user['role'] != 'admin':
        abort(403, message='Only admins can create API keys')
    
    # Generate new API key
    api_key = f'ak_{secrets.token_urlsafe(32)}'
    api_keys_db[api_key] = {
        'username': username,
        'name': json_data['name']
    }
    
    return {
        'api_key': api_key,
        'name': json_data['name']
    }


# Multiple auth methods on single endpoint
@app.get('/flexible-auth')
@app.auth_required(basic_auth)
@app.auth_required(token_auth)
def flexible_auth():
    """
    Endpoint accepting multiple authentication methods.
    Either Basic Auth OR Bearer token can be used.
    
    Examples:
    curl http://localhost:5000/flexible-auth -u admin:secret
    # OR
    curl http://localhost:5000/flexible-auth -H "Authorization: Bearer YOUR_TOKEN"
    """
    # Check which auth method was used
    if hasattr(basic_auth, 'current_user') and basic_auth.current_user:
        auth_method = 'basic'
        user = basic_auth.current_user
    else:
        auth_method = 'token'
        user = token_auth.current_user
    
    return {
        'message': 'Successfully authenticated',
        'auth_method': auth_method,
        'user': user
    }


if __name__ == '__main__':
    print("""
    APIFlask Authentication Demo
    ============================
    
    Available users:
    - admin/secret (admin role)
    - user/password (user role)
    - inactive_user/password (inactive account)
    
    Demo API Key: demo-api-key-123
    
    Try these commands:
    
    1. Public endpoint:
       curl http://localhost:5000/
    
    2. Login to get a token:
       curl -X POST http://localhost:5000/login -H "Content-Type: application/json" -d '{"username": "admin", "password": "secret"}'
    
    3. Basic Auth protected:
       curl http://localhost:5000/basic-protected -u admin:secret
    
    4. Token protected (use token from login):
       curl http://localhost:5000/token-protected -H "Authorization: Bearer YOUR_TOKEN"
    
    5. API Key protected:
       curl http://localhost:5000/api-key-protected -H "X-API-Key: demo-api-key-123"
    """)
    
    app.run(debug=True)
