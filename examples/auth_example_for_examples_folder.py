"""
Authentication Example
======================

This example shows how to add authentication to your APIFlask application
using HTTPBasicAuth and HTTPTokenAuth from security.py.

Run:
    $ pip install apiflask
    $ python app.py

Test:
    # Get a token
    $ curl -X POST http://127.0.0.1:5000/tokens \
           -H "Content-Type: application/json" \
           -d '{"username": "user", "password": "pass"}'

    # Use the token
    $ curl http://127.0.0.1:5000/protected \
           -H "Authorization: Bearer <your-token>"

    # Or use basic auth
    $ curl http://127.0.0.1:5000/protected-basic \
           -u user:pass
"""

from apiflask import APIFlask, HTTPBasicAuth, HTTPTokenAuth, Schema, abort
from apiflask.fields import String
from apiflask.validators import Length
from werkzeug.security import generate_password_hash, check_password_hash
import secrets

app = APIFlask(__name__)

# Create auth instances
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()

# Mock user database
users = {
    'user': generate_password_hash('pass'),
    'admin': generate_password_hash('admin')
}

# Mock token storage
tokens = {}


# Schemas
class TokenIn(Schema):
    username = String(required=True, validate=Length(1, 32))
    password = String(required=True, validate=Length(1, 128))


class TokenOut(Schema):
    token = String()
    token_type = String()


# Auth verification callbacks
@basic_auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users[username], password):
        return username
    return None


@token_auth.verify_token
def verify_token(token):
    if token in tokens:
        return tokens[token]
    return None


# Routes
@app.get('/')
def index():
    return {'message': 'Authentication Example API'}


@app.post('/tokens')
@app.input(TokenIn)
@app.output(TokenOut)
def create_token(data):
    """Create a new access token."""
    username = data['username']
    password = data['password']
    
    if username not in users or not check_password_hash(users[username], password):
        abort(401, message='Invalid username or password')
    
    # Generate token
    token = secrets.token_urlsafe(32)
    tokens[token] = username
    
    return {
        'token': token,
        'token_type': 'Bearer'
    }


@app.get('/protected')
@app.auth_required(token_auth)
def protected():
    """Token-protected endpoint."""
    return {
        'message': f'Hello {token_auth.current_user}!',
        'auth_type': 'token'
    }


@app.get('/protected-basic')
@app.auth_required(basic_auth)
def protected_basic():
    """Basic auth protected endpoint."""
    return {
        'message': f'Hello {basic_auth.current_user}!',
        'auth_type': 'basic'
    }


@app.delete('/tokens')
@app.auth_required(token_auth)
@app.output({}, 204)
def revoke_token():
    """Revoke the current token."""
    # Find and remove the current token
    current_token = None
    for token, username in tokens.items():
        if username == token_auth.current_user:
            current_token = token
            break
    
    if current_token:
        del tokens[current_token]
    
    return ''


if __name__ == '__main__':
    app.run(debug=True)
