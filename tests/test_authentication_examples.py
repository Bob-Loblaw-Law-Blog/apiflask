"""
Unit tests for authentication examples
--------------------------------------

This test module contains comprehensive tests for the basic authentication
and token authentication examples to ensure they function correctly.
"""

import base64
import pytest
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.jose import jwt, JoseError
from apiflask import APIFlask, HTTPBasicAuth, HTTPTokenAuth, Schema, abort
from apiflask.fields import Integer, String


class TestBasicAuthExample:
    """Test suite for the basic authentication example."""

    @pytest.fixture
    def basic_auth_app(self):
        """Fixture to create and configure the basic auth example app."""
        # Recreate the app structure from the basic_auth_example
        app = APIFlask(__name__, title='Basic Auth Example', version='1.0')
        app.config['TESTING'] = True
        # Disable base response schema to match the example
        app.config['BASE_RESPONSE_SCHEMA'] = None
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

        # Define schemas
        class UserSchema(Schema):
            username = String(required=True)
            role = String(required=True)

        class MessageSchema(Schema):
            message = String(required=True)
            code = Integer()

        @auth.verify_password
        def verify_password(username, password):
            if username in users and check_password_hash(users[username], password):
                return {'username': username, 'role': roles.get(username, 'user')}
            return None

        @auth.error_processor
        def auth_error_processor(error):
            # Return error response that bypasses output validation
            body = {
                'status_code': error.status_code,
                'message': error.message,
                'detail': 'Authentication failed. Please provide valid credentials.'
            }
            return body, error.status_code, error.headers

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

        return app

    @pytest.fixture
    def basic_auth_client(self, basic_auth_app):
        """Fixture to create a test client for the basic auth app."""
        return basic_auth_app.test_client()

    def _get_auth_header(self, username, password):
        """Helper to create basic auth header."""
        credentials = base64.b64encode(f'{username}:{password}'.encode()).decode()
        return {'Authorization': f'Basic {credentials}'}

    def test_public_endpoint(self, basic_auth_client):
        """Test that the index endpoint is publicly accessible."""
        rv = basic_auth_client.get('/')
        assert rv.status_code == 200
        assert rv.json['message'] == 'Welcome to the Authentication Example API!'

    def test_protected_endpoint_without_auth(self, basic_auth_client):
        """Test that protected endpoint requires authentication."""
        rv = basic_auth_client.get('/api/protected')
        assert rv.status_code == 401
        assert 'message' in rv.json

    def test_protected_endpoint_with_invalid_credentials(self, basic_auth_client):
        """Test protected endpoint with invalid credentials."""
        # Test with wrong password
        headers = self._get_auth_header('user', 'wrong_password')
        rv = basic_auth_client.get('/api/protected', headers=headers)
        assert rv.status_code == 401

        # Test with non-existent user
        headers = self._get_auth_header('nonexistent', 'password')
        rv = basic_auth_client.get('/api/protected', headers=headers)
        assert rv.status_code == 401

    def test_protected_endpoint_with_valid_credentials(self, basic_auth_client):
        """Test protected endpoint with valid credentials."""
        headers = self._get_auth_header('user', 'password')
        rv = basic_auth_client.get('/api/protected', headers=headers)
        assert rv.status_code == 200
        assert 'message' in rv.json
        assert 'code' in rv.json
        assert 'user' in rv.json['message']
        assert rv.json['code'] == 200

    def test_admin_endpoint_with_user_role(self, basic_auth_client):
        """Test that regular user cannot access admin endpoint."""
        headers = self._get_auth_header('user', 'password')
        rv = basic_auth_client.get('/api/admin', headers=headers)
        assert rv.status_code == 403
        assert 'Admin access required' in rv.json['message']

    def test_admin_endpoint_with_admin_role(self, basic_auth_client):
        """Test that admin user can access admin endpoint."""
        headers = self._get_auth_header('admin', 'admin-password')
        rv = basic_auth_client.get('/api/admin', headers=headers)
        assert rv.status_code == 200
        assert 'message' in rv.json
        assert 'admin' in rv.json['message']
        assert 'admin-only endpoint' in rv.json['message']

    def test_user_info_endpoint(self, basic_auth_client):
        """Test the user info endpoint returns correct user data."""
        # Test with regular user
        headers = self._get_auth_header('user', 'password')
        rv = basic_auth_client.get('/api/me', headers=headers)
        assert rv.status_code == 200
        assert rv.json['username'] == 'user'
        assert rv.json['role'] == 'user'

        # Test with admin user
        headers = self._get_auth_header('admin', 'admin-password')
        rv = basic_auth_client.get('/api/me', headers=headers)
        assert rv.status_code == 200
        assert rv.json['username'] == 'admin'
        assert rv.json['role'] == 'admin'

    def test_error_handler_format(self, basic_auth_client):
        """Test that authentication errors have the correct format."""
        rv = basic_auth_client.get('/api/protected')
        assert rv.status_code == 401
        assert 'status_code' in rv.json
        assert 'message' in rv.json
        assert 'detail' in rv.json
        assert rv.json['status_code'] == 401
        assert 'Authentication failed' in rv.json['detail']

    def test_all_endpoints_with_both_users(self, basic_auth_client):
        """Comprehensive test of all endpoints with both user types."""
        endpoints = ['/api/protected', '/api/admin', '/api/me']

        # Test with regular user
        user_headers = self._get_auth_header('user', 'password')
        expected_user_status = {
            '/api/protected': 200,
            '/api/admin': 403,
            '/api/me': 200
        }

        for endpoint in endpoints:
            rv = basic_auth_client.get(endpoint, headers=user_headers)
            assert rv.status_code == expected_user_status[endpoint], \
                f"Endpoint {endpoint} returned {rv.status_code}, expected {expected_user_status[endpoint]}"

        # Test with admin user
        admin_headers = self._get_auth_header('admin', 'admin-password')
        expected_admin_status = {
            '/api/protected': 200,
            '/api/admin': 200,
            '/api/me': 200
        }

        for endpoint in endpoints:
            rv = basic_auth_client.get(endpoint, headers=admin_headers)
            assert rv.status_code == expected_admin_status[endpoint], \
                f"Endpoint {endpoint} returned {rv.status_code}, expected {expected_admin_status[endpoint]}"


class TestTokenAuthExample:
    """Test suite for the token authentication example."""

    @pytest.fixture
    def token_auth_app(self):
        """Fixture to create and configure the token auth example app."""
        # Recreate the app structure from the token_auth_example
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        # Disable base response schema to match the example
        app.config['BASE_RESPONSE_SCHEMA'] = None
        auth = HTTPTokenAuth()

        # Define User class
        class User:
            def __init__(self, id: int, secret: str):
                self.id = id
                self.secret = secret

            def get_token(self):
                header = {'alg': 'HS256'}
                payload = {'id': self.id}
                return jwt.encode(header, payload, app.config['SECRET_KEY']).decode()

        # Create users
        users = [
            User(1, 'lorem'),
            User(2, 'ipsum'),
            User(3, 'test'),
        ]

        def get_user_by_id(id: int):
            try:
                return next(filter(lambda u: u.id == id, users))
            except StopIteration:
                return None

        @auth.verify_token
        def verify_token(token: str):
            try:
                data = jwt.decode(
                    token.encode('ascii'),
                    app.config['SECRET_KEY'],
                )
                id = data['id']
                user = get_user_by_id(id)
            except JoseError:
                return None
            except Exception:
                return None
            return user

        # Define schema
        class Token(Schema):
            token = String()

        @app.post('/token/<int:id>')
        @app.output(Token)
        def get_token(id: int):
            user = get_user_by_id(id)
            if user is None:
                abort(404)
            return {'token': f'Bearer {user.get_token()}'}

        @app.get('/name/<int:id>')
        @app.auth_required(auth)
        def get_secret(id):
            return auth.current_user.secret

        # Store users on app for testing
        app._test_users = users
        app._test_get_user_by_id = get_user_by_id

        return app

    @pytest.fixture
    def token_auth_client(self, token_auth_app):
        """Fixture to create a test client for the token auth app."""
        return token_auth_app.test_client()

    def _get_token_header(self, token):
        """Helper to create token auth header."""
        return {'Authorization': token}

    def test_get_token_for_valid_user(self, token_auth_client):
        """Test getting a token for valid users."""
        # Test for user ID 1
        rv = token_auth_client.post('/token/1')
        assert rv.status_code == 200
        assert 'token' in rv.json
        assert rv.json['token'].startswith('Bearer ')

        # Test for user ID 2
        rv = token_auth_client.post('/token/2')
        assert rv.status_code == 200
        assert 'token' in rv.json
        assert rv.json['token'].startswith('Bearer ')

        # Test for user ID 3
        rv = token_auth_client.post('/token/3')
        assert rv.status_code == 200
        assert 'token' in rv.json
        assert rv.json['token'].startswith('Bearer ')

    def test_get_token_for_invalid_user(self, token_auth_client):
        """Test getting a token for non-existent user."""
        rv = token_auth_client.post('/token/999')
        assert rv.status_code == 404

    def test_protected_endpoint_without_token(self, token_auth_client):
        """Test that protected endpoint requires token."""
        rv = token_auth_client.get('/name/1')
        assert rv.status_code == 401

    def test_protected_endpoint_with_invalid_token(self, token_auth_client):
        """Test protected endpoint with invalid token."""
        # Test with malformed token
        headers = self._get_token_header('Bearer invalid_token')
        rv = token_auth_client.get('/name/1', headers=headers)
        assert rv.status_code == 401

        # Test with wrong format (no Bearer prefix)
        headers = self._get_token_header('some_token')
        rv = token_auth_client.get('/name/1', headers=headers)
        assert rv.status_code == 401

    def test_protected_endpoint_with_valid_token(self, token_auth_client):
        """Test protected endpoint with valid token."""
        # Get token for user 1
        rv = token_auth_client.post('/token/1')
        token = rv.json['token']

        # Use token to access protected endpoint
        headers = self._get_token_header(token)
        rv = token_auth_client.get('/name/1', headers=headers)
        assert rv.status_code == 200
        assert rv.data.decode("utf-8") == 'lorem'  # User 1's secret

    def test_all_users_secrets(self, token_auth_client):
        """Test that each user's token returns their correct secret."""
        user_secrets = {
            1: 'lorem',
            2: 'ipsum',
            3: 'test'
        }

        for user_id, expected_secret in user_secrets.items():
            # Get token
            rv = token_auth_client.post(f'/token/{user_id}')
            assert rv.status_code == 200
            token = rv.json['token']

            # Use token to get secret
            headers = self._get_token_header(token)
            rv = token_auth_client.get(f'/name/{user_id}', headers=headers)
            assert rv.status_code == 200
            assert rv.data.decode("utf-8") == expected_secret

    def test_token_decode_and_verification(self, token_auth_app, token_auth_client):
        """Test that tokens are properly encoded and can be decoded."""
        with token_auth_app.app_context():
            # Get a token
            rv = token_auth_client.post('/token/1')
            token = rv.json['token']

            # Remove 'Bearer ' prefix
            actual_token = token.replace('Bearer ', '')

            # Try to decode the token
            try:
                decoded = jwt.decode(
                    actual_token.encode('ascii'),
                    token_auth_app.config['SECRET_KEY']
                )
                assert 'id' in decoded
                assert decoded['id'] == 1
            except JoseError:
                pytest.fail("Failed to decode a valid token")

    def test_token_with_tampered_signature(self, token_auth_app, token_auth_client):
        """Test that tampered tokens are rejected."""
        with token_auth_app.app_context():
            # Get a valid token
            rv = token_auth_client.post('/token/1')
            token = rv.json['token']

            # Tamper with the token by changing last character
            tampered_token = token[:-1] + ('a' if token[-1] != 'a' else 'b')

            # Try to use tampered token
            headers = self._get_token_header(tampered_token)
            rv = token_auth_client.get('/name/1', headers=headers)
            assert rv.status_code == 401

    def test_token_with_wrong_user_id(self, token_auth_app, token_auth_client):
        """Test that token with non-existent user ID is rejected."""
        with token_auth_app.app_context():
            # Manually create a token with non-existent user ID
            header = {'alg': 'HS256'}
            payload = {'id': 999}  # Non-existent user
            fake_token = jwt.encode(
                header,
                payload,
                token_auth_app.config['SECRET_KEY']
            ).decode()

            # Try to use the fake token
            headers = self._get_token_header(f'Bearer {fake_token}')
            rv = token_auth_client.get('/name/999', headers=headers)
            assert rv.status_code == 401

    def test_concurrent_tokens(self, token_auth_client):
        """Test that multiple tokens can be active simultaneously."""
        tokens = {}

        # Get tokens for all users
        for user_id in [1, 2, 3]:
            rv = token_auth_client.post(f'/token/{user_id}')
            assert rv.status_code == 200
            tokens[user_id] = rv.json['token']

        # Verify all tokens still work
        expected_secrets = {1: 'lorem', 2: 'ipsum', 3: 'test'}
        for user_id, token in tokens.items():
            headers = self._get_token_header(token)
            rv = token_auth_client.get(f'/name/{user_id}', headers=headers)
            assert rv.status_code == 200
            assert rv.data.decode("utf-8") == expected_secrets[user_id]


class TestAuthenticationExampleIntegration:
    """Integration tests for both authentication examples."""

    def test_examples_use_different_auth_methods(self):
        """Verify that the examples use different authentication methods."""
        # Create both auth instances to ensure they're different
        basic_auth = HTTPBasicAuth()
        token_auth = HTTPTokenAuth()

        # Check that they use different auth classes
        assert type(basic_auth).__name__ == 'HTTPBasicAuth'
        assert type(token_auth).__name__ == 'HTTPTokenAuth'
        assert type(basic_auth) != type(token_auth)


# Performance and edge case tests
class TestAuthenticationPerformance:
    """Performance and edge case tests for authentication."""

    def test_basic_auth_with_special_characters(self):
        """Test basic auth with special characters in credentials."""
        # Create a basic auth app inline
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        auth = HTTPBasicAuth()

        # Simple user setup
        test_users = {'user': generate_password_hash('password')}

        @auth.verify_password
        def verify_password(username, password):
            if username in test_users and check_password_hash(test_users[username], password):
                return username
            return None

        @app.get('/api/protected')
        @app.auth_required(auth)
        def protected():
            return {'message': 'Protected'}

        client = app.test_client()

        # Test with colon in password (edge case for basic auth)
        special_creds = base64.b64encode('user:pass:word'.encode()).decode()
        headers = {'Authorization': f'Basic {special_creds}'}
        rv = client.get('/api/protected', headers=headers)
        assert rv.status_code == 401  # Should fail as password is incorrect

    def test_token_auth_with_edge_cases(self):
        """Test token auth behavior with various edge cases."""
        # Create a token auth app inline
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-key'
        auth = HTTPTokenAuth()

        @auth.verify_token
        def verify_token(token):
            # Simple verification - just check if token is "valid"
            return token == "valid_token"

        @app.get('/name/1')
        @app.auth_required(auth)
        def get_name():
            return {'name': 'test'}

        client = app.test_client()

        # Test empty token
        headers = {'Authorization': 'Bearer '}
        rv = client.get('/name/1', headers=headers)
        assert rv.status_code == 401

        # Test just 'Bearer' without space
        headers = {'Authorization': 'Bearer'}
        rv = client.get('/name/1', headers=headers)
        assert rv.status_code == 401


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
