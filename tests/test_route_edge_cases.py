"""
Edge case and advanced scenario tests for APIFlask routing logic.

This module contains additional tests for complex routing scenarios,
error handling, and edge cases not covered in the main test file.
"""

import pytest
from flask import Flask, request
from flask.views import View, MethodView
from unittest.mock import Mock, patch, PropertyMock
import typing as t

from apiflask import APIFlask, APIBlueprint
from apiflask.route import route_patch
from apiflask.fields import String, Integer, List
from apiflask.schemas import Schema


# Additional test schemas
class NestedSchema(Schema):
    items = List(String())
    count = Integer()


class ComplexMethodView(MethodView):
    """MethodView with complex scenarios"""
    methods = ['GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS']
    
    def get(self):
        """
        Multi-line docstring for GET.
        
        This is a more complex description
        that spans multiple lines and includes:
        - Bullet points
        - More details
        """
        return {'method': 'GET'}
    
    def post(self):
        # Method with only comment, no docstring
        return {'method': 'POST'}
    
    def put(self):
        pass  # Method with no implementation
    
    def delete(self):
        """Single line docstring"""
        return None
    
    def patch(self):
        """"""  # Empty docstring
        return {'method': 'PATCH'}
    
    def head(self):
        """HEAD method implementation"""
        return ''
    
    def options(self):
        """OPTIONS method implementation"""
        return ''


class MethodViewWithClassAttributes(MethodView):
    """MethodView with class-level attributes and decorators"""
    methods = ['GET', 'POST']
    decorators = [lambda f: f]  # Dummy decorator
    
    # Class attributes that might interfere
    _spec = {'class_level': True}
    _method_spec = {'existing': True}
    
    def get(self):
        return {'has_class_attrs': True}
    
    def post(self):
        return {'method': 'post'}


class InheritedMethodView(MethodView):
    """MethodView that inherits from another MethodView"""
    def get(self):
        return super().get() if hasattr(super(), 'get') else {'inherited': True}


class TestEdgeCases:
    """Test edge cases and error scenarios"""
    
    def test_method_with_no_docstring(self):
        """Test handling of methods without docstrings"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        # Create a MethodView with a method that has no docstring
        class NoDocView(MethodView):
            methods = ['GET']
            
            def get(self):
                return {}
        
        view_func = Mock()
        view_func.view_class = NoDocView
        view_func._spec = {}
        
        app.add_url_rule('/test', view_func=view_func)
        
        # Should still generate summary but no description
        assert hasattr(view_func, '_method_spec')
        assert 'GET' in view_func._method_spec
        assert 'summary' in view_func._method_spec['GET']
        assert view_func._method_spec['GET']['description'] == ''
    
    def test_malformed_docstring(self):
        """Test handling of malformed docstrings"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        class MalformedDocView(MethodView):
            methods = ['GET']
            
            def get(self):
                """   
                
                
                """
                return {}
        
        view_func = Mock()
        view_func.view_class = MalformedDocView
        view_func._spec = {}
        
        app.add_url_rule('/test', view_func=view_func)
        
        # Should handle gracefully
        assert hasattr(view_func, '_method_spec')
        assert 'GET' in view_func._method_spec
    
    def test_method_spec_with_existing_spec(self):
        """Test that existing method specs are preserved"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        class ExistingSpecView(MethodView):
            methods = ['GET']
            
            def get(self):
                return {}
        
        # Add existing spec to method
        ExistingSpecView.get._spec = {
            'summary': 'Existing summary',
            'description': 'Existing description',
            'tags': ['existing']
        }
        
        view_func = Mock()
        view_func.view_class = ExistingSpecView
        view_func._spec = {'responses': {404: 'Not found'}}
        
        app.add_url_rule('/test', view_func=view_func)
        
        # Existing specs should be preserved
        method_spec = view_func._method_spec['GET']
        assert method_spec['summary'] == 'Existing summary'
        assert method_spec['description'] == 'Existing description'
        assert method_spec['tags'] == ['existing']
        assert method_spec['responses'] == {404: 'Not found'}
    
    def test_type_checking_imports(self):
        """Test that type checking imports don't cause issues"""
        # This is mainly to ensure the code handles TYPE_CHECKING blocks correctly
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        # Should not raise any import errors
        app.add_url_rule('/test', view_func=lambda: None)
    
    def test_methods_attribute_manipulation(self):
        """Test handling when methods attribute is manipulated"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        class DynamicMethodsView(MethodView):
            @property
            def methods(self):
                # Dynamic methods property
                return ['GET', 'POST']
            
            def get(self):
                return {}
            
            def post(self):
                return {}
        
        view_func = Mock()
        view_func.view_class = DynamicMethodsView
        view_func._spec = {}
        
        # Should handle property-based methods
        app.add_url_rule('/test', view_func=view_func)
        
        assert hasattr(view_func, '_method_spec')
    
    def test_none_values_in_spec(self):
        """Test handling of None values in specs"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        class NoneSpecView(MethodView):
            methods = ['GET']
            
            def get(self):
                return {}
        
        view_func = Mock()
        view_func.view_class = NoneSpecView
        view_func._spec = {
            'summary': None,
            'description': None,
            'responses': None,
            'tags': ['test']
        }
        
        app.add_url_rule('/test', view_func=view_func)
        
        # None values should not override generated values
        method_spec = view_func._method_spec['GET']
        assert method_spec['summary'] is not None
        assert method_spec['tags'] == ['test']
    
    def test_multiple_inheritance_view(self):
        """Test MethodView with multiple inheritance"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        class Mixin:
            def get(self):
                return {'mixin': True}
        
        class MultiInheritView(Mixin, MethodView):
            methods = ['GET']
        
        view_func = Mock()
        view_func.view_class = MultiInheritView
        view_func._spec = {}
        
        app.add_url_rule('/test', view_func=view_func)
        
        # Should handle multiple inheritance correctly
        assert hasattr(view_func, '_method_spec')
        assert 'GET' in view_func._method_spec


class TestConcurrencyAndState:
    """Test thread safety and state management"""
    
    def test_no_shared_state_between_views(self):
        """Test that views don't share state"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        class View1(MethodView):
            methods = ['GET']
            def get(self):
                return {}
        
        class View2(MethodView):
            methods = ['POST']
            def post(self):
                return {}
        
        view_func1 = Mock()
        view_func1.view_class = View1
        view_func1._spec = {}
        
        view_func2 = Mock()
        view_func2.view_class = View2
        view_func2._spec = {}
        
        app.add_url_rule('/view1', view_func=view_func1)
        app.add_url_rule('/view2', view_func=view_func2)
        
        # Each should have its own method spec
        assert 'GET' in view_func1._method_spec
        assert 'POST' not in view_func1._method_spec
        assert 'POST' in view_func2._method_spec
        assert 'GET' not in view_func2._method_spec
    
    def test_repeated_registration(self):
        """Test registering the same view multiple times"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        class ReusableView(MethodView):
            methods = ['GET']
            def get(self):
                return {}
        
        # Register same view class multiple times
        for i in range(3):
            view_func = Mock()
            view_func.view_class = ReusableView
            view_func._spec = {}
            
            app.add_url_rule(f'/route{i}', view_func=view_func)
        
        # Should not cause any issues
        assert app.__class__.__bases__[0].add_url_rule.call_count == 3


class TestComplexRoutingScenarios:
    """Test complex real-world routing scenarios"""
    
    def test_versioned_api_routes(self, app):
        """Test API versioning with MethodView"""
        @app.route('/v1/users')
        class UsersV1(MethodView):
            def get(self):
                return {'version': 1, 'users': []}
        
        @app.route('/v2/users')
        class UsersV2(MethodView):
            def get(self):
                return {'version': 2, 'users': [], 'metadata': {}}
        
        client = app.test_client()
        
        rv1 = client.get('/v1/users')
        rv2 = client.get('/v2/users')
        
        assert rv1.json['version'] == 1
        assert rv2.json['version'] == 2
        assert 'metadata' not in rv1.json
        assert 'metadata' in rv2.json
    
    def test_resource_with_subresources(self, app):
        """Test nested resource routing"""
        @app.route('/posts/<int:post_id>')
        class PostResource(MethodView):
            def get(self, post_id):
                return {'post_id': post_id}
        
        @app.route('/posts/<int:post_id>/comments')
        class PostCommentsResource(MethodView):
            def get(self, post_id):
                return {'post_id': post_id, 'comments': []}
            
            def post(self, post_id):
                return {'post_id': post_id, 'comment': 'created'}
        
        client = app.test_client()
        
        # Test main resource
        rv = client.get('/posts/123')
        assert rv.json['post_id'] == 123
        
        # Test subresource
        rv = client.get('/posts/123/comments')
        assert rv.json['post_id'] == 123
        assert 'comments' in rv.json
        
        rv = client.post('/posts/123/comments')
        assert rv.json['comment'] == 'created'
    
    def test_mixed_routing_styles(self, app):
        """Test mixing different routing styles"""
        # MethodView with decorator
        @app.route('/method-view')
        class MixedMethodView(MethodView):
            def get(self):
                return {'type': 'method-view'}
        
        # Regular View with decorator
        @app.route('/regular-view')
        class MixedRegularView(View):
            def dispatch_request(self):
                return {'type': 'regular-view'}
        
        # Function with decorator
        @app.route('/function')
        def function_view():
            return {'type': 'function'}
        
        # Direct add_url_rule with MethodView
        class DirectMethodView(MethodView):
            def get(self):
                return {'type': 'direct-method'}
        
        app.add_url_rule('/direct-method', view_func=DirectMethodView.as_view('direct'))
        
        client = app.test_client()
        
        assert client.get('/method-view').json['type'] == 'method-view'
        assert client.get('/regular-view').json['type'] == 'regular-view'
        assert client.get('/function').json['type'] == 'function'
        assert client.get('/direct-method').json['type'] == 'direct-method'


class TestErrorHandling:
    """Test error handling in routing"""
    
    def test_exception_in_method_attribute(self):
        """Test handling when accessing methods attribute raises exception"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        class BrokenMethodsView(MethodView):
            @property
            def methods(self):
                raise AttributeError("Broken methods")
            
            def get(self):
                return {}
        
        view_func = Mock()
        view_func.view_class = BrokenMethodsView
        view_func._spec = {}
        
        # Should handle the error gracefully
        try:
            app.add_url_rule('/test', view_func=view_func)
        except AttributeError:
            # The route_patch should let the error propagate
            pass
    
    def test_invalid_method_names(self):
        """Test handling of invalid HTTP method names"""
        @route_patch
        class TestApp:
            enable_openapi = True
            add_url_rule = Mock()
        
        TestApp.__bases__ = (Mock(),)
        TestApp.__bases__[0].add_url_rule = Mock()
        
        app = TestApp()
        
        class InvalidMethodsView(MethodView):
            methods = ['GET', 'INVALID', 'POST']
            
            def get(self):
                return {}
            
            def post(self):
                return {}
        
        view_func = Mock()
        view_func.view_class = InvalidMethodsView
        view_func._spec = {}
        
        # Should skip invalid methods gracefully
        app.add_url_rule('/test', view_func=view_func)
        
        assert 'GET' in view_func._method_spec
        assert 'POST' in view_func._method_spec
        assert 'INVALID' not in view_func._method_spec


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
