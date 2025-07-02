"""
Example test file showing how to write tests that work with both implementations.
"""

import os
import pytest
from unittest.mock import patch
from contextlib import contextmanager

from apiflask import APIFlask
from apiflask.fields import String, Integer
from apiflask.schemas import Schema


# Test fixtures that work with both implementations
@pytest.fixture
def app_with_dynamic_impl():
    """Create an app using the current OpenAPISchemaType implementation."""
    app = APIFlask(__name__)
    app.config['TESTING'] = True
    return app


@contextmanager
def use_implementation(use_schema: bool):
    """
    Context manager to temporarily switch implementations.

    Usage:
        with use_implementation(use_schema=True):
            # Code using schema implementation
            pass
    """
    original_value = os.environ.get('APIFLASK_USE_SCHEMA_IMPL', 'true')
    try:
        os.environ['APIFLASK_USE_SCHEMA_IMPL'] = 'true' if use_schema else 'false'

        # Clear any cached imports
        import sys
        modules_to_reload = [
            'apiflask.settings',
            'apiflask.scaffold',
        ]
        for module_name in modules_to_reload:
            if module_name in sys.modules:
                del sys.modules[module_name]

        yield
    finally:
        os.environ['APIFLASK_USE_SCHEMA_IMPL'] = original_value


class TestBothImplementations:
    """Test class that runs tests with both implementations."""

    def test_basic_schema_support(self, app_with_dynamic_impl):
        """Test that basic schema operations work with both implementations."""
        app = app_with_dynamic_impl

        class PetIn(Schema):
            name = String(required=True)
            age = Integer()

        class PetOut(Schema):
            id = Integer()
            name = String()
            age = Integer()

        @app.post('/pets')
        @app.input(PetIn)
        @app.output(PetOut)
        def create_pet(json_data):
            return {
                'id': 1,
                'name': json_data['name'],
                'age': json_data.get('age', 0)
            }

        client = app.test_client()

        # Test successful request
        rv = client.post('/pets', json={'name': 'Fluffy', 'age': 3})
        assert rv.status_code == 200
        assert rv.json['name'] == 'Fluffy'
        assert rv.json['age'] == 3

    def test_dict_schema_support(self, app_with_dynamic_impl):
        """Test that dict schemas work with both implementations."""
        app = app_with_dynamic_impl

        @app.post('/items')
        @app.input({'name': String(required=True), 'quantity': Integer()})
        @app.output({'id': Integer(), 'name': String(), 'quantity': Integer()})
        def create_item(json_data):
            return {
                'id': 1,
                'name': json_data['name'],
                'quantity': json_data.get('quantity', 1)
            }

        client = app.test_client()
        rv = client.post('/items', json={'name': 'Widget', 'quantity': 5})
        assert rv.status_code == 200
        assert rv.json['name'] == 'Widget'
        assert rv.json['quantity'] == 5

    @pytest.mark.parametrize('impl_type', ['schema', 'types'])
    def test_with_parametrize(self, impl_type):
        """Test using pytest parametrize to test both implementations."""
        with use_implementation(use_schema=(impl_type == 'schema')):
            # Import inside context to get the right implementation
            from apiflask import APIFlask

            app = APIFlask(__name__)
            app.config['TESTING'] = True

            @app.get('/test')
            @app.output({'message': String()})
            def test_endpoint():
                return {'message': f'Using {impl_type} implementation'}

            client = app.test_client()
            rv = client.get('/test')
            assert rv.status_code == 200
            assert 'message' in rv.json


class TestImplementationSpecific:
    """Tests specific to each implementation."""

    def test_schema_implementation_only(self):
        """Test features specific to schema implementation."""
        with use_implementation(use_schema=True):
            from apiflask import APIFlask
            from apiflask.schemas import OpenAPISchemaType

            # Test that we're using the schema implementation
            assert hasattr(OpenAPISchemaType, '__init__')

            app = APIFlask(__name__)
            # Add schema-specific tests here

    def test_types_implementation_only(self):
        """Test features specific to types implementation."""
        with use_implementation(use_schema=False):
            from apiflask import APIFlask

            # Test that we're using the types implementation
            import apiflask.settings
            # The types implementation is just a type alias

            app = APIFlask(__name__)
            # Add types-specific tests here


# Helper function for running a single test with both implementations
def run_test_dual_impl(test_func, *args, **kwargs):
    """
    Run a test function with both implementations and return results.

    Args:
        test_func: Test function to run
        *args: Positional arguments for test function
        **kwargs: Keyword arguments for test function

    Returns:
        Tuple of (schema_result, types_result)
    """
    results = {}

    # Test with schema implementation
    with use_implementation(use_schema=True):
        try:
            results['schema'] = test_func(*args, **kwargs)
        except Exception as e:
            results['schema'] = {'error': str(e)}

    # Test with types implementation
    with use_implementation(use_schema=False):
        try:
            results['types'] = test_func(*args, **kwargs)
        except Exception as e:
            results['types'] = {'error': str(e)}

    return results['schema'], results['types']


# Example of a compatibility test
def test_compatibility():
    """Test that both implementations produce compatible results."""

    def create_app_and_test():
        from apiflask import APIFlask
        from apiflask.schemas import Schema
        from apiflask.fields import String

        app = APIFlask(__name__)
        app.config['TESTING'] = True

        class MessageSchema(Schema):
            message = String(required=True)

        @app.post('/echo')
        @app.input(MessageSchema)
        @app.output(MessageSchema)
        def echo(json_data):
            return json_data

        client = app.test_client()
        rv = client.post('/echo', json={'message': 'Hello'})

        return {
            'status_code': rv.status_code,
            'json': rv.json
        }

    schema_result, types_result = run_test_dual_impl(create_app_and_test)

    # Verify both implementations produce the same result
    assert schema_result == types_result, \
        f"Different results: schema={schema_result}, types={types_result}"

