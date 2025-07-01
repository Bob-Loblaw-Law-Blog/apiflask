import openapi_spec_validator as osv
import pytest
from marshmallow.fields import Integer, URL

from apiflask.schemas import EmptySchema
from apiflask.schemas import FileSchema
from apiflask.schemas import PaginationSchema
from apiflask.schemas import Schema
from apiflask.schemas import validation_error_schema
from apiflask.schemas import http_error_schema
from apiflask.schemas import validation_error_detail_schema


# ----- EmptySchema Tests -----

@pytest.mark.parametrize('schema', [{}, EmptySchema])
def test_empty_schema_with_no_content(app, client, schema):
    @app.route('/foo')
    @app.output(schema, status_code=204)
    def empty_response():
        return ''

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    osv.validate(rv.json)
    assert 'content' not in rv.json['paths']['/foo']['get']['responses']['204']
    
    # Verify actual response
    rv = client.get('/foo')
    assert rv.status_code == 204
    assert rv.data == b''


@pytest.mark.parametrize('schema', [{}, EmptySchema])
def test_empty_schema_with_content_type(app, client, schema):
    @app.route('/bar')
    @app.output(schema, content_type='image/png')
    def empty_schema_with_content():
        return ''

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    assert 'content' in rv.json['paths']['/bar']['get']['responses']['200']
    assert rv.json['paths']['/bar']['get']['responses']['200']['content']['image/png']['schema'] == {}


def test_empty_schema_with_description(app, client):
    @app.route('/baz')
    @app.output(EmptySchema, description='Empty response with description')
    def empty_schema_with_description():
        return ''

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    assert rv.json['paths']['/baz']['get']['responses']['200']['description'] == 'Empty response with description'


def test_empty_schema_inheritance():
    # Ensure EmptySchema inherits from Schema
    assert issubclass(EmptySchema, Schema)
    
    # Instantiate to check it works as expected
    empty_schema = EmptySchema()
    assert isinstance(empty_schema, EmptySchema)
    assert isinstance(empty_schema, Schema)


# ----- FileSchema Tests -----

def test_file_schema_defaults(app, client):
    @app.get('/default-file')
    @app.output(FileSchema(), content_type='application/octet-stream')
    def get_default_file():
        return 'file'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    content = rv.json['paths']['/default-file']['get']['responses']['200']['content']
    assert 'application/octet-stream' in content
    schema = content['application/octet-stream']['schema'] 
    assert schema == {'type': 'string', 'format': 'binary'}


def test_file_schema_with_custom_type_format(app, client):
    @app.get('/custom-file')
    @app.output(
        FileSchema(type='object', format='base64'),
        content_type='application/pdf',
        description='A base64 encoded PDF file',
    )
    def get_custom_file():
        return 'base64-file-content'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    content = rv.json['paths']['/custom-file']['get']['responses']['200']['content']
    assert 'application/pdf' in content
    schema = content['application/pdf']['schema']
    assert schema == {'type': 'object', 'format': 'base64'}


def test_file_schema_multiple_content_types(app, client):
    file_schema = FileSchema(type='string', format='binary')
    
    @app.get('/multi-type-file')
    @app.output(
        file_schema,
        content_type=['image/jpeg', 'image/png'],
        description='An image file in JPEG or PNG format',
    )
    def get_multi_type_file():
        return 'image-file'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    content = rv.json['paths']['/multi-type-file']['get']['responses']['200']['content']
    assert 'image/jpeg' in content
    assert 'image/png' in content
    assert content['image/jpeg']['schema'] == {'type': 'string', 'format': 'binary'}
    assert content['image/png']['schema'] == {'type': 'string', 'format': 'binary'}


def test_file_schema_repr():
    f1 = FileSchema()
    assert repr(f1) == f'schema: \n  type: string\n  format: binary'
    
    f2 = FileSchema(type='object', format='base64')
    assert repr(f2) == f'schema: \n  type: object\n  format: base64'


# ----- PaginationSchema Tests -----

def test_pagination_schema_fields():
    pagination_schema = PaginationSchema()
    
    field_names = pagination_schema.fields.keys()
    assert 'page' in field_names
    assert 'per_page' in field_names
    assert 'pages' in field_names
    assert 'total' in field_names
    assert 'current' in field_names
    assert 'next' in field_names
    assert 'prev' in field_names
    assert 'first' in field_names
    assert 'last' in field_names

    # Verify field types
    assert isinstance(pagination_schema.fields['page'], Integer)
    assert isinstance(pagination_schema.fields['per_page'], Integer)
    assert isinstance(pagination_schema.fields['pages'], Integer)
    assert isinstance(pagination_schema.fields['total'], Integer)
    assert isinstance(pagination_schema.fields['current'], URL)
    assert isinstance(pagination_schema.fields['next'], URL)
    assert isinstance(pagination_schema.fields['prev'], URL)
    assert isinstance(pagination_schema.fields['first'], URL)
    assert isinstance(pagination_schema.fields['last'], URL)


def test_pagination_schema_in_app(app, client):
    @app.get('/paginated')
    @app.output(PaginationSchema)
    def get_paginated():
        return {
            'page': 1,
            'per_page': 10,
            'pages': 5,
            'total': 50,
            'current': 'http://example.com/items?page=1',
            'next': 'http://example.com/items?page=2',
            'prev': None,
            'first': 'http://example.com/items?page=1',
            'last': 'http://example.com/items?page=5',
        }

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    schema = rv.json['paths']['/paginated']['get']['responses']['200']['content']['application/json']['schema']
    assert '$ref' in schema
    assert schema['$ref'].endswith('/PaginationSchema')
    
    # Get the actual schema from components
    components = rv.json['components']['schemas']
    assert 'PaginationSchema' in components
    pagination_schema = components['PaginationSchema']
    assert pagination_schema['type'] == 'object'
    assert 'page' in pagination_schema['properties']
    assert 'per_page' in pagination_schema['properties']
    assert 'pages' in pagination_schema['properties']
    assert 'total' in pagination_schema['properties']
    assert 'current' in pagination_schema['properties']
    assert 'next' in pagination_schema['properties']
    assert 'prev' in pagination_schema['properties']
    assert 'first' in pagination_schema['properties']
    assert 'last' in pagination_schema['properties']


# ----- Base Schema Tests -----

def test_schema_inheritance():
    class MyCustomSchema(Schema):
        pass
    
    assert issubclass(MyCustomSchema, Schema)
    assert isinstance(MyCustomSchema(), Schema)


def test_schema_with_fields(app, client):
    class TestSchema(Schema):
        id = Integer(dump_default=123)
    
    @app.get('/test-schema')
    @app.output(TestSchema)
    def get_test_schema():
        return {'id': 456}

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    schema = rv.json['paths']['/test-schema']['get']['responses']['200']['content']['application/json']['schema']
    assert '$ref' in schema
    assert schema['$ref'].endswith('/TestSchema')
    
    # Get the actual schema from components
    components = rv.json['components']['schemas']
    assert 'TestSchema' in components
    test_schema = components['TestSchema']
    assert test_schema['type'] == 'object'
    assert 'id' in test_schema['properties']
    assert test_schema['properties']['id']['type'] == 'integer'


# ----- Error Schema Tests -----

def test_validation_error_schema_structure():
    # Check structure of validation_error_detail_schema
    assert validation_error_detail_schema['type'] == 'object'
    assert 'properties' in validation_error_detail_schema
    assert '<location>' in validation_error_detail_schema['properties']
    assert validation_error_detail_schema['properties']['<location>']['type'] == 'object'
    assert 'properties' in validation_error_detail_schema['properties']['<location>']
    assert '<field_name>' in validation_error_detail_schema['properties']['<location>']['properties']
    
    # Check structure of validation_error_schema
    assert validation_error_schema['type'] == 'object'
    assert 'properties' in validation_error_schema
    assert 'detail' in validation_error_schema['properties']
    assert validation_error_schema['properties']['detail'] == validation_error_detail_schema
    assert 'message' in validation_error_schema['properties']
    assert validation_error_schema['properties']['message']['type'] == 'string'


def test_http_error_schema_structure():
    assert http_error_schema['type'] == 'object'
    assert 'properties' in http_error_schema
    assert 'detail' in http_error_schema['properties']
    assert http_error_schema['properties']['detail']['type'] == 'object'
    assert 'message' in http_error_schema['properties']
    assert http_error_schema['properties']['message']['type'] == 'string'


def test_error_schema_in_app(app, client):
    app.config['APIFLASK_AUTO_VALIDATION_ERROR_RESPONSE'] = True
    
    class InputSchema(Schema):
        id = Integer(required=True)
    
    @app.post('/validate')
    @app.input(InputSchema)
    @app.output({})
    def post_validate(json_data):
        return {}

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    responses = rv.json['paths']['/validate']['post']['responses']
    
    # Check that 400 error response is documented
    assert '400' in responses
    assert 'content' in responses['400']
    assert 'application/json' in responses['400']['content']
    
    # Now send an invalid request to test actual error response
    rv = client.post('/validate', json={})
    assert rv.status_code == 400
    data = rv.json
    assert 'message' in data
    assert 'detail' in data
    assert isinstance(data['detail'], dict)
