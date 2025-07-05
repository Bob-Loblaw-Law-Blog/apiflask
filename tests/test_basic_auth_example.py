"""
Unit tests for the Basic Authentication Example
"""
import pytest
import base64
import sys
import os
from importlib import reload


@pytest.fixture
def client():
    """Create test client for the basic auth example app"""
    # Add the example path to sys.path
    app_path = os.path.join(
        os.path.dirname(__file__), 
        '../inputs/apiflask/examples/authentication/basic_auth_example'
    )
    sys.path.insert(0, app_path)
    
    # Import and reload the app module
    import app
    app = reload(app)
    
    # Get the Flask app instance and set testing mode
    _app = app.app
    _app.testing = True
    
    # Clean up sys.path
    sys.path.remove(app_path)
    
    # Return test client
    return _app.test_client()


def get_auth_header(username, password):
    """Helper function to create basic auth header"""
    credentials = f"{username}:{password}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return {'Authorization': f'Basic {encoded}'}


class TestPublicEndpoints:
    """Test public endpoints that don't require authentication"""
    
    def test_index_no_auth(self, client):
        """Test that index endpoint is accessible without authentication"""
        rv = client.get('/')
        assert rv.status_code == 200
        assert rv.json['message'] == 'Welcome to the Authentication Example API!'


class TestProtectedEndpoint:
    """Test the /api/protected endpoint"""
    
    def test_protected_no_auth(self, client):
        """Test that protected endpoint returns 401 without authentication"""
        rv = client.get('/api/protected')
        assert rv.status_code == 401
        assert 'WWW-Authenticate' in rv.headers
        assert 'Basic' in rv.headers['WWW-Authenticate']
    
    def test_protected_invalid_credentials(self, client):
        """Test protected endpoint with invalid credentials"""
        rv = client.get('/api/protected', headers=get_auth_header('invalid', 'wrong'))
        assert rv.status_code == 401
        assert 'Authentication failed' in rv.json['detail']
    
    def test_protected_valid_user(self, client):
        """Test protected endpoint with valid user credentials"""
        rv = client.get('/api/protected', headers=get_auth_header('user', 'password'))
        assert rv.status_code == 200
        assert rv.json['message'] == 'Hello, user! You accessed a protected endpoint.'
        assert rv.json['code'] == 200
    
    def test_protected_valid_admin(self, client):
        """Test protected endpoint with valid admin credentials"""
        rv = client.get('/api/protected', headers=get_auth_header('admin', 'admin-password'))
        assert rv.status_code == 200
        assert rv.json['message'] == 'Hello, admin! You accessed a protected endpoint.'
        assert rv.json['code'] == 200


class TestAdminEndpoint:
    """Test the /api/admin endpoint"""
    
    def test_admin_no_auth(self, client):
        """Test that admin endpoint returns 401 without authentication"""
        rv = client.get('/api/admin')
        assert rv.status_code == 401
    
    def test_admin_invalid_credentials(self, client):
        """Test admin endpoint with invalid credentials"""
        rv = client.get('/api/admin', headers=get_auth_header('hacker', 'attempt'))
        assert rv.status_code == 401
    
    def test_admin_regular_user(self, client):
        """Test admin endpoint with regular user credentials"""
        rv = client.get('/api/admin', headers=get_auth_header('user', 'password'))
        assert rv.status_code == 403
        assert 'Admin access required' in rv.json['message']
    
    def test_admin_valid_admin(self, client):
        """Test admin endpoint with valid admin credentials"""
        rv = client.get('/api/admin', headers=get_auth_header('admin', 'admin-password'))
        assert rv.status_code == 200
        assert rv.json['message'] == 'Hello, admin admin! You accessed an admin-only endpoint.'
        assert rv.json['code'] == 200


class TestUserInfoEndpoint:
    """Test the /api/me endpoint"""
    
    def test_me_no_auth(self, client):
        """Test that user info endpoint returns 401 without authentication"""
        rv = client.get('/api/me')
        assert rv.status_code == 401
    
    def test_me_invalid_credentials(self, client):
        """Test user info endpoint with invalid credentials"""
        rv = client.get('/api/me', headers=get_auth_header('fake', 'user'))
        assert rv.status_code == 401
    
    def test_me_regular_user(self, client):
        """Test user info endpoint with regular user credentials"""
        rv = client.get('/api/me', headers=get_auth_header('user', 'password'))
        assert rv.status_code == 200
        assert rv.json['username'] == 'user'
        assert rv.json['role'] == 'user'
    
    def test_me_admin_user(self, client):
        """Test user info endpoint with admin credentials"""
        rv = client.get('/api/me', headers=get_auth_header('admin', 'admin-password'))
        assert rv.status_code == 200
        assert rv.json['username'] == 'admin'
        assert rv.json['role'] == 'admin'


class TestAuthenticationFormats:
    """Test various authentication header formats"""
    
    def test_missing_auth_header(self, client):
        """Test request without Authorization header"""
        rv = client.get('/api/protected')
        assert rv.status_code == 401
    
    def test_wrong_auth_scheme(self, client):
        """Test with wrong authentication scheme"""
        rv = client.get('/api/protected', headers={'Authorization': 'Bearer some-token'})
        assert rv.status_code == 401
    
    def test_malformed_auth_header(self, client):
        """Test with malformed Authorization header"""
        rv = client.get('/api/protected', headers={'Authorization': 'Basic malformed'})
        assert rv.status_code == 401
    
    def test_empty_credentials(self, client):
        """Test with empty username and password"""
        rv = client.get('/api/protected', headers=get_auth_header('', ''))
        assert rv.status_code == 401
    
    def test_case_sensitive_username(self, client):
        """Test that username is case sensitive"""
        rv = client.get('/api/protected', headers=get_auth_header('USER', 'password'))
        assert rv.status_code == 401
        
        rv = client.get('/api/protected', headers=get_auth_header('Admin', 'admin-password'))
        assert rv.status_code == 401


class TestErrorHandling:
    """Test error handling and error responses"""
    
    def test_401_error_format(self, client):
        """Test the format of 401 error responses"""
        rv = client.get('/api/protected')
        assert rv.status_code == 401
        assert 'status_code' in rv.json
        assert rv.json['status_code'] == 401
        assert 'message' in rv.json
        assert 'detail' in rv.json
        assert rv.json['detail'] == 'Authentication failed. Please provide valid credentials.'
    
    def test_403_error_format(self, client):
        """Test the format of 403 error responses"""
        rv = client.get('/api/admin', headers=get_auth_header('user', 'password'))
        assert rv.status_code == 403
        assert 'message' in rv.json
        assert 'Admin access required' in rv.json['message']


class TestConcurrentRequests:
    """Test handling of concurrent requests with different users"""
    
    def test_user_isolation(self, client):
        """Test that different users don't interfere with each other"""
        # Make request as user
        rv1 = client.get('/api/me', headers=get_auth_header('user', 'password'))
        assert rv1.status_code == 200
        assert rv1.json['username'] == 'user'
        
        # Make request as admin
        rv2 = client.get('/api/me', headers=get_auth_header('admin', 'admin-password'))
        assert rv2.status_code == 200
        assert rv2.json['username'] == 'admin'
        
        # Make another request as user to ensure no state bleeding
        rv3 = client.get('/api/me', headers=get_auth_header('user', 'password'))
        assert rv3.status_code == 200
        assert rv3.json['username'] == 'user'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
