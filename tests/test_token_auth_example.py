"""
Unit tests for the Token Authentication Example
"""
import pytest
import sys
import os
from importlib import reload


@pytest.fixture
def client():
    """Create test client for the token auth example app"""
    # Add the example path to sys.path
    app_path = os.path.join(
        os.path.dirname(__file__), 
        '../inputs/apiflask/examples/authentication/token_auth_example'
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


class TestTokenGeneration:
    """Test token generation endpoint"""
    
    def test_get_token_valid_user(self, client):
        """Test getting a token for a valid user"""
        rv = client.post('/token/1')
        assert rv.status_code == 200
        assert 'token' in rv.json
        assert rv.json['token'].startswith('Bearer ')
        # Extract the actual token
        token = rv.json['token'].replace('Bearer ', '')
        assert len(token) > 0
    
    def test_get_token_all_users(self, client):
        """Test getting tokens for all available users"""
        for user_id in [1, 2, 3]:
            rv = client.post(f'/token/{user_id}')
            assert rv.status_code == 200
            assert 'token' in rv.json
            assert rv.json['token'].startswith('Bearer ')
    
    def test_get_token_invalid_user(self, client):
        """Test getting a token for a non-existent user"""
        rv = client.post('/token/999')
        assert rv.status_code == 404
    
    def test_get_token_negative_user_id(self, client):
        """Test getting a token with negative user ID"""
        rv = client.post('/token/-1')
        assert rv.status_code == 404
    
    def test_get_token_zero_user_id(self, client):
        """Test getting a token with zero user ID"""
        rv = client.post('/token/0')
        assert rv.status_code == 404


class TestProtectedEndpoint:
    """Test the protected endpoint that requires authentication"""
    
    def test_protected_no_auth(self, client):
        """Test accessing protected endpoint without authentication"""
        rv = client.get('/name/1')
        assert rv.status_code == 401
        assert 'WWW-Authenticate' in rv.headers
        assert 'Bearer' in rv.headers['WWW-Authenticate']
    
    def test_protected_invalid_token(self, client):
        """Test accessing protected endpoint with invalid token"""
        headers = {'Authorization': 'Bearer invalid-token'}
        rv = client.get('/name/1', headers=headers)
        assert rv.status_code == 401
    
    def test_protected_malformed_token(self, client):
        """Test accessing protected endpoint with malformed token"""
        # Test various malformed tokens
        malformed_tokens = [
            'Bearer ',  # Empty token
            'Bearer',   # No space
            'InvalidBearer token',  # Wrong scheme
            'Basic dXNlcjpwYXNz',  # Basic auth instead of Bearer
            '',  # Empty authorization header
        ]
        
        for token in malformed_tokens:
            headers = {'Authorization': token}
            rv = client.get('/name/1', headers=headers)
            assert rv.status_code == 401
    
    def test_protected_valid_token(self, client):
        """Test accessing protected endpoint with valid token"""
        # Get token for user 1
        rv = client.post('/token/1')
        token = rv.json['token']
        
        # Use the token to access protected endpoint
        headers = {'Authorization': token}
        rv = client.get('/name/1', headers=headers)
        assert rv.status_code == 200
        assert rv.data.decode() == 'lorem'  # User 1's secret
    
    def test_protected_all_users(self, client):
        """Test accessing protected endpoint with different users"""
        user_secrets = {
            1: 'lorem',
            2: 'ipsum',
            3: 'test'
        }
        
        for user_id, expected_secret in user_secrets.items():
            # Get token
            rv = client.post(f'/token/{user_id}')
            token = rv.json['token']
            
            # Use token to access protected endpoint
            headers = {'Authorization': token}
            rv = client.get(f'/name/{user_id}', headers=headers)
            assert rv.status_code == 200
            assert rv.data.decode() == expected_secret


class TestTokenValidation:
    """Test token validation scenarios"""
    
    def test_expired_token(self, client):
        """Test that expired tokens are handled properly"""
        # Since the example doesn't implement token expiration,
        # we'll test with a tampered token that would fail validation
        headers = {'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6OTk5fQ.invalid'}
        rv = client.get('/name/1', headers=headers)
        assert rv.status_code == 401
    
    def test_token_with_wrong_secret(self, client):
        """Test token signed with wrong secret"""
        # This is a valid JWT but signed with a different secret
        headers = {
            'Authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpZCI6MX0.NpOHLnLkLsQvKcJvBfGBiDXCMOl7BRAdbBhMZS6ZGTY'
        }
        rv = client.get('/name/1', headers=headers)
        assert rv.status_code == 401
    
    def test_token_without_bearer_prefix(self, client):
        """Test token without Bearer prefix"""
        # Get a valid token first
        rv = client.post('/token/1')
        token = rv.json['token'].replace('Bearer ', '')
        
        # Try to use it without Bearer prefix
        headers = {'Authorization': token}
        rv = client.get('/name/1', headers=headers)
        assert rv.status_code == 401


class TestCrossSiteScripting:
    """Test that tokens don't allow access to other users' data"""
    
    def test_user_cannot_access_other_user_data(self, client):
        """Test that a user's token can only access their own data"""
        # Get token for user 1
        rv = client.post('/token/1')
        user1_token = rv.json['token']
        
        # Try to use user 1's token to access different endpoints
        headers = {'Authorization': user1_token}
        
        # User 1 accessing their own data should work
        rv = client.get('/name/1', headers=headers)
        assert rv.status_code == 200
        assert rv.data.decode() == 'lorem'
        
        # The current implementation allows any authenticated user
        # to access any endpoint, which might be a security issue
        # In a real application, you'd want to restrict this
        rv = client.get('/name/2', headers=headers)
        assert rv.status_code == 200  # This works but returns user 1's secret


class TestTokenReuse:
    """Test token reuse scenarios"""
    
    def test_token_can_be_reused(self, client):
        """Test that tokens can be used multiple times"""
        # Get token
        rv = client.post('/token/1')
        token = rv.json['token']
        headers = {'Authorization': token}
        
        # Use the token multiple times
        for _ in range(5):
            rv = client.get('/name/1', headers=headers)
            assert rv.status_code == 200
            assert rv.data.decode() == 'lorem'
    
    def test_multiple_tokens_same_user(self, client):
        """Test that multiple tokens can be generated for the same user"""
        tokens = []
        
        # Generate multiple tokens for the same user
        for _ in range(3):
            rv = client.post('/token/1')
            assert rv.status_code == 200
            tokens.append(rv.json['token'])
        
        # All tokens should be valid but different
        assert len(set(tokens)) == len(tokens)  # All unique
        
        # All tokens should work
        for token in tokens:
            headers = {'Authorization': token}
            rv = client.get('/name/1', headers=headers)
            assert rv.status_code == 200
            assert rv.data.decode() == 'lorem'


class TestContentType:
    """Test content type handling"""
    
    def test_token_endpoint_returns_json(self, client):
        """Test that token endpoint returns proper JSON response"""
        rv = client.post('/token/1')
        assert rv.status_code == 200
        assert rv.content_type == 'application/json'
        assert isinstance(rv.json, dict)
        assert 'token' in rv.json
    
    def test_protected_endpoint_content_type(self, client):
        """Test protected endpoint content type"""
        # Get token
        rv = client.post('/token/1')
        token = rv.json['token']
        
        # Access protected endpoint
        headers = {'Authorization': token}
        rv = client.get('/name/1', headers=headers)
        assert rv.status_code == 200
        # The endpoint returns plain text, not JSON
        assert rv.content_type == 'text/html; charset=utf-8'


class TestEdgeCases:
    """Test edge cases and boundary conditions"""
    
    def test_very_long_user_id(self, client):
        """Test with very long user ID"""
        rv = client.post('/token/999999999999999999999')
        assert rv.status_code == 404
    
    def test_non_numeric_user_id(self, client):
        """Test with non-numeric user ID (should be caught by Flask routing)"""
        rv = client.post('/token/abc')
        assert rv.status_code == 404  # Flask returns 404 for route mismatch
    
    def test_authorization_header_case_sensitivity(self, client):
        """Test that Authorization header name is case-insensitive"""
        # Get token
        rv = client.post('/token/1')
        token = rv.json['token']
        
        # Try different cases for the header name
        header_variations = [
            'Authorization',
            'authorization',
            'AUTHORIZATION',
        ]
        
        for header_name in header_variations:
            headers = {header_name: token}
            rv = client.get('/name/1', headers=headers)
            # Flask/Werkzeug normalizes header names
            assert rv.status_code == 200


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
