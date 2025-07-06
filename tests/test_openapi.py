import json
import pytest
import os
from unittest.mock import patch
from contextlib import contextmanager
import importlib

import openapi_spec_validator as osv
from flask import request

from .schemas import Bar, Baz, Foo, Header, Pagination, Query, ResponseHeader
from apiflask import APIFlask, APIBlueprint, Schema, HTTPBasicAuth, HTTPTokenAuth
from apiflask.commands import spec_command
from apiflask.fields import Boolean, Integer, Integer, List, Number, String
from apiflask.schemas import Schema


class TestOpenAPIBasic:

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

class TestOpenAPIBlueprint:

    def test_openapi_blueprint(self, app):
        assert 'openapi' in app.blueprints
        rules = list(app.url_map.iter_rules())
        bp_endpoints = [rule.endpoint for rule in rules if rule.endpoint.startswith('openapi')]
        assert len(bp_endpoints) == 3
        assert 'openapi.spec' in bp_endpoints
        assert 'openapi.docs' in bp_endpoints
        assert 'openapi.swagger_ui_oauth_redirect' in bp_endpoints

        app = APIFlask(__name__, spec_path=None, docs_path=None)
        assert 'openapi' not in app.blueprints


    def test_spec_path(self, app):
        assert app.spec_path

        app = APIFlask(__name__, spec_path=None)
        assert app.spec_path is None
        assert 'openapi' in app.blueprints
        rules = list(app.url_map.iter_rules())
        bp_endpoints = [rule.endpoint for rule in rules if rule.endpoint.startswith('openapi')]
        assert len(bp_endpoints) == 2
        assert 'openapi.spec' not in bp_endpoints


    @pytest.mark.parametrize('spec_path', ['/spec.yaml', '/spec.yml'])
    def test_yaml_spec(self, spec_path):
        app = APIFlask(__name__, spec_path=spec_path)
        app.config['SPEC_FORMAT'] = 'yaml'
        client = app.test_client()

        rv = client.get(spec_path)
        assert rv.status_code == 200
        assert rv.headers['Content-Type'] == 'text/vnd.yaml'
        assert b'title: APIFlask' in rv.data


    def test_docs_path(self, app):
        assert app.docs_path

        app = APIFlask(__name__, docs_path=None)
        assert app.docs_path is None

        rules = list(app.url_map.iter_rules())
        bp_endpoints = [rule.endpoint for rule in rules if rule.endpoint.startswith('openapi')]
        assert len(bp_endpoints) == 1
        assert 'openapi.docs' not in bp_endpoints
        assert 'openapi.swagger_ui_oauth_redirect' not in bp_endpoints


    def test_docs_oauth2_redirect_path(self, client):
        rv = client.get('/docs/oauth2-redirect')
        assert rv.status_code == 200
        assert b'<title>Swagger UI: OAuth2 Redirect</title>' in rv.data
        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'oauth2RedirectUrl: "/docs/oauth2-redirect"' in rv.data

        app = APIFlask(__name__, docs_oauth2_redirect_path='/docs/oauth2/redirect')
        rv = app.test_client().get('/docs/oauth2/redirect')
        assert rv.status_code == 200
        assert b'<title>Swagger UI: OAuth2 Redirect</title>' in rv.data
        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'oauth2RedirectUrl: "/docs/oauth2/redirect"' in rv.data

        # Test the feature of external oauth2 redirect path
        app = APIFlask(
            __name__,
            docs_oauth2_redirect_path='/docs/oauth2/redirect/external',
            docs_oauth2_redirect_path_external=True,
        )
        rv = app.test_client().get('/docs/oauth2/redirect/external')
        assert rv.status_code == 200
        assert b'<title>Swagger UI: OAuth2 Redirect</title>' in rv.data
        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'oauth2RedirectUrl: "http://localhost/docs/oauth2/redirect/external"' in rv.data

        app = APIFlask(__name__, docs_oauth2_redirect_path=None)
        assert app.docs_oauth2_redirect_path is None

        rules = list(app.url_map.iter_rules())
        bp_endpoints = [rule.endpoint for rule in rules if rule.endpoint.startswith('openapi')]
        assert len(bp_endpoints) == 2
        assert 'openapi.docs' in bp_endpoints
        assert 'openapi.swagger_ui_oauth_redirect' not in bp_endpoints
        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'oauth2RedirectUrl' not in rv.data


    def test_disable_openapi_with_enable_openapi_arg(self, app):
        assert app.enable_openapi

        app = APIFlask(__name__, enable_openapi=False)
        assert app.enable_openapi is False

        rules = list(app.url_map.iter_rules())
        bp_endpoints = [rule.endpoint for rule in rules if rule.endpoint.startswith('openapi')]
        assert len(bp_endpoints) == 0


    def test_swagger_ui(self, client):
        # default APIFlask(docs_ui) value is swagger-ui
        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'Swagger UI' in rv.data

        app = APIFlask(__name__, docs_ui='swagger-ui')
        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'Swagger UI' in rv.data


    @pytest.mark.parametrize(
        'ui_name',
        [
            ('swagger-ui', b'Swagger UI'),
            ('redoc', b'Redoc'),
            ('elements', b'Elements'),
            ('rapidoc', b'RapiDoc'),
            ('rapipdf', b'RapiPDF'),
        ],
    )
    def test_other_ui(self, ui_name):
        app = APIFlask(__name__, docs_ui=ui_name[0])
        client = app.test_client()

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert ui_name[1] in rv.data


    def test_openapi_blueprint_url_prefix(self, app):
        assert app.openapi_blueprint_url_prefix is None

        prefix = '/api'
        app = APIFlask(__name__, openapi_blueprint_url_prefix=prefix)
        assert app.openapi_blueprint_url_prefix == prefix

        client = app.test_client()
        rv = client.get('/docs')
        assert rv.status_code == 404
        rv = client.get(f'{prefix}/docs')
        assert rv.status_code == 200

class TestOpenAPIExtensions:

    def test_specification_extensions(self, app, client):
        @app.get('/')
        @app.doc(extensions={'x-foo': {'foo': 'bar'}})
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/']['get']['x-foo'] == {'foo': 'bar'}

class TestOpenAPIHeaders:
    def test_spec_with_dict_headers(self, app, client):
        @app.route('/foo')
        @app.output(
            Foo,
            headers={
                'X-boolean': Boolean(metadata={'description': 'A boolean header'}),
                'X-integer': Integer(metadata={'description': 'An integer header'}),
                'X-number': Number(metadata={'description': 'A number header'}),
                'X-string': String(metadata={'description': 'A string header'}),
                'X-array': List(String(), metadata={'description': 'An array header'}),
            },
        )
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.json['paths']['/foo']['get']['responses']['200']['headers'] == {
            'X-boolean': {
                'description': 'A boolean header',
                'required': False,
                'schema': {'type': 'boolean'},
            },
            'X-integer': {
                'description': 'An integer header',
                'required': False,
                'schema': {'type': 'integer'},
            },
            'X-number': {
                'description': 'A number header',
                'required': False,
                'schema': {'type': 'number'},
            },
            'X-string': {
                'description': 'A string header',
                'required': False,
                'schema': {'type': 'string'},
            },
            'X-array': {
                'description': 'An array header',
                'required': False,
                'schema': {'items': {'type': 'string'}, 'type': 'array'},
                'style': 'form',
                'explode': True,
            },
        }


    def test_spec_with_empty_headers(self, app, client):
        @app.route('/foo')
        @app.output(Foo, headers={})
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.json['paths']['/foo']['get']['responses']['200']['headers'] == {}


    def test_spec_with_schema_headers(self, app, client):
        @app.route('/foo')
        @app.output(Foo, headers=ResponseHeader)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.json['paths']['/foo']['get']['responses']['200']['headers'] == {
            'X-Token': {
                'description': 'A custom token header',
                'required': True,
                'schema': {'type': 'string'},
            },
        }


    @pytest.mark.parametrize('openapi_version', ['3.0.0', '3.1.0'])
    def test_spec_validity_with_headers(self, app, client, openapi_version):
        app.config['OPENAPI_VERSION'] = openapi_version

        @app.route('/foo')
        @app.output(Foo, headers=ResponseHeader)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

class TestOpenAPIInfo:

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
        assert rv.json['info']['description'] == app.description
        assert rv.json['info']['termsOfService'] == app.terms_of_service
        assert rv.json['info']['contact'] == app.contact
        assert rv.json['info']['license'] == app.license


    def test_info_attribute(self, app, client):
        assert app.info is None

        app.info = {
            'description': 'My API',
            'termsOfService': 'http://example.com',
            'contact': {
                'name': 'API Support',
                'url': 'http://www.example.com/support',
                'email': 'support@example.com',
            },
            'license': {'name': 'Apache 2.0', 'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'},
        }

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['info']['description'] == app.info['description']
        assert rv.json['info']['termsOfService'] == app.info['termsOfService']
        assert rv.json['info']['contact'] == app.info['contact']
        assert rv.json['info']['license'] == app.info['license']


    def test_overwirte_info_attribute(self, app, client):
        assert app.info is None
        assert app.description is None
        assert app.terms_of_service is None
        assert app.contact is None
        assert app.license is None

        app.info = {
            'description': 'Not set',
            'termsOfService': 'Not set',
            'contact': {'name': 'Not set', 'url': 'Not set', 'email': 'Not set'},
            'license': {'name': 'Not set', 'url': 'Not set'},
        }

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
        assert rv.json['info']['description'] == app.description
        assert rv.json['info']['termsOfService'] == app.terms_of_service
        assert rv.json['info']['contact'] == app.contact
        assert rv.json['info']['license'] == app.license

class TestOpenAPIPaths:
    def test_spec_path_summary_description_from_docs(self, app, client):
        @app.route('/users')
        @app.output(Foo)
        def get_users():
            """Get Users"""
            pass

        @app.route('/users/<id>', methods=['PUT'])
        @app.output(Foo)
        def update_user(id):
            """Update User

            Update a user with specified ID.
            """
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/users']['get']['summary'] == 'Get Users'
        assert rv.json['paths']['/users/{id}']['put']['summary'] == 'Update User'
        assert (
            rv.json['paths']['/users/{id}']['put']['description'] == 'Update a user with specified ID.'
        )


    def test_spec_path_parameters_registration(self, app, client):
        @app.route('/strings/<some_string>')
        @app.output(Foo)
        def get_string(some_string):
            pass

        @app.route('/floats/<float:some_float>', methods=['POST'])
        @app.output(Foo)
        def get_float(some_float):
            pass

        @app.route('/integers/<int:some_integer>', methods=['PUT'])
        @app.output(Foo)
        def get_integer(some_integer):
            pass

        @app.route('/users/<int:user_id>/articles/<int:article_id>')
        @app.output(Foo)
        def get_article(user_id, article_id):
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/strings/{some_string}']['get']['parameters'][0]['in'] == 'path'
        assert (
            rv.json['paths']['/strings/{some_string}']['get']['parameters'][0]['name'] == 'some_string'
        )
        assert (
            rv.json['paths']['/strings/{some_string}']['get']['parameters'][0]['schema']['type']
            == 'string'
        )
        assert (
            rv.json['paths']['/floats/{some_float}']['post']['parameters'][0]['schema']['type']
            == 'number'
        )
        assert (
            rv.json['paths']['/integers/{some_integer}']['put']['parameters'][0]['schema']['type']
            == 'integer'
        )
        assert (
            rv.json['paths']['/users/{user_id}/articles/{article_id}']['get']['parameters'][0]['name']
            == 'user_id'
        )
        assert (
            rv.json['paths']['/users/{user_id}/articles/{article_id}']['get']['parameters'][1]['name']
            == 'article_id'
        )


    def test_spec_path_summary_auto_generation(self, app, client):
        @app.route('/users')
        @app.output(Foo)
        def get_users():
            pass

        @app.route('/users/<id>', methods=['PUT'])
        @app.output(Foo)
        def update_user(id):
            pass

        @app.route('/users/<id>', methods=['DELETE'])
        @app.output(Foo)
        def delete_user(id):
            """Summary from Docs

            Delete a user with specified ID.
            """
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/users']['get']['summary'] == 'Get Users'
        assert rv.json['paths']['/users/{id}']['put']['summary'] == 'Update User'
        assert rv.json['paths']['/users/{id}']['delete']['summary'] == 'Summary from Docs'
        assert (
            rv.json['paths']['/users/{id}']['delete']['description']
            == 'Delete a user with specified ID.'
        )


    def test_path_arguments_detection(self, app, client):
        @app.route('/foo/<bar>')
        @app.output(Foo)
        def pattern1(bar):
            pass

        @app.route('/<foo>/bar')
        @app.output(Foo)
        def pattern2(foo):
            pass

        @app.route('/<int:foo>/<bar>/baz')
        @app.output(Foo)
        def pattern3(foo, bar):
            pass

        @app.route('/foo/<int:bar>/<int:baz>')
        @app.output(Foo)
        def pattern4(bar, baz):
            pass

        @app.route('/<int:foo>/<bar>/<float:baz>')
        @app.output(Foo)
        def pattern5(foo, bar, baz):
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '/foo/{bar}' in rv.json['paths']
        assert '/{foo}/bar' in rv.json['paths']
        assert '/{foo}/{bar}/baz' in rv.json['paths']
        assert '/foo/{bar}/{baz}' in rv.json['paths']
        assert '/{foo}/{bar}/{baz}' in rv.json['paths']
        assert (
            rv.json['paths']['/{foo}/{bar}/{baz}']['get']['parameters'][0]['schema']['type']
            == 'integer'
        )
        assert (
            rv.json['paths']['/{foo}/{bar}/{baz}']['get']['parameters'][1]['schema']['type'] == 'string'
        )
        assert (
            rv.json['paths']['/{foo}/{bar}/{baz}']['get']['parameters'][2]['schema']['type'] == 'number'
        )


    def test_path_arguments_order(self, app, client):
        @app.route('/<foo>/bar')
        @app.input(Query, location='query')
        @app.output(Foo)
        def path_and_query(foo, query_data):
            pass

        @app.route('/<foo>/<bar>')
        @app.output(Foo)
        def two_path_variables(foo, bar):
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '/{foo}/bar' in rv.json['paths']
        assert '/{foo}/{bar}' in rv.json['paths']
        assert rv.json['paths']['/{foo}/bar']['get']['parameters'][0]['name'] == 'foo'
        assert rv.json['paths']['/{foo}/bar']['get']['parameters'][1]['name'] == 'id'
        assert rv.json['paths']['/{foo}/{bar}']['get']['parameters'][0]['name'] == 'foo'
        assert rv.json['paths']['/{foo}/{bar}']['get']['parameters'][1]['name'] == 'bar'


    def test_parameters_registration(self, app, client):
        @app.route('/foo')
        @app.input(Query, location='query')
        @app.output(Foo)
        def foo(query_data):
            pass

        @app.route('/bar')
        @app.input(Query, location='query', arg_name='query')
        @app.input(Pagination, location='query', arg_name='pagination')
        @app.input(Header, location='headers')
        def bar(query, pagination, headers_data):
            return {'query': query['id'], 'pagination': pagination, 'foo': headers_data['foo']}

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '/foo' in rv.json['paths']
        assert '/bar' in rv.json['paths']
        assert rv.json['paths']['/foo']['get']['parameters'][0]['name'] == 'id'
        assert len(rv.json['paths']['/foo']['get']['parameters']) == 1
        assert len(rv.json['paths']['/bar']['get']['parameters']) == 4
        rv = client.get('/bar')
        assert rv.status_code == 200
        assert rv.json['query'] == 1
        assert rv.json['pagination']['page'] == 1
        assert rv.json['pagination']['per_page'] == 10
        assert rv.json['foo'] == 'bar'


    def test_register_validation_error_response(self, app, client):
        error_code = str(app.config['VALIDATION_ERROR_STATUS_CODE'])

        @app.post('/foo')
        @app.input(Foo)
        def foo():
            pass

        @app.get('/bar')
        @app.input(Foo, location='query')
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['post']['responses'][error_code] is not None
        assert (
            rv.json['paths']['/foo']['post']['responses'][error_code]['description']
            == 'Validation error'
        )
        assert rv.json['paths']['/bar']['get']['responses'][error_code] is not None
        assert (
            rv.json['paths']['/bar']['get']['responses'][error_code]['description']
            == 'Validation error'
        )


    def test_auto_404_error(self, app, client):
        @app.get('/foo')
        def foo():
            pass

        @app.get('/bar/<int:id>')
        def bar():
            pass

        @app.get('/baz/<int:id>')
        @app.doc(responses={404: 'Pet not found'})
        def baz():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '404' not in rv.json['paths']['/foo']['get']['responses']
        assert '404' in rv.json['paths']['/bar/{id}']['get']['responses']
        assert rv.json['paths']['/bar/{id}']['get']['responses']['404']['description'] == 'Not found'
        assert (
            rv.json['paths']['/baz/{id}']['get']['responses']['404']['description'] == 'Pet not found'
        )

class TestOpenAPISecurity:
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
            'scheme': 'bearer',
            'type': 'http',
        }


    def test_apikey_auth_security_scheme(self, app, client):
        auth = HTTPTokenAuth('apiKey', header='X-API-Key')

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
            'name': 'X-API-Key',
            'in': 'header',
        }


    def test_custom_security_scheme_name(self, app, client):
        basic_auth = HTTPBasicAuth(security_scheme_name='basic_auth')
        token_auth = HTTPTokenAuth(header='X-API-Key', security_scheme_name='myToken')

        @app.get('/foo')
        @app.auth_required(basic_auth)
        def foo():
            pass

        @app.get('/bar')
        @app.auth_required(token_auth)
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'basic_auth' in rv.json['components']['securitySchemes']
        assert 'myToken' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['basic_auth'] == {
            'type': 'http',
            'scheme': 'basic',
        }
        assert rv.json['components']['securitySchemes']['myToken'] == {
            'type': 'apiKey',
            'name': 'X-API-Key',
            'in': 'header',
        }
        print(rv.json)
        assert 'basic_auth' in rv.json['paths']['/foo']['get']['security'][0]
        assert 'myToken' in rv.json['paths']['/bar']['get']['security'][0]


    def test_unknown_auth_security_scheme(self, app):
        from flask_httpauth import HTTPDigestAuth

        auth = HTTPDigestAuth()

        @app.get('/')
        @app.auth_required(auth)
        def foo():
            pass

        with pytest.raises(TypeError):
            app.spec


    def test_multiple_auth_names(self, app, client):
        auth1 = HTTPBasicAuth()
        auth2 = HTTPBasicAuth()
        auth3 = HTTPBasicAuth()

        @app.get('/foo')
        @app.auth_required(auth1)
        def foo():
            pass

        @app.get('/bar')
        @app.auth_required(auth2)
        def bar():
            pass

        @app.get('/baz')
        @app.auth_required(auth3)
        def baz():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'BasicAuth' in rv.json['components']['securitySchemes']
        assert 'BasicAuth_2' in rv.json['components']['securitySchemes']
        assert 'BasicAuth_3' in rv.json['components']['securitySchemes']


    def test_security_schemes_description(self, app, client):
        basic_auth = HTTPBasicAuth(description='some description for basic auth')
        token_auth = HTTPTokenAuth(description='some description for bearer auth')

        @app.get('/foo')
        @app.auth_required(basic_auth)
        def foo():
            pass

        @app.get('/bar')
        @app.auth_required(token_auth)
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'BasicAuth' in rv.json['components']['securitySchemes']
        assert 'BearerAuth' in rv.json['components']['securitySchemes']
        assert rv.json['components']['securitySchemes']['BasicAuth'] == {
            'type': 'http',
            'scheme': 'basic',
            'description': 'some description for basic auth',
        }
        assert rv.json['components']['securitySchemes']['BearerAuth'] == {
            'type': 'http',
            'scheme': 'bearer',
            'description': 'some description for bearer auth',
        }

class TestOpenAPITags:

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


    def test_simple_tags(self, app, client):
        assert app.tags is None
        app.tags = ['foo', 'bar', 'baz']

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags']
        assert {'name': 'foo'} in rv.json['tags']
        assert {'name': 'bar'} in rv.json['tags']
        assert {'name': 'baz'} in rv.json['tags']


    def test_simple_tag_from_blueprint(self, app, client):
        bp = APIBlueprint('test', __name__, tag='foo')
        app.register_blueprint(bp)

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags']
        assert {'name': 'foo'} in rv.json['tags']


    def test_tag_from_blueprint(self, app, client):
        tag = {
            'name': 'foo',
            'description': 'some description for foo',
            'externalDocs': {
                'description': 'Find more info about foo here',
                'url': 'https://docs.example.com/',
            },
        }
        bp = APIBlueprint('test', __name__, tag=tag)
        app.register_blueprint(bp)

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags']
        assert rv.json['tags'][0]['name'] == 'foo'
        assert rv.json['tags'][0]['description'] == 'some description for foo'
        assert rv.json['tags'][0]['externalDocs']['description'] == 'Find more info about foo here'
        assert rv.json['tags'][0]['externalDocs']['url'] == 'https://docs.example.com/'


    def test_auto_tag_from_blueprint(self, app, client):
        bp = APIBlueprint('foo', __name__)
        app.register_blueprint(bp)

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags']
        assert {'name': 'Foo'} in rv.json['tags']


    @pytest.mark.skipif(
        importlib.metadata.version('flask') < '2.0.1',
        reason='Depends on new behaviour introduced in Flask 2.0.1',
    )
    def test_auto_tag_from_nesting_blueprints(self, app, client):
        parent_bp = APIBlueprint('parent', __name__)
        child_bp = APIBlueprint('child', __name__)
        parent_bp.register_blueprint(child_bp)
        app.register_blueprint(parent_bp)

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags']
        assert {'name': 'Parent'} in rv.json['tags']
        assert {'name': 'Parent.Child'} in rv.json['tags']


    def test_path_tags(self, app, client):
        bp = APIBlueprint('foo', __name__)

        @bp.get('/')
        def foo():
            pass

        app.register_blueprint(bp)

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/']['get']['tags'] == ['Foo']


    @pytest.mark.parametrize('tag', ['test', {'name': 'test'}])
    def test_path_tags_with_blueprint_tag(self, app, client, tag):
        bp = APIBlueprint('foo', __name__, tag=tag)

        @bp.get('/')
        def foo():
            pass

        app.register_blueprint(bp)

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/']['get']['tags'] == ['test']


    @pytest.mark.skipif(
        importlib.metadata.version('flask') < '2.0.1',
        reason='Depends on new behaviour introduced in Flask 2.0.1',
    )
    def test_path_tags_with_nesting_blueprints(self, app, client):
        parent_bp = APIBlueprint('parent', __name__, url_prefix='/parent')
        child_bp = APIBlueprint('child', __name__, url_prefix='/child')

        @parent_bp.get('/')
        def foo():
            pass

        @child_bp.get('/')
        def bar():
            pass

        parent_bp.register_blueprint(child_bp)
        app.register_blueprint(parent_bp)

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/parent/']['get']['tags'] == ['Parent']
        assert rv.json['paths']['/parent/child/']['get']['tags'] == ['Parent.Child']

