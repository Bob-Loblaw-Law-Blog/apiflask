"""
Basic Authentication Example with APIFlask
-----------------------------------------

This example demonstrates how to use the HTTPBasicAuth class from apiflask.security
to protect API endpoints with username/password authentication.

To run this example:
    $ pip install apiflask
    $ python basic_auth_example.py

Then try the following curl commands:
    $ curl -X GET http://localhost:5000/api/protected
    $ curl -X GET http://localhost:5000/api/protected -u user:password
    $ curl -X GET http://localhost:5000/api/admin -u user:password
    $ curl -X GET http://localhost:5000/api/admin -u admin:admin-password
"""

from apiflask import APIFlask, HTTPBasicAuth, Schema, abort
from apiflask.fields import Integer, String
from werkzeug.security import generate_password_hash, check_password_hash

app = APIFlask(__name__, title='Basic Auth Example', version='1.0')
auth = HTTPBasicAuth(description='Use basic authentication with username/password')

# Mock user database
users = {
    'user': generate_password_hash('password'),
    'admin': generate_password_hash('admin-password')
}

# Mock user roles
roles = {
    'user': 'user',
    'admin': 'admin'
}

class UserSchema(Schema):
    username = String(required=True)
    role = String(required=True)

class MessageSchema(Schema):
    message = String(required=True)
    code = Integer()


@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users[username], password):
        # Return the user object, which will be stored in g.flask_httpauth_user
        return {'username': username, 'role': roles.get(username, 'user')}
    return None


@auth.error_processor
def auth_error_processor(error):
    return {
        'status_code': error.status_code,
        'message': error.message,
        'detail': 'Authentication failed. Please provide valid credentials.'
    }, error.status_code


@app.get('/')
def index():
    """Public endpoint that doesn't require authentication"""
    return {'message': 'Welcome to the Authentication Example API!'}, 200


@app.get('/api/protected')
@app.output(MessageSchema)
@app.auth_required(auth)
def protected():
    """Protected endpoint - requires basic authentication"""
    current_user = auth.current_user
    return {
        'message': f'Hello, {current_user["username"]}! You accessed a protected endpoint.',
        'code': 200
    }, 200


@app.get('/api/admin')
@app.output(MessageSchema)
@app.auth_required(auth)
def admin_only():
    """Admin-only endpoint - requires basic authentication and admin role"""
    current_user = auth.current_user
    if current_user.get('role') != 'admin':
        abort(403, 'Admin access required for this endpoint')

    return {
        'message': f'Hello, admin {current_user["username"]}! You accessed an admin-only endpoint.',
        'code': 200
    }, 200


@app.get('/api/me')
@app.output(UserSchema)
@app.auth_required(auth)
def get_user_info():
    """Get current user information"""
    current_user = auth.current_user
    return {
        'username': current_user['username'],
        'role': current_user['role']
    }, 200


if __name__ == '__main__':
    app.run(debug=True)
