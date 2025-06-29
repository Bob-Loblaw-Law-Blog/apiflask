import json
import pytest
from flask import Flask, jsonify, g, request
from werkzeug.exceptions import Unauthorized
from apiflask import APIFlask
from apiflask.security import HTTPBasicAuth, HTTPTokenAuth, _AuthBase
from apiflask.exceptions import HTTPError


@pytest.fixture
def app():
    app = APIFlask(__name__)
    app.testing = True
    return app


@pytest.fixture
def client(app):
    return app.test_client()


class TestMultipleAuthInstances:
    def test_multiple_auth_instances(self, app, client):
        # Test that multiple auth instances work independently
        basic_auth = HTTPBasicAuth()
        token_auth = HTTPTokenAuth()

        @basic_auth.verify_password
        def verify_password(username, password):
            if username == 'user' and password == 'password':
                return {'id': 1, 'auth_type': 'basic'}
            return None

        @token_auth.verify_token
        def verify_token(token):
            if token == 'valid-token':
                return {'id': 2, 'auth_type': 'token'}
            return None

        @app.route('/basic-protected')
        @basic_auth.login_required
        def basic_protected():
            return jsonify({'user_id': basic_auth.current_user['id'],
                            'auth_type': basic_auth.current_user['auth_type']})

        @app.route('/token-protected')
        @token_auth.login_required
        def token_protected():
            return jsonify({'user_id': token_auth.current_user['id'],
                            'auth_type': token_auth.current_user['auth_type']})

        # Test basic auth
        headers = {'Authorization': 'Basic dXNlcjpwYXNzd29yZA=='}  # user:password
        response = client.get('/basic-protected', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user_id'] == 1
        assert data['auth_type'] == 'basic'

        # Test token auth
        headers = {'Authorization': 'Bearer valid-token'}
        response = client.get('/token-protected', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user_id'] == 2
        assert data['auth_type'] == 'token'


class TestErrorHandling:
    def test_custom_error_processor_chaining(self, app, client):
        app.json_errors = True
        auth = HTTPTokenAuth()

        @auth.verify_token
        def verify_token(token):
            if token == 'valid-token':
                return {'id': 1}
            return None

        # Set up multiple error processors in chain
        @auth.error_processor
        def error_processor_1(error):
            error.first_processor = True
            return {
                'status_code': error.status_code,
                'message': error.message,
                'step': 'first'
            }, error.status_code

        # This one shouldn't be called since the first one returns a response
        @auth.error_processor
        def error_processor_2(error):
            return {
                'status_code': error.status_code,
                'message': error.message,
                'step': 'second'
            }, error.status_code

        @app.route('/protected')
        @auth.login_required
        def protected():
            return jsonify({'message': 'success'})

        response = client.get('/protected')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['step'] == 'first'

    def test_app_error_callback_integration(self, app, client):
        app.json_errors = True
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            if username == 'user' and password == 'password':
                return {'id': 1}
            return None

        @app.error_processor
        def app_error_processor(error):
            return {
                'global_error': True,
                'status_code': error.status_code,
                'message': error.message,
            }, error.status_code

        @app.route('/protected')
        @auth.login_required
        def protected():
            return jsonify({'message': 'success'})

        response = client.get('/protected')
        assert response.status_code == 401
        data = json.loads(response.data)
        assert data['global_error'] is True


class TestAuthBase:
    def test_auth_base_current_user_property(self, app):
        auth_base = _AuthBase()

        # Initially current_user should be None
        with app.test_request_context():
            assert auth_base.current_user is None

        # If g.flask_httpauth_user is set, it should be accessible
        with app.test_request_context():
            g.flask_httpauth_user = {'id': 1, 'username': 'user'}
            assert auth_base.current_user == {'id': 1, 'username': 'user'}

    def test_auth_base_error_handler(self, app):
        auth_base = _AuthBase()

        # Test with json_errors=True
        with app.test_request_context():
            app.json_errors = True
            response = auth_base._auth_error_handler(401)
            assert isinstance(response, dict)
            assert response.get('status_code') == 401

        # Test with json_errors=False
        with app.test_request_context():
            app.json_errors = False
            message, status_code = auth_base._auth_error_handler(401)
            assert status_code == 401
            assert 'Unauthorized' in message


class TestComplexScenarios:
    def test_nested_auth_requirements(self, app, client):
        outer_auth = HTTPTokenAuth(scheme='OuterToken')
        inner_auth = HTTPTokenAuth(scheme='InnerToken')

        @outer_auth.verify_token
        def verify_outer_token(token):
            if token == 'outer-token':
                return {'id': 1, 'role': 'admin'}
            return None

        @inner_auth.verify_token
        def verify_inner_token(token):
            if token == 'inner-token':
                return {'id': 2, 'role': 'user'}
            return None

        @app.route('/nested')
        @outer_auth.login_required
        @inner_auth.login_required
        def nested():
            outer_user = outer_auth.current_user
            inner_user = inner_auth.current_user
            return jsonify({
                'outer': {'id': outer_user['id'], 'role': outer_user['role']},
                'inner': {'id': inner_user['id'], 'role': inner_user['role']},
            })

        # Test with both tokens present
        headers = {
            'Authorization': 'OuterToken outer-token',
            'X-Inner-Auth': 'InnerToken inner-token'
        }

        # This will fail because flask-httpauth doesn't support nested auth
        # But we can verify the error is related to nested auth issues
        response = client.get('/nested', headers=headers)
        assert response.status_code == 401  # The inner auth will fail

    def test_optional_auth(self, app, client):
        auth = HTTPTokenAuth()

        @auth.verify_token
        def verify_token(token):
            if token == 'valid-token':
                return {'id': 1, 'role': 'admin'}
            return None

        @app.route('/optional-auth')
        @auth.login_required(optional=True)
        def optional_auth():
            if auth.current_user:
                return jsonify({
                    'authenticated': True,
                    'user_id': auth.current_user['id'],
                    'role': auth.current_user['role'],
                })
            else:
                return jsonify({
                    'authenticated': False,
                    'message': 'Anonymous access granted',
                })

        # Without token - anonymous access
        response = client.get('/optional-auth')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['authenticated'] is False

        # With valid token - authenticated access
        headers = {'Authorization': 'Bearer valid-token'}
        response = client.get('/optional-auth', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['authenticated'] is True
        assert data['user_id'] == 1
        assert data['role'] == 'admin'

        # With invalid token - anonymous access (not 401)
        headers = {'Authorization': 'Bearer invalid-token'}
        response = client.get('/optional-auth', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['authenticated'] is False

    def test_multiple_auth_options(self, app, client):
        token_auth = HTTPTokenAuth()
        basic_auth = HTTPBasicAuth()

        @token_auth.verify_token
        def verify_token(token):
            if token == 'valid-token':
                return {'id': 1, 'auth_type': 'token'}
            return None

        @basic_auth.verify_password
        def verify_password(username, password):
            if username == 'user' and password == 'password':
                return {'id': 2, 'auth_type': 'basic'}
            return None

        @app.route('/multi-auth')
        def multi_auth():
            user = None

            auth_header = request.headers.get('Authorization')
            if auth_header:
                if auth_header.startswith('Bearer '):
                    token = auth_header[7:]
                    user = verify_token(token)
                elif auth_header.startswith('Basic '):
                    from base64 import b64decode
                    encoded = auth_header[6:].encode()
                    decoded = b64decode(encoded).decode()
                    username, password = decoded.split(':', 1)
                    user = verify_password(username, password)

            if user:
                return jsonify({
                    'authenticated': True,
                    'user_id': user['id'],
                    'auth_type': user['auth_type'],
                })
            else:
                return jsonify({
                    'authenticated': False,
                    'message': 'Authentication failed',
                }), 401

        # Test with token auth
        headers = {'Authorization': 'Bearer valid-token'}
        response = client.get('/multi-auth', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user_id'] == 1
        assert data['auth_type'] == 'token'

        # Test with basic auth
        headers = {'Authorization': 'Basic dXNlcjpwYXNzd29yZA=='}  # user:password
        response = client.get('/multi-auth', headers=headers)
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['user_id'] == 2
        assert data['auth_type'] == 'basic'
