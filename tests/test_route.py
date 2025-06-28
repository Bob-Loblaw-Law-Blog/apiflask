"""
Unit tests for the route module (route.py).

This module tests the routing logic, including:
- The route_patch decorator
- The add_url_rule method modifications
- Support for both MethodView and View classes
- Spec recording for view classes
- Various HTTP methods and edge cases
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from flask import Flask
from flask.views import MethodView, View

from apiflask import APIFlask, APIBlueprint
from apiflask.route import route_patch


# Test fixtures and helper classes
class TestMethodView(MethodView):
    """Test MethodView class with multiple HTTP methods."""

    def get(self):
        """GET method docstring."""
        return 'GET response'

    def post(self):
        """POST method docstring."""
        return 'POST response'

    def put(self):
        """PUT method docstring."""
        return 'PUT response'

    def delete(self):
        """DELETE method docstring."""
        return 'DELETE response'

    def patch(self):
        """PATCH method docstring."""
        return 'PATCH response'


class TestMethodViewWithDecorators(MethodView):
    """Test MethodView with decorator specs."""
    decorators = []

    def get(self):
        """GET method with existing spec."""
        return 'GET response'

    def post(self):
        """POST method with existing spec."""
        return 'POST response'


class TestView(View):
    """Test regular View class (not MethodView)."""
    methods = ['GET', 'POST']

    def dispatch_request(self):
        return 'View response'


class EmptyMethodView(MethodView):
    """MethodView with no methods defined."""
    pass


class CustomMethodView(MethodView):
    """MethodView with only specific methods."""

    def get(self):
        return 'GET only'


# Parametrized test data for view classes
VIEW_CLASSES = [
    pytest.param(TestMethodView, 'MethodView', id='method_view'),
    pytest.param(TestView, 'View', id='regular_view'),
]

HTTP_METHODS = [
    pytest.param('GET', id='get'),
    pytest.param('POST', id='post'),
    pytest.param('PUT', id='put'),
    pytest.param('DELETE', id='delete'),
    pytest.param('PATCH', id='patch'),
    pytest.param('HEAD', id='head'),
    pytest.param('OPTIONS', id='options'),
]


class TestRoutePatchDecorator:
    """Test the route_patch decorator functionality."""

    def test_route_patch_adds_add_url_rule_method(self):
        """Test that route_patch adds the add_url_rule method to a class."""

        @route_patch
        class TestClass:
            pass

        assert hasattr(TestClass, 'add_url_rule')
        assert callable(TestClass.add_url_rule)

    def test_route_patch_preserves_class_attributes(self):
        """Test that route_patch preserves existing class attributes."""

        @route_patch
        class TestClass:
            existing_attr = 'test_value'

            def existing_method(self):
                return 'existing'

        assert hasattr(TestClass, 'existing_attr')
        assert TestClass.existing_attr == 'test_value'
        assert hasattr(TestClass, 'existing_method')
        assert callable(TestClass.existing_method)

    def test_route_patch_on_apiflask(self):
        """Test that APIFlask has the patched add_url_rule method."""
        app = APIFlask(__name__)
        assert hasattr(app, 'add_url_rule')
        assert callable(app.add_url_rule)

    def test_route_patch_on_apiblueprint(self):
        """Test that APIBlueprint has the patched add_url_rule method."""
        bp = APIBlueprint('test', __name__)
        assert hasattr(bp, 'add_url_rule')
        assert callable(bp.add_url_rule)


class TestAddUrlRule:
    """Test the patched add_url_rule method functionality."""

    @pytest.fixture
    def app(self):
        """Create a test APIFlask application."""
        return APIFlask(__name__)

    @pytest.fixture
    def blueprint(self):
        """Create a test APIBlueprint."""
        return APIBlueprint('test_bp', __name__)

    @pytest.mark.parametrize('view_class,class_type', VIEW_CLASSES)
    def test_add_url_rule_with_view_class(self, app, view_class, class_type):
        """Test add_url_rule with different view class types."""
        # Test passing view class directly
        app.add_url_rule('/test', view_func=view_class)

        # Check that the route was added
        assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]

    def test_add_url_rule_with_view_class_as_view(self, app):
        """Test add_url_rule with view class created by as_view()."""
        view_func = TestMethodView.as_view('test_view')
        app.add_url_rule('/test', view_func=view_func)

        # Check that the route was added
        assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]

    def test_add_url_rule_with_regular_function(self, app):
        """Test add_url_rule with a regular function."""
        def test_func():
            return 'test'

        app.add_url_rule('/test', view_func=test_func)

        # Check that the route was added
        assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]

    def test_add_url_rule_with_endpoint_name(self, app):
        """Test add_url_rule with custom endpoint name."""
        app.add_url_rule('/test', endpoint='custom_endpoint',
                        view_func=TestMethodView)

        # Check that the endpoint was set correctly
        assert 'custom_endpoint' in app.view_functions

    def test_add_url_rule_without_endpoint_uses_class_name(self, app):
        """Test that endpoint defaults to class name when not provided."""
        app.add_url_rule('/test', view_func=TestMethodView)

        # Check that the endpoint was set to class name
        assert 'TestMethodView' in app.view_functions

    @pytest.mark.parametrize('method', HTTP_METHODS)
    def test_add_url_rule_with_methods_option(self, app, method):
        """Test add_url_rule with specific HTTP methods."""
        def test_func():
            return 'test'

        app.add_url_rule('/test', view_func=test_func, methods=[method])

        # Check that the route accepts the specified method
        rules = [rule for rule in app.url_map.iter_rules() if rule.rule == '/test']
        assert len(rules) == 1
        assert method in rules[0].methods

    def test_add_url_rule_with_provide_automatic_options(self, app):
        """Test add_url_rule with provide_automatic_options parameter."""
        def test_func():
            return 'test'

        app.add_url_rule('/test', view_func=test_func,
                        provide_automatic_options=False)

        # Check that the route was added
        assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]

    def test_add_url_rule_with_additional_options(self, app):
        """Test add_url_rule with additional keyword arguments."""
        def test_func():
            return 'test'

        app.add_url_rule('/test', view_func=test_func,
                        strict_slashes=False,
                        defaults={'key': 'value'})

        # Check that the route was added with options
        rules = [rule for rule in app.url_map.iter_rules() if rule.rule == '/test']
        assert len(rules) == 1


class TestSpecRecording:
    """Test spec recording for view classes."""

    @pytest.fixture
    def app(self):
        """Create a test APIFlask application with OpenAPI enabled."""
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        return app

    def test_spec_recording_for_method_view(self, app):
        """Test that spec is recorded for MethodView classes."""
        view_func = TestMethodView.as_view('test_view')

        # Add the route
        app.add_url_rule('/test', view_func=view_func)

        # Check that spec was recorded
        assert hasattr(view_func, '_method_spec')
        assert isinstance(view_func._method_spec, dict)

        # Check that specs were recorded for each method
        for method in ['GET', 'POST', 'PUT', 'DELETE', 'PATCH']:
            assert method in view_func._method_spec
            assert 'summary' in view_func._method_spec[method]
            assert 'description' in view_func._method_spec[method]

    def test_spec_not_recorded_for_regular_view(self, app):
        """Test that spec is not recorded for regular View classes."""
        view_func = TestView.as_view('test_view')

        # Add the route
        app.add_url_rule('/test', view_func=view_func)

        # Check that spec was marked as hidden
        assert hasattr(view_func, '_spec')
        assert view_func._spec.get('hide') is True

    def test_spec_recording_with_existing_spec(self, app):
        """Test spec recording when view already has spec attributes."""
        view_func = TestMethodViewWithDecorators.as_view('test_view')

        # Add some existing spec
        view_func._spec = {'summary': 'Existing summary', 'tags': ['test']}

        # Add the route
        app.add_url_rule('/test', view_func=view_func)

        # Check that existing spec is preserved
        assert hasattr(view_func, '_method_spec')
        for method in ['GET', 'POST']:
            if method in view_func._method_spec:
                method_spec = view_func._method_spec[method]
                assert 'tags' in method_spec
                assert method_spec['tags'] == ['test']

    def test_spec_recording_only_once(self, app):
        """Test that spec is only recorded once for multiple add_url_rule calls."""
        view_func = TestMethodView.as_view('test_view')

        # Add the route multiple times
        app.add_url_rule('/test1', view_func=view_func)
        app.add_url_rule('/test2', view_func=view_func)

        # Mock the recording function to check it's not called twice
        with patch('apiflask.route.record_spec_for_view_class') as mock_record:
            app.add_url_rule('/test3', view_func=view_func)
            # Should not be called because _method_spec already exists
            mock_record.assert_not_called()

    def test_spec_recording_with_no_methods(self, app):
        """Test spec recording for MethodView with no methods defined."""
        view_func = EmptyMethodView.as_view('empty_view')

        # Add the route
        app.add_url_rule('/test', view_func=view_func)

        # Check that spec was recorded but empty
        assert hasattr(view_func, '_method_spec')
        assert view_func._method_spec == {}

    def test_generated_summary_and_description(self, app):
        """Test that summary and description are auto-generated correctly."""
        view_func = TestMethodView.as_view('test_view')

        # Add the route
        app.add_url_rule('/test', view_func=view_func)

        # Check generated summary
        assert 'Get TestMethodView' in view_func._method_spec['GET']['summary']
        assert 'Post TestMethodView' in view_func._method_spec['POST']['summary']

        # Check that generated flags are set
        assert view_func._method_spec['GET']['generated_summary'] is True
        assert view_func._method_spec['GET']['generated_description'] is True

    def test_spec_recording_with_disabled_openapi(self):
        """Test that spec is not recorded when OpenAPI is disabled."""
        # Create app with OpenAPI disabled
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        app.enable_openapi = False

        view_func = TestMethodView.as_view('test_view')

        # Add the route
        app.add_url_rule('/test', view_func=view_func)

        # Check that spec was not recorded
        assert not hasattr(view_func, '_method_spec') or view_func._method_spec == {}


class TestBlueprintRouting:
    """Test routing with APIBlueprint."""

    @pytest.fixture
    def app(self):
        """Create a test APIFlask application."""
        return APIFlask(__name__)

    @pytest.fixture
    def blueprint(self):
        """Create a test APIBlueprint."""
        return APIBlueprint('test_bp', __name__)

    @pytest.mark.parametrize('view_class,class_type', VIEW_CLASSES)
    def test_blueprint_add_url_rule_with_view_class(self, app, blueprint, view_class, class_type):
        """Test blueprint add_url_rule with different view class types."""
        blueprint.add_url_rule('/test', view_func=view_class)
        app.register_blueprint(blueprint)

        # Check that the route was added
        assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]

    def test_blueprint_with_url_prefix(self, app, blueprint):
        """Test blueprint routing with URL prefix."""
        blueprint.add_url_rule('/test', view_func=TestMethodView)
        app.register_blueprint(blueprint, url_prefix='/api')

        # Check that the route was added with prefix
        assert '/api/test' in [rule.rule for rule in app.url_map.iter_rules()]

    def test_blueprint_with_disabled_openapi(self, app):
        """Test blueprint with OpenAPI disabled."""
        blueprint = APIBlueprint('test_bp', __name__, enable_openapi=False)
        view_func = TestMethodView.as_view('test_view')

        blueprint.add_url_rule('/test', view_func=view_func)
        app.register_blueprint(blueprint)

        # The view should still work but no OpenAPI spec should be generated
        assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]


class TestEdgeCases:
    """Test edge cases and error scenarios."""

    @pytest.fixture
    def app(self):
        """Create a test APIFlask application."""
        return APIFlask(__name__)

    def test_add_url_rule_with_none_view_func(self, app):
        """Test add_url_rule with None as view_func."""
        # This should work - Flask allows registering rules without view funcs
        app.add_url_rule('/test', endpoint='test_endpoint', view_func=None)

        # The rule should be added but no view function registered
        assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]

    def test_add_url_rule_with_invalid_view_class(self, app):
        """Test add_url_rule with invalid view class."""
        class NotAView:
            """Not a valid view class."""
            pass

        # This should raise an error when trying to call as_view
        with pytest.raises(AttributeError):
            app.add_url_rule('/test', view_func=NotAView)

    def test_method_view_with_lowercase_methods(self, app):
        """Test MethodView with methods defined in lowercase."""
        class LowercaseMethodView(MethodView):
            # This is unusual but should be handled
            methods = ['get', 'post']  # lowercase

            def get(self):
                return 'GET'

            def post(self):
                return 'POST'

        # The methods should still be recognized
        view_func = LowercaseMethodView.as_view('lowercase_view')
        app.add_url_rule('/test', view_func=view_func)

        # Should work without errors
        assert '/test' in [rule.rule for rule in app.url_map.iter_rules()]

    def test_view_class_with_custom_as_view(self, app):
        """Test view class with custom as_view implementation."""
        class CustomView(MethodView):
            @classmethod
            def as_view(cls, name, *args, **kwargs):
                # Custom as_view that adds extra attributes
                view = super().as_view(name, *args, **kwargs)
                view.custom_attr = 'custom_value'
                return view

            def get(self):
                return 'GET'

        view_func = CustomView.as_view('custom_view')
        app.add_url_rule('/test', view_func=view_func)

        # Check custom attribute is preserved
        assert hasattr(view_func, 'custom_attr')
        assert view_func.custom_attr == 'custom_value'

    def test_multiple_routes_same_view_class(self, app):
        """Test multiple routes using the same view class."""
        # Register same view class with different endpoints
        app.add_url_rule('/test1', endpoint='endpoint1', view_func=TestMethodView)
        app.add_url_rule('/test2', endpoint='endpoint2', view_func=TestMethodView)

        # Both routes should work
        assert '/test1' in [rule.rule for rule in app.url_map.iter_rules()]
        assert '/test2' in [rule.rule for rule in app.url_map.iter_rules()]

        # Different endpoints should be created
        assert 'endpoint1' in app.view_functions
        assert 'endpoint2' in app.view_functions


class TestIntegrationWithDecorators:
    """Test integration with APIFlask decorators."""

    @pytest.fixture
    def app(self):
        """Create a test APIFlask application."""
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()

    def test_method_view_with_route_decorator(self, app, client):
        """Test MethodView with @app.route decorator."""
        @app.route('/test')
        class TestView(MethodView):
            def get(self):
                return {'message': 'GET'}

            def post(self):
                return {'message': 'POST'}

        # Test GET request
        rv = client.get('/test')
        assert rv.status_code == 200
        assert rv.json['message'] == 'GET'

        # Test POST request
        rv = client.post('/test')
        assert rv.status_code == 200
        assert rv.json['message'] == 'POST'

    def test_view_with_route_decorator(self, app, client):
        """Test regular View with @app.route decorator."""
        @app.route('/test')
        class RegularView(View):
            methods = ['GET', 'POST']

            def dispatch_request(self):
                return {'message': 'View'}

        # Test GET request
        rv = client.get('/test')
        assert rv.status_code == 200
        assert rv.json['message'] == 'View'

        # Test POST request
        rv = client.post('/test')
        assert rv.status_code == 200
        assert rv.json['message'] == 'View'

    @pytest.mark.parametrize('method', ['GET', 'POST', 'PUT', 'DELETE', 'PATCH'])
    def test_method_view_all_methods(self, app, client, method):
        """Test MethodView with all standard HTTP methods."""
        @app.route('/test')
        class AllMethodsView(MethodView):
            def get(self):
                return {'method': 'GET'}

            def post(self):
                return {'method': 'POST'}

            def put(self):
                return {'method': 'PUT'}

            def delete(self):
                return {'method': 'DELETE'}

            def patch(self):
                return {'method': 'PATCH'}

        # Make request with the specified method
        rv = getattr(client, method.lower())('/test')
        assert rv.status_code == 200
        assert rv.json['method'] == method


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
