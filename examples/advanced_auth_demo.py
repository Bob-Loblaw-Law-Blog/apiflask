"""
Advanced Authentication Demo for APIFlask
=========================================

This example demonstrates advanced authentication patterns including:
- JWT token authentication
- Role-based access control (RBAC)
- Permission-based authorization
- Custom authentication decorators
- OAuth2-style token refresh
- Rate limiting per user

Requirements:
pip install apiflask pyjwt

Run with: python advanced_auth_demo.py
"""

from apiflask import APIFlask, Schema, abort, HTTPTokenAuth
from apiflask.fields import String, Boolean, List, Integer, DateTime
from apiflask.validators import Length, OneOf
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import jwt
import secrets
from collections import defaultdict

app = APIFlask(__name__)
app.config['SECRET_KEY'] = 'your-secret-key-here'
app.config['JWT_ALGORITHM'] = 'HS256'
app.config['ACCESS_TOKEN_EXPIRE'] = 900  # 15 minutes
app.config['REFRESH_TOKEN_EXPIRE'] = 2592000  # 30 days

# Initialize authentication handler
auth = HTTPTokenAuth(scheme='Bearer', description='JWT Bearer token authentication')

# Mock database
users_db = {
    'admin': {
        'password_hash': generate_password_hash('admin123'),
        'roles': ['admin', 'user'],
        'permissions': ['users:read', 'users:write', 'users:delete', 'posts:read', 'posts:write', 'posts:delete'],
        'active': True,
        'email': 'admin@example.com'
    },
    'editor': {
        'password_hash': generate_password_hash('editor123'),
        'roles': ['editor', 'user'],
        'permissions': ['posts:read', 'posts:write', 'users:read'],
        'active': True,
        'email': 'editor@example.com'
    },
    'viewer': {
        'password_hash': generate_password_hash('viewer123'),
        'roles': ['user'],
        'permissions': ['posts:read', 'users:read'],
        'active': True,
        'email': 'viewer@example.com'
    }
}

# Refresh tokens storage
refresh_tokens_db = {}

# Rate limiting storage
rate_limit_storage = defaultdict(list)


# Schemas
class LoginSchema(Schema):
    username = String(required=True, validate=Length(1, 64))
    password = String(required=True, validate=Length(1, 128))


class TokenResponseSchema(Schema):
    access_token = String()
    refresh_token = String()
    token_type = String()
    expires_in = Integer()


class RefreshTokenSchema(Schema):
    refresh_token = String(required=True)


class UserSchema(Schema):
    username = String()
    email = String()
    roles = List(String())
    permissions = List(String())
    active = Boolean()


# Helper functions
def generate_jwt_token(username, token_type='access'):
    """Generate JWT token for user."""
    user = users_db[username]
    
    if token_type == 'access':
        expire = timedelta(seconds=app.config['ACCESS_TOKEN_EXPIRE'])
    else:
        expire = timedelta(seconds=app.config['REFRESH_TOKEN_EXPIRE'])
    
    payload = {
        'username': username,
        'roles': user['roles'],
        'permissions': user['permissions'],
        'type': token_type,
        'exp': datetime.utcnow() + expire,
        'iat': datetime.utcnow(),
        'jti': secrets.token_urlsafe(16)  # JWT ID for token revocation
    }
    
    return jwt.encode(payload, app.config['SECRET_KEY'], algorithm=app.config['JWT_ALGORITHM'])


def decode_jwt_token(token):
    """Decode and validate JWT token."""
    try:
        payload = jwt.decode(token, app.config['SECRET_KEY'], algorithms=[app.config['JWT_ALGORITHM']])
        return payload
    except jwt.ExpiredSignatureError:
        abort(401, message='Token has expired')
    except jwt.InvalidTokenError:
        abort(401, message='Invalid token')


# Authentication verification
@auth.verify_token
def verify_jwt_token(token):
    """Verify JWT token and return username."""
    payload = decode_jwt_token(token)
    
    if payload.get('type') != 'access':
        abort(401, message='Invalid token type')
    
    username = payload.get('username')
    if username and username in users_db:
        # Store additional info in auth context
        auth.current_payload = payload
        return username
    
    return None


@auth.error_processor
def auth_error_handler(error):
    """Custom error handler for authentication errors."""
    return {
        'error': 'authentication_failed',
        'message': error.message,
        'code': error.status_code,
        'timestamp': datetime.utcnow().isoformat()
    }, error.status_code


# Custom decorators for role and permission checking
def require_role(*required_roles):
    """Decorator to require specific roles."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(auth, 'current_payload'):
                abort(401, message='Authentication required')
            
            user_roles = auth.current_payload.get('roles', [])
            if not any(role in user_roles for role in required_roles):
                abort(403, message=f'Required role(s): {", ".join(required_roles)}')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(*required_permissions):
    """Decorator to require specific permissions."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not hasattr(auth, 'current_payload'):
                abort(401, message='Authentication required')
            
            user_permissions = auth.current_payload.get('permissions', [])
            if not all(perm in user_permissions for perm in required_permissions):
                abort(403, message=f'Required permission(s): {", ".join(required_permissions)}')
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def rate_limit(max_requests=10, window=60):
    """Simple rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if hasattr(auth, 'current_user') and auth.current_user:
                user = auth.current_user
                now = datetime.utcnow()
                
                # Clean old entries
                rate_limit_storage[user] = [
                    timestamp for timestamp in rate_limit_storage[user]
                    if (now - timestamp).seconds < window
                ]
                
                # Check rate limit
                if len(rate_limit_storage[user]) >= max_requests:
                    abort(429, message='Rate limit exceeded')
                
                # Add current request
                rate_limit_storage[user].append(now)
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Routes
@app.get('/')
def index():
    """Public endpoint with API information."""
    return {
        'name': 'Advanced Authentication Demo',
        'version': '1.0.0',
        'authentication': {
            'type': 'JWT Bearer Token',
            'login_endpoint': '/auth/login',
            'refresh_endpoint': '/auth/refresh',
            'token_header': 'Authorization: Bearer <token>'
        }
    }


@app.post('/auth/login')
@app.input(LoginSchema)
@app.output(TokenResponseSchema)
def login(json_data):
    """
    Login with username and password to get access and refresh tokens.
    
    Example:
    curl -X POST http://localhost:5000/auth/login \
         -H "Content-Type: application/json" \
         -d '{"username": "admin", "password": "admin123"}'
    """
    username = json_data['username']
    password = json_data['password']
    
    if username not in users_db:
        abort(401, message='Invalid credentials')
    
    user = users_db[username]
    if not check_password_hash(user['password_hash'], password):
        abort(401, message='Invalid credentials')
    
    if not user['active']:
        abort(403, message='Account is deactivated')
    
    # Generate tokens
    access_token = generate_jwt_token(username, 'access')
    refresh_token = generate_jwt_token(username, 'refresh')
    
    # Store refresh token
    refresh_tokens_db[refresh_token] = {
        'username': username,
        'created_at': datetime.utcnow()
    }
    
    return {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'token_type': 'Bearer',
        'expires_in': app.config['ACCESS_TOKEN_EXPIRE']
    }


@app.post('/auth/refresh')
@app.input(RefreshTokenSchema)
@app.output(TokenResponseSchema)
def refresh_token(json_data):
    """
    Refresh access token using refresh token.
    
    Example:
    curl -X POST http://localhost:5000/auth/refresh \
         -H "Content-Type: application/json" \
         -d '{"refresh_token": "YOUR_REFRESH_TOKEN"}'
    """
    refresh_token = json_data['refresh_token']
    
    # Decode refresh token
    payload = decode_jwt_token(refresh_token)
    
    if payload.get('type') != 'refresh':
        abort(401, message='Invalid token type')
    
    # Check if refresh token exists in storage
    if refresh_token not in refresh_tokens_db:
        abort(401, message='Invalid refresh token')
    
    username = payload.get('username')
    if not username or username not in users_db:
        abort(401, message='Invalid user')
    
    # Generate new access token
    new_access_token = generate_jwt_token(username, 'access')
    
    return {
        'access_token': new_access_token,
        'refresh_token': refresh_token,  # Return same refresh token
        'token_type': 'Bearer',
        'expires_in': app.config['ACCESS_TOKEN_EXPIRE']
    }


@app.post('/auth/logout')
@app.auth_required(auth)
@app.output({}, status_code=204)
def logout():
    """
    Logout by invalidating refresh tokens.
    
    Example:
    curl -X POST http://localhost:5000/auth/logout \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """
    # In a real app, you'd invalidate the JWT token (e.g., using Redis blacklist)
    # Here we just remove refresh tokens for the user
    username = auth.current_user
    tokens_to_remove = [
        token for token, data in refresh_tokens_db.items()
        if data['username'] == username
    ]
    for token in tokens_to_remove:
        del refresh_tokens_db[token]
    
    return ''


@app.get('/users')
@app.auth_required(auth)
@require_permission('users:read')
@app.output(UserSchema(many=True))
def list_users():
    """
    List all users (requires 'users:read' permission).
    
    Example:
    curl http://localhost:5000/users \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """
    return [
        {
            'username': username,
            'email': data['email'],
            'roles': data['roles'],
            'permissions': data['permissions'],
            'active': data['active']
        }
        for username, data in users_db.items()
    ]


@app.get('/admin/dashboard')
@app.auth_required(auth)
@require_role('admin')
def admin_dashboard():
    """
    Admin-only dashboard (requires 'admin' role).
    
    Example:
    curl http://localhost:5000/admin/dashboard \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """
    return {
        'message': 'Welcome to admin dashboard',
        'stats': {
            'total_users': len(users_db),
            'active_tokens': len(refresh_tokens_db)
        }
    }


@app.get('/editor/posts')
@app.auth_required(auth)
@require_role('editor', 'admin')
@require_permission('posts:read')
def editor_posts():
    """
    Editor endpoint (requires 'editor' or 'admin' role AND 'posts:read' permission).
    
    Example:
    curl http://localhost:5000/editor/posts \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """
    return {
        'posts': [
            {'id': 1, 'title': 'First Post', 'status': 'published'},
            {'id': 2, 'title': 'Second Post', 'status': 'draft'}
        ]
    }


@app.get('/profile')
@app.auth_required(auth)
@app.output(UserSchema)
def get_profile():
    """
    Get current user's profile.
    
    Example:
    curl http://localhost:5000/profile \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """
    username = auth.current_user
    user = users_db[username]
    
    return {
        'username': username,
        'email': user['email'],
        'roles': user['roles'],
        'permissions': user['permissions'],
        'active': user['active']
    }


@app.get('/rate-limited')
@app.auth_required(auth)
@rate_limit(max_requests=5, window=60)
def rate_limited_endpoint():
    """
    Rate-limited endpoint (5 requests per minute per user).
    
    Example:
    curl http://localhost:5000/rate-limited \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """
    return {
        'message': 'This endpoint is rate limited',
        'remaining_requests': 5 - len(rate_limit_storage[auth.current_user])
    }


@app.get('/token-info')
@app.auth_required(auth)
def token_info():
    """
    Get information about the current JWT token.
    
    Example:
    curl http://localhost:5000/token-info \
         -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """
    payload = auth.current_payload
    
    return {
        'username': payload['username'],
        'roles': payload['roles'],
        'permissions': payload['permissions'],
        'issued_at': datetime.fromtimestamp(payload['iat']).isoformat(),
        'expires_at': datetime.fromtimestamp(payload['exp']).isoformat(),
        'token_id': payload['jti']
    }


if __name__ == '__main__':
    print("""
    Advanced Authentication Demo
    ============================
    
    Available users:
    - admin/admin123 (admin role, all permissions)
    - editor/editor123 (editor role, read/write posts)
    - viewer/viewer123 (user role, read only)
    
    Features demonstrated:
    - JWT authentication
    - Role-based access control
    - Permission-based authorization
    - Token refresh
    - Rate limiting
    
    Try these commands:
    
    1. Login as admin:
       curl -X POST http://localhost:5000/auth/login -H "Content-Type: application/json" -d '{"username": "admin", "password": "admin123"}'
    
    2. Access admin dashboard (use token from login):
       curl http://localhost:5000/admin/dashboard -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    
    3. List users (requires users:read permission):
       curl http://localhost:5000/users -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
    """)
    
    app.run(debug=True)
