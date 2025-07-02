"""Example test file that tests app.py with both implementations."""

import pytest
from unittest.mock import patch, MagicMock

from adapter import SchemaTypeAdapter
from settings_patch import use_schema_implementation, use_types_implementation


def test_app_output_decorator(openapi_schema_type_implementation):
    """Test app.output decorator with both implementations."""
    from apiflask import APIFlask
    from apiflask.schemas import Schema
    
    app = APIFlask(__name__)
    
    class TestSchema(Schema):
        pass
    
    # The fixture automatically handles switching implementation
    @app.get('/')
    @app.output(TestSchema)
    def index():
        return {'message': 'Hello, world!'}
    
    # Verify the function was decorated correctly
    assert hasattr(index, '_spec')
    assert 'response' in index._spec
    
    # Verify schema is handled correctly according to implementation
    response_schema = index._spec['response']['schema']
    assert SchemaTypeAdapter.is_valid_openapi_schema_type(response_schema)


def test_app_output_with_dict_schema(openapi_schema_type_implementation):
    """Test app.output decorator with dict schema in both implementations."""
    from apiflask import APIFlask
    
    app = APIFlask(__name__)
    
    test_dict_schema = {
        'type': 'object',
        'properties': {
            'message': {'type': 'string'}
        }
    }
    
    @app.get('/')
    @app.output(test_dict_schema)
    def index():
        return {'message': 'Hello, world!'}
    
    # Verify the function was decorated correctly
    assert hasattr(index, '_spec')
    assert 'response' in index._spec
    
    # Verify schema is handled correctly according to implementation
    response_schema = index._spec['response']['schema']
    assert SchemaTypeAdapter.is_valid_openapi_schema_type(response_schema)


# Test with manual context managers
def test_with_schema_implementation():
    """Test with schema implementation manually."""
    with use_schema_implementation():
        from apiflask.settings import VALIDATION_ERROR_SCHEMA
        assert SchemaTypeAdapter.is_valid_openapi_schema_type(VALIDATION_ERROR_SCHEMA)


def test_with_types_implementation():
    """Test with types implementation manually."""
    with use_types_implementation():
        from apiflask.settings import VALIDATION_ERROR_SCHEMA
        assert SchemaTypeAdapter.is_valid_openapi_schema_type(VALIDATION_ERROR_SCHEMA)


# Test app initialization
def test_app_initialization_with_both_implementations(openapi_schema_type_implementation):
    """Test app initialization with both implementations."""
    from apiflask import APIFlask
    
    app = APIFlask(__name__)
    
    # Test app config with appropriate schema types
    assert SchemaTypeAdapter.is_valid_openapi_schema_type(app.config['VALIDATION_ERROR_SCHEMA'])
    assert SchemaTypeAdapter.is_valid_openapi_schema_type(app.config['HTTP_ERROR_SCHEMA'])
