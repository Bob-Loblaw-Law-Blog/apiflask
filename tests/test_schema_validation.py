import pytest
from marshmallow import ValidationError

from apiflask.schemas import Schema
from apiflask.schemas import validation_error_schema, http_error_schema


class UserSchema(Schema):
    name = Schema.String(required=True)
    age = Schema.Integer(required=True)
    email = Schema.Email()


def test_validation_error_responses(app, client):
    app.config['APIFLASK_AUTO_VALIDATION_ERROR_RESPONSE'] = True

    @app.post('/users')
    @app.input(UserSchema)
    @app.output({})
    def create_user(json_data):
        return {}

    # Test missing required fields
    resp = client.post('/users', json={})
    assert resp.status_code == 400
    data = resp.json
    assert 'message' in data
    assert 'detail' in data
    assert 'json' in data['detail']
    assert 'name' in data['detail']['json']
    assert 'age' in data['detail']['json']

    # Test with invalid type
    resp = client.post('/users', json={'name': 'John', 'age': 'invalid'})
    assert resp.status_code == 400
    data = resp.json
    assert 'detail' in data
    assert 'json' in data['detail']
    assert 'age' in data['detail']['json']

    # Test with invalid email
    resp = client.post('/users', json={'name': 'John', 'age': 25, 'email': 'not-an-email'})
    assert resp.status_code == 400
    data = resp.json
    assert 'detail' in data
    assert 'json' in data['detail']
    assert 'email' in data['detail']['json']

    # Test valid data
    resp = client.post('/users', json={'name': 'John', 'age': 25, 'email': 'john@example.com'})
    assert resp.status_code == 200


def test_validation_error_schema_in_openapi(app, client):
    app.config['APIFLASK_AUTO_VALIDATION_ERROR_RESPONSE'] = True

    @app.post('/users')
    @app.input(UserSchema)
    @app.output({})
    def create_user(json_data):
        return {}

    resp = client.get('/openapi.json')
    assert resp.status_code == 200
    assert '400' in resp.json['paths']['/users']['post']['responses']
    resp_400 = resp.json['paths']['/users']['post']['responses']['400']
    
    assert 'content' in resp_400
    assert 'application/json' in resp_400['content']
    schema = resp_400['content']['application/json']['schema']
    
    # Check if the validation error schema structure is as expected
    assert schema['type'] == 'object'
    assert 'properties' in schema
    assert 'detail' in schema['properties']
    assert 'message' in schema['properties']


def test_http_error_responses(app, client):
    @app.route('/not-found')
    def not_found():
        # Simulate a 404 error
        from flask import abort
        abort(404)

    @app.route('/server-error')
    def server_error():
        # Simulate a 500 error
        from flask import abort
        abort(500)

    # Test 404 error response
    resp = client.get('/not-found')
    assert resp.status_code == 404
    data = resp.json
    assert 'message' in data
    assert 'Not Found' in data['message']

    # Test 500 error response
    resp = client.get('/server-error')
    assert resp.status_code == 500
    data = resp.json
    assert 'message' in data
    assert 'Internal Server Error' in data['message']


def test_custom_error_responses(app, client):
    app.config['APIFLASK_AUTO_HTTP_ERROR_RESPONSE'] = True
    
    # Register a custom HTTPException handler
    @app.errorhandler(404)
    def handle_404(error):
        return {'message': 'Custom Not Found', 'custom_field': 'test'}, 404
        
    @app.route('/custom-not-found')
    def custom_not_found():
        from flask import abort
        abort(404)
    
    # Test custom 404 error response
    resp = client.get('/custom-not-found')
    assert resp.status_code == 404
    data = resp.json
    assert 'message' in data
    assert 'Custom Not Found' == data['message']
    assert 'custom_field' in data
    assert 'test' == data['custom_field']


def test_schema_validation_methods():
    schema = UserSchema()
    
    # Valid data
    valid_data = {'name': 'Jane', 'age': 30, 'email': 'jane@example.com'}
    result = schema.load(valid_data)
    assert result == valid_data
    
    # Invalid data - missing required field
    invalid_data = {'age': 30}
    with pytest.raises(ValidationError) as excinfo:
        schema.load(invalid_data)
    errors = excinfo.value.messages
    assert 'name' in errors
    assert 'Missing data for required field.' in errors['name']
    
    # Invalid data - wrong type
    invalid_data = {'name': 'Jane', 'age': 'thirty'}
    with pytest.raises(ValidationError) as excinfo:
        schema.load(invalid_data)
    errors = excinfo.value.messages
    assert 'age' in errors
    assert 'Not a valid integer.' in errors['age']
