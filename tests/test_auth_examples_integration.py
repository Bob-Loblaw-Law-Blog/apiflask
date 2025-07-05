"""
Integration tests for authentication examples to be added to the main test suite
This file can be integrated into the existing apiflask/tests directory
"""
import os
import sys
from importlib import metadata, reload

import pytest


@pytest.fixture
def basic_auth_client():
    """Create test client for basic auth example"""
    app_path = os.path.join(
        os.path.dirname(__file__), 
        '../examples/authentication/basic_auth_example'
    )
    sys.path.insert(0, app_path)
    import app
    app = reload(app)
    _app = app.app
    _app.testing = True
    sys.path.remove(app_path)
    return _app.test_client()


@pytest.fixture
def token_auth_client():
    """Create test client for token auth example"""
    app_path = os.path.join(
        os.path.dirname(__file__), 
        '../examples/authentication/token_auth_example'
    )
    sys.path.insert(0, app_path)
    import app
    app = reload(app)
    _app = app.app
    _app.testing = True
    sys.path.remove(app_path)
    return _app.test_client()


class TestAuthenticationExamples:
    """Integration tests for authentication examples"""
    
    def test_basic_auth_example_smoke(self, basic_auth_client):
        """Smoke test for basic auth example"""
        # Test public endpoint
        rv = basic_auth_client.get('/')
        assert rv.status_code == 200
        
        # Test protected endpoint without auth
        rv = basic_auth_client.get('/api/protected')
        assert rv.status_code == 401
        
        # Test with valid auth
        import base64
        credentials = base64.b64encode(b'user:password').decode()
        headers = {'Authorization': f'Basic {credentials}'}
        rv = basic_auth_client.get('/api/protected', headers=headers)
        assert rv.status_code == 200
    
    def test_token_auth_example_smoke(self, token_auth_client):
        """Smoke test for token auth example"""
        # Get token
        rv = token_auth_client.post('/token/1')
        assert rv.status_code == 200
        assert 'token' in rv.json
        
        # Test protected endpoint without token
        rv = token_auth_client.get('/name/1')
        assert rv.status_code == 401
        
        # Test with valid token
        token = token_auth_client.post('/token/1').json['token']
        headers = {'Authorization': token}
        rv = token_auth_client.get('/name/1', headers=headers)
        assert rv.status_code == 200


# This can be added to the existing test_examples.py file
auth_examples = [
    'authentication/basic_auth_example',
    'authentication/token_auth_example',
]


@pytest.mark.parametrize('example', auth_examples)
def test_auth_example_imports(example):
    """Test that authentication examples can be imported"""
    app_path = os.path.join(
        os.path.dirname(__file__), f'../examples/{example}'
    )
    sys.path.insert(0, app_path)
    try:
        import app
        assert hasattr(app, 'app')
        assert hasattr(app, 'auth')
    finally:
        sys.path.remove(app_path)
