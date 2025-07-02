"""Test harness for testing both OpenAPISchemaType implementations."""

import pytest
import unittest
from unittest.mock import patch

from adapter import SchemaTypeAdapter, using_schema_implementation, using_types_implementation

from apiflask.schemas import Schema, OpenAPISchemaType as SchemaOpenAPIType
from apiflask.types import OpenAPISchemaType as TypesOpenAPIType


class TestBothImplementations:
    """Base class for tests that need to run against both implementations."""
    
    def run_test_with_both_implementations(self, test_func):
        """Run the same test function with both implementations."""
        with using_types_implementation():
            print(f"Running test with types implementation: {test_func.__name__}")
            test_func()
        
        with using_schema_implementation():
            print(f"Running test with schema implementation: {test_func.__name__}")
            test_func()


class TestOpenAPISchemaTypeAdapter(TestBothImplementations):
    """Test the adapter itself."""
    
    def test_create_openapi_schema_type(self):
        """Test creating an OpenAPISchemaType with both implementations."""
        
        def test_impl():
            # Test with a Schema
            class TestSchema(Schema):
                pass
            
            test_schema = TestSchema()
            result = SchemaTypeAdapter.create_openapi_schema_type(test_schema)
            assert SchemaTypeAdapter.is_valid_openapi_schema_type(result)
            
            # Test with a dict
            test_dict = {'type': 'object', 'properties': {'name': {'type': 'string'}}}
            result = SchemaTypeAdapter.create_openapi_schema_type(test_dict)
            assert SchemaTypeAdapter.is_valid_openapi_schema_type(result)
            
            # Test with a Schema class
            result = SchemaTypeAdapter.create_openapi_schema_type(TestSchema)
            assert SchemaTypeAdapter.is_valid_openapi_schema_type(result)
        
        self.run_test_with_both_implementations(test_impl)


# Mock tests for scaffold functions
class TestScaffoldFunctions(TestBothImplementations):
    """Test scaffold functions with both implementations."""
    
    def test_jsonify_with_schema(self):
        """Test the _jsonify function works with both implementations."""
        
        def test_impl():
            from unittest.mock import MagicMock
            from apiflask.scaffold import _jsonify
            
            # Mock schema
            test_schema = MagicMock()
            test_schema.dump.return_value = {"name": "test"}
            
            # Mock current_app
            current_app = MagicMock()
            current_app.config = {
                'BASE_RESPONSE_SCHEMA': None,
                'BASE_RESPONSE_DATA_KEY': 'data'
            }
            
            with patch('apiflask.scaffold.current_app', current_app):
                result = _jsonify({"name": "test"}, test_schema)
                test_schema.dump.assert_called_once()
        
        # This test would need to be adapted to work with the actual scaffold code
        # self.run_test_with_both_implementations(test_impl)
        pass


# Example test for settings
@pytest.mark.parametrize('implementation', ['types', 'schema'])
def test_validation_error_schema(implementation):
    """Test validation_error_schema with both implementations."""
    if implementation == 'types':
        with using_types_implementation():
            from apiflask.settings import VALIDATION_ERROR_SCHEMA
            assert SchemaTypeAdapter.is_valid_openapi_schema_type(VALIDATION_ERROR_SCHEMA)
    else:
        with using_schema_implementation():
            from apiflask.settings import VALIDATION_ERROR_SCHEMA
            assert SchemaTypeAdapter.is_valid_openapi_schema_type(VALIDATION_ERROR_SCHEMA)


# Example of patching scaffold functions for testing
class TestScaffoldPatching:
    """Test patching scaffold functions for testing."""
    
    @patch('apiflask.scaffold.OpenAPISchemaType', new_callable=lambda: TypesOpenAPIType)
    def test_with_types_implementation(self, mock_schema_type):
        """Test with types implementation through patching."""
        from apiflask.scaffold import _jsonify
        # Your test here
        pass
    
    @patch('apiflask.scaffold.OpenAPISchemaType', new_callable=lambda: SchemaOpenAPIType)
    def test_with_schema_implementation(self, mock_schema_type):
        """Test with schema implementation through patching."""
        from apiflask.scaffold import _jsonify
        # Your test here
        pass


if __name__ == '__main__':
    unittest.main()
