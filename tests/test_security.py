"""
Comprehensive test suite for the security module in APIFlask
Tests HTTPBasicAuth and HTTPTokenAuth classes with their custom features
"""

import pytest
import base64
import time
from flask import g, Flask
from werkzeug.exceptions import Unauthorized, Forbidden

from apiflask import APIFlask, APIBlueprint
from apiflask.security import HTTPBasicAuth, HTTPTokenAuth
from apiflask.exceptions import HTTPError


class TestHTTPBasicAuth:
    """Tests for HTTPBasicAuth class"""

    def test_init_with_defaults(self):
        """Test HTTPBasicAuth initialization with default values"""
        auth = HTTPBasicAuth()
        assert auth.scheme == 'Basic'
        assert auth.realm == 'Authentication Required'
        assert auth.description is None
        assert auth.security_scheme_name is None

    def test_init_with_custom_values(self):
        """Test HTTPBasicAuth initialization with custom values"""
        auth = HTTPBasicAuth(
            scheme='CustomBasic',
            realm='Protected Area',
            description='Basic authentication for API access',
            security_scheme_name='MyBasicAuth'
        )
        assert auth.scheme == 'CustomBasic'
        assert auth.realm == 'Protected Area'
        assert auth.description == 'Basic authentication for API access'
        assert auth.security_scheme_name == 'MyBasicAuth'

    def test_current_user_property(self, app):
        """Test current_user property returns correct user"""
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            if username == 'test' and password == 'pass':
                return {'username': 'test', 'id': 1}
            return None

        @app.route('/test')
        @auth.login_required
        def test_route():
            # Check that current_user property works
            assert auth.current_user == {'username': 'test', 'id': 1}
            return {'user': auth.current_user}

        client = app.test_client()

        # Test without authentication
        rv = client.get('/test')
        assert rv.status_code == 401

        # Test with valid authentication
        rv = client.get('/test',
                       headers={'Authorization': 'Basic dGVzdDpwYXNz'})  # test:pass in base64
        assert rv.status_code == 200
        assert rv.json == {'user': {'username': 'test', 'id': 1}}

    def test_current_user_without_auth(self, app):
        """Test current_user returns None when not authenticated"""
        auth = HTTPBasicAuth()

        @app.route('/test')
        def test_route():
            return {'user': auth.current_user}

        client = app.test_client()
        rv = client.get('/test')
        assert rv.status_code == 200
        assert rv.json == {'user': None}

    def test_password_verification_flow(self, app):
        """Test the complete password verification flow"""
        auth = HTTPBasicAuth()
        verification_called = []

        @auth.verify_password
        def verify_password(username, password):
            verification_called.append((username, password))
            if username == 'admin' and password == 'secret':
                return {'username': 'admin', 'role': 'admin'}
            return None

        @app.route('/protected')
        @auth.login_required
        def protected():
            return {'message': 'success', 'user': auth.current_user}

        client = app.test_client()

        # Test invalid credentials
        rv = client.get('/protected',
                       headers={'Authorization': 'Basic YWRtaW46d3Jvbmc='})  # admin:wrong
        assert rv.status_code == 401
        assert verification_called[-1] == ('admin', 'wrong')

        # Test valid credentials
        rv = client.get('/protected',
                       headers={'Authorization': 'Basic YWRtaW46c2VjcmV0'})  # admin:secret
        assert rv.status_code == 200
        assert rv.json['user']['username'] == 'admin'
        assert verification_called[-1] == ('admin', 'secret')


class TestHTTPTokenAuth:
    """Tests for HTTPTokenAuth class"""

    def test_init_with_defaults(self):
        """Test HTTPTokenAuth initialization with default values"""
        auth = HTTPTokenAuth()
        assert auth.scheme == 'Bearer'
        assert auth.realm == 'Authentication Required'
        assert auth.header is None
        assert auth.description is None
        assert auth.security_scheme_name is None

    def test_init_with_custom_values(self):
        """Test HTTPTokenAuth initialization with custom values"""
        auth = HTTPTokenAuth(
            scheme='ApiKey',
            realm='API Access',
            header='X-API-Key',
            description='API key authentication',
            security_scheme_name='MyApiKey'
        )
        assert auth.scheme == 'ApiKey'
        assert auth.realm == 'API Access'
        assert auth.header == 'X-API-Key'
        assert auth.description == 'API key authentication'
        assert auth.security_scheme_name == 'MyApiKey'

    def test_bearer_token_verification(self, app):
        """Test Bearer token verification"""
        auth = HTTPTokenAuth()
        valid_tokens = {
            'token123': {'username': 'user1', 'id': 1},
            'token456': {'username': 'user2', 'id': 2}
        }

        @auth.verify_token
        def verify_token(token):
            return valid_tokens.get(token)

        @app.route('/api/data')
        @auth.login_required
        def api_data():
            return {'data': 'secret', 'user': auth.current_user}

        client = app.test_client()

        # Test without token
        rv = client.get('/api/data')
        assert rv.status_code == 401

        # Test with invalid token
        rv = client.get('/api/data',
                       headers={'Authorization': 'Bearer invalid'})
        assert rv.status_code == 401

        # Test with valid token
        rv = client.get('/api/data',
                       headers={'Authorization': 'Bearer token123'})
        assert rv.status_code == 200
        assert rv.json['user']['username'] == 'user1'

    def test_custom_header_token(self, app):
        """Test token verification with custom header"""
        auth = HTTPTokenAuth(header='X-API-Key')

        @auth.verify_token
        def verify_token(token):
            if token == 'valid-api-key':
                return {'api_key': token}
            return None

        @app.route('/api/resource')
        @auth.login_required
        def api_resource():
            return {'resource': 'data', 'auth': auth.current_user}

        client = app.test_client()

        # Test without custom header
        rv = client.get('/api/resource')
        assert rv.status_code == 401

        # Test with wrong header
        rv = client.get('/api/resource',
                       headers={'Authorization': 'Bearer valid-api-key'})
        assert rv.status_code == 401

        # Test with correct custom header
        rv = client.get('/api/resource',
                       headers={'X-API-Key': 'valid-api-key'})
        assert rv.status_code == 200
        assert rv.json['auth']['api_key'] == 'valid-api-key'

    def test_current_user_property_token(self, app):
        """Test current_user property with token auth"""
        auth = HTTPTokenAuth()

        @auth.verify_token
        def verify_token(token):
            if token == 'user-token':
                return {'username': 'testuser', 'token': token}
            return None

        @app.route('/profile')
        @auth.login_required
        def profile():
            user = auth.current_user
            assert user is not None
            assert user['username'] == 'testuser'
            return {'profile': user}

        client = app.test_client()

        rv = client.get('/profile',
                       headers={'Authorization': 'Bearer user-token'})
        assert rv.status_code == 200
        assert rv.json['profile']['username'] == 'testuser'

    def test_token_auth_with_custom_scheme(self, app):
        """Test token auth with custom scheme name"""
        auth = HTTPTokenAuth(scheme='JWT')

        @auth.verify_token
        def verify(token):
            if token == 'valid-jwt':
                return {'token': token}
            return None

        @app.route('/api/data')
        @auth.login_required
        def api_data():
            return {'data': 'protected'}

        client = app.test_client()

        # Test with Bearer scheme (should fail)
        rv = client.get('/api/data',
                       headers={'Authorization': 'Bearer valid-jwt'})
        assert rv.status_code == 401

        # Test with JWT scheme
        rv = client.get('/api/data',
                       headers={'Authorization': 'JWT valid-jwt'})
        assert rv.status_code == 200

    def test_malformed_authorization_header(self, app):
        """Test various malformed authorization headers"""
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            if username == 'test' and password == 'pass':
                return {'username': 'test', 'id': 1}
            return None

        @app.route('/test')
        @auth.login_required
        def test():
            return {'ok': True}

        client = app.test_client()

        # Test various malformed headers
        malformed_headers = [
            {'Authorization': ''},  # Empty
            {'Authorization': 'Basic'},  # Missing credentials
            {'Authorization': 'Basic '},  # Missing credentials with space
            {'Authorization': 'NotBasic dGVzdDp0ZXN0'},  # Wrong scheme
            {'Authorization': 'Basic @#$%^&*'},  # Invalid base64
            {'Authorization': 'Basic ' + base64.b64encode(b'onlyusername').decode()},  # Missing password
        ]

        for headers in malformed_headers:
            rv = client.get('/test', headers=headers)
            assert rv.status_code == 401, f"Failed for headers: {headers}"

class TestMultipleAuthMethods:
    """Test scenarios with multiple authentication methods"""

    def test_different_auth_per_endpoint(self, app):
        """Test different auth methods for different endpoints"""
        basic_auth = HTTPBasicAuth()
        token_auth = HTTPTokenAuth()

        @basic_auth.verify_password
        def verify_password(username, password):
            if username == 'user' and password == 'pass':
                return {'auth_type': 'basic', 'username': username}
            return None

        @token_auth.verify_token
        def verify_token(token):
            if token == 'valid-token':
                return {'auth_type': 'token', 'token': token}
            return None

        @app.route('/basic-endpoint')
        @basic_auth.login_required
        def basic_endpoint():
            return {'auth': basic_auth.current_user}

        @app.route('/token-endpoint')
        @token_auth.login_required
        def token_endpoint():
            return {'auth': token_auth.current_user}

        client = app.test_client()

        # Test basic auth endpoint with basic credentials
        rv = client.get('/basic-endpoint',
                       headers={'Authorization': 'Basic dXNlcjpwYXNz'})
        assert rv.status_code == 200
        assert rv.json['auth']['auth_type'] == 'basic'

        # Test token endpoint with bearer token
        rv = client.get('/token-endpoint',
                       headers={'Authorization': 'Bearer valid-token'})
        assert rv.status_code == 200
        assert rv.json['auth']['auth_type'] == 'token'

        # Test cross-auth (should fail)
        rv = client.get('/basic-endpoint',
                       headers={'Authorization': 'Bearer valid-token'})
        assert rv.status_code == 401

        rv = client.get('/token-endpoint',
                       headers={'Authorization': 'Basic dXNlcjpwYXNz'})
        assert rv.status_code == 401

    def test_auth_isolation_between_instances(self, app):
        """Test that different auth instances maintain isolation"""
        auth1 = HTTPBasicAuth()
        auth2 = HTTPBasicAuth()

        users1 = []
        users2 = []

        @auth1.verify_password
        def verify1(username, password):
            users1.append(username)
            if username == 'user1':
                return {'id': 1, 'username': username}
            return None

        @auth2.verify_password
        def verify2(username, password):
            users2.append(username)
            if username == 'user2':
                return {'id': 2, 'username': username}
            return None

        @app.route('/area1')
        @auth1.login_required
        def area1():
            return {'user': auth1.current_user}

        @app.route('/area2')
        @auth2.login_required
        def area2():
            return {'user': auth2.current_user}

        client = app.test_client()

        # Test with user1 on area1
        creds1 = base64.b64encode(b'user1:pass').decode()
        rv = client.get('/area1',
                       headers={'Authorization': f'Basic {creds1}'})
        assert rv.status_code == 200
        assert rv.json['user']['username'] == 'user1'
        assert 'user1' in users1
        assert 'user1' not in users2  # Should not have been verified by auth2

        # Test with user2 on area2
        creds2 = base64.b64encode(b'user2:pass').decode()
        rv = client.get('/area2',
                       headers={'Authorization': f'Basic {creds2}'})
        assert rv.status_code == 200
        assert rv.json['user']['username'] == 'user2'
        assert 'user2' in users2
        assert 'user2' not in users1  # Should not have been verified by auth1

class TestAuthErrorHandling:
    """Tests for authentication error handling"""

    def test_default_error_handler_json_mode(self, app):
        """Test default error handler returns JSON errors when json_errors=True"""
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            return None  # Always fail

        @app.route('/protected')
        @auth.login_required
        def protected():
            return {'data': 'secret'}

        # APIFlask has json_errors=True by default
        client = app.test_client()
        rv = client.get('/protected')
        assert rv.status_code == 401
        assert rv.json is not None
        # Check that it returns JSON error format
        assert 'message' in rv.json or 'detail' in rv.json or 'error' in rv.json

    def test_default_error_handler_non_json_mode(self, app):
        """Test default error handler returns text errors when json_errors=False"""
        app.json_errors = False
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            return None  # Always fail

        @app.route('/protected')
        @auth.login_required
        def protected():
            return {'data': 'secret'}

        client = app.test_client()
        rv = client.get('/protected')
        assert rv.status_code == 401
        # In non-JSON mode, it should return plain text
        assert rv.content_type != 'application/json'

    def test_custom_error_processor(self, app):
        """Test that custom error processor receives HTTPError instance"""
        auth = HTTPTokenAuth()
        received_errors = []

        @auth.error_processor
        def handle_auth_error(error):
            received_errors.append(error)
            # Verify it's an HTTPError instance
            assert isinstance(error, HTTPError)
            assert hasattr(error, 'status_code')
            assert hasattr(error, 'message')

            return {
                'custom_error': True,
                'status': error.status_code,
                'detail': str(error.message)
            }, error.status_code

        @auth.verify_token
        def verify_token(token):
            return None  # Always fail

        @app.route('/api/protected')
        @auth.login_required
        def protected():
            return {'data': 'protected'}

        client = app.test_client()
        rv = client.get('/api/protected')

        assert rv.status_code == 401
        assert len(received_errors) == 1
        assert received_errors[0].status_code == 401

        data = rv.get_json()
        assert data['custom_error'] is True
        assert data['status'] == 401

    def test_error_processor_with_roles_forbidden(self, app):
        """Test error processor handles 403 Forbidden for role-based access"""
        auth = HTTPBasicAuth()
        error_log = []

        @auth.error_processor
        def log_errors(error):
            error_log.append({
                'status': error.status_code,
                'message': error.message
            })
            return {'error': 'Access Denied', 'code': error.status_code}, error.status_code

        @auth.verify_password
        def verify_password(username, password):
            if username == 'user' and password == 'pass':
                return {'username': 'user'}
            return None

        @auth.get_user_roles
        def get_roles(user):
            return 'user'  # Regular user, not admin

        @app.route('/admin')
        @app.auth_required(auth, roles=['admin'])
        def admin_area():
            return {'area': 'admin'}

        client = app.test_client()

        # Authenticate as regular user trying to access admin area
        rv = client.get('/admin',
                       headers={'Authorization': 'Basic dXNlcjpwYXNz'})  # user:pass

        assert rv.status_code == 403  # Forbidden, not 401
        assert len(error_log) == 1
        assert error_log[0]['status'] == 403

        data = rv.get_json()
        assert data['error'] == 'Access Denied'
        assert data['code'] == 403

    def test_multiple_auth_schemes_error_handling(self, app):
        """Test error handling with multiple auth schemes"""
        basic_auth = HTTPBasicAuth()
        token_auth = HTTPTokenAuth()

        @basic_auth.verify_password
        def verify_password(username, password):
            return None

        @token_auth.verify_token
        def verify_token(token):
            return None

        @app.route('/basic-protected')
        @basic_auth.login_required
        def basic_protected():
            return {'auth': 'basic'}

        @app.route('/token-protected')
        @token_auth.login_required
        def token_protected():
            return {'auth': 'token'}

        client = app.test_client()

        # Test basic auth endpoint
        rv = client.get('/basic-protected')
        assert rv.status_code == 401

        # Test token auth endpoint
        rv = client.get('/token-protected')
        assert rv.status_code == 401

        # Both should return JSON errors by default
        rv = client.get('/basic-protected')
        assert rv.content_type == 'application/json'

        rv = client.get('/token-protected')
        assert rv.content_type == 'application/json'


class TestAuthIntegration:
    """Integration tests for authentication with APIFlask features"""

    def test_auth_with_method_view(self, app):
        """Test authentication with Flask MethodView"""
        from flask.views import MethodView

        auth = HTTPTokenAuth()
        tokens = {
            'read-token': {'permission': 'read'},
            'write-token': {'permission': 'write'}
        }

        @auth.verify_token
        def verify_token(token):
            return tokens.get(token)

        @app.route('/resource')
        class ResourceView(MethodView):
            decorators = [auth.login_required]

            def get(self):
                return {'action': 'read', 'user': auth.current_user}

            def post(self):
                user = auth.current_user
                if user.get('permission') != 'write':
                    return {'error': 'Write permission required'}, 403
                return {'action': 'write', 'user': user}

        client = app.test_client()

        # Test GET without auth
        rv = client.get('/resource')
        assert rv.status_code == 401

        # Test GET with read token
        rv = client.get('/resource',
                       headers={'Authorization': 'Bearer read-token'})
        assert rv.status_code == 200
        assert rv.json['action'] == 'read'

        # Test POST with read token (should succeed auth but fail permission)
        rv = client.post('/resource',
                        headers={'Authorization': 'Bearer read-token'})
        assert rv.status_code == 403

        # Test POST with write token
        rv = client.post('/resource',
                        headers={'Authorization': 'Bearer write-token'})
        assert rv.status_code == 200
        assert rv.json['action'] == 'write'

    def test_optional_auth(self, app):
        """Test optional authentication pattern"""
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            if username == 'user' and password == 'pass':
                return {'username': username, 'premium': True}
            return None

        @app.route('/content')
        @auth.login_required(optional=True)
        def content():
            user = auth.current_user
            if user and user.get('premium'):
                return {'content': 'Premium content', 'user': user}
            return {'content': 'Basic content', 'user': user}

        client = app.test_client()

        # Test without auth - should work but return basic content
        rv = client.get('/content')
        assert rv.status_code == 200
        assert rv.json['content'] == 'Basic content'
        assert rv.json['user'] is None

        # Test with auth - should return premium content
        rv = client.get('/content',
                       headers={'Authorization': 'Basic dXNlcjpwYXNz'})  # user:pass
        assert rv.status_code == 200
        assert rv.json['content'] == 'Premium content'
        assert rv.json['user']['username'] == 'user'

    def test_auth_in_blueprint(self, app):
        """Test authentication in APIBlueprint"""
        from apiflask import APIBlueprint

        bp = APIBlueprint('api', __name__, url_prefix='/api')
        auth = HTTPTokenAuth()

        @auth.verify_token
        def verify_token(token):
            if token == 'valid-token':
                return {'token': token}
            return None

        @bp.route('/data')
        @auth.login_required
        def get_data():
            return {'data': 'protected', 'auth': auth.current_user}

        app.register_blueprint(bp)
        client = app.test_client()

        # Test without token
        rv = client.get('/api/data')
        assert rv.status_code == 401

        # Test with valid token
        rv = client.get('/api/data',
                       headers={'Authorization': 'Bearer valid-token'})
        assert rv.status_code == 200
        assert rv.json['data'] == 'protected'

    def test_multiple_auth_instances(self, app):
        """Test multiple instances of auth objects"""
        user_auth = HTTPBasicAuth()
        admin_auth = HTTPBasicAuth()

        @user_auth.verify_password
        def verify_user(username, password):
            if username == 'user' and password == 'userpass':
                return {'username': username, 'type': 'user'}
            return None

        @admin_auth.verify_password
        def verify_admin(username, password):
            if username == 'admin' and password == 'adminpass':
                return {'username': username, 'type': 'admin'}
            return None

        @app.route('/user/profile')
        @user_auth.login_required
        def user_profile():
            return {'profile': user_auth.current_user}

        @app.route('/admin/dashboard')
        @admin_auth.login_required
        def admin_dashboard():
            return {'dashboard': admin_auth.current_user}

        client = app.test_client()

        # Test user auth on user endpoint
        rv = client.get('/user/profile',
                       headers={'Authorization': 'Basic dXNlcjp1c2VycGFzcw=='})  # user:userpass
        assert rv.status_code == 200
        assert rv.json['profile']['type'] == 'user'

        # Test admin auth on admin endpoint
        rv = client.get('/admin/dashboard',
                       headers={'Authorization': 'Basic YWRtaW46YWRtaW5wYXNz'})  # admin:adminpass
        assert rv.status_code == 200
        assert rv.json['dashboard']['type'] == 'admin'

        # Test user auth on admin endpoint (should fail)
        rv = client.get('/admin/dashboard',
                       headers={'Authorization': 'Basic dXNlcjp1c2VycGFzcw=='})
        assert rv.status_code == 401


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_empty_credentials(self, app):
        """Test handling of empty credentials"""
        auth = HTTPBasicAuth()
        verify_calls = []

        @auth.verify_password
        def verify_password(username, password):
            verify_calls.append((username, password))
            if username and password:
                return {'username': username}
            return None

        @app.route('/secure')
        @auth.login_required
        def secure():
            return {'user': auth.current_user}

        client = app.test_client()

        # Test with empty Authorization header value
        rv = client.get('/secure', headers={'Authorization': 'Basic '})
        assert rv.status_code == 401

        # Test with malformed base64
        rv = client.get('/secure', headers={'Authorization': 'Basic malformed'})
        assert rv.status_code == 401

    def test_unicode_credentials(self, app):
        """Test handling of unicode in credentials"""
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            # Test unicode handling
            if username == 'user' and password == 'пароль':  # Russian for "password"
                return {'username': username}
            return None

        @app.route('/secure')
        @auth.login_required
        def secure():
            return {'user': auth.current_user}

        client = app.test_client()

        # Test with unicode password (base64 encoded "user:пароль")
        import base64
        creds = base64.b64encode('user:пароль'.encode('utf-8')).decode('ascii')
        rv = client.get('/secure',
                       headers={'Authorization': f'Basic {creds}'})
        # This will work or fail depending on Flask-HTTPAuth's unicode handling

    def test_auth_without_verify_callback(self, app):
        """Test authentication without setting verify callback"""
        auth = HTTPBasicAuth()

        @app.route('/secure')
        @auth.login_required
        def secure():
            return {'data': 'should not reach here'}

        client = app.test_client()

        # Should fail since no verify callback is set
        rv = client.get('/secure',
                       headers={'Authorization': 'Basic dXNlcjpwYXNz'})
        assert rv.status_code == 401

    def test_concurrent_requests_isolation(self, app):
        """Test that auth state is properly isolated between requests"""
        auth = HTTPTokenAuth()

        @auth.verify_token
        def verify_token(token):
            if token == 'user1-token':
                return {'id': 1, 'username': 'user1'}
            elif token == 'user2-token':
                return {'id': 2, 'username': 'user2'}
            return None

        @app.route('/whoami')
        @auth.login_required
        def whoami():
            return {'user': auth.current_user}

        client = app.test_client()

        # Simulate concurrent requests with different users
        rv1 = client.get('/whoami',
                        headers={'Authorization': 'Bearer user1-token'})
        rv2 = client.get('/whoami',
                        headers={'Authorization': 'Bearer user2-token'})

        assert rv1.json['user']['username'] == 'user1'
        assert rv2.json['user']['username'] == 'user2'
        assert rv1.json['user']['id'] != rv2.json['user']['id']

    def test_auth_state_cleanup(self, app):
        """Test that auth state is cleaned up between requests"""
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            if username == 'test' and password == 'test':
                return {'username': 'test'}
            return None

        @app.route('/public')
        def public():
            # This should not have any auth state
            return {'user': auth.current_user}

        @app.route('/private')
        @auth.login_required
        def private():
            return {'user': auth.current_user}

        client = app.test_client()

        # First make authenticated request
        rv = client.get('/private',
                       headers={'Authorization': 'Basic dGVzdDp0ZXN0'})  # test:test
        assert rv.status_code == 200
        assert rv.json['user']['username'] == 'test'

        # Then make unauthenticated request to public endpoint
        rv = client.get('/public')
        assert rv.status_code == 200
        assert rv.json['user'] is None  # Should be None, not the previous user

class TestPerformanceAndCaching:
    """Test performance-related aspects of authentication"""

    def test_auth_caching_within_request(self, app):
        """Test that auth verification is cached within a single request"""
        auth = HTTPBasicAuth()
        verification_count = []

        @auth.verify_password
        def verify_password(username, password):
            verification_count.append(1)
            if username == 'user' and password == 'pass':
                return {'username': username, 'count': len(verification_count)}
            return None

        @app.route('/test')
        @auth.login_required
        def test_route():
            # Access current_user multiple times
            user1 = auth.current_user
            user2 = auth.current_user
            user3 = auth.current_user

            # Should be the same object
            assert user1 is user2 is user3

            # Verification should only happen once
            return {'user': user1, 'verifications': len(verification_count)}

        client = app.test_client()

        # Reset counter
        verification_count.clear()

        rv = client.get('/test',
                       headers={'Authorization': 'Basic dXNlcjpwYXNz'})
        assert rv.status_code == 200
        # Should only verify once despite multiple current_user accesses
        assert rv.json['verifications'] == 1

    def test_no_auth_caching_between_requests(self, app):
        """Test that auth is not cached between different requests"""
        auth = HTTPTokenAuth()
        request_id = 0

        @auth.verify_token
        def verify_token(token):
            nonlocal request_id
            request_id += 1
            if token == 'valid':
                return {'token': token, 'request_id': request_id}
            return None

        @app.route('/test')
        @auth.login_required
        def test_route():
            return auth.current_user

        client = app.test_client()

        # Make multiple requests
        results = []
        for i in range(3):
            rv = client.get('/test',
                           headers={'Authorization': 'Bearer valid'})
            assert rv.status_code == 200
            results.append(rv.json['request_id'])

        # Each request should have a different request_id
        assert results == [1, 2, 3]

    def test_expensive_user_lookup_optimization(self, app):
        """Test pattern for optimizing expensive user lookups"""
        auth = HTTPBasicAuth()
        db_queries = []

        # Simulate expensive database lookup
        def get_user_from_db(username):
            db_queries.append(username)
            time.sleep(0.01)  # Simulate DB delay
            if username == 'user':
                return {'id': 1, 'username': username, 'email': 'user@example.com'}
            return None

        @auth.verify_password
        def verify_password(username, password):
            if password != 'correct':
                return None

            # Only do expensive lookup if password is correct
            user = get_user_from_db(username)
            return user

        @app.route('/profile')
        @auth.login_required
        def profile():
            user = auth.current_user
            # Multiple accesses should not trigger multiple DB queries
            return {
                'id': user['id'],
                'username': user['username'],
                'email': user['email'],
                'queries': len(db_queries)
            }

        client = app.test_client()

        # Test with wrong password - should not query DB
        db_queries.clear()
        rv = client.get('/profile',
                       headers={'Authorization': 'Basic dXNlcjp3cm9uZw=='})  # user:wrong
        assert rv.status_code == 401
        assert len(db_queries) == 0  # No DB query for wrong password

        # Test with correct password
        db_queries.clear()
        rv = client.get('/profile',
                       headers={'Authorization': 'Basic dXNlcjpjb3JyZWN0'})  # user:correct
        assert rv.status_code == 200
        assert rv.json['queries'] == 1  # Only one DB query

class TestComplexBlueprints:
    """Test complex blueprint scenarios with authentication"""

    def test_nested_blueprint_auth(self, app):
        """Test authentication in nested blueprints"""
        # Create nested blueprint structure
        api = APIBlueprint('api', __name__, url_prefix='/api')
        v1 = APIBlueprint('v1', __name__, url_prefix='/v1')
        v2 = APIBlueprint('v2', __name__, url_prefix='/v2')

        # Different auth for different versions
        auth_v1 = HTTPBasicAuth()
        auth_v2 = HTTPTokenAuth()

        @auth_v1.verify_password
        def verify_v1(username, password):
            if username == 'v1user' and password == 'v1pass':
                return {'username': username, 'version': 1}
            return None

        @auth_v2.verify_token
        def verify_v2(token):
            if token == 'v2-token':
                return {'token': token, 'version': 2}
            return None

        @v1.route('/data')
        @auth_v1.login_required
        def v1_data():
            return {'version': 1, 'user': auth_v1.current_user}

        @v2.route('/data')
        @auth_v2.login_required
        def v2_data():
            return {'version': 2, 'user': auth_v2.current_user}

        # Register nested blueprints
        api.register_blueprint(v1)
        api.register_blueprint(v2)
        app.register_blueprint(api)

        client = app.test_client()

        # Test v1 endpoint with basic auth
        rv = client.get('/api/v1/data',
                       headers={'Authorization': 'Basic djF1c2VyOnYxcGFzcw=='})  # v1user:v1pass
        assert rv.status_code == 200
        assert rv.json['version'] == 1
        assert rv.json['user']['version'] == 1

        # Test v2 endpoint with token auth
        rv = client.get('/api/v2/data',
                       headers={'Authorization': 'Bearer v2-token'})
        assert rv.status_code == 200
        assert rv.json['version'] == 2
        assert rv.json['user']['version'] == 2

        # Test cross-version auth (should fail)
        rv = client.get('/api/v1/data',
                       headers={'Authorization': 'Bearer v2-token'})
        assert rv.status_code == 401

        rv = client.get('/api/v2/data',
                       headers={'Authorization': 'Basic djF1c2VyOnYxcGFzcw=='})
        assert rv.status_code == 401

    def test_blueprint_auth_inheritance(self, app):
        """Test auth inheritance in blueprint hierarchies"""
        # Parent blueprint with auth
        api = APIBlueprint('api', __name__, url_prefix='/api')
        auth = HTTPTokenAuth()

        @auth.verify_token
        def verify_token(token):
            if token == 'api-token':
                return {'token': token, 'level': 'api'}
            return None

        # Apply auth to all routes in blueprint
        @api.before_request
        @auth.login_required
        def check_auth():
            pass

        @api.route('/info')
        def api_info():
            return {'info': 'API info', 'user': auth.current_user}

        # Child endpoints
        @api.route('/users')
        def users():
            return {'users': [], 'auth': auth.current_user}

        @api.route('/public')
        def public():
            # This will still require auth due to before_request
            return {'data': 'not really public'}

        app.register_blueprint(api)
        client = app.test_client()

        # All endpoints should require auth
        endpoints = ['/api/info', '/api/users', '/api/public']

        for endpoint in endpoints:
            # Without token
            rv = client.get(endpoint)
            assert rv.status_code == 401, f"{endpoint} should require auth"

            # With token
            rv = client.get(endpoint,
                           headers={'Authorization': 'Bearer api-token'})
            assert rv.status_code == 200, f"{endpoint} should work with token"
