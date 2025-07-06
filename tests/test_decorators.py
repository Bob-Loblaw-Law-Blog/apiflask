"""
Consolidated tests for APIFlask decorators.

This module contains all tests for APIFlask decorators including:
- Basic decorator availability tests
- @auth_required decorator tests
- @doc decorator tests
- @input decorator tests
- @output decorator tests
"""

import io
from dataclasses import dataclass

import openapi_spec_validator as osv
import pytest
from flask import make_response
from flask.views import MethodView
from werkzeug.datastructures import FileStorage

from .schemas import (
    Bar, Baz, CustomHTTPError, EnumPathParameter, Files, Foo, Form,
    FormAndFiles, Query
)
from apiflask import APIBlueprint, Schema
from apiflask.fields import Field, Integer, String
from apiflask.security import HTTPBasicAuth, HTTPTokenAuth
from apiflask.validators import Length, OneOf


class TestBasicDecorators:
    """Tests for basic decorator availability on app and blueprint objects."""

    def test_app_decorators(self, app):
        assert hasattr(app, 'auth_required')
        assert hasattr(app, 'input')
        assert hasattr(app, 'output')
        assert hasattr(app, 'doc')

    def test_bp_decorators(self, app):
        bp = APIBlueprint('test', __name__)
        assert hasattr(bp, 'auth_required')
        assert hasattr(bp, 'input')
        assert hasattr(bp, 'output')
        assert hasattr(bp, 'doc')


class TestAuthRequiredDecorator:
    """Tests for the @auth_required decorator."""

    def test_auth_required(self, app, client):
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            if username == 'foo' and password == 'bar':
                return {'user': 'foo'}
            elif username == 'bar' and password == 'foo':
                return {'user': 'bar'}
            elif username == 'baz' and password == 'baz':
                return {'user': 'baz'}

        @auth.get_user_roles
        def get_roles(user):
            if user['user'] == 'bar':
                return 'admin'
            elif user['user'] == 'baz':
                return 'moderator'
            return 'normal'

        @app.route('/foo')
        @app.auth_required(auth)
        def foo():
            return auth.current_user

        @app.route('/bar')
        @app.auth_required(auth, roles=['admin'])
        def bar():
            return auth.current_user

        @app.route('/baz')
        @app.auth_required(auth, roles=['admin', 'moderator'])
        def baz():
            return auth.current_user

        rv = client.get('/foo')
        assert rv.status_code == 401

        rv = client.get('/foo', headers={'Authorization': 'Basic Zm9vOmJhcg=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'foo'}

        rv = client.get('/bar', headers={'Authorization': 'Basic Zm9vOmJhcg=='})
        assert rv.status_code == 403

        rv = client.get('/foo', headers={'Authorization': 'Basic YmFyOmZvbw=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'bar'}

        rv = client.get('/bar', headers={'Authorization': 'Basic YmFyOmZvbw=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'bar'}

        rv = client.get('/baz', headers={'Authorization': 'Basic Zm9vOmJhcg=='})
        assert rv.status_code == 403

        rv = client.get('/baz', headers={'Authorization': 'Basic YmFyOmZvbw=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'bar'}

        rv = client.get('/baz', headers={'Authorization': 'Basic YmF6OmJheg=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'baz'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'BasicAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['BasicAuth'] == {
            'scheme': 'basic',
            'type': 'http',
        }

        assert 'BasicAuth' in rv.json['paths']['/foo']['get']['security'][0]
        assert 'BasicAuth' in rv.json['paths']['/bar']['get']['security'][0]
        assert 'BasicAuth' in rv.json['paths']['/baz']['get']['security'][0]

    def test_auth_required_with_methodview(self, app, client):
        auth = HTTPBasicAuth()

        @auth.verify_password
        def verify_password(username, password):
            if username == 'foo' and password == 'bar':
                return {'user': 'foo'}
            elif username == 'bar' and password == 'foo':
                return {'user': 'bar'}
            elif username == 'baz' and password == 'baz':
                return {'user': 'baz'}

        @auth.get_user_roles
        def get_roles(user):
            if user['user'] == 'bar':
                return 'admin'
            elif user['user'] == 'baz':
                return 'moderator'
            return 'normal'

        @app.route('/')
        class FooView(MethodView):
            @app.auth_required(auth)
            def get(self):
                return auth.current_user

            @app.auth_required(auth, roles=['admin'])
            def post(self):
                return auth.current_user

            @app.auth_required(auth, roles=['admin', 'moderator'])
            def delete(self):
                return auth.current_user

        rv = client.get('/')
        assert rv.status_code == 401

        rv = client.get('/', headers={'Authorization': 'Basic Zm9vOmJhcg=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'foo'}

        rv = client.post('/', headers={'Authorization': 'Basic Zm9vOmJhcg=='})
        assert rv.status_code == 403

        rv = client.get('/', headers={'Authorization': 'Basic YmFyOmZvbw=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'bar'}

        rv = client.post('/', headers={'Authorization': 'Basic YmFyOmZvbw=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'bar'}

        rv = client.delete('/', headers={'Authorization': 'Basic Zm9vOmJhcg=='})
        assert rv.status_code == 403

        rv = client.delete('/', headers={'Authorization': 'Basic YmFyOmZvbw=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'bar'}

        rv = client.delete('/', headers={'Authorization': 'Basic YmF6OmJheg=='})
        assert rv.status_code == 200
        assert rv.json == {'user': 'baz'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'BasicAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['BasicAuth'] == {
            'scheme': 'basic',
            'type': 'http',
        }

        assert 'BasicAuth' in rv.json['paths']['/']['get']['security'][0]
        assert 'BasicAuth' in rv.json['paths']['/']['post']['security'][0]
        assert 'BasicAuth' in rv.json['paths']['/']['delete']['security'][0]

    def test_auth_required_at_blueprint_before_request(self, app, client):
        bp = APIBlueprint('auth', __name__)
        no_auth_bp = APIBlueprint('no-auth', __name__)

        auth = HTTPTokenAuth()

        @bp.before_request
        @bp.auth_required(auth)
        def before():
            pass

        @bp.get('/foo')
        def foo():
            pass

        @bp.get('/bar')
        def bar():
            pass

        @bp.route('/baz')
        class BazView(MethodView):
            def get(self):
                pass

            def post(self):
                pass

        @no_auth_bp.get('/eggs')
        def eggs():
            return 'no auth'

        app.register_blueprint(bp)
        app.register_blueprint(no_auth_bp)

        rv = client.get('/foo')
        assert rv.status_code == 401
        rv = client.get('/bar')
        assert rv.status_code == 401
        rv = client.get('/baz')
        assert rv.status_code == 401
        rv = client.get('/eggs')
        assert rv.status_code == 200

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        assert 'auth' in app._auth_blueprints
        assert 'no-auth' not in app._auth_blueprints

        assert 'BearerAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['BearerAuth'] == {
            'scheme': 'bearer',
            'type': 'http',
        }

        assert 'BearerAuth' in rv.json['paths']['/foo']['get']['security'][0]
        assert 'BearerAuth' in rv.json['paths']['/bar']['get']['security'][0]
        assert 'BearerAuth' in rv.json['paths']['/baz']['get']['security'][0]
        assert 'BearerAuth' in rv.json['paths']['/baz']['post']['security'][0]
        assert 'security' not in rv.json['paths']['/eggs']['get']

    def test_lowercase_token_scheme_value(self, app, client):
        auth = HTTPTokenAuth(scheme='bearer')

        @app.route('/')
        @app.auth_required(auth)
        def index():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        assert 'BearerAuth' in rv.json['components']['securitySchemes']
        assert 'BearerAuth' in rv.json['paths']['/']['get']['security'][0]


class TestDocDecorator:
    """Tests for the @doc decorator."""

    def test_doc_summary_and_description(self, app, client):
        @app.route('/foo')
        @app.doc(summary='summary from doc decorator')
        def foo():
            pass

        @app.route('/bar')
        @app.doc(summary='summary for bar', description='some description for bar')
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['summary'] == 'summary from doc decorator'
        assert 'description' not in rv.json['paths']['/foo']['get']
        assert rv.json['paths']['/bar']['get']['summary'] == 'summary for bar'
        assert rv.json['paths']['/bar']['get']['description'] == 'some description for bar'

    def test_doc_summary_and_description_with_methodview(self, app, client):
        @app.route('/baz')
        class BazView(MethodView):
            @app.doc(summary='summary from doc decorator')
            def get(self):
                pass

            @app.doc(summary='summary for baz', description='some description for baz')
            def post(self):
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/baz']['get']['summary'] == 'summary from doc decorator'
        assert 'description' not in rv.json['paths']['/baz']['get']
        assert rv.json['paths']['/baz']['post']['summary'] == 'summary for baz'
        assert rv.json['paths']['/baz']['post']['description'] == 'some description for baz'

    def test_doc_tags(self, app, client):
        app.tags = ['foo', 'bar']

        @app.route('/foo')
        @app.doc(tags=['foo'])
        def foo():
            pass

        @app.route('/bar')
        @app.doc(tags=['foo', 'bar'])
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['tags'] == ['foo']
        assert rv.json['paths']['/bar']['get']['tags'] == ['foo', 'bar']

    def test_doc_tags_with_methodview(self, app, client):
        @app.route('/baz')
        class BazView(MethodView):
            @app.doc(tags=['foo'])
            def get(self):
                pass

            @app.doc(tags=['foo', 'bar'])
            def post(self):
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/baz']['get']['tags'] == ['foo']
        assert rv.json['paths']['/baz']['post']['tags'] == ['foo', 'bar']

    def test_doc_hide(self, app, client):
        @app.route('/foo')
        @app.doc(hide=True)
        def foo():
            pass

        @app.get('/baz')
        def get_baz():
            pass

        @app.post('/baz')
        @app.doc(hide=True)
        def post_baz():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '/foo' not in rv.json['paths']
        assert '/baz' in rv.json['paths']
        assert 'get' in rv.json['paths']['/baz']
        assert 'post' not in rv.json['paths']['/baz']

    def test_doc_hide_with_methodview(self, app, client):
        @app.route('/bar')
        class BarView(MethodView):
            def get(self):
                pass

            @app.doc(hide=True)
            def post(self):
                pass

        @app.route('/secret')
        class SecretView(MethodView):
            @app.doc(hide=True)
            def get(self):
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '/bar' in rv.json['paths']
        assert 'get' in rv.json['paths']['/bar']
        assert 'post' not in rv.json['paths']['/bar']
        assert '/secret' in rv.json['paths']

    def test_doc_deprecated(self, app, client):
        @app.route('/foo')
        @app.doc(deprecated=True)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['deprecated']

    def test_doc_deprecated_with_methodview(self, app, client):
        @app.route('/foo')
        class FooAPIView(MethodView):
            @app.doc(deprecated=True)
            def get(self):
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['deprecated']

    def test_doc_responses(self, app, client):
        @app.route('/foo')
        @app.input(Foo)
        @app.output(Foo)
        @app.doc(responses={200: 'success', 400: 'bad', 404: 'not found', 500: 'server error'})
        def foo():
            pass

        @app.route('/bar')
        @app.input(Foo)
        @app.output(Foo)
        @app.doc(responses=[200, 400, 404, 500])
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '200' in rv.json['paths']['/foo']['get']['responses']
        assert '400' in rv.json['paths']['/foo']['get']['responses']
        # overwrite existing error descriptions
        assert rv.json['paths']['/foo']['get']['responses']['200']['description'] == 'success'
        assert rv.json['paths']['/foo']['get']['responses']['400']['description'] == 'bad'
        assert '404' in rv.json['paths']['/foo']['get']['responses']
        assert rv.json['paths']['/foo']['get']['responses']['404']['description'] == 'not found'
        assert '500' in rv.json['paths']['/foo']['get']['responses']
        assert rv.json['paths']['/foo']['get']['responses']['500']['description'] == 'server error'

        assert '200' in rv.json['paths']['/bar']['get']['responses']
        assert '400' in rv.json['paths']['/bar']['get']['responses']
        assert (
            rv.json['paths']['/bar']['get']['responses']['200']['description'] == 'Successful response'
        )
        assert rv.json['paths']['/bar']['get']['responses']['400']['description'] == 'Bad Request'
        assert '404' in rv.json['paths']['/foo']['get']['responses']
        assert rv.json['paths']['/bar']['get']['responses']['404']['description'] == 'Not Found'
        assert '500' in rv.json['paths']['/bar']['get']['responses']
        assert (
            rv.json['paths']['/bar']['get']['responses']['500']['description']
            == 'Internal Server Error'
        )

    def test_doc_responses_custom_spec(self, app, client):
        response_spec = {
            'description': 'Success',
            'content': {
                'application/json': {
                    'schema': {
                        'type': 'object',
                        'properties': {
                            'data': {
                                'type': 'object',
                                'properties': {
                                    'id': {'type': 'integer'},
                                    'name': {'type': 'string'},
                                },
                            }
                        },
                    }
                }
            },
        }

        @app.get('/foo')
        @app.input(Foo)
        @app.output(Foo)
        @app.doc(responses={200: response_spec})
        def foo():
            return {'message': 'Hello!'}

        @app.get('/bar')
        @app.doc(
            responses={
                200: {'description': 'Success', 'content': {'application/json': {'schema': Foo}}},
                400: {
                    'description': 'Error',
                    'content': {'application/json': {'schema': CustomHTTPError}},
                },
                404: {
                    'description': 'Error',
                    'content': {'application/json': {'schema': CustomHTTPError()}},
                },
            }
        )
        def say_hello():
            return {'message': 'Hello!'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '200' in rv.json['paths']['/foo']['get']['responses']
        assert rv.json['paths']['/foo']['get']['responses']['200'] == response_spec

        assert '200' in rv.json['paths']['/bar']['get']['responses']
        assert '400' in rv.json['paths']['/bar']['get']['responses']
        assert '404' in rv.json['paths']['/bar']['get']['responses']
        assert rv.json['paths']['/bar']['get']['responses']['200']['description'] == 'Success'
        assert rv.json['paths']['/bar']['get']['responses']['400']['description'] == 'Error'
        assert rv.json['paths']['/bar']['get']['responses']['400']['content']['application/json'][
            'schema'
        ] == {'$ref': '#/components/schemas/CustomHTTPError'}
        assert rv.json['components']['schemas']['CustomHTTPError'] == {
            'type': 'object',
            'properties': {
                'status_code': {'type': 'string'},
                'message': {'type': 'string'},
                'custom': {'type': 'string'},
            },
            'required': ['custom', 'message', 'status_code'],
        }

    def test_doc_responses_additional_content_type(self, app, client):
        """Verify that it is possible to add additional media types for a response's status code."""
        description = 'something'

        @app.route('/foo')
        @app.input(Foo)
        @app.output(Foo)
        @app.doc(
            responses={
                200: {
                    'content': {
                        'text/html': {},
                    },
                },
            }
        )
        def foo():
            pass

        @app.route('/bar')
        @app.input(Foo)
        @app.output(Foo)
        @app.doc(
            responses={
                200: {
                    'content': {
                        'text/html': {},
                    },
                    'description': description,
                },
            }
        )
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '200' in rv.json['paths']['/foo']['get']['responses']
        assert 'application/json' in rv.json['paths']['/foo']['get']['responses']['200']['content']
        assert 'text/html' in rv.json['paths']['/foo']['get']['responses']['200']['content']
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['description'] == 'Successful response'
        )  # noqa: E501
        assert '200' in rv.json['paths']['/bar']['get']['responses']
        assert 'application/json' in rv.json['paths']['/bar']['get']['responses']['200']['content']
        assert 'text/html' in rv.json['paths']['/bar']['get']['responses']['200']['content']
        assert rv.json['paths']['/bar']['get']['responses']['200']['description'] == description

    def test_doc_responses_with_methodview(self, app, client):
        @app.route('/foo')
        class FooAPIView(MethodView):
            @app.input(Foo)
            @app.output(Foo)
            @app.doc(responses={200: 'success', 400: 'bad', 404: 'not found', 500: 'server error'})
            def get(self):
                pass

        @app.route('/bar')
        class BarAPIView(MethodView):
            @app.input(Foo)
            @app.output(Foo)
            @app.doc(responses=[200, 400, 404, 500])
            def get(self):
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '200' in rv.json['paths']['/foo']['get']['responses']
        assert '400' in rv.json['paths']['/foo']['get']['responses']
        # don't overwrite exist error description
        assert rv.json['paths']['/foo']['get']['responses']['200']['description'] == 'success'
        assert rv.json['paths']['/foo']['get']['responses']['400']['description'] == 'bad'
        assert '404' in rv.json['paths']['/foo']['get']['responses']
        assert rv.json['paths']['/foo']['get']['responses']['404']['description'] == 'not found'
        assert '500' in rv.json['paths']['/foo']['get']['responses']
        assert rv.json['paths']['/foo']['get']['responses']['500']['description'] == 'server error'

        assert '200' in rv.json['paths']['/bar']['get']['responses']
        assert '400' in rv.json['paths']['/bar']['get']['responses']
        assert (
            rv.json['paths']['/bar']['get']['responses']['200']['description'] == 'Successful response'
        )
        assert rv.json['paths']['/bar']['get']['responses']['400']['description'] == 'Bad Request'
        assert '404' in rv.json['paths']['/foo']['get']['responses']
        assert rv.json['paths']['/bar']['get']['responses']['404']['description'] == 'Not Found'
        assert '500' in rv.json['paths']['/bar']['get']['responses']
        assert (
            rv.json['paths']['/bar']['get']['responses']['500']['description']
            == 'Internal Server Error'
        )

    def test_doc_operationid(self, app, client):
        @app.route('/foo')
        @app.doc(operation_id='getSomeFoo')
        def foo():
            pass

        @app.route('/bar')
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['operationId'] == 'getSomeFoo'
        assert 'operationId' not in rv.json['paths']['/bar']['get']

    def test_doc_security(self, app, client):
        @app.route('/foo')
        @app.doc(security='ApiKeyAuth')
        def foo():
            pass

        @app.route('/bar')
        @app.doc(security=['BasicAuth', 'ApiKeyAuth'])
        def bar():
            pass

        @app.route('/baz')
        @app.doc(security=[{'OAuth2': ['read', 'write']}])
        def baz():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['security'] == [{'ApiKeyAuth': []}]
        assert rv.json['paths']['/bar']['get']['security'] == [{'BasicAuth': []}, {'ApiKeyAuth': []}]
        assert rv.json['paths']['/baz']['get']['security'] == [{'OAuth2': ['read', 'write']}]

    def test_doc_security_invalid_value(self, app):
        @app.route('/foo')
        @app.doc(security={'BasicAuth': []})
        def foo():
            pass

        with pytest.raises(ValueError):
            app.spec


class TestInputDecorator:
    """Tests for the @input decorator."""

    def test_input(self, app, client):
        @app.route('/foo', methods=['POST'])
        @app.input(Foo)
        def foo(json_data):
            return json_data

        @app.route('/bar')
        class BarView(MethodView):
            @app.input(Foo)
            def post(self, json_data):
                return json_data

        for rule in ['/foo', '/bar']:
            rv = client.post(rule)
            assert rv.status_code == 422
            assert rv.json == {
                'detail': {'json': {'name': ['Missing data for required field.']}},
                'message': 'Validation error',
            }

            rv = client.post(rule, json={'id': 1})
            assert rv.status_code == 422
            assert rv.json == {
                'detail': {'json': {'name': ['Missing data for required field.']}},
                'message': 'Validation error',
            }

            rv = client.post(rule, json={'id': 1, 'name': 'bar'})
            assert rv.status_code == 200
            assert rv.json == {'id': 1, 'name': 'bar'}

            rv = client.post(rule, json={'name': 'bar'})
            assert rv.status_code == 200
            assert rv.json == {'name': 'bar'}

            rv = client.get('/openapi.json')
            assert rv.status_code == 200
            osv.validate(rv.json)
            assert (
                rv.json['paths'][rule]['post']['requestBody']['content']['application/json']['schema'][
                    '$ref'
                ]
                == '#/components/schemas/Foo'
            )

    def test_input_with_query_location(self, app, client):
        @app.route('/foo', methods=['POST'])
        @app.input(Foo, location='query', arg_name='foo')
        @app.input(Bar, location='query', arg_name='bar')
        def foo(foo, bar):
            return {'name': foo['name'], 'name2': bar['name2']}

        rv = client.post('/foo')
        assert rv.status_code == 422
        assert rv.json == {
            'detail': {'query': {'name': ['Missing data for required field.']}},
            'message': 'Validation error',
        }

        rv = client.post('/foo?id=1&name=bar')
        assert rv.status_code == 422
        assert rv.json == {
            'detail': {'query': {'name2': ['Missing data for required field.']}},
            'message': 'Validation error',
        }

        rv = client.post('/foo?id=1&name=bar&id2=2&name2=baz')
        assert rv.status_code == 200
        assert rv.json == {'name': 'bar', 'name2': 'baz'}

        rv = client.post('/foo?name=bar&name2=baz')
        assert rv.status_code == 200
        assert rv.json == {'name': 'bar', 'name2': 'baz'}

    def test_input_with_form_location(self, app, client):
        @app.post('/')
        @app.input(Form, location='form')
        def index(form_data):
            return form_data

        rv = client.post('/')
        assert rv.status_code == 422

        rv = client.post('/', data={'name': 'foo'})
        assert rv.status_code == 200
        assert rv.json == {'name': 'foo'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/']['post']['requestBody']['content'][
                'application/x-www-form-urlencoded'
            ]['schema']['$ref']
            == '#/components/schemas/Form'
        )

    def test_input_with_files_location(self, app, client):
        @app.post('/')
        @app.input(Files, location='files')
        def index(files_data):
            return {'files': len(files_data['files'])}

        rv = client.post('/')
        assert rv.status_code == 422

        rv = client.post(
            '/',
            data={
                'files': (io.BytesIO(b'foo content'), 'foo.txt'),
            },
        )
        assert rv.status_code == 200
        assert rv.json == {'files': 1}

        rv = client.post(
            '/',
            data={
                'files': [
                    (io.BytesIO(b'foo content'), 'foo.txt'),
                    (io.BytesIO(b'bar content'), 'bar.txt'),
                ]
            },
        )
        assert rv.status_code == 200
        assert rv.json == {'files': 2}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/']['post']['requestBody']['content']['multipart/form-data']['schema'][
                '$ref'
            ]
            == '#/components/schemas/Files'
        )

    def test_input_with_form_and_files_location(self, app, client):
        @app.post('/')
        @app.input(FormAndFiles, location='form_and_files')
        def index(form_and_files_data):
            files_length = len(form_and_files_data['files'])
            return {'name': form_and_files_data['name'], 'files': files_length}

        rv = client.post('/')
        assert rv.status_code == 422

        rv = client.post(
            '/',
            data={
                'name': 'foo',
                'files': (io.BytesIO(b'foo content'), 'foo.txt'),
            },
        )
        assert rv.status_code == 200
        assert rv.json == {'name': 'foo', 'files': 1}

        rv = client.post(
            '/',
            data={
                'name': 'bar',
                'files': [
                    (io.BytesIO(b'foo content'), 'foo.txt'),
                    (io.BytesIO(b'bar content'), 'bar.txt'),
                ],
            },
        )
        assert rv.status_code == 200
        assert rv.json == {'name': 'bar', 'files': 2}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/']['post']['requestBody']['content']['multipart/form-data']['schema'][
                '$ref'
            ]
            == '#/components/schemas/FormAndFiles'
        )

    def test_input_with_path_location(self, app, client):
        @app.post('/pets/<category>')
        @app.input(EnumPathParameter, location='path')
        def post_pets(path_data):
            return {'category': path_data['category']}

        rv = client.post('/pets/dogs')
        assert rv.status_code == 200
        assert rv.json == {'category': 'dogs'}

        rv = client.post('/pets/cats')
        assert rv.status_code == 200
        assert rv.json == {'category': 'cats'}

        rv = client.post('/pets/horses')
        assert rv.status_code == 422
        assert rv.json == {
            'detail': {'path': {'category': ['Not a valid choice.']}},
            'message': 'Validation error',
        }

    def test_input_with_headers_location(self, app, client):
        class Headers(Schema):
            x_foo = String(data_key='X-Foo')
            x_bar = String(data_key='X-Bar', required=True)

        @app.post('/')
        @app.input(Headers, location='headers')
        def index(headers_data):
            return {'foo': headers_data.get('x_foo'), 'bar': headers_data['x_bar']}

        rv = client.post('/')
        assert rv.status_code == 422

        rv = client.post('/', headers={'X-Foo': 'foo'})
        assert rv.status_code == 422

        rv = client.post('/', headers={'X-Bar': 'bar'})
        assert rv.status_code == 200
        assert rv.json == {'foo': None, 'bar': 'bar'}

        rv = client.post('/', headers={'X-Foo': 'foo', 'X-Bar': 'bar'})
        assert rv.status_code == 200
        assert rv.json == {'foo': 'foo', 'bar': 'bar'}

    def test_input_with_cookies_location(self, app, client):
        class Cookies(Schema):
            foo = String(required=True)

        @app.post('/')
        @app.input(Cookies, location='cookies')
        def index(cookiedata):
            return {'foo': cookiedata['foo']}

        client.set_cookie('localhost', 'foo', 'bar')

        rv = client.post('/')
        assert rv.status_code == 200
        assert rv.json == {'foo': 'bar'}

    def test_input_multiple_with_one_request_body(self, app, client):
        @app.post('/')
        @app.input(Foo, location='json')
        @app.input(Bar, location='query')
        def index(json_data, query_data):
            return {'name': json_data['name'], 'name2': query_data['name2']}

        rv = client.post('/')
        assert rv.status_code == 422

        rv = client.post('/?name2=bar', json={'name': 'foo'})
        assert rv.status_code == 200
        assert rv.json == {'name': 'foo', 'name2': 'bar'}

    def test_input_validation_error_with_custom_schema(self, app, client):
        class Schema(Schema):
            name = String(required=True, validate=Length(min=5))

        @app.post('/')
        @app.input(Schema)
        def index(json_data):
            return json_data

        rv = client.post('/')
        assert rv.status_code == 422
        assert rv.json == {
            'detail': {'json': {'name': ['Missing data for required field.']}},
            'message': 'Validation error',
        }

        rv = client.post('/', json={'name': 'foo'})
        assert rv.status_code == 422
        assert rv.json == {
            'detail': {'json': {'name': ['Shorter than minimum length 5.']}},
            'message': 'Validation error',
        }

        rv = client.post('/', json={'name': 'valid'})
        assert rv.status_code == 200
        assert rv.json == {'name': 'valid'}

    def test_input_dict_schema(self, app, client):
        schema = {
            'type': 'object',
            'properties': {'name': {'type': 'string'}},
            'required': ['name'],
        }

        @app.post('/')
        @app.input(schema)
        def index(json_data):
            return json_data

        rv = client.post('/')
        assert rv.status_code == 422

        rv = client.post('/', json={'name': 'foo'})
        assert rv.status_code == 200
        assert rv.json == {'name': 'foo'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

    def test_input_with_arg_name_parameter(self, app, client):
        @app.post('/bar')
        @app.input(Foo, arg_name='custom_name')
        def bar(custom_name):
            return custom_name

        rv = client.post('/bar', json={'name': 'foo'})
        assert rv.status_code == 200
        assert rv.json == {'name': 'foo'}

    def test_multi_input_with_different_location(self, app, client):
        @app.post('/multi')
        @app.input(Foo, location='json', arg_name='json_data')
        @app.input(Bar, location='query', arg_name='query_data')
        @app.input(Baz, location='headers', arg_name='header_data')
        @app.input(Form, location='form', arg_name='form_data')
        def multi(json_data, query_data, header_data, form_data):
            return {
                'json': json_data,
                'query': query_data,
                'headers': header_data,
                'form': form_data,
            }

        form_input = {'name': 'the form'}
        query_input = {'id2': 123, 'name2': 'the query'}
        header_input = {'id3': 999, 'name3': 'the header'}
        json_input = {'id': 444, 'name': 'the json'}

        rv = client.post(
            '/multi',
            data=form_input,
            query_string=query_input,
            json=json_input,
            headers={Baz._declared_fields['name3'].data_key: header_input['name3']},
        )
        assert rv.status_code == 200
        assert rv.json == {
            'json': json_input,
            'query': query_input,
            'headers': {'name3': header_input['name3']},
            'form': form_input,
        }

    def test_input_file_with_file_storage_object(self, app, client):
        @app.post('/upload')
        @app.input(Files, location='files')
        def upload(files_data):
            files = files_data['files']
            if isinstance(files, list):
                return {'count': len(files)}
            elif isinstance(files, FileStorage):
                return {'name': files.filename}

        rv = client.post(
            '/upload',
            data={
                'files': (io.BytesIO(b'foo'), 'test.txt'),
            },
        )
        assert rv.status_code == 200
        assert rv.json == {'name': 'test.txt'}

    def test_input_with_empty_json(self, app, client):
        @app.post('/')
        @app.input(Foo)
        def index(json_data):
            return json_data

        rv = client.post(
            '/',
            data='',
            content_type='application/json',
        )
        assert rv.status_code == 400

    def test_input_with_malformed_json(self, app, client):
        @app.post('/')
        @app.input(Foo)
        def index(json_data):
            return json_data

        rv = client.post(
            '/',
            data='{"bad": json}',
            content_type='application/json',
        )
        assert rv.status_code == 400

    def test_input_with_schema_example_parameter(self, app, client):
        @app.post('/')
        @app.input(Foo, example={'id': 1, 'name': 'foo'})
        def index(json_data):
            return json_data

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/']['post']['requestBody']['content']['application/json']['example']
            == {'id': 1, 'name': 'foo'}
        )

    def test_input_with_examples_parameter(self, app, client):
        @app.post('/')
        @app.input(
            Foo,
            examples={
                'example one': {
                    'summary': 'An example',
                    'value': {'id': 1, 'name': 'foo'},
                },
                'example two': {
                    'summary': 'Another example',
                    'value': {'id': 2, 'name': 'bar'},
                },
            },
        )
        def index(json_data):
            return json_data

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/']['post']['requestBody']['content']['application/json']['examples']
            == {
                'example one': {
                    'summary': 'An example',
                    'value': {'id': 1, 'name': 'foo'},
                },
                'example two': {
                    'summary': 'Another example',
                    'value': {'id': 2, 'name': 'bar'},
                },
            }
        )


class TestOutputDecorator:
    """Tests for the @output decorator."""

    def test_output(self, app, client):
        @app.route('/foo')
        @app.output(Foo)
        def foo():
            return {'name': 'bar'}

        @app.route('/bar')
        @app.output(Foo, status_code=201)
        def bar():
            return {'name': 'foo'}

        @app.route('/baz')
        @app.input(Query, location='query')
        @app.output(Foo, status_code=201)
        def baz(query_data):
            if query_data['id'] == 1:
                return {'name': 'baz'}, 202
            elif query_data['id'] == 2:
                return {'name': 'baz'}, {'Location': '/baz'}
            elif query_data['id'] == 3:
                return {'name': 'baz'}, 202, {'Location': '/baz'}
            return ({'name': 'baz'},)

        rv = client.get('/foo')
        assert rv.status_code == 200
        assert rv.json == {'id': 123, 'name': 'bar'}

        rv = client.get('/bar')
        assert rv.status_code == 201
        assert rv.json == {'id': 123, 'name': 'foo'}

        rv = client.get('/baz')
        assert rv.status_code == 202
        assert rv.json == {'id': 123, 'name': 'baz'}
        assert 'Location' not in rv.headers

        rv = client.get('/baz?id=2')
        assert rv.status_code == 201
        assert rv.json == {'id': 123, 'name': 'baz'}
        assert rv.headers.get('Location') == '/baz'

        rv = client.get('/baz?id=3')
        assert rv.status_code == 202
        assert rv.json == {'id': 123, 'name': 'baz'}
        assert rv.headers.get('Location') == '/baz'

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['content']['application/json'][
                'schema'
            ]['$ref']
            == '#/components/schemas/Foo'
        )
        assert (
            rv.json['paths']['/bar']['get']['responses']['201']['content']['application/json'][
                'schema'
            ]['$ref']
            == '#/components/schemas/Foo'
        )

    def test_output_with_methodview(self, app, client):
        @app.route('/foo')
        class FooView(MethodView):
            @app.output(Foo)
            def get(self):
                return {'name': 'bar'}

            @app.output(Foo, status_code=201)
            def post(self):
                return {'name': 'foo'}

        rv = client.get('/foo')
        assert rv.status_code == 200
        assert rv.json == {'id': 123, 'name': 'bar'}

        rv = client.post('/foo')
        assert rv.status_code == 201
        assert rv.json == {'id': 123, 'name': 'foo'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['content']['application/json'][
                'schema'
            ]['$ref']
            == '#/components/schemas/Foo'
        )
        assert (
            rv.json['paths']['/foo']['post']['responses']['201']['content']['application/json'][
                'schema'
            ]['$ref']
            == '#/components/schemas/Foo'
        )

    def test_output_with_response_object(self, app, client):
        @app.route('/foo')
        @app.output(Foo)
        def foo():
            return make_response({'name': 'bar'})

        rv = client.get('/foo')
        assert rv.status_code == 200
        assert rv.json == {'id': 123, 'name': 'bar'}

    def test_output_with_dataclass(self, app, client):
        @dataclass
        class Data:
            name: str

        @app.route('/foo')
        @app.output(Foo)
        def foo():
            return Data('bar')

        rv = client.get('/foo')
        assert rv.status_code == 200
        assert rv.json == {'id': 123, 'name': 'bar'}

    def test_output_with_description_parameter(self, app, client):
        @app.route('/foo')
        @app.output(Foo, description='The description for output.')
        def foo():
            return {'name': 'bar'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['description']
            == 'The description for output.'
        )

    def test_output_with_example_parameter(self, app, client):
        @app.route('/foo')
        @app.output(Foo, example={'id': 1, 'name': 'foo'})
        def foo():
            return {'name': 'bar'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['content']['application/json'][
                'example'
            ]
            == {'id': 1, 'name': 'foo'}
        )

    def test_output_with_examples_parameter(self, app, client):
        @app.route('/foo')
        @app.output(
            Foo,
            examples={
                'example one': {
                    'summary': 'An example',
                    'value': {'id': 1, 'name': 'foo'},
                },
                'example two': {
                    'summary': 'Another example',
                    'value': {'id': 2, 'name': 'bar'},
                },
            },
        )
        def foo():
            return {'name': 'bar'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['content']['application/json'][
                'examples'
            ]
            == {
                'example one': {
                    'summary': 'An example',
                    'value': {'id': 1, 'name': 'foo'},
                },
                'example two': {
                    'summary': 'Another example',
                    'value': {'id': 2, 'name': 'bar'},
                },
            }
        )

    def test_output_with_headers_parameter(self, app, client):
        @app.route('/foo')
        @app.output(Foo, headers={'X-Foo': 'foo'})
        def foo():
            return {'name': 'foo'}

        @app.route('/bar')
        @app.output(Foo, headers={'X-Foo': {'description': 'some description'}})
        def bar():
            return {'name': 'bar'}

        @app.route('/baz')
        @app.output(Foo, headers={'X-Foo': {'description': 'some description', 'schema': str}})
        def baz():
            return {'name': 'baz'}

        @app.route('/spam')
        @app.output(Foo, headers={'X-Foo': {'description': 'some description', 'schema': {'type': 'string'}}})
        def spam():
            return {'name': 'spam'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'x-foo' in rv.json['paths']['/foo']['get']['responses']['200']['headers']
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['headers']['x-foo']
            == {'description': 'foo', 'schema': {'type': 'string'}}
        )
        assert 'x-foo' in rv.json['paths']['/bar']['get']['responses']['200']['headers']
        assert (
            rv.json['paths']['/bar']['get']['responses']['200']['headers']['x-foo']
            == {'description': 'some description', 'schema': {'type': 'string'}}
        )
        assert 'x-foo' in rv.json['paths']['/baz']['get']['responses']['200']['headers']
        assert (
            rv.json['paths']['/baz']['get']['responses']['200']['headers']['x-foo']
            == {'description': 'some description', 'schema': {'type': 'string'}}
        )
        assert 'x-foo' in rv.json['paths']['/spam']['get']['responses']['200']['headers']
        assert (
            rv.json['paths']['/spam']['get']['responses']['200']['headers']['x-foo']
            == {'description': 'some description', 'schema': {'type': 'string'}}
        )

    def test_output_with_links_parameter(self, app, client):
        @app.route('/pets/<int:pet_id>')
        @app.output(Foo)
        def get_pet(pet_id):
            return {'name': 'bar'}

        @app.route('/pets')
        @app.output(
            Foo,
            links={
                'getPetById': {
                    'operationId': 'get_pet',
                    'parameters': {'pet_id': '$response.body#/id'},
                }
            },
        )
        def create_pet():
            return {'name': 'foo'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'getPetById' in rv.json['paths']['/pets']['get']['responses']['200']['links']
        assert (
            rv.json['paths']['/pets']['get']['responses']['200']['links']['getPetById']
            == {
                'operationId': 'get_pet',
                'parameters': {'pet_id': '$response.body#/id'},
            }
        )

    def test_output_dict_schema(self, app, client):
        schema = {
            'type': 'object',
            'properties': {'name': {'type': 'string'}},
        }

        @app.route('/foo')
        @app.output(schema)
        def foo():
            return {'name': 'bar'}

        rv = client.get('/foo')
        assert rv.status_code == 200
        assert rv.json == {'name': 'bar'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

    def test_output_with_content_type_parameter(self, app, client):
        @app.route('/foo')
        @app.output(Foo, content_type='application/xml')
        def foo():
            return '<?xml version="1.0" encoding="UTF-8" ?>
