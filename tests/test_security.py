import json
import pytest
from flask import Flask, jsonify, g
from apiflask import APIFlask
from apiflask.security import HTTPBasicAuth, HTTPTokenAuth
from apiflask.exceptions import HTTPError


@pytest.fixture
def app():
    app = APIFlask(__name__)

    @app.route('/ping')
    def ping():
        return jsonify({'message': 'pong'})

    return app


@pytest.fixture
def client(app):
    return app.test_client()


def test_http_basic_auth_authenticate_success(app, client):
    auth = HTTPBasicAuth()

    @auth.verify_password
    def verify_password(username, password):
        if username == 'user' and password == 'password':
            return {'id': 1, 'username': 'user'}
        return None

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'user_id': auth.current_user['id']})

    # Test with valid credentials
    headers = {'Authorization': 'Basic dXNlcjpwYXNzd29yZA=='}  # user:password
    response = client.get('/protected', headers=headers)
    assert response.status_code == 200
    assert json.loads(response.data) == {'user_id': 1}


def test_http_basic_auth_authenticate_failure(app, client):
    auth = HTTPBasicAuth()

    @auth.verify_password
    def verify_password(username, password):
        if username == 'user' and password == 'password':
            return {'id': 1, 'username': 'user'}
        return None

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'user_id': auth.current_user['id']})

    # Test with invalid credentials
    headers = {'Authorization': 'Basic dXNlcjp3cm9uZ3Bhc3M='}  # user:wrongpass
    response = client.get('/protected', headers=headers)
    assert response.status_code == 401

    # Test with missing credentials
    response = client.get('/protected')
    assert response.status_code == 401


def test_http_token_auth_authenticate_success(app, client):
    auth = HTTPTokenAuth()

    @auth.verify_token
    def verify_token(token):
        if token == 'valid-token':
            return {'id': 1, 'username': 'user'}
        return None

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'user_id': auth.current_user['id']})

    # Test with valid token
    headers = {'Authorization': 'Bearer valid-token'}
    response = client.get('/protected', headers=headers)
    assert response.status_code == 200
    assert json.loads(response.data) == {'user_id': 1}


def test_http_token_auth_authenticate_failure(app, client):
    auth = HTTPTokenAuth()

    @auth.verify_token
    def verify_token(token):
        if token == 'valid-token':
            return {'id': 1, 'username': 'user'}
        return None

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'user_id': auth.current_user['id']})

    # Test with invalid token
    headers = {'Authorization': 'Bearer invalid-token'}
    response = client.get('/protected', headers=headers)
    assert response.status_code == 401

    # Test with missing token
    response = client.get('/protected')
    assert response.status_code == 401


def test_current_user_property(app, client):
    auth = HTTPBasicAuth()

    @auth.verify_password
    def verify_password(username, password):
        if username == 'user' and password == 'password':
            return {'id': 1, 'username': 'user', 'role': 'admin'}
        return None

    @app.route('/user-info')
    @auth.login_required
    def user_info():
        # Test that auth.current_user is accessible
        user = auth.current_user
        return jsonify({
            'id': user['id'],
            'username': user['username'],
            'role': user['role'],
        })

    headers = {'Authorization': 'Basic dXNlcjpwYXNzd29yZA=='}  # user:password
    response = client.get('/user-info', headers=headers)
    assert response.status_code == 200
    data = json.loads(response.data)
    assert data['id'] == 1
    assert data['username'] == 'user'
    assert data['role'] == 'admin'


def test_custom_error_handler(app, client):
    app.json_errors = True
    auth = HTTPTokenAuth()

    @auth.verify_token
    def verify_token(token):
        if token == 'valid-token':
            return {'id': 1, 'username': 'user'}
        return None

    @auth.error_processor
    def custom_auth_error(error):
        return {
            'status': 'error',
            'code': error.status_code,
            'message': error.message,
            'custom_field': 'custom_value'
        }, error.status_code

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'message': 'success'})

    response = client.get('/protected')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['status'] == 'error'
    assert data['code'] == 401
    assert 'message' in data
    assert data['custom_field'] == 'custom_value'


def test_custom_token_scheme(app, client):
    auth = HTTPTokenAuth(scheme='ApiKey')

    @auth.verify_token
    def verify_token(token):
        if token == 'valid-key':
            return {'id': 1}
        return None

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'message': 'success'})

    # Test with valid header format for ApiKey scheme
    headers = {'Authorization': 'ApiKey valid-key'}
    response = client.get('/protected', headers=headers)
    assert response.status_code == 200

    # Test with invalid scheme
    headers = {'Authorization': 'Bearer valid-key'}
    response = client.get('/protected', headers=headers)
    assert response.status_code == 401


def test_custom_header_token_auth(app, client):
    auth = HTTPTokenAuth(header='X-API-Key')

    @auth.verify_token
    def verify_token(token):
        if token == 'valid-api-key':
            return {'id': 1}
        return None

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'message': 'success'})

    # Test with valid custom header
    headers = {'X-API-Key': 'valid-api-key'}
    response = client.get('/protected', headers=headers)
    assert response.status_code == 200

    # Test with invalid custom header
    headers = {'X-API-Key': 'invalid-api-key'}
    response = client.get('/protected', headers=headers)
    assert response.status_code == 401

    # Test with missing custom header
    response = client.get('/protected')
    assert response.status_code == 401


def test_json_error_response_format(app, client):
    app.json_errors = True
    auth = HTTPBasicAuth()

    @auth.verify_password
    def verify_password(username, password):
        if username == 'user' and password == 'password':
            return {'id': 1}
        return None

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'message': 'success'})

    response = client.get('/protected')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert 'message' in data
    assert data['status_code'] == 401


def test_non_json_error_response_format(app, client):
    app.json_errors = False
    auth = HTTPBasicAuth()

    @auth.verify_password
    def verify_password(username, password):
        if username == 'user' and password == 'password':
            return {'id': 1}
        return None

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'message': 'success'})

    response = client.get('/protected')
    assert response.status_code == 401
    # Should not be JSON response
    with pytest.raises(json.JSONDecodeError):
        json.loads(response.data)
    # Should be a text response
    assert 'Unauthorized' in response.data.decode('utf-8')


def test_auth_error_handler_original(app, client):
    auth = HTTPBasicAuth()

    @auth.verify_password
    def verify_password(username, password):
        if username == 'user' and password == 'password':
            return {'id': 1}
        return None

    @app.route('/protected')
    @auth.login_required
    def protected():
        return jsonify({'message': 'success'})

    # Test the default _auth_error_handler with json_errors=True
    app.json_errors = True
    response = client.get('/protected')
    assert response.status_code == 401
    data = json.loads(response.data)
    assert data['status_code'] == 401
    assert 'message' in data

    # Test the default _auth_error_handler with json_errors=False
    app.json_errors = False
    response = client.get('/protected')
    assert response.status_code == 401
    assert 'Unauthorized' in response.data.decode('utf-8')


def test_g_object_access(app, client):
    auth = HTTPTokenAuth()

    @auth.verify_token
    def verify_token(token):
        if token == 'valid-token':
            return {'id': 1, 'username': 'user'}
        return None

    @app.route('/check-g')
    @auth.login_required
    def check_g():
        assert g.flask_httpauth_user == auth.current_user
        return jsonify({'message': 'g.flask_httpauth_user exists'})

    headers = {'Authorization': 'Bearer valid-token'}
    response = client.get('/check-g', headers=headers)
    assert response.status_code == 200
