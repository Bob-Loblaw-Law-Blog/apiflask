"""
Parametrized tests for routing logic with both View and MethodView classes.

This module provides comprehensive parameterized tests to ensure routing works
correctly with both Flask view classes across various scenarios.
"""
import pytest
from unittest.mock import Mock, patch
from flask.views import MethodView, View

from apiflask import APIFlask, APIBlueprint
from apiflask.schemas import Schema
from apiflask.fields import String, Integer


# Test schemas
class QuerySchema(Schema):
    """Test query schema."""
    search = String(required=False)
    limit = Integer(required=False)


class BodySchema(Schema):
    """Test body schema."""
    name = String(required=True)
    value = Integer(required=True)


class ResponseSchema(Schema):
    """Test response schema."""
    message = String()
    status = String()


# Test view classes for parallel testing
class TestMethodViewComplete(MethodView):
    """Complete MethodView with all HTTP methods and decorators."""
    
    def get(self):
        """Get items."""
        return {'method': 'GET', 'data': 'list'}
    
    def post(self):
        """Create item."""
        return {'method': 'POST', 'data': 'created'}, 201
    
    def put(self):
        """Update item."""
        return {'method': 'PUT', 'data': 'updated'}
    
    def patch(self):
        """Partially update item."""
        return {'method': 'PATCH', 'data': 'patched'}
    
    def delete(self):
        """Delete item."""
        return {'method': 'DELETE', 'data': 'deleted'}, 204
    
    def head(self):
        """Head request."""
        return ''
    
    def options(self):
        """Options request."""
        return ''


class TestViewComplete(View):
    """Complete View class with multiple HTTP methods."""
    methods = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']
    
    def dispatch_request(self):
        """Dispatch request based on method."""
        method = request.method
        if method == 'DELETE':
            return '', 204
        elif method == 'POST':
            return {'method': method, 'data': 'view_response'}, 201
        else:
            return {'method': method, 'data': 'view_response'}


class MethodViewPartial(MethodView):
    """MethodView with only some methods implemented."""
    
    def get(self):
        return {'method': 'GET'}
    
    def post(self):
        return {'method': 'POST'}


class ViewPartial(View):
    """View with limited methods."""
    methods = ['GET', 'POST']
    
    def dispatch_request(self):
        return {'method': request.method}


# Parametrized test configurations
VIEW_CLASS_PAIRS = [
    pytest.param(
        TestMethodViewComplete, 
        TestViewComplete, 
        'complete',
        id='complete_views'
    ),
    pytest.param(
        MethodViewPartial, 
        ViewPartial,
        'partial',
        id='partial_views'
    ),
]

HTTP_METHOD_CONFIGS = [
    pytest.param('GET', 200, 'get', id='GET'),
    pytest.param('POST', 201, 'post', id='POST'),
    pytest.param('PUT', 200, 'put', id='PUT'),
    pytest.param('PATCH', 200, 'patch', id='PATCH'),
    pytest.param('DELETE', 204, 'delete', id='DELETE'),
    pytest.param('HEAD', 200, 'head', id='HEAD'),
    pytest.param('OPTIONS', 200, 'options', id='OPTIONS'),
]

ROUTE_CONFIGS = [
    pytest.param('/items', None, {}, id='simple_route'),
    pytest.param('/items/<int:item_id>', None, {}, id='route_with_param'),
    pytest.param('/api/v1/items', None, {'strict_slashes': False}, id='route_with_options'),
    pytest.param('/custom', 'custom_endpoint', {}, id='custom_endpoint'),
]


class TestParallelViewClasses:
    """Test both View and MethodView classes in parallel with same scenarios."""
    
    @pytest.fixture
    def app(self):
        """Create test application."""
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.mark.parametrize('method_view_class,view_class,test_type', VIEW_CLASS_PAIRS)
    @pytest.mark.parametrize('route,endpoint,options', ROUTE_CONFIGS)
    def test_parallel_routing(self, app, client, method_view_class, view_class, 
                            test_type, route, endpoint, options):
        """Test routing works identically for both view class types."""
        # Register MethodView
        method_route = f'{route}/method'
        app.add_url_rule(
            method_route,
            endpoint=f'{endpoint}_method' if endpoint else None,
            view_func=method_view_class,
            **options
        )
        
        # Register View
        view_route = f'{route}/view'
        app.add_url_rule(
            view_route,
            endpoint=f'{endpoint}_view' if endpoint else None,
            view_func=view_class,
            **options
        )
        
        # Test that both routes are registered
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert method_route in rules
        assert view_route in rules
        
        # Test GET requests work for both
        if test_type == 'complete' or 'GET' in getattr(view_class, 'methods', []):
            rv_method = client.get(method_route)
            rv_view = client.get(view_route)
            
            assert rv_method.status_code == 200
            assert rv_view.status_code == 200
    
    @pytest.mark.parametrize('method_view_class,view_class,test_type', VIEW_CLASS_PAIRS)
    def test_parallel_blueprint_registration(self, app, method_view_class, view_class, test_type):
        """Test both view classes work with blueprints."""
        # Create blueprint
        bp = APIBlueprint('test_bp', __name__)
        
        # Register both view types on blueprint
        bp.add_url_rule('/method', view_func=method_view_class)
        bp.add_url_rule('/view', view_func=view_class)
        
        # Register blueprint
        app.register_blueprint(bp, url_prefix='/api')
        
        # Check routes are registered
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert '/api/method' in rules
        assert '/api/view' in rules
    
    @pytest.mark.parametrize('method,expected_status,client_method', HTTP_METHOD_CONFIGS)
    def test_parallel_http_methods(self, app, client, method, expected_status, client_method):
        """Test various HTTP methods work for both view types."""
        # Skip if method not in complete views
        if method not in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE']:
            pytest.skip(f"Method {method} not implemented in test views")
        
        # Register both view types
        app.add_url_rule('/method', view_func=TestMethodViewComplete)
        app.add_url_rule('/view', view_func=TestViewComplete)
        
        # Test method on MethodView
        if hasattr(client, client_method):
            rv_method = getattr(client, client_method)('/method')
            assert rv_method.status_code == expected_status
        
        # Test method on View
        if hasattr(client, client_method):
            rv_view = getattr(client, client_method)('/view')
            assert rv_view.status_code == expected_status


class TestParametrizedDecorators:
    """Test decorators with both view classes using parameterization."""
    
    @pytest.fixture
    def app(self):
        """Create test application."""
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.mark.parametrize('use_method_view', [True, False], ids=['MethodView', 'View'])
    def test_input_decorator(self, app, client, use_method_view):
        """Test input decorator works with both view types."""
        if use_method_view:
            @app.route('/test')
            class TestView(MethodView):
                @app.input(BodySchema)
                def post(self, json_data):
                    return {'received': json_data}
        else:
            # For View class, we need to use function decorator
            @app.post('/test')
            @app.input(BodySchema)
            def test_view(json_data):
                return {'received': json_data}
        
        # Test with valid data
        rv = client.post('/test', json={'name': 'test', 'value': 42})
        assert rv.status_code == 200
        assert rv.json['received']['name'] == 'test'
        assert rv.json['received']['value'] == 42
        
        # Test with invalid data
        rv = client.post('/test', json={'name': 'test'})
        assert rv.status_code == 422  # Validation error
    
    @pytest.mark.parametrize('use_method_view', [True, False], ids=['MethodView', 'View'])
    def test_output_decorator(self, app, client, use_method_view):
        """Test output decorator works with both view types."""
        if use_method_view:
            @app.route('/test')
            class TestView(MethodView):
                @app.output(ResponseSchema)
                def get(self):
                    return {'message': 'Hello', 'status': 'ok'}
        else:
            @app.get('/test')
            @app.output(ResponseSchema)
            def test_view():
                return {'message': 'Hello', 'status': 'ok'}
        
        rv = client.get('/test')
        assert rv.status_code == 200
        assert rv.json['message'] == 'Hello'
        assert rv.json['status'] == 'ok'
    
    @pytest.mark.parametrize('use_method_view', [True, False], ids=['MethodView', 'View'])
    @pytest.mark.parametrize('location', ['query', 'headers', 'cookies'])
    def test_input_locations(self, app, client, use_method_view, location):
        """Test input from various locations with both view types."""
        if use_method_view:
            @app.route('/test')
            class TestView(MethodView):
                @app.input(QuerySchema, location=location)
                def get(self, data):
                    return {'location': location, 'data': data}
        else:
            @app.get('/test')
            @app.input(QuerySchema, location=location)
            def test_view(data):
                return {'location': location, 'data': data}
        
        # Prepare request based on location
        kwargs = {}
        if location == 'query':
            kwargs['query_string'] = 'search=test&limit=10'
        elif location == 'headers':
            kwargs['headers'] = {'search': 'test', 'limit': '10'}
        elif location == 'cookies':
            client.set_cookie('/', 'search', 'test')
            client.set_cookie('/', 'limit', '10')
        
        rv = client.get('/test', **kwargs)
        assert rv.status_code == 200
        assert rv.json['location'] == location


class TestParametrizedSpecGeneration:
    """Test OpenAPI spec generation for both view types."""
    
    @pytest.fixture
    def app(self):
        """Create test application with OpenAPI enabled."""
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return app.test_client()
    
    @pytest.mark.parametrize('use_method_view', [True, False], ids=['MethodView', 'View'])
    def test_spec_generation(self, app, client, use_method_view):
        """Test OpenAPI spec is generated correctly for both view types."""
        if use_method_view:
            @app.route('/test')
            class TestView(MethodView):
                """Test API endpoint."""
                
                def get(self):
                    """Get test data."""
                    return {'data': 'test'}
                
                def post(self):
                    """Create test data."""
                    return {'created': True}
        else:
            # View class doesn't generate individual method specs
            @app.route('/test')
            class TestView(View):
                """Test API endpoint."""
                methods = ['GET', 'POST']
                
                def dispatch_request(self):
                    return {'data': 'test'}
        
        # Get OpenAPI spec
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        
        spec = rv.json
        assert '/test' in spec['paths']
        
        if use_method_view:
            # MethodView should have separate specs for each method
            assert 'get' in spec['paths']['/test']
            assert 'post' in spec['paths']['/test']
            
            # Check summaries were generated
            get_spec = spec['paths']['/test']['get']
            assert 'summary' in get_spec
            post_spec = spec['paths']['/test']['post']
            assert 'summary' in post_spec
    
    @pytest.mark.parametrize('view_type,expected_methods', [
        (TestMethodViewComplete, ['get', 'post', 'put', 'patch', 'delete']),
        (MethodViewPartial, ['get', 'post']),
    ])
    def test_method_view_spec_methods(self, app, client, view_type, expected_methods):
        """Test that correct methods are included in spec for MethodView."""
        app.add_url_rule('/test', view_func=view_type)
        
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        
        spec = rv.json
        assert '/test' in spec['paths']
        
        # Check expected methods are in spec
        for method in expected_methods:
            assert method in spec['paths']['/test']
        
        # Check no extra methods
        path_methods = set(spec['paths']['/test'].keys())
        assert path_methods == set(expected_methods)


class TestParametrizedEdgeCases:
    """Test edge cases with parameterization."""
    
    @pytest.fixture
    def app(self):
        """Create test application."""
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        return app
    
    @pytest.mark.parametrize('num_routes', [1, 5, 10, 20], ids=lambda x: f'{x}_routes')
    @pytest.mark.parametrize('use_method_view', [True, False], ids=['MethodView', 'View'])
    def test_multiple_routes_same_class(self, app, num_routes, use_method_view):
        """Test registering multiple routes with same view class."""
        view_class = TestMethodViewComplete if use_method_view else TestViewComplete
        
        # Register multiple routes
        for i in range(num_routes):
            app.add_url_rule(
                f'/test{i}',
                endpoint=f'test{i}',
                view_func=view_class
            )
        
        # Check all routes are registered
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        for i in range(num_routes):
            assert f'/test{i}' in rules
    
    @pytest.mark.parametrize('prefix', ['', '/api', '/api/v1', '/very/long/prefix/path'])
    @pytest.mark.parametrize('use_method_view', [True, False], ids=['MethodView', 'View'])
    def test_blueprint_url_prefixes(self, app, prefix, use_method_view):
        """Test blueprints with various URL prefixes."""
        bp = APIBlueprint('test_bp', __name__)
        view_class = TestMethodViewComplete if use_method_view else TestViewComplete
        
        bp.add_url_rule('/test', view_func=view_class)
        app.register_blueprint(bp, url_prefix=prefix if prefix else None)
        
        # Check route is registered with correct prefix
        expected_route = f'{prefix}/test' if prefix else '/test'
        rules = [rule.rule for rule in app.url_map.iter_rules()]
        assert expected_route in rules
    
    @pytest.mark.parametrize('enable_openapi', [True, False])
    @pytest.mark.parametrize('use_method_view', [True, False], ids=['MethodView', 'View'])
    def test_openapi_toggle(self, use_method_view, enable_openapi):
        """Test OpenAPI can be enabled/disabled for both view types."""
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        
        if not enable_openapi:
            app.enable_openapi = False
        
        view_class = TestMethodViewComplete if use_method_view else TestViewComplete
        app.add_url_rule('/test', view_func=view_class)
        
        client = app.test_client()
        
        if enable_openapi:
            # OpenAPI endpoint should be available
            rv = client.get('/openapi.json')
            assert rv.status_code == 200
        else:
            # OpenAPI endpoint should not exist
            rv = client.get('/openapi.json')
            assert rv.status_code == 404


class TestParametrizedAsViewMethod:
    """Test as_view() method behavior with parameterization."""
    
    @pytest.fixture
    def app(self):
        """Create test application."""
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        return app
    
    @pytest.mark.parametrize('name', ['test', 'my_view', 'api_endpoint', 'HTTPView'])
    @pytest.mark.parametrize('view_class', [TestMethodViewComplete, MethodViewPartial])
    def test_as_view_names(self, app, name, view_class):
        """Test as_view() with various endpoint names."""
        view_func = view_class.as_view(name)
        app.add_url_rule(f'/{name}', view_func=view_func)
        
        # Check endpoint is registered with correct name
        assert name in app.view_functions
    
    @pytest.mark.parametrize('init_kwargs', [
        {},
        {'arg1': 'value1'},
        {'arg1': 'value1', 'arg2': 'value2'},
        {'config': {'key': 'value'}},
    ])
    def test_as_view_with_init_kwargs(self, app, init_kwargs):
        """Test as_view() with initialization kwargs."""
        class InitMethodView(MethodView):
            def __init__(self, **kwargs):
                super().__init__()
                self.kwargs = kwargs
            
            def get(self):
                return {'kwargs': self.kwargs}
        
        view_func = InitMethodView.as_view('test', **init_kwargs)
        app.add_url_rule('/test', view_func=view_func)
        
        # The view should be created with the kwargs
        client = app.test_client()
        rv = client.get('/test')
        assert rv.status_code == 200
        assert rv.json['kwargs'] == init_kwargs


if __name__ == '__main__':
    # Import request for dispatch_request methods
    from flask import request
    pytest.main([__file__, '-v'])
