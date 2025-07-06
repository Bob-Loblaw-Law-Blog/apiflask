import pytest
import json

import openapi_spec_validator as osv
from flask.views import MethodView

from apiflask import APIFlask
from apiflask import APIBlueprint
from apiflask.commands import spec_command
from apiflask.security import HTTPBasicAuth
from apiflask.schemas import EmptySchema, http_error_schema
from .schemas import Foo, HTTPError, Query, ValidationError


class TestSettingsApiDocs:

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
        assert b'src="https://cdn.example.com/redoc.js"' in rv.data


    @pytest.mark.parametrize('config_value', [{}, {'disableSearch': True, 'hideLoading': True}])
    def test_redoc_config(self, client, config_value):
        app = APIFlask(__name__, docs_ui='redoc')
        app.config['REDOC_CONFIG'] = config_value
        client = app.test_client()

        rv = client.get('/docs')
        assert rv.status_code == 200
        if config_value == {}:
            assert b'{},' in rv.data
        else:
            assert b'"disableSearch": true' in rv.data
            assert b'"hideLoading": true' in rv.data


    def test_swagger_ui_resources(self, app, client):
        app.config['SWAGGER_UI_CSS'] = 'https://cdn.example.com/swagger-ui.css'
        app.config['SWAGGER_UI_BUNDLE_JS'] = 'https://cdn.example.com/swagger-ui.bundle.js'
        app.config['SWAGGER_UI_STANDALONE_PRESET_JS'] = 'https://cdn.example.com/swagger-ui.preset.js'

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'href="https://cdn.example.com/swagger-ui.css"' in rv.data
        assert b'src="https://cdn.example.com/swagger-ui.bundle.js"' in rv.data
        assert b'src="https://cdn.example.com/swagger-ui.preset.js"' in rv.data


    def test_swagger_ui_layout(self, app, client):
        app.config['SWAGGER_UI_LAYOUT'] = 'StandaloneLayout'

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'StandaloneLayout' in rv.data
        assert b'BaseLayout' not in rv.data


    def test_swagger_ui_config(self, app, client):
        app.config['SWAGGER_UI_CONFIG'] = {'deepLinking': False, 'layout': 'StandaloneLayout'}

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'"deepLinking": false' in rv.data
        assert b'"layout": "StandaloneLayout"' in rv.data


    def test_swagger_ui_oauth_config(self, app, client):
        app.config['SWAGGER_UI_OAUTH_CONFIG'] = {
            'clientId': 'foo',
            'usePkceWithAuthorizationCodeGrant': True,
        }

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'ui.initOAuth(' in rv.data
        assert b'"clientId": "foo"' in rv.data
        assert b'"usePkceWithAuthorizationCodeGrant": true' in rv.data


    def test_elements_config(self):
        app = APIFlask(__name__, docs_ui='elements')

        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        # test default router
        assert b'router="hash"' in rv.data

        app.config['ELEMENTS_CONFIG'] = {'hideTryIt': False, 'router': 'memory'}

        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'hideTryIt=false' in rv.data
        assert b'router="memory"' in rv.data


    def test_elements_layout(self):
        app = APIFlask(__name__, docs_ui='elements')
        app.config['ELEMENTS_LAYOUT'] = 'stacked'

        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'layout="stacked"' in rv.data
        assert b'layout="sidebar"' not in rv.data


    def test_elements_resources(self):
        app = APIFlask(__name__, docs_ui='elements')
        app.config['ELEMENTS_CSS'] = 'https://cdn.example.com/elements.css'
        app.config['ELEMENTS_JS'] = 'https://cdn.example.com/elements.js'

        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'href="https://cdn.example.com/elements.css"' in rv.data
        assert b'src="https://cdn.example.com/elements.js"' in rv.data


    def test_rapidoc_config(self):
        app = APIFlask(__name__, docs_ui='rapidoc')
        app.config['RAPIDOC_CONFIG'] = {'update-route': False, 'layout': 'row'}

        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'update-route=false' in rv.data
        assert b'layout="row"' in rv.data


    def test_rapidoc_theme(self):
        app = APIFlask(__name__, docs_ui='rapidoc')
        app.config['RAPIDOC_THEME'] = 'dark'

        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'theme="dark"' in rv.data
        assert b'theme="light"' not in rv.data


    def test_rapidoc_resources(self):
        app = APIFlask(__name__, docs_ui='rapidoc')
        app.config['RAPIDOC_JS'] = 'https://cdn.example.com/rapidoc.js'

        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'src="https://cdn.example.com/rapidoc.js"' in rv.data


    def test_rapipdf_config(self):
        app = APIFlask(__name__, docs_ui='rapipdf')
        app.config['RAPIPDF_CONFIG'] = {'include-example': True, 'button-label': 'Generate!'}

        rv = app.test_client().get('/docs')
        assert rv.status_code == 200
        assert b'include-example=true' in rv.data
        assert b'button-label="Generate!"' in rv.data


    def test_rapipdf_resources(self):
        app = APIFlask(__name__, docs_ui='rapipdf')
        client = app.test_client()
        app.config['RAPIPDF_JS'] = 'https://cdn.example.com/rapipdf.js'

        rv = client.get('/docs')
        assert rv.status_code == 200
        assert b'src="https://cdn.example.com/rapipdf.js"' in rv.data

class TestSettingsAutoBehaviour:

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

        @app.get('/spam')
        def get_spam():
            """Spam Summary

            some description
            """
            pass

        @app.get('/eggs')
        @app.doc(summary='Eggs from doc decortor')
        def get_eggs():
            """Eggs Summary

            some description
            """
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        if config_value:
            assert rv.json['paths']['/foo']['get']['summary'] == 'Foo'
            assert rv.json['paths']['/bar']['get']['summary'] == 'Get Bar'
            assert rv.json['paths']['/baz']['get']['summary'] == 'Baz Summary'
            assert rv.json['paths']['/spam']['get']['summary'] == 'Spam Summary'
        else:
            assert 'summary' not in rv.json['paths']['/foo']['get']
            assert 'summary' not in rv.json['paths']['/bar']['get']
            assert 'summary' not in rv.json['paths']['/baz']['get']
            assert 'summary' not in rv.json['paths']['/spam']['get']
        assert rv.json['paths']['/eggs']['get']['summary'] == 'Eggs from doc decortor'


    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_path_summary_with_methodview(self, app, client, config_value):
        app.config['AUTO_OPERATION_SUMMARY'] = config_value

        @app.route('/foo')
        class Foo(MethodView):
            def get(self):
                pass

            def post(self):
                """Post Summary"""
                pass

            def delete(self):
                """Delete Summary

                some description
                """
                pass

            @app.doc(summary='Put from doc decortor')
            def put(self):
                """Delete Summary

                some description
                """
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        if config_value:
            assert rv.json['paths']['/foo']['get']['summary'] == 'Get Foo'
            assert rv.json['paths']['/foo']['post']['summary'] == 'Post Summary'
            assert rv.json['paths']['/foo']['delete']['summary'] == 'Delete Summary'
        else:
            assert 'summary' not in rv.json['paths']['/foo']['get']
            assert 'summary' not in rv.json['paths']['/foo']['post']
            assert 'summary' not in rv.json['paths']['/foo']['delete']
        assert rv.json['paths']['/foo']['put']['summary'] == 'Put from doc decortor'


    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_path_description(self, app, client, config_value):
        app.config['AUTO_OPERATION_DESCRIPTION'] = config_value

        @app.get('/foo')
        def get_foo():
            """Foo

            some description for foo
            """
            pass

        @app.get('/bar')
        @app.doc(description='bar from doc decortor')
        def get_bar():
            """Bar

            some description for bar
            """
            pass

        @app.route('/baz')
        class Baz(MethodView):
            def get(self):
                """Baz

                some description for baz
                """
                pass

            @app.doc(description='post from doc decortor')
            def post(self):
                """Baz

                some description for baz
                """
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        if config_value:
            assert rv.json['paths']['/foo']['get']['description'] == 'some description for foo'
            assert rv.json['paths']['/baz']['get']['description'] == 'some description for baz'
        else:
            assert 'description' not in rv.json['paths']['/foo']['get']
            assert 'description' not in rv.json['paths']['/baz']['get']
        assert rv.json['paths']['/bar']['get']['description'] == 'bar from doc decortor'
        assert rv.json['paths']['/baz']['post']['description'] == 'post from doc decortor'


    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_200_response_for_bare_views(self, app, client, config_value):
        app.config['AUTO_200_RESPONSE'] = config_value

        @app.get('/foo')
        def foo():
            pass

        @app.route('/bar')
        class Bar(MethodView):
            def get(self):
                pass

            def post(self):
                pass

        @app.route('/baz')
        class Baz(MethodView):
            def get(self):
                pass

            @app.input(Foo)
            def post(self):
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert bool('/foo' in rv.json['paths']) is config_value
        assert bool('/bar' in rv.json['paths']) is config_value
        assert '/baz' in rv.json['paths']
        assert bool('get' in rv.json['paths']['/baz']) is config_value
        assert 'post' in rv.json['paths']['/baz']


    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_200_response_for_no_output_views(self, app, client, config_value):
        app.config['AUTO_200_RESPONSE'] = config_value

        @app.get('/foo')
        @app.input(Query, location='query')
        def foo():
            pass

        @app.route('/bar')
        class Bar(MethodView):
            @app.input(Query, location='query')
            def get(self):
                pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert '/foo' in rv.json['paths']
        assert '/bar' in rv.json['paths']
        assert bool('200' in rv.json['paths']['/foo']['get']['responses']) is config_value
        assert bool('200' in rv.json['paths']['/bar']['get']['responses']) is config_value


    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_validation_error_response(self, app, client, config_value):
        app.config['AUTO_VALIDATION_ERROR_RESPONSE'] = config_value

        @app.post('/foo')
        @app.input(Foo)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert bool('422' in rv.json['paths']['/foo']['post']['responses']) is config_value
        if config_value:
            assert 'ValidationError' in rv.json['components']['schemas']
            assert (
                '#/components/schemas/ValidationError'
                in rv.json['paths']['/foo']['post']['responses']['422']['content']['application/json'][
                    'schema'
                ]['$ref']
            )


    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_auth_error_response(self, app, client, config_value):
        app.config['AUTO_AUTH_ERROR_RESPONSE'] = config_value
        auth = HTTPBasicAuth()

        @app.post('/foo')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert bool('401' in rv.json['paths']['/foo']['post']['responses']) is config_value
        if config_value:
            assert 'HTTPError' in rv.json['components']['schemas']
            assert (
                '#/components/schemas/HTTPError'
                in rv.json['paths']['/foo']['post']['responses']['401']['content']['application/json'][
                    'schema'
                ]['$ref']
            )


    @pytest.mark.parametrize('config_value', [True, False])
    def test_blueprint_level_auto_auth_error_response(self, app, client, config_value):
        app.config['AUTO_AUTH_ERROR_RESPONSE'] = config_value
        bp = APIBlueprint('auth', __name__)
        no_auth_bp = APIBlueprint('no-auth', __name__)

        auth = HTTPBasicAuth()

        @bp.before_request
        @bp.auth_required(auth)
        def before():
            pass

        @bp.post('/foo')
        def foo():
            pass

        @bp.post('/bar')
        def bar():
            pass

        @no_auth_bp.post('/baz')
        def baz():
            return 'no auth'

        app.register_blueprint(bp)
        app.register_blueprint(no_auth_bp)

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)

        assert 'auth' in app._auth_blueprints
        assert 'no-auth' not in app._auth_blueprints

        assert bool('401' in rv.json['paths']['/foo']['post']['responses']) is config_value
        assert bool('401' in rv.json['paths']['/bar']['post']['responses']) is config_value
        assert '401' not in rv.json['paths']['/baz']['post']['responses']
        if config_value:
            assert 'HTTPError' in rv.json['components']['schemas']
            assert (
                '#/components/schemas/HTTPError'
                in rv.json['paths']['/foo']['post']['responses']['401']['content']['application/json'][
                    'schema'
                ]['$ref']
            )
            assert (
                '#/components/schemas/HTTPError'
                in rv.json['paths']['/bar']['post']['responses']['401']['content']['application/json'][
                    'schema'
                ]['$ref']
            )


    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_404_error(self, app, client, config_value):
        app.config['AUTO_404_RESPONSE'] = config_value

        @app.get('/foo/<int:id>')
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert bool('404' in rv.json['paths']['/foo/{id}']['get']['responses']) is config_value
        if config_value:
            assert 'HTTPError' in rv.json['components']['schemas']
            assert (
                '#/components/schemas/HTTPError'
                in rv.json['paths']['/foo/{id}']['get']['responses']['404']['content'][
                    'application/json'
                ]['schema']['$ref']
            )


    @pytest.mark.parametrize('config_value', [True, False])
    def test_auto_operationid(self, app, client, config_value):
        app.config['AUTO_OPERATION_ID'] = config_value

        @app.get('/foo')
        def foo():
            pass

        bp = APIBlueprint('test', __name__)

        @bp.get('/foo')
        def bp_foo():
            pass

        @bp.post('/bar')
        def bar():
            pass

        app.register_blueprint(bp, url_prefix='/test')

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert bool('operationId' in rv.json['paths']['/foo']['get']) == config_value
        assert bool('operationId' in rv.json['paths']['/test/foo']['get']) == config_value
        if config_value:
            assert rv.json['paths']['/foo']['get']['operationId'] == 'get_foo'
            assert rv.json['paths']['/test/foo']['get']['operationId'] == 'get_test_bp_foo'
            assert rv.json['paths']['/test/bar']['post']['operationId'] == 'post_test_bar'

class TestSettingsOpenApiFields:

    def test_openapi_fields(self, app, client):
        openapi_version = '3.0.2'
        description = 'My API'
        tags = [
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
        contact = {
            'name': 'API Support',
            'url': 'http://www.example.com/support',
            'email': 'support@example.com',
        }
        license = {'name': 'Apache 2.0', 'url': 'http://www.apache.org/licenses/LICENSE-2.0.html'}
        terms_of_service = 'http://example.com/terms/'
        external_docs = {'description': 'Find more info here', 'url': 'https://docs.example.com/'}
        servers = [
            {'url': 'http://localhost:5000/', 'description': 'Development server'},
            {'url': 'https://api.example.com/', 'description': 'Production server'},
        ]
        app.config['OPENAPI_VERSION'] = openapi_version
        app.config['DESCRIPTION'] = description
        app.config['TAGS'] = tags
        app.config['CONTACT'] = contact
        app.config['LICENSE'] = license
        app.config['TERMS_OF_SERVICE'] = terms_of_service
        app.config['EXTERNAL_DOCS'] = external_docs
        app.config['SERVERS'] = servers

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['openapi'] == openapi_version
        assert rv.json['tags'] == tags
        assert rv.json['servers'] == servers
        assert rv.json['externalDocs'] == external_docs
        assert rv.json['info']['description'] == description
        assert rv.json['info']['contact'] == contact
        assert rv.json['info']['license'] == license
        assert rv.json['info']['termsOfService'] == terms_of_service


    def test_info(self, app, client):
        app.config['INFO'] = {
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
        assert rv.json['info']['description'] == app.config['INFO']['description']
        assert rv.json['info']['termsOfService'] == app.config['INFO']['termsOfService']
        assert rv.json['info']['contact'] == app.config['INFO']['contact']
        assert rv.json['info']['license'] == app.config['INFO']['license']


    def test_overwrite_info(self, app, client):
        app.config['INFO'] = {
            'description': 'Not set',
            'termsOfService': 'Not set',
            'contact': {'name': 'Not set', 'url': 'Not set', 'email': 'Not set'},
            'license': {'name': 'Not set', 'url': 'Not set'},
        }

        app.config['DESCRIPTION'] = 'My API'
        app.config['CONTACT'] = {
            'name': 'API Support',
            'url': 'http://www.example.com/support',
            'email': 'support@example.com',
        }
        app.config['LICENSE'] = {
            'name': 'Apache 2.0',
            'url': 'http://www.apache.org/licenses/LICENSE-2.0.html',
        }
        app.config['TERMS_OF_SERVICE'] = 'http://example.com/terms/'

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['info']['description'] == app.config['DESCRIPTION']
        assert rv.json['info']['termsOfService'] == app.config['TERMS_OF_SERVICE']
        assert rv.json['info']['contact'] == app.config['CONTACT']
        assert rv.json['info']['license'] == app.config['LICENSE']


    def test_security_schemes(self, app, client):
        app.config['SECURITY_SCHEMES'] = {
            'ApiKeyAuth': {'type': 'apiKey', 'in': 'header', 'name': 'X-API-Key'},
            'BasicAuth': {
                'type': 'http',
                'scheme': 'basic',
            },
        }

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert len(rv.json['components']['securitySchemes']) == 2
        assert (
            rv.json['components']['securitySchemes']['ApiKeyAuth']
            == app.config['SECURITY_SCHEMES']['ApiKeyAuth']
        )
        assert (
            rv.json['components']['securitySchemes']['BasicAuth']
            == app.config['SECURITY_SCHEMES']['BasicAuth']
        )

class TestSettingsOpenApiSpec:

    def test_json_spec_mimetype(self, app, client):
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        assert rv.mimetype == 'application/json'

        app.config['JSON_SPEC_MIMETYPE'] = 'application/custom.json'

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        assert rv.mimetype == 'application/custom.json'


    def test_yaml_spec_mimetype(self):
        app = APIFlask(__name__, spec_path='/openapi.yaml')
        app.config['SPEC_FORMAT'] = 'yaml'
        client = app.test_client()

        rv = client.get('/openapi.yaml')
        assert rv.status_code == 200
        assert rv.mimetype == 'text/vnd.yaml'

        app.config['YAML_SPEC_MIMETYPE'] = 'text/custom.yaml'

        rv = client.get('/openapi.yaml')
        assert rv.status_code == 200
        assert rv.mimetype == 'text/custom.yaml'


    @pytest.mark.parametrize('format', ['yaml', 'yml', 'json'])
    def test_spec_format(self, app, client, cli_runner, format):
        app.config['SPEC_FORMAT'] = format

        result = cli_runner.invoke(spec_command)
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        if format == 'json':
            assert '"title": "APIFlask",' in result.output
            assert b'"title":"APIFlask",' in rv.data
            assert rv.headers['Content-Type'] == 'application/json'
        else:
            assert 'title: APIFlask' in result.output
            assert b'title: APIFlask' in rv.data
            assert rv.headers['Content-Type'] == 'text/vnd.yaml'


    def test_local_spec_path(self, app, cli_runner, tmp_path):
        local_spec_path = tmp_path / 'api.json'
        app.config['LOCAL_SPEC_PATH'] = local_spec_path

        result = cli_runner.invoke(spec_command)
        assert 'openapi' in result.output
        with open(local_spec_path) as f:
            assert json.loads(f.read()) == app.spec


    @pytest.mark.parametrize('indent', [0, 2, 4])
    def test_local_spec_json_indent(self, app, cli_runner, indent):
        app.config['LOCAL_SPEC_JSON_INDENT'] = indent

        result = cli_runner.invoke(spec_command)
        if indent == 0:
            assert '{"info": {' in result.output
        else:
            assert f'{{\n{" " * indent}"info": {{' in result.output

class TestSettingsResponseCustomization:

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

        @app.get('/spam')
        @app.output(Foo, status_code=206)
        def spam():
            pass

        @app.get('/eggs/<int:id>')
        def eggs():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['responses']['200']['description'] == 'Success'
        assert rv.json['paths']['/bar']['get']['responses']['201']['description'] == 'Success'
        assert rv.json['paths']['/baz']['get']['responses']['200']['description'] == 'Success'
        assert rv.json['paths']['/spam']['get']['responses']['206']['description'] == 'Success'
        assert (
            rv.json['paths']['/eggs/{id}']['get']['responses']['404']['description'] == 'Egg not found'
        )


    def test_validation_error_status_code_and_description(self, app, client):
        app.config['VALIDATION_ERROR_STATUS_CODE'] = 400
        app.config['VALIDATION_ERROR_DESCRIPTION'] = 'Bad'

        @app.post('/foo')
        @app.input(Foo)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['post']['responses']['400'] is not None
        assert rv.json['paths']['/foo']['post']['responses']['400']['description'] == 'Bad'


    @pytest.mark.parametrize('schema', [http_error_schema, ValidationError])
    def test_validation_error_schema(self, app, client, schema):
        app.config['VALIDATION_ERROR_SCHEMA'] = schema

        @app.post('/foo')
        @app.input(Foo)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['post']['responses']['422']
        assert rv.json['paths']['/foo']['post']['responses']['422']['description'] == 'Validation error'
        assert 'ValidationError' in rv.json['components']['schemas']


    def test_validation_error_schema_bad_type(self, app):
        app.config['VALIDATION_ERROR_SCHEMA'] = 'schema'

        @app.post('/foo')
        @app.input(Foo)
        def foo():
            pass

        with pytest.raises(TypeError):
            app.spec


    def test_auth_error_status_code_and_description(self, app, client):
        app.config['AUTH_ERROR_STATUS_CODE'] = 403
        app.config['AUTH_ERROR_DESCRIPTION'] = 'Bad'
        auth = HTTPBasicAuth()

        @app.post('/foo')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['post']['responses']['403'] is not None
        assert rv.json['paths']['/foo']['post']['responses']['403']['description'] == 'Bad'


    def test_auth_error_schema(self, app, client):
        auth = HTTPBasicAuth()

        @app.post('/foo')
        @app.auth_required(auth)
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['post']['responses']['401']
        assert 'HTTPError' in rv.json['components']['schemas']


    def test_http_auth_error_response(self, app, client):
        @app.get('/foo')
        @app.output(Foo)
        @app.doc(responses={204: 'empty', 400: 'bad', 404: 'not found', 500: 'server error'})
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert 'HTTPError' in rv.json['components']['schemas']
        assert (
            '#/components/schemas/HTTPError'
            in rv.json['paths']['/foo']['get']['responses']['404']['content']['application/json'][
                'schema'
            ]['$ref']
        )
        assert (
            '#/components/schemas/HTTPError'
            in rv.json['paths']['/foo']['get']['responses']['500']['content']['application/json'][
                'schema'
            ]['$ref']
        )
        assert 'content' not in rv.json['paths']['/foo']['get']['responses']['204']


    @pytest.mark.parametrize('schema', [http_error_schema, HTTPError])
    def test_http_error_schema(self, app, client, schema):
        app.config['HTTP_ERROR_SCHEMA'] = schema

        @app.get('/foo')
        @app.output(Foo)
        @app.doc(responses={400: 'bad', 404: 'not found', 500: 'server error'})
        def foo():
            pass

        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        osv.validate(rv.json)
        assert rv.json['paths']['/foo']['get']['responses']['404']
        assert 'HTTPError' in rv.json['components']['schemas']


    def test_http_error_schema_bad_type(self, app):
        app.config['HTTP_ERROR_SCHEMA'] = 'schema'

        @app.get('/foo')
        @app.output(Foo)
        @app.doc(responses={400: 'bad', 404: 'not found', 500: 'server error'})
        def foo():
            pass

        with pytest.raises(TypeError):
            app.spec
