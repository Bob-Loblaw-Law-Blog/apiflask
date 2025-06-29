import json
import pytest
from flask import Flask, jsonify
from apiflask import APIFlask
from apiflask.security import HTTPBasicAuth, HTTPTokenAuth
from apiflask.exceptions import HTTPError


@pytest.fixture
def app():
    app = APIFlask(__name__)
    app.config['TESTING'] = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_integration_with_apiflask_auth_required(app, client):
    auth = HTTPTokenAuth()

    @auth.verify_token
    def verify_token(token):
        if token == 'valid-token':
            return {'id': 1}
        return None

    @app.get('/protected')
    @app.auth_required(auth)
    def protected():
        return {'message': 'success'}

    # Test with valid token
    headers = {'Authorization': 'Bearer valid-token'}
    response = client.get('/protected', headers=headers)
    assert response.status_code == 200

    # Test with invalid token
    headers = {'Authorization': 'Bearer invalid-token'}
    response = client.get('/protected', headers=headers)
    assert response.status_code == 401


def test_integration_with_custom_error_responses(app, client):
    app.json_errors = True
    auth = HTTPBasicAuth()

    @auth.verify_password
    def verify_password(username, password):
        if username == 'user' and password == 'password':
            return {'id': 1}
        return None

    # Custom error handler for the app
    @app.error_processor
    def app_error_processor(error):
        return {
            'error': True,
            'code': error.status_code,
            'name': error.__class__.__name__,
            'description': error.message,
        }, error.status_code

    @app.get('/protected')
    @app.auth_required(auth)
    def protected():
        return {'message': 'success'}

    response = client.get('/protected')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['error'] is True
    assert data['code'] == 401
    assert 'name' in data
    assert 'description' in data


def test_integration_with_apiflask_doc_auth(app, client):
    auth = HTTPBasicAuth(description="Authentication for secure API endpoints")

    @auth.verify_password
    def verify_password(username, password):
        if username == 'user' and password == 'password':
            return {'id': 1}
        return None

    @app.get('/protected')
    @app.auth_required(auth)
    def protected():
        return {'message': 'success'}

    # Verify the OpenAPI spec includes the auth description
    spec = app.spec
    assert 'BasicAuth' in spec['components']['securitySchemes']
    assert spec['components']['securitySchemes']['BasicAuth']['description'] == "Authentication for secure API endpoints"

    # Verify that the endpoint has security requirements
    assert 'security' in spec['paths']['/protected']['get']
    assert spec['paths']['/protected']['get']['security'][0]['BasicAuth'] == []


def test_authbase_error_handler_integration(app, client):
    app.json_errors = True
    auth = HTTPTokenAuth()

    @auth.verify_token
    def verify_token(token):
        return None  # Always fail authentication for testing

    @app.get('/protected')
    @app.auth_required(auth)
    def protected():
        return {'message': 'success'}

    # Ensure the default _auth_error_handler works with APIFlask
    response = client.get('/protected')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['status_code'] == 401
    assert 'message' in data


def test_auth_error_processor_precedence(app, client):
    app.json_errors = True
    auth = HTTPTokenAuth()

    @auth.verify_token
    def verify_token(token):
        return None  # Always fail authentication for testing

    # Set auth-specific error processor
    @auth.error_processor
    def auth_error_processor(error):
        return {
            'source': 'auth',
            'status_code': error.status_code,
            'message': error.message,
        }, error.status_code

    # Set app-wide error processor
    @app.error_processor
    def app_error_processor(error):
        return {
            'source': 'app',
            'status_code': error.status_code,
            'message': error.message,
        }, error.status_code

    @app.get('/protected')
    @app.auth_required(auth)
    def protected():
        return {'message': 'success'}

    # Auth-specific error processor should take precedence
    response = client.get('/protected')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['source'] == 'auth'  # Verify that auth's error processor was used


def test_auth_required_optional_parameter(app, client):
    auth = HTTPTokenAuth()

    @auth.verify_token
    def verify_token(token):
        if token == 'valid-token':
            return {'id': 1}
        return None

    @app.get('/optional')
    @app.auth_required(auth, optional=True)
    def optional():
        if auth.current_user:
            return {'message': 'authenticated', 'user_id': auth.current_user['id']}
        return {'message': 'anonymous'}

    # Test with no auth - should still work
    response = client.get('/optional')
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'anonymous'

    # Test with valid auth
    headers = {'Authorization': 'Bearer valid-token'}
    response = client.get('/optional', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['message'] == 'authenticated'
    assert data['user_id'] == 1


def test_error_handled_multiple_times(app, client):
    app.json_errors = True
    auth = HTTPTokenAuth()

    @auth.verify_token
    def verify_token(token):
        return None  # Always fail

    error_processor_calls = []

    @app.error_processor
    def global_error_processor(error):
        error_processor_calls.append('global')
        return {
            'source': 'global',
            'status_code': error.status_code
        }, error.status_code

    @auth.error_processor
    def auth_error_processor(error):
        error_processor_calls.append('auth')
        return {
            'source': 'auth',
            'status_code': error.status_code
        }, error.status_code

    @app.get('/protected')
    @app.auth_required(auth)
    def protected():
        return {'message': 'success'}

    response = client.get('/protected')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['source'] == 'auth'

    # Should only call the auth error processor, not both
    assert error_processor_calls == ['auth']


def test_auth_error_with_app_errorhandler(app, client):
    auth = HTTPBasicAuth()

    @auth.verify_password
    def verify_password(username, password):
        return None  # Always fail

    @app.errorhandler(401)
    def handle_401(error):
        return {'message': 'Custom 401 handler', 'code': 401}, 401

    @app.get('/protected')
    @app.auth_required(auth)
    def protected():
        return {'message': 'success'}

    response = client.get('/protected')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['message'] == 'Custom 401 handler'  # App's errorhandler wins
