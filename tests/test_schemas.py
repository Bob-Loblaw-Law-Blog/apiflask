"""
Comprehensive unit tests for APIFlask schemas.

This module provides complete test coverage for the schemas module including:
- EmptySchema validation and usage
- FileSchema with different formats and types
- PaginationSchema field validation
- Schema base class functionality
- Error schemas (validation_error_schema, http_error_schema)
- Edge cases and error handling
"""

import io
import pytest
from typing import Any
from marshmallow import ValidationError, fields
from werkzeug.datastructures import FileStorage
import openapi_spec_validator as osv
from flask import make_response, send_file

from apiflask import APIFlask, Schema
from apiflask.schemas import (
    EmptySchema,
    FileSchema,
    PaginationSchema,
    validation_error_schema,
    http_error_schema,
    validation_error_detail_schema
)
from apiflask.fields import Integer, String, URL, File


class TestEmptySchema:
    """Test EmptySchema functionality"""

    def test_empty_schema_204_response(self, app: APIFlask, client):
        """Test EmptySchema with 204 No Content response"""
        @app.delete('/resource/<int:id>')
        @app.output(EmptySchema, status_code=204)
        def delete_resource(id):
            return ''

        rv = client.delete('/resource/123')
        assert rv.status_code == 204
        assert rv.data == b''
        assert rv.content_length == None

    def test_empty_schema_200_response(self, app: APIFlask, client):
        """Test EmptySchema with 200 OK response generates empty schema"""
        @app.post('/clear')
        @app.output(EmptySchema)
        def clear_data():
            return ''

        rv = client.post('/clear')
        assert rv.status_code == 200

        # Check OpenAPI spec
        rv_spec = client.get('/openapi.json')
        assert rv_spec.status_code == 200
        response_spec = rv_spec.json['paths']['/clear']['post']['responses']['200']
        assert 'content' in response_spec
        assert response_spec['content']['application/json']['schema'] == {}

    def test_empty_schema_dict_equivalent(self, app: APIFlask, client):
        """Test that EmptySchema is equivalent to using empty dict"""
        @app.delete('/foo')
        @app.output(EmptySchema, status_code=204)
        def delete_foo():
            return ''

        @app.delete('/bar')
        @app.output({}, status_code=204)
        def delete_bar():
            return ''

        rv_spec = client.get('/openapi.json')
        assert rv_spec.status_code == 200

        foo_spec = rv_spec.json['paths']['/foo']['delete']['responses']['204']
        bar_spec = rv_spec.json['paths']['/bar']['delete']['responses']['204']

        assert foo_spec == bar_spec
        assert 'content' not in foo_spec
        assert 'content' not in bar_spec

    def test_empty_schema_with_content_type(self, app: APIFlask, client):
        """Test EmptySchema with custom content type"""
        @app.get('/empty-image')
        @app.output(EmptySchema, content_type='image/png')
        def get_empty_image():
            return ''

        rv = client.get('/empty-image')
        assert rv.status_code == 200

        rv_spec = client.get('/openapi.json')
        response_spec = rv_spec.json['paths']['/empty-image']['get']['responses']['200']
        assert 'image/png' in response_spec['content']
        assert response_spec['content']['image/png']['schema'] == {}

    def test_empty_schema_inheritance(self):
        """Test that EmptySchema inherits from Schema correctly"""
        assert issubclass(EmptySchema, Schema)

        # Test instantiation
        empty = EmptySchema()
        assert hasattr(empty, 'load')
        assert hasattr(empty, 'dump')
        assert hasattr(empty, 'fields')
        assert len(empty.fields) == 0


class TestFileSchema:
    """Test FileSchema functionality"""

    def test_file_schema_basic(self, app: APIFlask, client):
        """Test basic FileSchema usage"""
        @app.get('/download')
        @app.output(
            FileSchema(),
            content_type='application/pdf',
            description='A PDF file'
        )
        def download_file():
            return send_file(io.BytesIO(b'PDF content'), mimetype='application/pdf')

        rv = client.get('/download')
        assert rv.status_code == 200
        assert rv.content_type == 'application/pdf'

    def test_file_schema_binary_format(self, app: APIFlask, client):
        """Test FileSchema with binary format (default)"""
        @app.get('/image')
        @app.output(
            FileSchema(type='string', format='binary'),
            content_type='image/jpeg'
        )
        def get_image():
            return send_file(io.BytesIO(b'JPEG data'), mimetype='image/jpeg')

        rv_spec = client.get('/openapi.json')
        content = rv_spec.json['paths']['/image']['get']['responses']['200']['content']
        assert 'image/jpeg' in content
        assert content['image/jpeg']['schema'] == {'type': 'string', 'format': 'binary'}

    def test_file_schema_base64_format(self, app: APIFlask, client):
        """Test FileSchema with base64 format"""
        @app.get('/encoded-file')
        @app.output(
            FileSchema(type='string', format='base64'),
            content_type='application/octet-stream'
        )
        def get_encoded_file():
            return 'base64encodedcontent'

        rv_spec = client.get('/openapi.json')
        content = rv_spec.json['paths']['/encoded-file']['get']['responses']['200']['content']
        assert 'application/octet-stream' in content
        assert content['application/octet-stream']['schema'] == {'type': 'string', 'format': 'base64'}

    def test_file_schema_repr(self):
        """Test FileSchema string representation"""
        # Test default values
        f1 = FileSchema()
        assert repr(f1) == 'schema: \n  type: string\n  format: binary'

        # Test custom values
        f2 = FileSchema(type='string', format='base64')
        assert repr(f2) == 'schema: \n  type: string\n  format: base64'

    def test_file_schema_multiple_endpoints(self, app: APIFlask, client):
        """Test FileSchema used in multiple endpoints with different content types"""
        file_schema = FileSchema()

        @app.get('/download/pdf')
        @app.output(file_schema, content_type='application/pdf')
        def download_pdf():
            return send_file(io.BytesIO(b'PDF'), mimetype='application/pdf')

        @app.get('/download/zip')
        @app.output(file_schema, content_type='application/zip')
        def download_zip():
            return send_file(io.BytesIO(b'ZIP'), mimetype='application/zip')

        rv_spec = client.get('/openapi.json')
        pdf_content = rv_spec.json['paths']['/download/pdf']['get']['responses']['200']['content']
        zip_content = rv_spec.json['paths']['/download/zip']['get']['responses']['200']['content']

        assert 'application/pdf' in pdf_content
        assert 'application/zip' in zip_content
        assert pdf_content['application/pdf']['schema'] == {'type': 'string', 'format': 'binary'}
        assert zip_content['application/zip']['schema'] == {'type': 'string', 'format': 'binary'}

    def test_file_schema_initialization(self):
        """Test FileSchema initialization with various parameters"""
        # Test default initialization
        f1 = FileSchema()
        assert f1.type == 'string'
        assert f1.format == 'binary'

        # Test with custom type and format
        f2 = FileSchema(type='string', format='base64')
        assert f2.type == 'string'
        assert f2.format == 'base64'

        # FileSchema doesn't validate type/format values during init
        # This is by design - validation happens at the OpenAPI spec level
        f3 = FileSchema(type='custom', format='custom')
        assert f3.type == 'custom'
        assert f3.format == 'custom'


class TestPaginationSchema:
    """Test PaginationSchema functionality"""

    def test_pagination_schema_fields(self):
        """Test that PaginationSchema has all expected fields"""
        schema = PaginationSchema()

        expected_fields = ['page', 'per_page', 'pages', 'total',
                          'current', 'next', 'prev', 'first', 'last']

        for field_name in expected_fields:
            assert field_name in schema.fields

        # Check field types
        assert isinstance(schema.fields['page'], Integer)
        assert isinstance(schema.fields['per_page'], Integer)
        assert isinstance(schema.fields['pages'], Integer)
        assert isinstance(schema.fields['total'], Integer)
        assert isinstance(schema.fields['current'], URL)
        assert isinstance(schema.fields['next'], URL)
        assert isinstance(schema.fields['prev'], URL)
        assert isinstance(schema.fields['first'], URL)
        assert isinstance(schema.fields['last'], URL)

    def test_pagination_schema_serialization(self):
        """Test PaginationSchema serialization"""
        schema = PaginationSchema()

        data = {
            'page': 2,
            'per_page': 10,
            'pages': 5,
            'total': 50,
            'current': 'http://example.com/items?page=2',
            'next': 'http://example.com/items?page=3',
            'prev': 'http://example.com/items?page=1',
            'first': 'http://example.com/items?page=1',
            'last': 'http://example.com/items?page=5'
        }

        result = schema.dump(data)
        assert result == data

    def test_pagination_schema_partial_data(self):
        """Test PaginationSchema with partial data"""
        schema = PaginationSchema()

        # Only some fields provided
        partial_data = {
            'page': 1,
            'per_page': 20,
            'total': 100
        }

        result = schema.dump(partial_data)
        assert result == partial_data

        # Load should also work with partial data
        loaded = schema.load(partial_data)
        assert loaded == partial_data

    def test_pagination_schema_validation(self):
        """Test PaginationSchema validation"""
        schema = PaginationSchema()

        # Invalid URL should raise validation error
        invalid_data = {
            'page': 1,
            'current': 'not-a-url'
        }

        with pytest.raises(ValidationError) as exc_info:
            schema.load(invalid_data)

        assert 'current' in exc_info.value.messages
        assert 'Not a valid URL' in str(exc_info.value.messages['current'])

    def test_pagination_schema_in_endpoint(self, app: APIFlask, client):
        """Test PaginationSchema used in an endpoint"""
        @app.get('/items')
        @app.output(PaginationSchema)
        def get_items():
            return {
                'page': 1,
                'per_page': 10,
                'pages': 3,
                'total': 30,
                'current': 'http://example.com/items?page=1',
                'next': 'http://example.com/items?page=2',
                'first': 'http://example.com/items?page=1',
                'last': 'http://example.com/items?page=3'
            }

        rv = client.get('/items')
        assert rv.status_code == 200
        assert rv.json['page'] == 1
        assert rv.json['total'] == 30
        assert 'prev' not in rv.json  # Optional field not provided

    def test_pagination_schema_inheritance(self):
        """Test custom schema inheriting from PaginationSchema"""
        class CustomPaginationSchema(PaginationSchema):
            custom_field = String()

        schema = CustomPaginationSchema()
        assert 'page' in schema.fields
        assert 'custom_field' in schema.fields

        data = {
            'page': 1,
            'per_page': 10,
            'custom_field': 'custom value'
        }

        result = schema.dump(data)
        assert result == data

    def test_pagination_with_invalid_urls(self):
        """Test PaginationSchema with malformed URLs"""
        schema = PaginationSchema()

        # Invalid URLs should raise ValidationError
        invalid_data = {
            'current': 'not a url',
            'next': 'ht!tp://bad url',
            'prev': '////',
            'first': 'javascript:alert(1)',
            'last': ''
        }

        with pytest.raises(ValidationError) as exc_info:
            schema.load(invalid_data)

        errors = exc_info.value.messages
        for field in ['current', 'next', 'prev', 'first', 'last']:
            assert field in errors

    def test_pagination_with_huge_numbers(self):
        """Test PaginationSchema with very large numbers"""
        schema = PaginationSchema()

        import sys
        huge_data = {
            'page': sys.maxsize,
            'per_page': 1000000,
            'pages': sys.maxsize // 2,
            'total': sys.maxsize
        }

        # Should handle large integers
        result = schema.load(huge_data)
        assert result == huge_data


class TestSchemaConstants:
    """Test schema constants for error responses"""

    def test_validation_error_detail_schema(self):
        """Test validation_error_detail_schema structure"""
        assert isinstance(validation_error_detail_schema, dict)
        assert validation_error_detail_schema['type'] == 'object'
        assert 'properties' in validation_error_detail_schema

        location_schema = validation_error_detail_schema['properties']['<location>']
        assert location_schema['type'] == 'object'

        field_schema = location_schema['properties']['<field_name>']
        assert field_schema['type'] == 'array'
        assert field_schema['items']['type'] == 'string'

    def test_validation_error_schema(self):
        """Test validation_error_schema structure"""
        assert isinstance(validation_error_schema, dict)
        assert validation_error_schema['type'] == 'object'
        assert 'properties' in validation_error_schema

        properties = validation_error_schema['properties']
        assert 'detail' in properties
        assert 'message' in properties

        assert properties['detail'] == validation_error_detail_schema
        assert properties['message']['type'] == 'string'

    def test_http_error_schema(self):
        """Test http_error_schema structure"""
        assert isinstance(http_error_schema, dict)
        assert http_error_schema['type'] == 'object'
        assert 'properties' in http_error_schema

        properties = http_error_schema['properties']
        assert 'detail' in properties
        assert 'message' in properties

        assert properties['detail']['type'] == 'object'
        assert properties['message']['type'] == 'string'

    def test_error_schemas_in_openapi(self, app: APIFlask, client):
        """Test that error schemas are properly included in OpenAPI spec"""
        @app.get('/test')
        @app.output(EmptySchema)
        def test_endpoint():
            return ''

        rv = client.get('/openapi.json')
        assert rv.status_code == 200

        # Validate the complete OpenAPI spec
        osv.validate(rv.json)


class TestSchemaBaseClass:
    """Test the base Schema class"""

    def test_schema_base_class(self):
        """Test that Schema is properly defined and can be used"""
        from marshmallow import Schema as MarshmallowSchema

        # Verify Schema is based on marshmallow Schema
        assert issubclass(Schema, MarshmallowSchema)

        # Test creating a custom schema
        class CustomSchema(Schema):
            name = String(required=True)
            age = Integer()

        schema = CustomSchema()

        # Test validation
        valid_data = {'name': 'John', 'age': 25}
        result = schema.load(valid_data)
        assert result == valid_data

        # Test validation error
        invalid_data = {'age': 25}  # missing required field
        with pytest.raises(ValidationError) as exc_info:
            schema.load(invalid_data)
        assert 'name' in exc_info.value.messages

    def test_schema_with_nested_fields(self):
        """Test Schema with nested fields"""
        class AddressSchema(Schema):
            street = String()
            city = String()

        class UserSchema(Schema):
            name = String()
            address = fields.Nested(AddressSchema)

        schema = UserSchema()
        data = {
            'name': 'John',
            'address': {
                'street': '123 Main St',
                'city': 'New York'
            }
        }

        result = schema.load(data)
        assert result == data


class TestEdgeCases:
    """Test edge cases and special scenarios"""

    def test_file_schema_with_flask_response(self, app: APIFlask, client):
        """Test FileSchema with different Flask response types"""
        @app.get('/file/response')
        @app.output(FileSchema(), content_type='text/plain')
        def file_with_response():
            response = make_response('file content')
            response.headers['Content-Type'] = 'text/plain'
            return response

        rv = client.get('/file/response')
        assert rv.status_code == 200
        assert rv.content_type == 'text/plain'
        assert rv.data == b'file content'

    def test_empty_schema_with_headers(self, app: APIFlask, client):
        """Test EmptySchema with custom headers"""
        @app.post('/action')
        @app.output(EmptySchema, status_code=204)
        def perform_action():
            return '', 204, {'X-Custom-Header': 'value'}

        rv = client.post('/action')
        assert rv.status_code == 204
        assert rv.headers.get('X-Custom-Header') == 'value'
        assert rv.data == b''

    def test_schema_inheritance_chain(self):
        """Test complex schema inheritance"""
        class BaseSchema(Schema):
            id = Integer()

        class MiddleSchema(BaseSchema):
            name = String()

        class FinalSchema(MiddleSchema):
            email = String()

        schema = FinalSchema()
        assert 'id' in schema.fields
        assert 'name' in schema.fields
        assert 'email' in schema.fields

        data = {'id': 1, 'name': 'Test', 'email': 'test@example.com'}
        result = schema.load(data)
        assert result == data

    def test_multiple_inheritance_schemas(self):
        """Test schemas with multiple inheritance"""
        class TimestampMixin(Schema):
            created_at = String()
            updated_at = String()

        class AuthorMixin(Schema):
            author_id = Integer()
            author_name = String()

        class PostSchema(TimestampMixin, AuthorMixin):
            title = String()
            content = String()

        schema = PostSchema()
        expected_fields = ['created_at', 'updated_at', 'author_id', 'author_name', 'title', 'content']
        for field in expected_fields:
            assert field in schema.fields

    def test_schema_with_method_override(self):
        """Test overriding schema methods"""
        class CustomSchema(Schema):
            value = Integer()

            def load(self, data, **kwargs):
                # Custom preprocessing
                if isinstance(data, dict) and 'value' in data:
                    data = data.copy()
                    data['value'] = data['value'] * 2
                return super().load(data, **kwargs)

        schema = CustomSchema()
        result = schema.load({'value': 5})
        assert result['value'] == 10


class TestOpenAPISpecValidation:
    """Test that schemas generate valid OpenAPI specifications"""

    def test_complete_openapi_spec_validation(self, app: APIFlask, client):
        """Test that a complex API with various schemas generates valid OpenAPI spec"""
        # Create endpoints using different schemas
        @app.get('/empty')
        @app.output(EmptySchema, status_code=204)
        def empty():
            return ''

        @app.get('/file')
        @app.output(FileSchema(), content_type='application/pdf')
        def file():
            return 'file'

        @app.get('/pagination')
        @app.output(PaginationSchema)
        def pagination():
            return {'page': 1, 'total': 10}

        class CustomSchema(Schema):
            name = String()
            value = Integer()

        @app.post('/custom')
        @app.input(CustomSchema)
        @app.output(CustomSchema)
        def custom(data):
            return data

        # Get and validate OpenAPI spec
        rv = client.get('/openapi.json')
        assert rv.status_code == 200

        # This will raise if the spec is invalid
        osv.validate(rv.json)

        # Verify each endpoint is properly documented
        paths = rv.json['paths']
        assert '/empty' in paths
        assert '/file' in paths
        assert '/pagination' in paths
        assert '/custom' in paths
