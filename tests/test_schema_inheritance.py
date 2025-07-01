import pytest
from marshmallow import EXCLUDE
from marshmallow import fields
from marshmallow.validate import Range, Length

from apiflask.schemas import Schema


def test_basic_schema_inheritance():
    class BaseSchema(Schema):
        id = fields.Integer(required=True)
        created_at = fields.DateTime(dump_only=True)
    
    class UserSchema(BaseSchema):
        name = fields.String(required=True)
        email = fields.Email()
    
    # Instantiate schemas
    base_schema = BaseSchema()
    user_schema = UserSchema()
    
    # Check that UserSchema has all fields from BaseSchema
    assert 'id' in user_schema.fields
    assert 'created_at' in user_schema.fields
    assert 'name' in user_schema.fields
    assert 'email' in user_schema.fields
    
    # Test serialization
    user_data = {
        'id': 123,
        'created_at': '2023-01-01T12:00:00',
        'name': 'John Doe',
        'email': 'john@example.com'
    }
    result = user_schema.dump(user_data)
    assert result == user_data


def test_multi_level_inheritance():
    class BaseSchema(Schema):
        id = fields.Integer(required=True)
    
    class TimestampedSchema(BaseSchema):
        created_at = fields.DateTime(dump_only=True)
        updated_at = fields.DateTime(dump_only=True)
    
    class UserSchema(TimestampedSchema):
        name = fields.String(required=True)
    
    # Instantiate schema
    user_schema = UserSchema()
    
    # Check that UserSchema has all fields from the inheritance chain
    assert 'id' in user_schema.fields
    assert 'created_at' in user_schema.fields
    assert 'updated_at' in user_schema.fields
    assert 'name' in user_schema.fields


def test_schema_meta_inheritance():
    class BaseSchema(Schema):
        class Meta:
            unknown = EXCLUDE
            ordered = True
        
        id = fields.Integer()
    
    class UserSchema(BaseSchema):
        name = fields.String()
    
    # Check that Meta options are inherited
    assert UserSchema.Meta.unknown == EXCLUDE
    assert UserSchema.Meta.ordered is True
    
    # Test unknown field handling (should be excluded)
    user_schema = UserSchema()
    result = user_schema.load({'id': 1, 'name': 'John', 'extra_field': 'ignored'})
    assert 'extra_field' not in result


def test_schema_meta_override():
    class BaseSchema(Schema):
        class Meta:
            unknown = EXCLUDE
            ordered = True
        
        id = fields.Integer()
    
    class UserSchema(BaseSchema):
        class Meta:
            unknown = EXCLUDE  # Same as parent
            ordered = False    # Override parent
        
        name = fields.String()
    
    # Check that Meta options are properly set
    assert UserSchema.Meta.unknown == EXCLUDE
    assert UserSchema.Meta.ordered is False


def test_schema_with_validators():
    class UserSchema(Schema):
        name = fields.String(required=True, validate=Length(min=3, max=50))
        age = fields.Integer(validate=Range(min=18, max=120))
    
    user_schema = UserSchema()
    
    # Test valid data
    valid_data = {'name': 'John Doe', 'age': 30}
    result = user_schema.load(valid_data)
    assert result == valid_data
    
    # Test invalid name (too short)
    invalid_data = {'name': 'Jo', 'age': 30}
    with pytest.raises(Exception) as excinfo:
        user_schema.load(invalid_data)
    errors = excinfo.value.messages
    assert 'name' in errors
    assert 'Shorter than minimum length' in str(errors['name'])
    
    # Test invalid age (too low)
    invalid_data = {'name': 'John', 'age': 15}
    with pytest.raises(Exception) as excinfo:
        user_schema.load(invalid_data)
    errors = excinfo.value.messages
    assert 'age' in errors
    assert 'Less than minimum value' in str(errors['age'])


def test_schema_field_inheritance_with_override():
    class BaseSchema(Schema):
        id = fields.Integer(required=True)
        name = fields.String()
    
    class ExtendedSchema(BaseSchema):
        # Override name field
        name = fields.String(required=True, validate=Length(min=3))
    
    base_schema = BaseSchema()
    extended_schema = ExtendedSchema()
    
    # Check that base schema has original field
    assert 'name' in base_schema.fields
    assert base_schema.fields['name'].required is False
    assert not hasattr(base_schema.fields['name'], 'validate') or base_schema.fields['name'].validate is None
    
    # Check that extended schema has overridden field
    assert 'name' in extended_schema.fields
    assert extended_schema.fields['name'].required is True
    assert hasattr(extended_schema.fields['name'], 'validate')
    assert extended_schema.fields['name'].validate is not None


def test_schema_in_app(app, client):
    class UserSchema(Schema):
        id = fields.Integer()
        name = fields.String(required=True)
        email = fields.Email()
    
    @app.post('/users')
    @app.input(UserSchema)
    @app.output(UserSchema)
    def create_user(json_data):
        # Echo the input data with an added id
        result = dict(json_data)
        result['id'] = 123
        return result
    
    # Verify OpenAPI spec
    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    
    # Check input schema
    request_body = rv.json['paths']['/users']['post']['requestBody']
    assert 'content' in request_body
    assert 'application/json' in request_body['content']
    schema_ref = request_body['content']['application/json']['schema']['$ref']
    assert schema_ref.endswith('/UserSchema')
    
    # Check output schema
    response = rv.json['paths']['/users']['post']['responses']['200']
    assert 'content' in response
    assert 'application/json' in response['content']
    schema_ref = response['content']['application/json']['schema']['$ref']
    assert schema_ref.endswith('/UserSchema')
    
    # Check schema definition
    components = rv.json['components']['schemas']
    assert 'UserSchema' in components
    user_schema = components['UserSchema']
    assert user_schema['type'] == 'object'
    assert 'id' in user_schema['properties']
    assert 'name' in user_schema['properties']
    assert 'email' in user_schema['properties']
    assert 'name' in user_schema.get('required', [])
    
    # Test actual request
    rv = client.post('/users', json={'name': 'John', 'email': 'john@example.com'})
    assert rv.status_code == 200
    assert rv.json == {'id': 123, 'name': 'John', 'email': 'john@example.com'}
