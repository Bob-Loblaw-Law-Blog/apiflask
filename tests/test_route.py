"""
Comprehensive unit tests for APIFlask routing logic.

Tests the route_patch decorator functionality with parameterized tests
covering various Flask endpoint methods and both View and MethodView classes.
"""

import pytest
from flask import Flask
from flask.views import View, MethodView
from unittest.mock import Mock, patch, MagicMock
import typing as t

from apiflask import APIFlask, APIBlueprint
from apiflask.route import route_patch
from apiflask.fields import String, Integer
from apiflask.schemas import Schema


# Test schemas
class TestInputSchema(Schema):
    name = String(required=True)
    age = Integer()


class TestOutputSchema(Schema):
    message = String()
    id = Integer()


# Test view classes
class TestView(View):
    """Test View class"""
    def dispatch_request(self):
        return {'message': 'View response'}


class TestMethodView(MethodView):
    """Test MethodView class
    
    Includes multiple HTTP methods for comprehensive testing.
    """
    
    def get(self):
        """Get a test resource"""
        return {'message': 'GET response'}
    
    def post(self):
        """Create a test resource
        
        This method creates a new test resource.
        """
        return {'message': 'POST response', 'id': 1}
    
    def put(self):
        """Update a test resource"""
        return {'message': 'PUT response'}
    
    def delete(self):
        """Delete a test resource"""
        return {'message': 'DELETE response'}
    
    def patch(self):
        return {'message': 'PATCH response'}


class TestMethodViewLimited(MethodView):
    """MethodView with limited methods"""
    methods = ['GET', 'POST']
    
    def get(self):
        """Get limited resource"""
        return {'message': 'Limited GET'}
    
    def post(self):
        return {'message': 'Limited POST'}


class TestMethodViewNoMethods(MethodView):
    """MethodView with no methods attribute"""
    pass


# Fixtures
@pytest.fixture
def app():
    """Create a test APIFlask app"""
    app = APIFlask(__name__)
    return app


@pytest.fixture
def blueprint():
    """Create a test APIBlueprint"""
    bp = APIBlueprint('test', __name__)
    return bp


@pytest.fixture
def patched_class():
    """Create a class patched with route_patch decorator"""
    @route_patch
    class TestClass:
        def add_url_rule(self, rule, endpoint=None, view_func=None, 
                        provide_automatic_options=None, **options):
            # Store arguments for assertions
            self._last_call = {
                'rule': rule,
                'endpoint': endpoint,
                'view_func': view_func,
                'provide_automatic_options': provide_automatic_options,
                'options': options
            }
    
    # Mock the parent class add_url_rule
    TestClass.__bases__ = (Mock(),)
    TestClass.__bases__[0].add_url_rule = Mock()
    
    return TestClass


class TestRoutePatch:
    """Test the route_patch decorator functionality"""
    
    def test_route_patch_adds_add_url_rule_method(self):
        """Test that route_patch adds the add_url_rule method"""
        @route_patch
        class TestClass:
            pass
        
        assert hasattr(TestClass, 'add_url_rule')
        assert callable(TestClass.add_url_rule)
    
    @pytest.mark.parametrize("view_class,expected_endpoint", [
        (TestView, 'TestView'),
        (TestMethodView, 'TestMethodView'),
        (TestMethodViewLimited, 'TestMethodViewLimited'),
    ])
    def test_add_url_rule_with_view_class(self, patched_class, view_class, expected_endpoint):
        """Test add_url_rule with view class passed directly"""
        instance = patched_class()
        instance.enable_openapi = True
        
        # Mock as_view method
        mock_view_func = Mock()
        mock_view_func.view_class = view_class
        view_class.as_view = Mock(return_value=mock_view_func)
        
        instance.add_url_rule('/test', view_func=view_class)
        
        # Verify as_view was called with correct endpoint
        view_class.as_view.assert_called_once_with(expected_endpoint)
        
        # Verify parent add_url_rule was called
        assert instance.__class__.__bases__[0].add_url_rule.called
    
    @pytest.mark.parametrize("endpoint", [None, 'custom_endpoint'])
    def test_add_url_rule_endpoint_handling(self, patched_class, endpoint):
        """Test endpoint handling when passing view class"""
        instance = patched_class()
        instance.enable_openapi = True
        
        mock_view_func = Mock()
        mock_view_func.view_class = TestMethodView
        TestMethodView.as_view = Mock(return_value=mock_view_func)
        
        instance.add_url_rule('/test', endpoint=endpoint, view_func=TestMethodView)
        
        expected_endpoint = endpoint if endpoint else 'TestMethodView'
        TestMethodView.as_view.assert_called_once_with(expected_endpoint)
    
    @pytest.mark.parametrize("method_name,has_docstring,has_multiline", [
        ('get', True, True),
        ('post', True, True),
        ('put', True, False),
        ('delete', True, False),
        ('patch', False, False),
    ])
    def test_method_spec_recording(self, patched_class, method_name, has_docstring, has_multiline):
        """Test spec recording for MethodView methods"""
        instance = patched_class()
        instance.enable_openapi = True
        
        # Create view function with view_class attribute
        view_func = Mock()
        view_func.view_class = TestMethodView
        view_func._spec = {}
        
        # Ensure methods attribute exists
        if not hasattr(TestMethodView, 'methods'):
            TestMethodView.methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
        
        instance.add_url_rule('/test', view_func=view_func)
        
        # Check that method spec was recorded
        assert hasattr(view_func, '_method_spec')
        assert method_name.upper() in view_func._method_spec
        
        method_spec = view_func._method_spec[method_name.upper()]
        assert 'summary' in method_spec
        assert 'description' in method_spec
        
        # Check generated flags
        assert method_spec.get('generated_summary') is True
        assert method_spec.get('generated_description') is True
    
    def test_view_class_skip_non_methodview(self, patched_class):
        """Test that non-MethodView classes are skipped"""
        instance = patched_class()
        instance.enable_openapi = True
        
        # Create view function with View class (not MethodView)
        view_func = Mock()
        view_func.view_class = TestView
        
        instance.add_url_rule('/test', view_func=view_func)
        
        # Check that it was marked as hidden
        assert hasattr(view_func, '_spec')
        assert view_func._spec == {'hide': True}
        assert not hasattr(view_func, '_method_spec')
    
    def test_no_methods_defined(self, patched_class):
        """Test handling of MethodView with no methods"""
        instance = patched_class()
        instance.enable_openapi = True
        
        view_func = Mock()
        view_func.view_class = TestMethodViewNoMethods
        view_func._spec = {}
        
        # Ensure no methods attribute
        if hasattr(TestMethodViewNoMethods, 'methods'):
            delattr(TestMethodViewNoMethods, 'methods')
        
        instance.add_url_rule('/test', view_func=view_func)
        
        # Should return early without recording method spec
        assert not hasattr(view_func, '_method_spec')
    
    def test_decorator_spec_inheritance(self, patched_class):
        """Test that decorator specs are inherited by methods"""
        instance = patched_class()
        instance.enable_openapi = True
        
        # Create view function with existing spec
        view_func = Mock()
        view_func.view_class = TestMethodViewLimited
        view_func._spec = {
            'tags': ['test-tag'],
            'responses': {404: {'description': 'Not found'}},
            'summary': 'View level summary'  # This should not override method summary
        }
        
        instance.add_url_rule('/test', view_func=view_func)
        
        # Check that specs were inherited
        assert hasattr(view_func, '_method_spec')
        for method in ['GET', 'POST']:
            method_spec = view_func._method_spec[method]
            # These should be inherited
            assert method_spec.get('tags') == ['test-tag']
            assert method_spec.get('responses') == {404: {'description': 'Not found'}}
            # Summary should be generated, not inherited
            assert method_spec.get('summary') != 'View level summary'
    
    def test_method_spec_not_duplicated(self, patched_class):
        """Test that method spec is not extracted multiple times"""
        instance = patched_class()
        instance.enable_openapi = True
        
        view_func = Mock()
        view_func.view_class = TestMethodView
        view_func._spec = {}
        
        # Add the _method_spec attribute to simulate already processed
        view_func._method_spec = {'GET': {'summary': 'Existing'}}
        
        instance.add_url_rule('/test', view_func=view_func)
        
        # Should return early and not modify existing spec
        assert view_func._method_spec == {'GET': {'summary': 'Existing'}}
    
    @pytest.mark.parametrize("openapi_enabled", [True, False])
    def test_openapi_enabled_check(self, patched_class, openapi_enabled):
        """Test that spec recording only happens when OpenAPI is enabled"""
        instance = patched_class()
        instance.enable_openapi = openapi_enabled
        
        view_func = Mock()
        view_func.view_class = TestMethodView
        
        instance.add_url_rule('/test', view_func=view_func)
        
        if openapi_enabled:
            assert hasattr(view_func, '_method_spec') or hasattr(view_func, '_spec')
        else:
            # When OpenAPI is disabled, spec recording shouldn't happen
            assert not hasattr(view_func, '_method_spec')
    
    def test_regular_function_passthrough(self, patched_class):
        """Test that regular functions are passed through unchanged"""
        instance = patched_class()
        instance.enable_openapi = True
        
        def regular_view():
            return 'response'
        
        instance.add_url_rule('/test', view_func=regular_view)
        
        # Should not have view class handling
        assert not hasattr(regular_view, '_method_spec')
        # Parent add_url_rule should be called
        assert instance.__class__.__bases__[0].add_url_rule.called
    
    @pytest.mark.parametrize("provide_automatic_options", [None, True, False])
    def test_provide_automatic_options_passthrough(self, patched_class, provide_automatic_options):
        """Test that provide_automatic_options is passed through correctly"""
        instance = patched_class()
        
        instance.add_url_rule('/test', view_func=lambda: None, 
                            provide_automatic_options=provide_automatic_options)
        
        # Check that parent was called with correct arguments
        call_args = instance.__class__.__bases__[0].add_url_rule.call_args
        assert call_args[1]['provide_automatic_options'] == provide_automatic_options
    
    def test_additional_options_passthrough(self, patched_class):
        """Test that additional options are passed through"""
        instance = patched_class()
        
        additional_options = {
            'methods': ['GET', 'POST'],
            'strict_slashes': False,
            'defaults': {'page': 1},
            'subdomain': 'api',
        }
        
        instance.add_url_rule('/test', view_func=lambda: None, **additional_options)
        
        # Check that parent was called with all options
        call_args = instance.__class__.__bases__[0].add_url_rule.call_args
        for key, value in additional_options.items():
            assert call_args[1][key] == value


class TestIntegrationWithAPIFlask:
    """Integration tests with actual APIFlask instances"""
    
    def test_apiflask_with_methodview(self, app):
        """Test APIFlask with MethodView integration"""
        @app.route('/api/resource')
        class ResourceAPI(MethodView):
            def get(self):
                return {'data': 'get'}
            
            def post(self):
                return {'data': 'post'}
        
        client = app.test_client()
        
        # Test GET
        rv = client.get('/api/resource')
        assert rv.status_code == 200
        assert rv.json == {'data': 'get'}
        
        # Test POST
        rv = client.post('/api/resource')
        assert rv.status_code == 200
        assert rv.json == {'data': 'post'}
    
    def test_apiflask_with_view(self, app):
        """Test APIFlask with regular View integration"""
        @app.route('/api/view')
        class BasicView(View):
            def dispatch_request(self):
                return {'data': 'view'}
        
        client = app.test_client()
        rv = client.get('/api/view')
        assert rv.status_code == 200
        assert rv.json == {'data': 'view'}
    
    def test_blueprint_with_methodview(self, app, blueprint):
        """Test APIBlueprint with MethodView integration"""
        @blueprint.route('/resource')
        class BlueprintResource(MethodView):
            def get(self):
                return {'source': 'blueprint'}
        
        app.register_blueprint(blueprint, url_prefix='/bp')
        client = app.test_client()
        
        rv = client.get('/bp/resource')
        assert rv.status_code == 200
        assert rv.json == {'source': 'blueprint'}
    
    @pytest.mark.parametrize("method,expected_status", [
        ('GET', 200),
        ('POST', 200),
        ('PUT', 405),  # Not implemented
        ('DELETE', 405),  # Not implemented
    ])
    def test_method_routing(self, app, method, expected_status):
        """Test that only implemented methods are routed"""
        @app.route('/limited')
        class LimitedAPI(MethodView):
            methods = ['GET', 'POST']
            
            def get(self):
                return {'method': 'get'}
            
            def post(self):
                return {'method': 'post'}
        
        client = app.test_client()
        rv = getattr(client, method.lower())('/limited')
        assert rv.status_code == expected_status


class TestOpenAPISpecGeneration:
    """Test OpenAPI spec generation for route_patch"""
    
    def test_methodview_openapi_spec(self, app):
        """Test that MethodView generates correct OpenAPI spec"""
        @app.route('/docs-test')
        class DocsAPI(MethodView):
            def get(self):
                """Retrieve documentation test
                
                This endpoint retrieves test documentation.
                """
                return {'doc': 'test'}
            
            def post(self):
                """Create documentation test"""
                return {'created': True}
        
        client = app.test_client()
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        
        spec = rv.json
        assert '/docs-test' in spec['paths']
        
        # Check GET spec
        get_spec = spec['paths']['/docs-test']['get']
        assert get_spec['summary'] == 'Retrieve documentation test'
        assert 'This endpoint retrieves test documentation.' in get_spec['description']
        
        # Check POST spec
        post_spec = spec['paths']['/docs-test']['post']
        assert post_spec['summary'] == 'Create documentation test'
    
    def test_view_hidden_from_openapi(self, app):
        """Test that regular View classes are hidden from OpenAPI"""
        @app.route('/hidden-view')
        class HiddenView(View):
            def dispatch_request(self):
                return {'hidden': True}
        
        client = app.test_client()
        rv = client.get('/openapi.json')
        assert rv.status_code == 200
        
        spec = rv.json
        assert '/hidden-view' not in spec['paths']
    
    def test_decorators_with_methodview(self, app):
        """Test that decorators work with MethodView"""
        from apiflask import input, output, doc
        
        @app.route('/decorated')
        class DecoratedAPI(MethodView):
            decorators = [doc(responses={404: 'Not found'})]
            
            @input(TestInputSchema)
            @output(TestOutputSchema)
            def post(self, json_data):
                return {'message': f"Hello {json_data['name']}", 'id': 1}
        
        client = app.test_client()
        
        # Test the endpoint
        rv = client.post('/decorated', json={'name': 'Test', 'age': 25})
        assert rv.status_code == 200
        assert rv.json['message'] == 'Hello Test'
        
        # Check OpenAPI spec
        rv = client.get('/openapi.json')
        spec = rv.json
        post_spec = spec['paths']['/decorated']['post']
        
        # Check that decorator specs are included
        assert '404' in post_spec['responses']
        assert 'requestBody' in post_spec
        assert '200' in post_spec['responses']


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
