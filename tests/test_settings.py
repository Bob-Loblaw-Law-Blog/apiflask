"""
Consolidated tests for APIFlask settings and configuration.

This module contains all tests for APIFlask configuration settings including:
- Auto behavior settings (tags, servers, operation summaries, etc.)
- API documentation settings (Swagger UI, ReDoc, etc.)
- OpenAPI spec customization settings
- Response customization settings
- OpenAPI field configuration
"""

import openapi_spec_validator as osv
import pytest
from flask.views import MethodView

from .schemas import Foo, HTTPError, Query, ValidationError
from apiflask import APIBlueprint, APIFlask
from apiflask.schemas import EmptySchema, http_error_schema
from apiflask.security import HTTPBasicAuth


class TestAutoBehaviorSettings:
    """Tests for automatic behavior configuration settings."""

    def test_auto_tags(self, app, client):
        bp = APIBlueprint('foo', __name__)
        app.config['AUTO_TAGS'] = False

        @bp.get('/')
        def foo():
            pass

        app.register_blueprint(bp)
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags'] == []
        assert 'tags' not in rv.json['paths']['/']['get']

    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_servers(self, app, client, config_value):
        app.config['AUTO_SERVERS'] = config_value
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert bool('servers' in rv.json) == config_value

    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_path_summary(self, app, client, config_value):
        app.config['AUTO_OPERATION_SUMMARY'] = config_value

        @app.get('/foo')
        def foo():
            pass

        @app.get('/bar')
        def get_bar():
            pass

        @app.get('/baz')
        def get_baz():
            """Baz Summary"""
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        if config_value:
            assert rv.json['paths']['/foo']['get']['summary'] == 'Foo'
            assert rv.json['paths']['/bar']['get']['summary'] == 'Get Bar'
            assert rv.json['paths']['/baz']['get']['summary'] == 'Baz Summary'
        else:
            assert 'summary' not in rv.json['paths']['/foo']['get']
            assert 'summary' not in rv.json['paths']['/bar']['get']
            assert rv.json['paths']['/baz']['get']['summary'] == 'Baz Summary'

    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_path_description(self, app, client, config_value):
        app.config['AUTO_OPERATION_DESCRIPTION'] = config_value

        @app.get('/foo')
        def foo():
            """Foo function with docstring

            This is the description part.
            Multiple lines here.
            """
            pass

        @app.get('/bar')
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        if config_value:
            assert 'This is the description part.' in rv.json['paths']['/foo']['get']['description']
            assert 'description' not in rv.json['paths']['/bar']['get']
        else:
            assert 'description' not in rv.json['paths']['/foo']['get']

    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_validation_error_response(self, app, client, config_value):
        app.config['AUTO_VALIDATION_ERROR_RESPONSE'] = config_value

        @app.post('/foo')
        @app.input(Foo)
        def foo(json_data):
            return json_data

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        if config_value:
            assert '422' in rv.json['paths']['/foo']['post']['responses']
            assert (
                rv.json['paths']['/foo']['post']['responses']['422']['description']
                == 'Validation Error'
            )
        else:
            assert '422' not in rv.json['paths']['/foo']['post']['responses']

    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_auth_error_response(self, app, client, config_value):
        app.config['AUTO_AUTH_ERROR_RESPONSE'] = config_value
        auth = HTTPBasicAuth()

        @app.get('/foo')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        if config_value:
            assert '401' in rv.json['paths']['/foo']['get']['responses']
            assert '403' in rv.json['paths']['/foo']['get']['responses']
        else:
            assert '401' not in rv.json['paths']['/foo']['get']['responses']
            assert '403' not in rv.json['paths']['/foo']['get']['responses']

    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_abort_error_response(self, app, client, config_value):
        app.config['AUTO_404_RESPONSE'] = config_value

        @app.get('/users/<int:user_id>')
        def get_user(user_id):
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        if config_value:
            assert '404' in rv.json['paths']['/users/{user_id}']['get']['responses']
        else:
            assert '404' not in rv.json['paths']['/users/{user_id}']['get']['responses']

    def test_auto_tags_with_methodview(self, app, client):
        bp = APIBlueprint('foo', __name__)
        app.config['AUTO_TAGS'] = True

        @bp.route('/bar')
        class Bar(MethodView):
            def get(self):
                pass

            def post(self):
                pass

        app.register_blueprint(bp)
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert {'name': 'foo'} in rv.json['tags']
        assert rv.json['paths']['/bar']['get']['tags'] == ['foo']
        assert rv.json['paths']['/bar']['post']['tags'] == ['foo']

    def test_operation_id_config(self, app, client):
        app.config['AUTO_OPERATION_ID'] = True

        @app.get('/users')
        def get_users():
            pass

        @app.post('/users')
        def create_user():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/users']['get']['operationId'] == 'get_users'
        assert rv.json['paths']['/users']['post']['operationId'] == 'create_user'


class TestAPIDocsSettings:
    """Tests for API documentation UI settings."""

    def test_docs_favicon(self, app, client):
        app.config['DOCS_FAVICON'] = '/my-favicon.png'

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'href="/my-favicon.png"' in rv.data

    @pytest.mark.parametrize('config_value', [True, False])
    def test_docs_use_google_font(self, client, config_value):
        app = APIFlask(__name__, docs_ui='redoc')
        app.config['REDOC_USE_GOOGLE_FONT'] = config_value
        client = app.test_client()

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert bool(b'fonts.googleapis.com' in rv.data) is config_value

    def test_redoc_standalone_js(self, client):
        app = APIFlask(__name__, docs_ui='redoc')
        app.config['REDOC_STANDALONE_JS'] = 'https://cdn.example.com/redoc.js'
        client = app.test_client()

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'https://cdn.example.com/redoc.js' in rv.data

    def test_swagger_ui_config(self, app, client):
        app.config['SWAGGER_UI_CONFIG'] = {
            'deepLinking': True,
            'displayRequestDuration': True,
        }

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'"deepLinking": true' in rv.data
        assert b'"displayRequestDuration": true' in rv.data

    def test_swagger_ui_oauth_config(self, app, client):
        app.config['SWAGGER_UI_OAUTH_CONFIG'] = {
            'clientId': 'your-client-id',
            'realm': 'your-realm',
            'appName': 'your-app-name',
        }

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'"clientId": "your-client-id"' in rv.data
        assert b'"realm": "your-realm"' in rv.data
        assert b'"appName": "your-app-name"' in rv.data

    def test_redoc_config(self):
        app = APIFlask(__name__, docs_ui='redoc')
        app.config['REDOC_CONFIG'] = {
            'hideDownloadButton': True,
            'disableSearch': True,
        }
        client = app.test_client()

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'"hideDownloadButton": true' in rv.data
        assert b'"disableSearch": true' in rv.data

    def test_swagger_ui_bundle_js(self, app, client):
        app.config['SWAGGER_UI_BUNDLE_JS'] = 'https://cdn.example.com/swagger-ui-bundle.js'

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'https://cdn.example.com/swagger-ui-bundle.js' in rv.data

    def test_swagger_ui_standalone_preset_js(self, app, client):
        app.config['SWAGGER_UI_STANDALONE_PRESET_JS'] = 'https://cdn.example.com/swagger-ui-standalone-preset.js'

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'https://cdn.example.com/swagger-ui-standalone-preset.js' in rv.data

    def test_swagger_ui_css(self, app, client):
        app.config['SWAGGER_UI_CSS'] = 'https://cdn.example.com/swagger-ui.css'

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'https://cdn.example.com/swagger-ui.css' in rv.data

    def test_docs_path_config(self):
        app = APIFlask(__name__)
        app.config['DOCS_PATH'] = '/documentation'

        rv = app.test_client().get('/documentation')
        assert rv.status_code == 200

    def test_spec_path_config(self, app):
        app.config['SPEC_PATH'] = '/my-spec'

        rv = app.test_client().get('/my-spec')
        assert rv.status_code == 200
        assert rv.content_type.startswith('application/json')

    def test_disable_docs(self):
        app = APIFlask(__name__)
        app.config['DOCS_PATH'] = None

        rv = app.test_client().get('/docs')
        assert rv.status_code == 404

    def test_disable_spec_endpoint(self, app):
        app.config['SPEC_PATH'] = None

        rv = app.test_client().get('/openapi.json')
        assert rv.status_code == 404


class TestOpenAPISpecSettings:
    """Tests for OpenAPI specification configuration."""

    def test_spec_format_config(self, app, client):
        app.config['SPEC_FORMAT'] = 'yaml'

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        assert rv.content_type.startswith('text/plain')
        assert 'openapi:' in rv.get_data(as_text=True)

    def test_json_spec_format_config(self, app, client):
        app.config['SPEC_FORMAT'] = 'json'

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        assert rv.content_type.startswith('application/json')

    @pytest.mark.parametrize('config_value', [True, False])
    def test_spec_processor_pass_object_config(self, app, client, config_value):
        app.config['SPEC_PROCESSOR_PASS_OBJECT'] = config_value

        @app.spec_processor
        def process_spec(spec):
            if config_value:
                # spec should be an APISpec object
                spec.title = 'Modified Title'
            else:
                # spec should be a dict
                spec['info']['title'] = 'Modified Title'
            return spec

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['info']['title'] == 'Modified Title'


class TestResponseCustomizationSettings:
    """Tests for response customization configuration."""

    def test_response_description_config(self, app, client):
        app.config['SUCCESS_DESCRIPTION'] = 'Success'
        app.config['NOT_FOUND_DESCRIPTION'] = 'Egg not found'

        @app.get('/foo')
        @app.input(Foo)  # 200
        def only_body_schema(foo):
            pass

        @app.get('/bar')
        @app.output(Foo, status_code=201)
        def create():
            pass

        @app.get('/baz')
        @app.output(EmptySchema)
        def no_schema():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['responses']['200']['description'] == 'Success'
        assert rv.json['paths']['/bar']['get']['responses']['201']['description'] == 'Success'
        assert rv.json['paths']['/baz']['get']['responses']['200']['description'] == 'Success'

    def test_custom_error_schema(self, app, client):
        app.config['VALIDATION_ERROR_SCHEMA'] = ValidationError
        app.config['HTTP_ERROR_SCHEMA'] = HTTPError

        @app.post('/foo')
        @app.input(Foo)
        def foo(json_data):
            pass

        @app.get('/bar')
        @app.auth_required(HTTPBasicAuth())
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        # Check validation error schema
        validation_error_ref = rv.json['paths']['/foo']['post']['responses']['422']['content'][
            'application/json'
        ]['schema']['$ref']
        assert validation_error_ref == '#/components/schemas/ValidationError'

        # Check HTTP error schema
        http_error_ref = rv.json['paths']['/bar']['get']['responses']['401']['content'][
            'application/json'
        ]['schema']['$ref']
        assert http_error_ref == '#/components/schemas/HTTPError'

    def test_custom_error_status_codes(self, app, client):
        app.config['VALIDATION_ERROR_STATUS_CODE'] = 400
        app.config['AUTH_ERROR_STATUS_CODE'] = 403

        @app.post('/foo')
        @app.input(Foo)
        def foo(json_data):
            pass

        @app.get('/bar')
        @app.auth_required(HTTPBasicAuth())
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        assert '400' in rv.json['paths']['/foo']['post']['responses']
        assert '422' not in rv.json['paths']['/foo']['post']['responses']
        assert '403' in rv.json['paths']['/bar']['get']['responses']
        assert '401' not in rv.json['paths']['/bar']['get']['responses']

    def test_response_description_customization(self, app, client):
        app.config['VALIDATION_ERROR_DESCRIPTION'] = 'Request validation failed'
        app.config['AUTH_ERROR_DESCRIPTION'] = 'Authentication required'
        app.config['HTTP_ERROR_DESCRIPTION'] = 'Server error occurred'

        @app.post('/foo')
        @app.input(Foo)
        def foo(json_data):
            pass

        @app.get('/bar')
        @app.auth_required(HTTPBasicAuth())
        def bar():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        assert (
            rv.json['paths']['/foo']['post']['responses']['422']['description']
            == 'Request validation failed'
        )
        assert (
            rv.json['paths']['/bar']['get']['responses']['401']['description']
            == 'Authentication required'
        )

    def test_custom_response_schema_function(self, app, client):
        def custom_http_error_schema():
            return {
                'type': 'object',
                'properties': {
                    'error': {'type': 'string'},
                    'code': {'type': 'integer'},
                },
                'required': ['error', 'code'],
            }

        app.config['HTTP_ERROR_SCHEMA'] = custom_http_error_schema

        @app.get('/foo')
        @app.auth_required(HTTPBasicAuth())
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        schema = rv.json['paths']['/foo']['get']['responses']['401']['content'][
            'application/json'
        ]['schema']
        assert schema['properties']['error']['type'] == 'string'
        assert schema['properties']['code']['type'] == 'integer'

    def test_disable_auto_error_responses(self, app, client):
        app.config['AUTO_VALIDATION_ERROR_RESPONSE'] = False
        app.config['AUTO_AUTH_ERROR_RESPONSE'] = False
        app.config['AUTO_404_RESPONSE'] = False

        @app.post('/foo')
        @app.input(Foo)
        @app.auth_required(HTTPBasicAuth())
        def foo(json_data):
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        responses = rv.json['paths']['/foo']['post']['responses']
        assert '422' not in responses
        assert '401' not in responses
        assert '403' not in responses
        assert '404' not in responses


class TestOpenAPIFieldsSettings:
    """Tests for OpenAPI field configuration settings."""

    def test_openapi_version_config(self, app, client):
        app.config['OPENAPI_VERSION'] = '3.0.2'

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['openapi'] == '3.0.2'

    def test_info_config(self, app, client):
        app.config['INFO'] = {
            'title': 'My Custom API',
            'version': '2.0.0',
            'description': 'Custom API description',
        }

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['info']['title'] == 'My Custom API'
        assert rv.json['info']['version'] == '2.0.0'
        assert rv.json['info']['description'] == 'Custom API description'

    def test_servers_config(self, app, client):
        app.config['SERVERS'] = [
            {'url': 'https://api.example.com/v1', 'description': 'Production server'},
            {'url': 'https://staging.example.com/v1', 'description': 'Staging server'},
        ]

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['servers'] == [
            {'url': 'https://api.example.com/v1', 'description': 'Production server'},
            {'url': 'https://staging.example.com/v1', 'description': 'Staging server'},
        ]

    def test_tags_config(self, app, client):
        app.config['TAGS'] = [
            {'name': 'users', 'description': 'User operations'},
            {'name': 'posts', 'description': 'Post operations'},
        ]

        @app.get('/users')
        @app.doc(tags=['users'])
        def get_users():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['tags'] == [
            {'name': 'users', 'description': 'User operations'},
            {'name': 'posts', 'description': 'Post operations'},
        ]

    def test_external_docs_config(self, app, client):
        app.config['EXTERNAL_DOCS'] = {
            'description': 'Find more info here',
            'url': 'https://docs.example.com',
        }

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['externalDocs'] == {
            'description': 'Find more info here',
            'url': 'https://docs.example.com',
        }

    def test_security_schemes_config(self, app, client):
        app.config['SECURITY_SCHEMES'] = {
            'ApiKeyAuth': {
                'type': 'apiKey',
                'in': 'header',
                'name': 'X-API-Key'
            }
        }

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['components']['securitySchemes']['ApiKeyAuth'] == {
            'type': 'apiKey',
            'in': 'header',
            'name': 'X-API-Key'
        }

    def test_path_parameter_description_config(self, app, client):
        app.config['PATH_PARAMETER_DESCRIPTIONS'] = {
            'user_id': 'The unique identifier for a user',
            'post_id': 'The unique identifier for a post',
        }

        @app.get('/users/<int:user_id>')
        def get_user(user_id):
            pass

        @app.get('/posts/<int:post_id>')
        def get_post(post_id):
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        user_param = rv.json['paths']['/users/{user_id}']['get']['parameters'][0]
        assert user_param['description'] == 'The unique identifier for a user'

        post_param = rv.json['paths']['/posts/{post_id}']['get']['parameters'][0]
        assert post_param['description'] == 'The unique identifier for a post'

    def test_operation_id_config(self, app, client):
        app.config['AUTO_OPERATION_ID'] = True

        @app.get('/users')
        def get_all_users():
            pass

        @app.post('/users')
        def create_new_user():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/users']['get']['operationId'] == 'get_all_users'
        assert rv.json['paths']['/users']['post']['operationId'] == 'create_new_user'

    def test_schema_name_resolver_config(self, app, client):
        def custom_schema_name_resolver(schema):
            return f'Custom{schema.__name__}'

        app.config['SCHEMA_NAME_RESOLVER'] = custom_schema_name_resolver

        @app.post('/foo')
        @app.input(Foo)
        @app.output(Foo)
        def foo(json_data):
            return json_data

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'CustomFoo' in rv.json['components']['schemas']
