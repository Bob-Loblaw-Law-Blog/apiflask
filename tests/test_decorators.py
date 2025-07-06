import io
import pytest
from dataclasses import dataclass

import openapi_spec_validator as osv
from flask import make_response
from flask.views import MethodView

from apiflask import APIBlueprint
from apiflask.security import HTTPBasicAuth, HTTPTokenAuth
from .schemas import Bar, CustomHTTPError, EnumPathParameter, Files, Foo, Form, FormAndFiles, Query, Schema
from apiflask.fields import Field, String
from apiflask.validators import Length, OneOf

from werkzeug.datastructures import FileStorage

class TestDecoratorBase:

    def test_app_decorators(self, app):
        with app.app_context():
            assert hasattr(app, 'auth_required')
            assert hasattr(app, 'input')
            assert hasattr(app, 'output')
            assert hasattr(app, 'doc')


    def test_bp_decorators(app):
        bp = APIBlueprint('test', __name__)
        assert hasattr(bp, 'auth_required')
        assert hasattr(bp, 'input')
        assert hasattr(bp, 'output')
        assert hasattr(bp, 'doc')


class TestDecoratorAuthRequired:

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
        class Foo(MethodView):
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
        class Baz(MethodView):
            def get(self):
                pass

            def post(self):
                pass

        @no_auth_bp.get('/eggs')
        def eggs():
            return 'no auth'

        with app.app_context():
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

class TestDecoratorDoc:

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
        class Baz(MethodView):
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
        class Baz(MethodView):
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
        class Bar(MethodView):
            def get(self):
                pass

            @app.doc(hide=True)
            def post(self):
                pass

        @app.route('/secret')
        class Secret(MethodView):
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
        class FooAPI(MethodView):
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
        class FooAPI(MethodView):
            @app.input(Foo)
            @app.output(Foo)
            @app.doc(responses={200: 'success', 400: 'bad', 404: 'not found', 500: 'server error'})
            def get(self):
                pass

        @app.route('/bar')
        class BarAPI(MethodView):
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

class TestDecoratorInput:
    def test_input(self, app, client):
        @app.route('/foo', methods=['POST'])
        @app.input(Foo)
        def foo(json_data):
            return json_data

        @app.route('/bar')
        class Bar(MethodView):
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

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            'application/x-www-form-urlencoded'
            in rv.json['paths']['/']['post']['requestBody']['content']
        )
        assert (
            rv.json['paths']['/']['post']['requestBody']['content'][
                'application/x-www-form-urlencoded'
            ]['schema']['$ref']
            == '#/components/schemas/Form'
        )
        assert 'Form' in rv.json['components']['schemas']

        rv = client.post('/', data={'name': 'foo'})
        assert rv.status_code == 200
        assert rv.json == {'name': 'foo'}


    def test_input_with_files_location(self, app, client):
        @app.post('/')
        @app.input(Files, location='files')
        def index(files_data):
            data = {}
            if 'image' in files_data and isinstance(files_data['image'], FileStorage):
                data['image'] = True
            return data

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'multipart/form-data' in rv.json['paths']['/']['post']['requestBody']['content']
        assert (
            rv.json['paths']['/']['post']['requestBody']['content']['multipart/form-data']['schema'][
                '$ref'
            ]
            == '#/components/schemas/Files'
        )
        assert 'image' in rv.json['components']['schemas']['Files']['properties']
        assert rv.json['components']['schemas']['Files']['properties']['image']['type'] == 'string'
        assert rv.json['components']['schemas']['Files']['properties']['image']['format'] == 'binary'

        rv = client.post(
            '/',
            data={
                'image': (io.BytesIO(b'test'), 'test.jpg'),
            },
            content_type='multipart/form-data',
        )
        assert rv.status_code == 200
        assert rv.json == {'image': True}


    def test_input_with_form_and_files_location(self, app, client):
        @app.post('/')
        @app.input(FormAndFiles, location='form_and_files')
        def index(form_and_files_data):
            data = {}
            if 'name' in form_and_files_data:
                data['name'] = True
            if 'image' in form_and_files_data and isinstance(form_and_files_data['image'], FileStorage):
                data['image'] = True
            return data

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'multipart/form-data' in rv.json['paths']['/']['post']['requestBody']['content']
        assert (
            rv.json['paths']['/']['post']['requestBody']['content']['multipart/form-data']['schema'][
                '$ref'
            ]
            == '#/components/schemas/FormAndFiles'
        )
        assert 'name' in rv.json['components']['schemas']['FormAndFiles']['properties']
        assert 'image' in rv.json['components']['schemas']['FormAndFiles']['properties']
        assert (
            rv.json['components']['schemas']['FormAndFiles']['properties']['image']['type'] == 'string'
        )
        assert (
            rv.json['components']['schemas']['FormAndFiles']['properties']['image']['format']
            == 'binary'
        )

        rv = client.post(
            '/',
            data={'name': 'foo', 'image': (io.BytesIO(b'test'), 'test.jpg')},
            content_type='multipart/form-data',
        )
        assert rv.status_code == 200
        assert rv.json == {'name': True, 'image': True}


    def test_input_with_json_or_form_location(self, app, client):
        @app.post('/')
        @app.input(Form, location='json_or_form')
        def index(json_or_form_data):
            return json_or_form_data

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            'application/x-www-form-urlencoded'
            in rv.json['paths']['/']['post']['requestBody']['content']
        )
        assert 'application/json' in rv.json['paths']['/']['post']['requestBody']['content']
        assert (
            rv.json['paths']['/']['post']['requestBody']['content']['application/json']['schema'][
                '$ref'
            ]
            == '#/components/schemas/Form'
        )
        assert (
            rv.json['paths']['/']['post']['requestBody']['content'][
                'application/x-www-form-urlencoded'
            ]['schema']['$ref']
            == '#/components/schemas/Form'
        )
        assert 'Form' in rv.json['components']['schemas']

        rv = client.post('/', data={'name': 'foo'})
        assert rv.status_code == 200
        assert rv.json == {'name': 'foo'}

        rv = client.post('/', json={'name': 'foo'})
        assert rv.status_code == 200
        assert rv.json == {'name': 'foo'}


    def test_input_with_path_location(self, app, client):
        @app.get('/<image_type>')
        @app.input(EnumPathParameter, location='path')
        def index(image_type, path_data):
            return {'image_type': image_type}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '/{image_type}' in rv.json['paths']
        assert len(rv.json['paths']['/{image_type}']['get']['parameters']) == 1
        assert rv.json['paths']['/{image_type}']['get']['parameters'][0]['in'] == 'path'
        assert rv.json['paths']['/{image_type}']['get']['parameters'][0]['name'] == 'image_type'
        assert rv.json['paths']['/{image_type}']['get']['parameters'][0]['schema'] == {
            'type': 'string',
            'enum': ['jpg', 'png', 'tiff', 'webp'],
        }

        rv = client.get('/png')
        assert rv.status_code == 200
        assert rv.json == {'image_type': 'png'}

        rv = client.get('/gif')
        assert rv.status_code == 422
        assert rv.json['message'] == 'Validation error'
        assert 'path' in rv.json['detail']
        assert 'image_type' in rv.json['detail']['path']
        assert rv.json['detail']['path']['image_type'] == ['Must be one of: jpg, png, tiff, webp.']


    @pytest.mark.parametrize(
        'locations',
        [
            ['files', 'form'],
            ['files', 'json'],
            ['form', 'json'],
            ['form_and_files', 'json'],
            ['form_and_files', 'form'],
            ['form_and_files', 'files'],
            ['json_or_form', 'json'],
            ['json_or_form', 'files'],
            ['json_or_form', 'form'],
            ['json_or_form', 'form_and_files'],
        ],
    )
    def test_multiple_input_body_location(self, app, locations):
        arg_name_1 = f'{locations[0]}_data'  # noqa: F841
        arg_name_2 = f'{locations[1]}_data'  # noqa: F841
        with pytest.raises(RuntimeError):

            @app.route('/foo')
            @app.input(Foo, location=locations[0])
            @app.input(Bar, location=locations[1])
            def foo(arg_name_1, arg_name_2):
                pass


    def test_input_with_dict_schema(self, app, client):
        dict_schema = {'name': String(required=True)}

        @app.get('/foo')
        @app.input(dict_schema, location='query')
        def foo(query_data):
            return query_data

        @app.post('/bar')
        @app.input(dict_schema, schema_name='MyName')
        def bar(json_data):
            return json_data

        @app.post('/baz')
        @app.input(dict_schema)
        def baz(json_data):
            return json_data

        @app.post('/spam')
        @app.input(dict_schema)
        def spam(json_data):
            return json_data

        rv = client.get('/foo')
        assert rv.status_code == 422
        assert rv.json == {
            'detail': {'query': {'name': ['Missing data for required field.']}},
            'message': 'Validation error',
        }

        rv = client.get('/foo?name=grey')
        assert rv.status_code == 200
        assert rv.json == {'name': 'grey'}

        rv = client.post('/bar')
        assert rv.status_code == 422
        assert rv.json == {
            'detail': {'json': {'name': ['Missing data for required field.']}},
            'message': 'Validation error',
        }

        rv = client.post('/bar', json={'name': 'grey'})
        assert rv.status_code == 200
        assert rv.json == {'name': 'grey'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['parameters'][0] == {
            'in': 'query',
            'name': 'name',
            'required': True,
            'schema': {'type': 'string'},
        }
        # TODO check the excess item "'x-scope': ['']" in schema object
        # https://github.com/p1c2u/openapi-spec-validator/issues/53
        assert (
            rv.json['paths']['/bar']['post']['requestBody']['content']['application/json']['schema'][
                '$ref'
            ]
            == '#/components/schemas/MyName'
        )
        assert rv.json['components']['schemas']['MyName'] == {
            'properties': {'name': {'type': 'string'}},
            'required': ['name'],
            'type': 'object',
        }
        # default schema name is "Generated"
        assert (
            rv.json['paths']['/baz']['post']['requestBody']['content']['application/json']['schema'][
                '$ref'
            ]
            == '#/components/schemas/Generated'
        )
        assert (
            rv.json['paths']['/spam']['post']['requestBody']['content']['application/json']['schema'][
                '$ref'
            ]
            == '#/components/schemas/Generated1'
        )


    def test_input_body_example(self, app, client):
        example = {'name': 'foo', 'id': 2}
        examples = {
            'example foo': {'summary': 'an example of foo', 'value': {'name': 'foo', 'id': 1}},
            'example bar': {'summary': 'an example of bar', 'value': {'name': 'bar', 'id': 2}},
        }

        @app.post('/foo')
        @app.input(Foo, example=example)
        def foo():
            pass

        @app.post('/bar')
        @app.input(Foo, examples=examples)
        def bar():
            pass

        @app.route('/baz')
        class Baz(MethodView):
            @app.input(Foo, example=example)
            def get(self):
                pass

            @app.input(Foo, examples=examples)
            def post(self):
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/foo']['post']['requestBody']['content']['application/json']['example']
            == example
        )
        assert (
            rv.json['paths']['/bar']['post']['requestBody']['content']['application/json']['examples']
            == examples
        )

        assert (
            rv.json['paths']['/baz']['get']['requestBody']['content']['application/json']['example']
            == example
        )
        assert (
            rv.json['paths']['/baz']['post']['requestBody']['content']['application/json']['examples']
            == examples
        )


    def test_skip_validation(self, app, client):
        incorrect_json = {'name': 'Kitty', 'category': 'unknown'}

        class PetIn(Schema):
            name = String(required=True, validate=Length(0, 10))
            category = String(required=True, validate=OneOf(['dog', 'cat']))

        @app.patch('/pets_without_validation/<int:pet_id>')
        @app.input(PetIn, validation=False)
        def pets_without_validation(pet_id, json_data):
            return {'pet_id': pet_id, 'json_data': json_data}

        no_validated_rv = client.patch('/pets_without_validation/1', json=incorrect_json)
        assert no_validated_rv.status_code == 200
        assert no_validated_rv.json['json_data']['name'] == 'Kitty'
        assert no_validated_rv.json['json_data']['category'] == 'unknown'

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        assert (
            rv.json['paths']['/pets_without_validation/{pet_id}']['patch']['requestBody']['content'][
                'application/json'
            ]['schema']['$ref']
            == '#/components/schemas/PetIn'
        )
        assert 'PetIn' in rv.json['components']['schemas']


    @pytest.mark.parametrize('validation', [True, False])
    @pytest.mark.parametrize('payload', [[], [{'bar': 'baz'}], [{'qux': 'baz'}]])
    def test_skip_validation_list_input(self, app, client, validation, payload):
        class FooIn(Schema):
            bar = String(required=True)

        @app.put('/foo/bulk')
        @app.input(FooIn(many=True), validation=validation)
        def bulk_put_foo(json_data):
            return json_data

        rv = client.put('/foo/bulk', json=payload)
        if validation and payload and 'bar' not in payload[0]:
            assert rv.status_code == 422
        else:
            assert rv.status_code == 200
            assert rv.json == payload


    @pytest.mark.parametrize('validation', [True, False])
    @pytest.mark.parametrize('payload', [{}, {'bar': 'qux'}])
    def test_skip_validation_arg_name(self, app, client, validation, payload):
        class FooIn(Schema):
            bar = String(required=True)

        @app.post('/foo')
        @app.input(FooIn, arg_name='baz', validation=validation)
        def post_foo(baz):
            return baz

        rv = client.post('/foo', json=payload)
        if validation and not payload:
            assert rv.status_code == 422
        else:
            assert rv.status_code == 200
            assert rv.json == payload

class TestDecoratorOutput:
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
        assert rv.headers['Location'].endswith('/baz')

        rv = client.get('/baz?id=3')
        assert rv.status_code == 202
        assert rv.json == {'id': 123, 'name': 'baz'}
        assert rv.headers['Location'].endswith('/baz')

        rv = client.get('/baz?id=4')
        assert rv.status_code == 201
        assert rv.json == {'id': 123, 'name': 'baz'}
        assert 'Location' not in rv.headers


    def test_output_with_methodview(self, app, client):
        @app.route('/')
        class FooAPI(MethodView):
            @app.output(Foo)
            def get(self):
                return {'name': 'bar'}

            @app.output(Foo, status_code=201)
            def post(self):
                return {'name': 'foo'}

            @app.input(Query, location='query')
            @app.output(Foo, status_code=201)
            def delete(self, query_data):
                if query_data['id'] == 1:
                    return {'name': 'baz'}, 202
                elif query_data['id'] == 2:
                    return {'name': 'baz'}, {'Location': '/baz'}
                elif query_data['id'] == 3:
                    return {'name': 'baz'}, 202, {'Location': '/baz'}
                return ({'name': 'baz'},)

        rv = client.get('/')
        assert rv.status_code == 200
        assert rv.json == {'id': 123, 'name': 'bar'}

        rv = client.post('/')
        assert rv.status_code == 201
        assert rv.json == {'id': 123, 'name': 'foo'}

        rv = client.delete('/')
        assert rv.status_code == 202
        assert rv.json == {'id': 123, 'name': 'baz'}
        assert 'Location' not in rv.headers

        rv = client.delete('/?id=2')
        assert rv.status_code == 201
        assert rv.json == {'id': 123, 'name': 'baz'}
        assert rv.headers['Location'].endswith('/baz')

        rv = client.delete('/?id=3')
        assert rv.status_code == 202
        assert rv.json == {'id': 123, 'name': 'baz'}
        assert rv.headers['Location'].endswith('/baz')

        rv = client.delete('/?id=4')
        assert rv.status_code == 201
        assert rv.json == {'id': 123, 'name': 'baz'}
        assert 'Location' not in rv.headers


    def test_output_with_dict_schema(self, app, client):
        dict_schema = {'name': String(dump_default='grey')}

        @app.get('/foo')
        @app.output(dict_schema, schema_name='MyName')
        def foo():
            return ''

        @app.get('/bar')
        @app.output(dict_schema, schema_name='MyName')
        def bar():
            return {'name': 'peter'}

        @app.get('/baz')
        @app.output(dict_schema)
        def baz():
            pass

        @app.get('/spam')
        @app.output(dict_schema)
        def spam():
            pass

        @app.get('/eggs')
        @app.output({})
        def eggs():
            pass

        rv = client.get('/foo')
        assert rv.status_code == 200
        assert rv.json == {'name': 'grey'}

        rv = client.get('/bar')
        assert rv.status_code == 200
        assert rv.json == {'name': 'peter'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['content']['application/json'][
                'schema'
            ]['$ref']
            == '#/components/schemas/MyName'
        )
        assert rv.json['components']['schemas']['MyName'] == {
            'properties': {'name': {'type': 'string'}},
            'type': 'object',
        }
        assert (
            rv.json['paths']['/bar']['get']['responses']['200']['content']['application/json'][
                'schema'
            ]['$ref']
            == '#/components/schemas/MyName1'
        )
        # default schema name is "Generated"
        assert (
            rv.json['paths']['/baz']['get']['responses']['200']['content']['application/json'][
                'schema'
            ]['$ref']
            == '#/components/schemas/Generated'
        )
        assert (
            rv.json['paths']['/spam']['get']['responses']['200']['content']['application/json'][
                'schema'
            ]['$ref']
            == '#/components/schemas/Generated1'
        )


    def test_output_with_object_schema(self, app, client):
        class BaseResponse(Schema):
            data = Field()
            message = String(dump_default='Success')

        app.config['BASE_RESPONSE_SCHEMA'] = BaseResponse

        class PetOut(Schema):
            name = String()

        @dataclass
        class Pet:
            name: str

        @dataclass
        class Response:
            data: Pet

        @app.get('/foo')
        @app.output(PetOut)
        def foo():
            pet = Pet('foo')
            return Response(data=pet)

        rv = client.get('/foo')
        assert rv.status_code == 200
        assert rv.json['data'] == {'name': 'foo'}


    def test_output_body_example(self, app, client):
        example = {'name': 'foo', 'id': 2}
        examples = {
            'example foo': {'summary': 'an example of foo', 'value': {'name': 'foo', 'id': 1}},
            'example bar': {'summary': 'an example of bar', 'value': {'name': 'bar', 'id': 2}},
        }

        @app.get('/foo')
        @app.output(Foo, example=example)
        def foo():
            pass

        @app.get('/bar')
        @app.output(Foo, examples=examples)
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['content']['application/json'][
                'example'
            ]
            == example
        )
        assert (
            rv.json['paths']['/bar']['get']['responses']['200']['content']['application/json'][
                'examples'
            ]
            == examples
        )


    def test_output_with_empty_dict_as_schema(self, app, client):
        @app.delete('/foo')
        @app.output({}, status_code=204)
        def delete_foo():
            return ''

        @app.route('/bar')
        class Bar(MethodView):
            @app.output({}, status_code=204)
            def delete(self):
                return ''

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'content' not in rv.json['paths']['/foo']['delete']['responses']['204']
        assert 'content' not in rv.json['paths']['/bar']['delete']['responses']['204']

        rv = client.delete('/foo')
        assert rv.status_code == 204
        rv = client.delete('/bar')
        assert rv.status_code == 204


    def test_output_response_object_directly(self, app, client):
        @app.get('/foo')
        @app.output(Foo)
        def foo():
            return make_response({'message': 'hello'})

        rv = client.get('/foo')
        assert rv.status_code == 200
        assert rv.json['message'] == 'hello'


    def test_response_links(self, app, client):
        links = {
            'foo': {'operationId': 'getFoo', 'parameters': {'id': 1}},
            'bar': {'operationId': 'getBar', 'parameters': {'id': 2}},
        }

        @app.get('/foo')
        @app.output(Foo, links=links)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['responses']['200']['links'] == links


    def test_response_links_ref(self, app, client):
        links = {'getFoo': {'$ref': '#/components/links/foo'}}

        @app.spec_processor
        def add_links(spec):
            spec['components']['links'] = {'foo': {'operationId': 'getFoo', 'parameters': {'id': 1}}}
            return spec

        @app.get('/foo')
        @app.output(Foo, links=links)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'getFoo' in rv.json['paths']['/foo']['get']['responses']['200']['links']


    def test_response_content_type(self, app, client):
        @app.get('/foo')
        @app.output(Foo)  # default value is application/json
        def foo():
            pass

        @app.get('/bar')
        @app.output(Foo, content_type='image/png')
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert len(rv.json['paths']['/foo']['get']['responses']['200']['content']) == 1
        assert len(rv.json['paths']['/bar']['get']['responses']['200']['content']) == 1
        assert 'application/json' in rv.json['paths']['/foo']['get']['responses']['200']['content']
        assert 'image/png' in rv.json['paths']['/bar']['get']['responses']['200']['content']
