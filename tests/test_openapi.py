"""
Consolidated tests for APIFlask OpenAPI functionality.

This module contains all tests for OpenAPI-related features including:
- Basic OpenAPI spec generation and validation
- Info object properties (title, version, description, etc.)
- Security schemes and authentication
- Tags and tag organization
- Blueprint integration
- Headers handling
- Paths and operations
- Extensions support
"""

import importlib
import json

import openapi_spec_validator as osv
import pytest
from flask import request

from .schemas import Bar, Baz, Foo, Query, Form, Files, FormAndFiles
from apiflask import APIBlueprint, APIFlask, HTTPBasicAuth, HTTPTokenAuth, Schema
from apiflask.commands import spec_command
from apiflask.fields import Integer, String


class TestBasicOpenAPI:
    """Tests for basic OpenAPI spec generation and core functionality."""

    def test_spec(self, app):
        assert app.spec
        assert 'openapi' in app.spec

    def test_spec_processor(self, app, client):
        @app.spec_processor
        def edit_spec(spec):
            assert spec['openapi'] == '3.0.3'
            spec['openapi'] = '3.0.2'
            assert app.title == 'APIFlask'
            assert spec['info']['title'] == 'APIFlask'
            spec['info']['title'] = 'Foo'
            return spec

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['openapi'] == '3.0.2'
        assert rv.json['info']['title'] == 'Foo'

    def test_spec_processor_pass_object(self, app, client):
        app.config['SPEC_PROCESSOR_PASS_OBJECT'] = True

        class NotUsedSchema(Schema):
            id = Integer()

        @app.spec_processor
        def process_spec(spec):
            spec.title = 'Foo'
            spec.components.schema('NotUsed', schema=NotUsedSchema)
            return spec

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['info']['title'] == 'Foo'
        assert 'NotUsed' in rv.json['components']['schemas']
        assert 'id' in rv.json['components']['schemas']['NotUsed']['properties']

    @pytest.mark.parametrize('spec_format', ['json', 'yaml', 'yml'])
    def test_get_spec(self, app, spec_format):
        spec = app._get_spec(spec_format)

        if spec_format == 'json':
            assert isinstance(spec, dict)
        else:
            assert 'title: APIFlask' in spec

    def test_get_spec_force_update(self, app):
        app._get_spec()

        @app.route('/foo')
        @app.output(Foo)
        def foo():
            pass

        spec = app._get_spec()
        assert '/foo' not in spec['paths']

        new_spec = app._get_spec(force_update=True)
        assert '/foo' in new_spec['paths']

    def test_spec_bypass_endpoints(self, app):
        bp = APIBlueprint('foo', __name__, static_folder='static', url_prefix='/foo')
        app.register_blueprint(bp)

        spec = app._get_spec()
        assert '/static' not in spec['paths']
        assert '/foo/static' not in spec['paths']
        assert '/docs' not in spec['paths']
        assert '/openapi.json' not in spec['paths']
        assert '/docs/oauth2-redirect' not in spec['paths']

    def test_spec_bypass_methods(self, app):
        class Foo:
            def bar(self):
                pass

        app.add_url_rule('/foo', 'foo', Foo().bar)

        spec = app._get_spec()
        assert '/foo' not in spec['paths']

    def test_spec_attribute(self, app):
        spec = app._get_spec()

        @app.route('/foo')
        @app.output(Foo)
        def foo():
            pass

        assert '/foo' not in spec['paths']
        assert '/foo' in app.spec['paths']

    def test_spec_schemas(self, app):
        @app.route('/foo')
        @app.output(Foo(partial=True))
        def foo():
            pass

        @app.route('/bar')
        @app.output(Bar(many=True))
        def bar():
            pass

        @app.route('/baz')
        @app.output(Baz)
        def baz():
            pass

        class Spam(Schema):
            id = Integer()

        @app.route('/spam')
        @app.output(Spam)
        def spam():
            pass

        class Ham(Schema):
            id = Integer()

        @app.route('/ham')
        @app.output(Ham)
        def ham():
            pass

        spec = app.spec
        assert len(spec['components']['schemas']) == 5
        assert 'FooUpdate' in spec['components']['schemas']
        assert 'Bar' in spec['components']['schemas']
        assert 'Baz' in spec['components']['schemas']
        assert 'Spam' in spec['components']['schemas']
        assert 'Ham' in spec['components']['schemas']

    def test_servers_and_externaldocs(self, app):
        assert app.external_docs is None
        assert app.servers is None

        app.external_docs = {'description': 'Find more info here', 'url': 'https://docs.example.com/'}
        app.servers = [
            {'url': 'http://localhost:5000/', 'description': 'Development server'},
            {'url': 'https://api.example.com/', 'description': 'Production server'},
        ]

        rv = app.test_client().get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['externalDocs'] == {
            'description': 'Find more info here',
            'url': 'https://docs.example.com/',
        }
        assert rv.json['servers'] == [
            {'url': 'http://localhost:5000/', 'description': 'Development server'},
            {'url': 'https://api.example.com/', 'description': 'Production server'},
        ]

    def test_default_servers(self, app):
        assert app.servers is None

        rv = app.test_client().get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        with app.test_request_context():
            assert rv.json['servers'] == [
                {
                    'url': f'{request.url_root}',
                },
            ]

    def test_default_servers_without_req_context(self, cli_runner):
        result = cli_runner.invoke(spec_command)
        assert 'openapi' in result.output
        assert 'servers' not in json.loads(result.output)

    def test_auto_200_response(self, app, client):
        @app.get('/foo')
        def bare():
            pass

        @app.get('/bar')
        @app.input(Foo)
        def only_input():
            pass

        @app.get('/baz')
        @app.doc(summary='some summary')
        def only_doc():
            pass

        @app.get('/eggs')
        @app.output(Foo, status_code=204)
        def output_204():
            pass

        @app.get('/spam')
        @app.doc(responses={204: 'empty'})
        def doc_responses():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '200' in rv.json['paths']['/foo']['get']['responses']
        assert '200' in rv.json['paths']['/bar']['get']['responses']
        assert '200' in rv.json['paths']['/baz']['get']['responses']
        assert '200' not in rv.json['paths']['/eggs']['get']['responses']
        assert '200' not in rv.json['paths']['/spam']['get']['responses']
        assert rv.json['paths']['/spam']['get']['responses']['204']['description'] == 'empty'

    def test_sync_local_json_spec(self, app, client, tmp_path):
        app.config['AUTO_SERVERS'] = False

        local_spec_path = tmp_path / 'openapi.json'
        app.config['SYNC_LOCAL_SPEC'] = True
        app.config['LOCAL_SPEC_PATH'] = local_spec_path
        app.config['SPEC_FORMAT'] = 'json'

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        with open(local_spec_path) as f:
            spec_content = json.loads(f.read())
            assert spec_content == app.spec
            assert 'info' in spec_content
            assert 'paths' in spec_content

    def test_sync_local_yaml_spec(self, app, client, tmp_path):
        app.config['AUTO_SERVERS'] = False

        local_spec_path = tmp_path / 'openapi.json'
        app.config['SYNC_LOCAL_SPEC'] = True
        app.config['LOCAL_SPEC_PATH'] = local_spec_path
        app.config['SPEC_FORMAT'] = 'yaml'

        rv = client.get('/openapi.json')
        assert rv.status_code == 200

        with open(local_spec_path) as f:
            spec_content = f.read()
            assert spec_content == str(app.spec)
            assert 'title: APIFlask' in spec_content

    def test_sync_local_spec_no_path(self, app):
        app.config['SYNC_LOCAL_SPEC'] = True

        with pytest.raises(TypeError):
            app.spec


class TestOpenAPIInfo:
    """Tests for OpenAPI info object properties."""

    def test_info_title_and_version(self, app):
        assert app.title == 'APIFlask'
        assert app.version == '0.1.0'

        app = APIFlask(__name__, title='Foo', version='1.0')
        assert app.spec['info']['title'] == 'Foo'
        assert app.spec['info']['version'] == '1.0'

    def test_other_info_fields(self, app, client):
        assert app.description is None
        assert app.terms_of_service is None
        assert app.contact is None
        assert app.license is None

        app.description = 'My API'
        app.terms_of_service = 'http://example.com/terms/'
        app.contact = {
            'name': 'API Support',
            'url': 'http://www.example.com/support',
            'email': 'support@example.com',
        }
        app.license = {'name': 'Apache 2.0', 'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['info']['description'] == 'My API'
        assert rv.json['info']['termsOfService'] == 'http://example.com/terms/'
        assert rv.json['info']['contact'] == {
            'name': 'API Support',
            'url': 'http://www.example.com/support',
            'email': 'support@example.com',
        }
        assert rv.json['info']['license'] == {
            'name': 'Apache 2.0',
            'url': 'http://www.apache.org/licenses/LICENSE-2.0.html',
        }

    def test_empty_title(self):
        with pytest.raises(ValueError):
            APIFlask(__name__, title='')

    def test_setting_title(self, app, client):
        app.title = 'Foo'
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['info']['title'] == 'Foo'

    def test_setting_version(self, app, client):
        app.version = '2.0.0'
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['info']['version'] == '2.0.0'


class TestOpenAPISecurity:
    """Tests for OpenAPI security schemes and authentication."""

    def test_httpbasicauth_security_scheme(self, app, client):
        auth = HTTPBasicAuth()

        @app.get('/')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'BasicAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['BasicAuth'] == {
            'type': 'http',
            'scheme': 'basic',
        }

    def test_httptokenauth_security_scheme(self, app, client):
        auth = HTTPTokenAuth()

        @app.get('/')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'BearerAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['BearerAuth'] == {
            'type': 'http',
            'scheme': 'bearer',
        }

    def test_httptokenauth_security_scheme_with_custom_scheme(self, app, client):
        auth = HTTPTokenAuth(scheme='Token')

        @app.get('/')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'TokenAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['TokenAuth'] == {
            'type': 'http',
            'scheme': 'token',
        }

    def test_httptokenauth_security_scheme_with_in_header(self, app, client):
        auth = HTTPTokenAuth(header='X-API-KEY')

        @app.get('/')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'ApiKeyAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['ApiKeyAuth'] == {
            'type': 'apiKey',
            'name': 'X-API-KEY',
            'in': 'header',
        }

    def test_httptokenauth_security_scheme_with_in_query(self, app, client):
        auth = HTTPTokenAuth(header='api_key', header_type=None)

        @app.get('/')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'ApiKeyAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['ApiKeyAuth'] == {
            'type': 'apiKey',
            'name': 'api_key',
            'in': 'query',
        }

    def test_httptokenauth_security_scheme_with_custom_description(self, app, client):
        auth = HTTPTokenAuth(description='custom description')

        @app.get('/')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'BearerAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['BearerAuth'] == {
            'type': 'http',
            'scheme': 'bearer',
            'description': 'custom description',
        }

    def test_multiple_auth_on_one_endpoint(self, app, client):
        auth1 = HTTPBasicAuth()
        auth2 = HTTPTokenAuth()

        @app.get('/')
        @app.auth_required(auth1)
        @app.auth_required(auth2)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'BasicAuth' in rv.json['components']['securitySchemes']
        assert 'BearerAuth' in rv.json['components']['securitySchemes']
        assert len(rv.json['paths']['/']['get']['security']) == 2
        assert {'BasicAuth': []} in rv.json['paths']['/']['get']['security']
        assert {'BearerAuth': []} in rv.json['paths']['/']['get']['security']


class TestOpenAPITags:
    """Tests for OpenAPI tags and tag organization."""

    def test_tags(self, app, client):
        assert app.tags is None
        app.tags = [
            {
                'name': 'foo',
                'description': 'some description for foo',
                'externalDocs': {
                    'description': 'Find more info about foo here',
                    'url': 'https://docs.example.com/',
                },
            },
            {'name': 'bar', 'description': 'some description for bar'},
        ]

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags']
        assert {'name': 'bar', 'description': 'some description for bar'} in rv.json['tags']
        assert rv.json['tags'][0]['name'] == 'foo'
        assert rv.json['tags'][0]['description'] == 'some description for foo'
        assert rv.json['tags'][0]['externalDocs']['description'] == 'Find more info about foo here'
        assert rv.json['tags'][0]['externalDocs']['url'] == 'https://docs.example.com/'
        assert rv.json['tags'][1]['name'] == 'bar'
        assert rv.json['tags'][1]['description'] == 'some description for bar'

    def test_auto_tags_for_blueprint(self, app, client):
        bp = APIBlueprint('foo', __name__)

        @bp.get('/')
        def foo():
            pass

        @bp.get('/bar')
        def bar():
            pass

        app.register_blueprint(bp)
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert {'name': 'foo'} in rv.json['tags']
        assert rv.json['paths']['/']['get']['tags'] == ['foo']
        assert rv.json['paths']['/bar']['get']['tags'] == ['foo']

    def test_auto_tags_for_blueprint_url_prefix(self, app, client):
        bp = APIBlueprint('foo', __name__, url_prefix='/test')

        @bp.get('/')
        def foo():
            pass

        app.register_blueprint(bp)
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert {'name': 'foo'} in rv.json['tags']
        assert rv.json['paths']['/test/']['get']['tags'] == ['foo']

    def test_empty_blueprint_no_auto_tag(self, app, client):
        bp = APIBlueprint('foo', __name__)

        # register an empty blueprint shouldn't add a tag
        app.register_blueprint(bp)
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags'] == []

    def test_manual_tag_for_blueprint(self, app, client):
        bp = APIBlueprint('foo', __name__)
        bp.tag = {'name': 'Custom', 'description': 'Some description for the custom tag.'}

        @bp.get('/')
        def foo():
            pass

        app.register_blueprint(bp)
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert {'name': 'Custom', 'description': 'Some description for the custom tag.'} in rv.json[
            'tags'
        ]
        assert rv.json['paths']['/']['get']['tags'] == ['Custom']

    def test_global_tag_for_endpoint_function(self, app, client):
        app.tags = [
            {
                'name': 'foo',
                'description': 'some description for foo',
            },
            {'name': 'bar', 'description': 'some description for bar'},
        ]

        @app.get('/')
        def foo():
            """test summary for api index"""
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags']
        assert {'name': 'foo', 'description': 'some description for foo'} in rv.json['tags']
        assert {'name': 'bar', 'description': 'some description for bar'} in rv.json['tags']
        assert rv.json['paths']['/']['get']['tags'] == ['foo']


class TestOpenAPIBlueprint:
    """Tests for OpenAPI blueprint integration."""

    def test_tag_on_blueprint(self, app, client):
        foo_bp = APIBlueprint('foo', __name__)
        foo_bp.tag = 'foo'

        @foo_bp.get('/')
        def foo():
            pass

        bar_bp = APIBlueprint('bar', __name__)
        bar_bp.tag = {'name': 'bar', 'description': 'some description for bar'}

        @bar_bp.get('/')
        def bar():
            pass

        app.register_blueprint(foo_bp, url_prefix='/foo')
        app.register_blueprint(bar_bp, url_prefix='/bar')
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert {'name': 'foo'} in rv.json['tags']
        assert {
            'name': 'bar',
            'description': 'some description for bar',
        } in rv.json['tags']
        assert rv.json['paths']['/foo/']['get']['tags'] == ['foo']
        assert rv.json['paths']['/bar/']['get']['tags'] == ['bar']

    def test_blueprint_tag_override_for_view_function(self, app, client):
        bp = APIBlueprint('foo', __name__)
        bp.tag = 'foo'

        @bp.get('/')
        @bp.doc(tags=['bar'])
        def bar():
            pass

        app.register_blueprint(bp)
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/']['get']['tags'] == ['bar']

    def test_pass_additional_spec_plugins(self, app, client):
        bp = APIBlueprint(
            'foo',
            __name__,
            abp_responses={'400': {'description': 'Bad request'}},
            abp_parameters={'foo': {'name': 'foo', 'in': 'query'}},
            abp_tags=['foo'],
        )

        @bp.get('/')
        def foo():
            pass

        app.register_blueprint(bp)
        app.spec_plugins

        spec = app.spec
        spec_dict = spec
        if hasattr(spec, 'to_dict'):  # if spec is an APISpec object
            spec_dict = spec.to_dict()

        assert 'foo' in spec_dict['components']['parameters']
        assert spec_dict['components']['parameters']['foo']['in'] == 'query'
        assert 'foo' in spec_dict['tags'][0]['name']


class TestOpenAPIHeaders:
    """Tests for OpenAPI headers handling."""

    def test_add_response_headers(self, app, client):
        @app.get('/')
        def hello():
            return {'message': 'Hello!'}, {'X-Foo': 'foo', 'X-Bar': 'bar'}

        rv = client.get('/')
        assert rv.status_code == 200
        assert rv.json == {'message': 'Hello!'}
        assert rv.headers.get('X-Foo') == 'foo'
        assert rv.headers.get('X-Bar') == 'bar'

    def test_output_with_headers_openapi_schema(self, app, client):
        @app.get('/foo')
        @app.output(Foo, headers={'X-Foo': 'some description'})
        def foo():
            return {'name': 'foo'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'x-foo' in rv.json['paths']['/foo']['get']['responses']['200']['headers']
        assert (
            rv.json['paths']['/foo']['get']['responses']['200']['headers']['x-foo']
            == {'description': 'some description', 'schema': {'type': 'string'}}
        )

    def test_api_response_header_case_insensitive(self, app, client):
        @app.get('/')
        @app.output(Foo, headers={'X-Foo': 'some description', 'x-bar': 'bar description'})
        def foo():
            return {'name': 'foo'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'x-foo' in rv.json['paths']['/']['get']['responses']['200']['headers']
        assert 'x-bar' in rv.json['paths']['/']['get']['responses']['200']['headers']

    def test_input_with_header_as_datakey(self, app, client):
        class Headers(Schema):
            token = String(data_key='Authorization')

        @app.post('/auth')
        @app.input(Headers, location='headers')
        def auth(headers_data):
            return headers_data

        rv = client.post('/auth', headers={'X-API-Key': 'secret'})
        assert rv.status_code == 422

        rv = client.post('/auth', headers={'Authorization': 'Bearer token123'})
        assert rv.status_code == 200
        assert rv.json == {'token': 'Bearer token123'}


class TestOpenAPIPaths:
    """Tests for OpenAPI paths and operations."""

    def test_path_summary_and_operation_summary(self, app, client):
        @app.get('/foo')
        def get_foo():
            """Get Foo"""
            pass

        @app.get('/bar')
        def bar():
            pass

        @app.get('/baz')
        @app.doc(summary='Baz summary')
        def baz():
            """Baz function summary"""
            pass

        @app.get('/egg')
        @app.doc(summary='Egg summary')
        def get_egg():
            """Get Egg"""
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        assert rv.json['paths']['/foo']['get']['summary'] == 'Get Foo'
        assert rv.json['paths']['/bar']['get']['summary'] == 'Bar'
        assert rv.json['paths']['/baz']['get']['summary'] == 'Baz summary'
        assert rv.json['paths']['/egg']['get']['summary'] == 'Egg summary'

    def test_path_description(self, app, client):
        @app.get('/foo')
        def foo():
            """Foo summary

            This is the description for the foo endpoint.
            It can be multiple lines.
            """
            pass

        @app.get('/bar')
        @app.doc(description='Bar description from doc decorator')
        def bar():
            """Bar summary

            Bar function description
            """
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        assert rv.json['paths']['/foo']['get']['summary'] == 'Foo summary'
        assert 'This is the description for the foo endpoint.' in rv.json['paths']['/foo']['get']['description']
        assert rv.json['paths']['/bar']['get']['summary'] == 'Bar summary'
        assert rv.json['paths']['/bar']['get']['description'] == 'Bar description from doc decorator'

    def test_path_parameters(self, app, client):
        @app.get('/users/<int:user_id>')
        def get_user(user_id):
            return {'id': user_id}

        @app.get('/users/<user_id>/posts/<int:post_id>')
        def get_post(user_id, post_id):
            return {'user_id': user_id, 'post_id': post_id}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        # Check user_id parameter in first endpoint
        user_params = rv.json['paths']['/users/{user_id}']['get']['parameters']
        assert len(user_params) == 1
        assert user_params[0]['name'] == 'user_id'
        assert user_params[0]['in'] == 'path'
        assert user_params[0]['required'] is True
        assert user_params[0]['schema']['type'] == 'integer'

        # Check parameters in second endpoint
        post_params = rv.json['paths']['/users/{user_id}/posts/{post_id}']['get']['parameters']
        assert len(post_params) == 2
        param_names = [p['name'] for p in post_params]
        assert 'user_id' in param_names
        assert 'post_id' in param_names

    def test_duplicate_operation_id_handling(self, app, client):
        @app.get('/users')
        def get_users():
            pass

        @app.post('/users')
        def create_user():
            pass

        @app.get('/users/<int:user_id>')
        def get_user(user_id):
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        # Operation IDs should be unique
        operation_ids = []
        for path_item in rv.json['paths'].values():
            for operation in path_item.values():
                if 'operationId' in operation:
                    operation_ids.append(operation['operationId'])

        assert len(operation_ids) == len(set(operation_ids))  # All unique

    def test_method_view_paths(self, app, client):
        from flask.views import MethodView

        @app.route('/items')
        class ItemAPI(MethodView):
            def get(self):
                """Get all items"""
                pass

            def post(self):
                """Create a new item"""
                pass

        @app.route('/items/<int:item_id>')
        class ItemDetailAPI(MethodView):
            def get(self, item_id):
                """Get a specific item"""
                pass

            def put(self, item_id):
                """Update an item"""
                pass

            def delete(self, item_id):
                """Delete an item"""
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        # Check that all methods are present
        assert 'get' in rv.json['paths']['/items']
        assert 'post' in rv.json['paths']['/items']
        assert 'get' in rv.json['paths']['/items/{item_id}']
        assert 'put' in rv.json['paths']['/items/{item_id}']
        assert 'delete' in rv.json['paths']['/items/{item_id}']

        # Check summaries
        assert rv.json['paths']['/items']['get']['summary'] == 'Get all items'
        assert rv.json['paths']['/items']['post']['summary'] == 'Create a new item'

    def test_route_with_multiple_methods(self, app, client):
        @app.route('/multi', methods=['GET', 'POST'])
        def multi_method():
            """Handle multiple methods"""
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        assert 'get' in rv.json['paths']['/multi']
        assert 'post' in rv.json['paths']['/multi']
        assert rv.json['paths']['/multi']['get']['summary'] == 'Handle multiple methods'
        assert rv.json['paths']['/multi']['post']['summary'] == 'Handle multiple methods'


class TestOpenAPIExtensions:
    """Tests for OpenAPI extensions support."""

    def test_spec_extension(self, app, client):
        app.spec_extension = {'x-custom': 'value'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['x-custom'] == 'value'

    def test_info_extension(self, app, client):
        app.info['x-logo'] = {'url': 'https://example.com/logo.png'}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['info']['x-logo']['url'] == 'https://example.com/logo.png'
