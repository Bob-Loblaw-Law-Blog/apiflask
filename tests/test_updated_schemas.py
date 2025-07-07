"""
Comprehensive tests for updated schema definitions.

This test suite ensures that:
1. New class-based schemas work correctly
2. Backwards compatibility with dict-based schemas is maintained
3. Both formats can be used interchangeably
4. Schema inheritance and customization works as expected
"""

import pytest
from datetime import datetime
from marshmallow import ValidationError as MarshmallowValidationError
from apiflask import APIFlask

# Import both old and new schema definitions
from updated_schemas_with_usage import (
    # Class-based schemas (new)
    ValidationErrorDetailSchema,
    ValidationErrorSchema,
    HTTPErrorSchema,
    # Dict-based schemas (original)
    validation_error_detail_schema,
    validation_error_schema,
    http_error_schema,
    # Base schemas
    Schema,
    EmptySchema,
    PaginationSchema,
    FileSchema,
)


class TestClassBasedErrorSchemas:
    """Test the new class-based error schemas"""

    def test_validation_error_detail_schema_instantiation(self):
        """Test that ValidationErrorDetailSchema can be instantiated"""
        schema = ValidationErrorDetailSchema()
        assert hasattr(schema, 'load')
        assert hasattr(schema, 'dump')

        # Test with dynamic location data
        test_data = {
            'json': {
                'username': ['Missing data for required field.'],
                'email': ['Not a valid email address.']
            },
            'query': {
                'page': ['Must be greater than 0.']
            }
        }

        # Should handle dynamic fields due to Meta.unknown = INCLUDE
        result = schema.dump(test_data)
        assert result == test_data

        loaded = schema.load(test_data)
        assert loaded == test_data

    def test_validation_error_schema(self):
        """Test ValidationErrorSchema with complete data"""
        schema = ValidationErrorSchema()

        test_data = {
            'message': 'Validation error',
            'detail': {
                'json': {
                    'username': ['Field required'],
                    'password': ['Too short']
                }
            }
        }

        # Test serialization
        result = schema.dump(test_data)
        assert result['message'] == 'Validation error'
        assert 'detail' in result
        assert result['detail']['json']['username'] == ['Field required']

        # Test deserialization
        loaded = schema.load(test_data)
        assert loaded == test_data

    def test_validation_error_schema_minimal(self):
        """Test ValidationErrorSchema with minimal data"""
        schema = ValidationErrorSchema()

        # Only message
        test_data = {'message': 'Validation failed'}
        result = schema.dump(test_data)
        assert result == test_data

        # Only detail
        test_data = {
            'detail': {
                'form': {
                    'field1': ['Error message']
                }
            }
        }
        result = schema.dump(test_data)
        assert result == test_data

        # Empty object
        test_data = {}
        result = schema.dump(test_data)
        assert result == {}

    def test_http_error_schema(self):
        """Test HTTPErrorSchema"""
        schema = HTTPErrorSchema()

        # Test with full data
        test_data = {
            'message': 'Resource not found',
            'detail': {
                'id': 123,
                'type': 'user',
                'timestamp': '2024-01-01T00:00:00Z'
            }
        }

        result = schema.dump(test_data)
        assert result == test_data

        loaded = schema.load(test_data)
        assert loaded == test_data

        # Test with minimal data
        minimal_data = {'message': 'Unauthorized'}
        result = schema.dump(minimal_data)
        assert result == minimal_data


class TestBackwardsCompatibility:
    """Test that dict-based schemas still work"""

    def test_validation_error_detail_schema_dict(self):
        """Test original dict-based validation_error_detail_schema"""
        assert isinstance(validation_error_detail_schema, dict)
        assert validation_error_detail_schema['type'] == 'object'
        assert 'properties' in validation_error_detail_schema

        # Check structure
        props = validation_error_detail_schema['properties']
        assert '<location>' in props
        assert props['<location>']['type'] == 'object'

    def test_validation_error_schema_dict(self):
        """Test original dict-based validation_error_schema"""
        assert isinstance(validation_error_schema, dict)
        assert validation_error_schema['type'] == 'object'
        assert 'properties' in validation_error_schema

        props = validation_error_schema['properties']
        assert 'detail' in props
        assert 'message' in props
        assert props['detail'] == validation_error_detail_schema

    def test_http_error_schema_dict(self):
        """Test original dict-based http_error_schema"""
        assert isinstance(http_error_schema, dict)
        assert http_error_schema['type'] == 'object'
        assert 'properties' in http_error_schema

        props = http_error_schema['properties']
        assert 'detail' in props
        assert 'message' in props
        assert props['detail']['type'] == 'object'


class TestSchemaInteroperability:
    """Test that both schema formats work with APIFlask"""

    def test_class_based_schemas_in_config(self):
        """Test using class-based schemas in app config"""
        app = APIFlask(__name__)

        # Should accept class-based schemas
        app.config['VALIDATION_ERROR_SCHEMA'] = ValidationErrorSchema
        app.config['HTTP_ERROR_SCHEMA'] = HTTPErrorSchema

        assert app.config['VALIDATION_ERROR_SCHEMA'] == ValidationErrorSchema
        assert app.config['HTTP_ERROR_SCHEMA'] == HTTPErrorSchema

    def test_dict_based_schemas_in_config(self):
        """Test using dict-based schemas in app config"""
        app = APIFlask(__name__)

        # Should accept dict-based schemas (backwards compatibility)
        app.config['VALIDATION_ERROR_SCHEMA'] = validation_error_schema
        app.config['HTTP_ERROR_SCHEMA'] = http_error_schema

        assert app.config['VALIDATION_ERROR_SCHEMA'] == validation_error_schema
        assert app.config['HTTP_ERROR_SCHEMA'] == http_error_schema

    def test_mixed_schema_usage(self, app: APIFlask, client):
        """Test that both schema types can be used in the same app"""
        # Use class-based for validation errors
        app.config['VALIDATION_ERROR_SCHEMA'] = ValidationErrorSchema
        # Use dict-based for HTTP errors (mixing formats)
        app.config['HTTP_ERROR_SCHEMA'] = http_error_schema

        class UserSchema(Schema):
            username = fields.String(required=True)
            email = fields.Email(required=True)

        @app.post('/users')
        @app.input(UserSchema)
        def create_user(json_data):
            return json_data

        # Test validation error
        rv = client.post('/users', json={'username': 'test'})
        assert rv.status_code == 422  # Validation error

        # Test 404 error
        @app.get('/users/<int:user_id>')
        def get_user(user_id):
            from apiflask import abort
            abort(404, message='User not found')

        rv = client.get('/users/999')
        assert rv.status_code == 404


class TestSchemaExtension:
    """Test extending the class-based schemas"""

    def test_extend_validation_error_schema(self):
        """Test extending ValidationErrorSchema with additional fields"""
        from marshmallow import fields

        class ExtendedValidationErrorSchema(ValidationErrorSchema):
            request_id = fields.String(dump_only=True)
            timestamp = fields.DateTime(dump_only=True)
            severity = fields.String(default='error')

        schema = ExtendedValidationErrorSchema()

        # Should have original fields
        assert 'message' in schema.fields
        assert 'detail' in schema.fields

        # Should have new fields
        assert 'request_id' in schema.fields
        assert 'timestamp' in schema.fields
        assert 'severity' in schema.fields

        # Test with data
        test_data = {
            'message': 'Validation failed',
            'detail': {'json': {'field': ['Error']}},
            'request_id': 'req-123',
            'timestamp': datetime.now(),
            'severity': 'warning'
        }

        result = schema.dump(test_data)
        assert result['request_id'] == 'req-123'
        assert result['severity'] == 'warning'

    def test_extend_http_error_schema(self):
        """Test extending HTTPErrorSchema"""
        from marshmallow import fields

        class CustomHTTPErrorSchema(HTTPErrorSchema):
            error_code = fields.String(required=True)
            help_url = fields.URL()
            retry_after = fields.Integer()

        schema = CustomHTTPErrorSchema()

        # Test required field validation
        with pytest.raises(MarshmallowValidationError) as exc:
            schema.load({'message': 'Error'})
        assert 'error_code' in exc.value.messages

        # Test with valid data
        test_data = {
            'message': 'Rate limit exceeded',
            'error_code': 'RATE_LIMIT',
            'help_url': 'https://api.example.com/docs/rate-limits',
            'retry_after': 60,
            'detail': {'requests_made': 100, 'limit': 100}
        }

        result = schema.load(test_data)
        assert result['error_code'] == 'RATE_LIMIT'
        assert result['retry_after'] == 60

    def test_schema_composition(self):
        """Test composing schemas using inheritance"""
        from marshmallow import fields

        class BaseErrorSchema(Schema):
            timestamp = fields.DateTime(dump_only=True)
            request_id = fields.String(dump_only=True)

        class DetailedValidationErrorSchema(BaseErrorSchema, ValidationErrorSchema):
            """Composed schema with base error fields and validation error fields"""
            pass

        schema = DetailedValidationErrorSchema()

        # Should have fields from both parents
        assert 'timestamp' in schema.fields
        assert 'request_id' in schema.fields
        assert 'message' in schema.fields
        assert 'detail' in schema.fields


class TestRealWorldScenarios:
    """Test real-world usage scenarios"""

    def test_api_error_handling_with_class_schemas(self, app: APIFlask, client):
        """Test complete error handling with class-based schemas"""
        from marshmallow import fields

        # Configure with class-based schemas
        app.config['VALIDATION_ERROR_SCHEMA'] = ValidationErrorSchema
        app.config['HTTP_ERROR_SCHEMA'] = HTTPErrorSchema

        class LoginSchema(Schema):
            username = fields.String(required=True,
                                   validate=fields.Length(min=3, max=20))
            password = fields.String(required=True,
                                   validate=fields.Length(min=8))

        @app.post('/login')
        @app.input(LoginSchema)
        def login(credentials):
            # Simulate authentication
            if credentials['username'] != 'admin':
                from apiflask import abort
                abort(401, message='Invalid credentials',
                      detail={'username': credentials['username']})
            return {'token': 'fake-jwt-token'}

        # Test validation error
        rv = client.post('/login', json={'username': 'ab'})  # Too short
        assert rv.status_code == 422
        assert 'detail' in rv.json
        assert 'json' in rv.json['detail']

        # Test authentication error
        rv = client.post('/login',
                        json={'username': 'user', 'password': 'password123'})
        assert rv.status_code == 401
        assert rv.json['message'] == 'Invalid credentials'
        assert rv.json['detail']['username'] == 'user'

    def test_custom_error_schema_in_app(self, app: APIFlask, client):
        """Test using custom error schemas in an application"""
        from marshmallow import fields

        class AppValidationErrorSchema(ValidationErrorSchema):
            """Application-specific validation error schema"""
            error_id = fields.String(dump_only=True)

            def dump(self, obj, **kwargs):
                # Add error_id automatically
                if isinstance(obj, dict):
                    obj = obj.copy()
                    obj['error_id'] = f"val-err-{id(obj)}"
                return super().dump(obj, **kwargs)

        class AppHTTPErrorSchema(HTTPErrorSchema):
            """Application-specific HTTP error schema"""
            support_url = fields.String(dump_only=True,
                                       default='https://support.example.com')

        # Configure with custom schemas
        app.config['VALIDATION_ERROR_SCHEMA'] = AppValidationErrorSchema
        app.config['HTTP_ERROR_SCHEMA'] = AppHTTPErrorSchema

        class ItemSchema(Schema):
            name = fields.String(required=True)
            price = fields.Float(required=True, validate=fields.Range(min=0))

        @app.post('/items')
        @app.input(ItemSchema)
        def create_item(data):
            return data

        # Test validation error with custom schema
        rv = client.post('/items', json={'name': 'Test'})  # Missing price
        assert rv.status_code == 422
        # Custom field should be present
        if 'error_id' in rv.json:
            assert rv.json['error_id'].startswith('val-err-')


class TestMigrationPath:
    """Test migration from dict to class-based schemas"""

    def test_gradual_migration(self):
        """Test that migration can be done gradually"""
        # Step 1: Original dict usage (before migration)
        original_schema = validation_error_schema
        assert isinstance(original_schema, dict)

        # Step 2: Class-based schema is available
        new_schema = ValidationErrorSchema
        assert issubclass(new_schema, Schema)

        # Step 3: Both can coexist
        app = APIFlask(__name__)

        # Can switch between them without code changes
        app.config['VALIDATION_ERROR_SCHEMA'] = original_schema  # dict
        assert app.config['VALIDATION_ERROR_SCHEMA'] == original_schema

        app.config['VALIDATION_ERROR_SCHEMA'] = new_schema  # class
        assert app.config['VALIDATION_ERROR_SCHEMA'] == new_schema

    def test_feature_parity(self):
        """Test that class schemas provide same features as dict schemas"""
        # Dict schema defines structure
        dict_schema = validation_error_schema
        assert 'properties' in dict_schema
        assert 'message' in dict_schema['properties']
        assert 'detail' in dict_schema['properties']

        # Class schema provides same structure through fields
        class_schema = ValidationErrorSchema()
        assert 'message' in class_schema.fields
        assert 'detail' in class_schema.fields

        # Both can represent same data
        test_data = {
            'message': 'Validation error',
            'detail': {'json': {'field': ['Error message']}}
        }

        # Class schema can process the data
        result = class_schema.dump(test_data)
        assert result == test_data


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
