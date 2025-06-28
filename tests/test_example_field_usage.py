"""
Unit tests for Field type imports specifically used in APIFlask examples.

This module provides targeted tests for each field type as it appears in the example code,
with comments referencing the specific example file where each usage pattern originates.
"""

import io
import pytest
from marshmallow import ValidationError

from apiflask import Schema
from apiflask.fields import (
    Integer, String, Field, File, List, Nested
)
from apiflask.validators import Length, OneOf, FileSize, FileType, Range
from werkzeug.datastructures import FileStorage


class TestStringFieldFromExamples:
    """Tests for String field usage patterns from examples"""

    def test_string_with_length_validation(self):
        """
        Reference: basic/app.py, orm/app.py - PetIn schema
        Tests String field with Length validator for pet names
        """
        class PetIn(Schema):
            name = String(required=True, validate=Length(0, 10))

        schema = PetIn()

        # Valid name within length limit
        result = schema.load({'name': 'Kitty'})
        assert result['name'] == 'Kitty'

        # Name exceeding length limit
        with pytest.raises(ValidationError) as exc:
            schema.load({'name': 'VeryLongPetName'})
        assert 'name' in exc.value.messages
        assert 'Length must be between 0 and 10' in str(exc.value.messages['name'][0])

    def test_string_with_oneof_validation(self):
        """
        Reference: basic/app.py, orm/app.py - PetIn schema
        Tests String field with OneOf validator for pet categories
        """
        class PetIn(Schema):
            category = String(required=True, validate=OneOf(['dog', 'cat']))

        schema = PetIn()

        # Valid categories
        assert schema.load({'category': 'dog'})['category'] == 'dog'
        assert schema.load({'category': 'cat'})['category'] == 'cat'

        # Invalid category
        with pytest.raises(ValidationError) as exc:
            schema.load({'category': 'bird'})
        assert 'category' in exc.value.messages
        assert 'Must be one of: dog, cat' in str(exc.value.messages['category'][0])

    def test_string_basic_output(self):
        """
        Reference: basic/app.py, orm/app.py - PetOut schema
        Tests basic String field for output serialization
        """
        class PetOut(Schema):
            name = String()
            category = String()

        schema = PetOut()

        # Test serialization
        pet_data = {'name': 'Coco', 'category': 'dog'}
        result = schema.dump(pet_data)
        assert result['name'] == 'Coco'
        assert result['category'] == 'dog'

    def test_string_token_field(self):
        """
        Reference: auth/token_auth/app.py - Token schema
        Tests String field for authentication tokens
        """
        class Token(Schema):
            token = String()

        schema = Token()

        # Test token handling
        token_data = {'token': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'}
        result = schema.dump(token_data)
        assert result['token'].startswith('Bearer ')

        # Test loading
        loaded = schema.load(token_data)
        assert loaded['token'] == token_data['token']


class TestIntegerFieldFromExamples:
    """Tests for Integer field usage patterns from examples"""

    def test_integer_basic_output(self):
        """
        Reference: basic/app.py, orm/app.py - PetOut schema
        Tests Integer field for ID serialization
        """
        class PetOut(Schema):
            id = Integer()

        schema = PetOut()

        # Test integer serialization
        result = schema.dump({'id': 42})
        assert result['id'] == 42
        assert isinstance(result['id'], int)

        # Test type conversion during load
        result = schema.load({'id': '123'})
        assert result['id'] == 123
        assert isinstance(result['id'], int)

    def test_integer_with_defaults(self):
        """
        Reference: pagination/app.py - PetQuery schema
        Tests Integer field with load_default values
        """
        class PetQuery(Schema):
            page = Integer(load_default=1)
            per_page = Integer(load_default=20)

        schema = PetQuery()

        # Test default values
        result = schema.load({})
        assert result['page'] == 1
        assert result['per_page'] == 20

        # Test overriding defaults
        result = schema.load({'page': 5, 'per_page': 10})
        assert result['page'] == 5
        assert result['per_page'] == 10

    def test_integer_with_range_validation(self):
        """
        Reference: pagination/app.py - PetQuery schema
        Tests Integer field with Range validator
        """
        class PetQuery(Schema):
            per_page = Integer(load_default=20, validate=Range(max=30))

        schema = PetQuery()

        # Valid range
        result = schema.load({'per_page': 25})
        assert result['per_page'] == 25

        # Exceeds maximum
        with pytest.raises(ValidationError) as exc:
            schema.load({'per_page': 50})
        assert 'per_page' in exc.value.messages
        assert 'less than or equal to 30' in str(exc.value.messages['per_page'][0])

    def test_integer_in_base_response(self):
        """
        Reference: base_response/app.py - BaseResponse schema
        Tests Integer field for response codes
        """
        class BaseResponse(Schema):
            code = Integer()

        schema = BaseResponse()

        # Test HTTP status codes
        result = schema.dump({'code': 200})
        assert result['code'] == 200

        result = schema.dump({'code': 404})
        assert result['code'] == 404


class TestFieldGenericFromExamples:
    """Tests for generic Field usage patterns from examples"""

    def test_field_as_generic_data_container(self):
        """
        Reference: base_response/app.py - BaseResponse schema
        Tests Field as a generic container for 'data' key
        """
        class BaseResponse(Schema):
            data = Field()  # Generic field accepting any data type
            message = String()
            code = Integer()

        schema = BaseResponse()

        # Test with dictionary data
        response = {
            'data': {'id': 1, 'name': 'Test Item'},
            'message': 'Success',
            'code': 200
        }
        result = schema.dump(response)
        assert result['data'] == {'id': 1, 'name': 'Test Item'}
        assert isinstance(result['data'], dict)

        # Test with list data
        response['data'] = [1, 2, 3, 4, 5]
        result = schema.dump(response)
        assert result['data'] == [1, 2, 3, 4, 5]
        assert isinstance(result['data'], list)

        # Test with string data
        response['data'] = 'Simple string response'
        result = schema.dump(response)
        assert result['data'] == 'Simple string response'
        assert isinstance(result['data'], str)

        # Test with None
        response['data'] = None
        result = schema.dump(response)
        assert result['data'] is None


class TestFileFieldFromExamples:
    """Tests for File field usage patterns from examples"""

    def test_file_with_validation(self):
        """
        Reference: file_upload/app.py - Image schema
        Tests File field with FileType and FileSize validators
        """
        class Image(Schema):
            image = File(validate=[
                FileType(['.png', '.jpg', '.jpeg', '.gif']),
                FileSize(max='5 MB')
            ])

        schema = Image()

        # Create mock file
        file_content = b'fake image data'
        file_obj = io.BytesIO(file_content)
        file_storage = FileStorage(
            stream=file_obj,
            filename='test_image.jpg',
            content_type='image/jpeg'
        )

        # Test file loading
        result = schema.load({'image': file_storage})
        assert result['image'] == file_storage
        assert result['image'].filename == 'test_image.jpg'

    def test_file_with_form_data(self):
        """
        Reference: file_upload/app.py - ProfileIn schema
        Tests File field combined with String field for profile creation
        """
        class ProfileIn(Schema):
            name = String()
            avatar = File(validate=[
                FileType(['.png', '.jpg', '.jpeg']),
                FileSize(max='2 MB')
            ])

        schema = ProfileIn()

        # Create mock avatar file
        avatar_data = b'avatar image bytes'
        avatar_obj = io.BytesIO(avatar_data)
        avatar_file = FileStorage(
            stream=avatar_obj,
            filename='avatar.png',
            content_type='image/png'
        )

        # Test combined form and file data
        form_data = {
            'name': 'John Doe',
            'avatar': avatar_file
        }

        result = schema.load(form_data)
        assert result['name'] == 'John Doe'
        assert result['avatar'] == avatar_file
        assert result['avatar'].filename == 'avatar.png'


class TestListFieldFromExamples:
    """Tests for List field usage patterns from examples"""

    def test_list_with_nested_schemas(self):
        """
        Reference: pagination/app.py - PetsOut schema
        Tests List field containing Nested schema objects
        """
        class PetOut(Schema):
            id = Integer()
            name = String()
            category = String()

        class PetsOut(Schema):
            pets = List(Nested(PetOut))

        schema = PetsOut()

        # Test serialization of pet list
        pets_data = {
            'pets': [
                {'id': 1, 'name': 'Pet 1', 'category': 'dog'},
                {'id': 2, 'name': 'Pet 2', 'category': 'cat'},
                {'id': 3, 'name': 'Pet 3', 'category': 'dog'}
            ]
        }

        result = schema.dump(pets_data)
        assert len(result['pets']) == 3
        assert result['pets'][0]['name'] == 'Pet 1'
        assert result['pets'][1]['category'] == 'cat'
        assert result['pets'][2]['id'] == 3

        # Test deserialization
        loaded = schema.load(pets_data)
        assert len(loaded['pets']) == 3
        assert all(isinstance(pet['id'], int) for pet in loaded['pets'])


class TestNestedFieldFromExamples:
    """Tests for Nested field usage patterns from examples"""

    def test_nested_single_object(self):
        """
        Reference: pagination/app.py - PetsOut schema (pagination field)
        Tests Nested field for single object embedding
        """
        class PaginationSchema(Schema):
            page = Integer()
            per_page = Integer()
            total = Integer()
            pages = Integer()

        class ResponseSchema(Schema):
            pagination = Nested(PaginationSchema)

        schema = ResponseSchema()

        # Test nested object serialization
        data = {
            'pagination': {
                'page': 2,
                'per_page': 20,
                'total': 100,
                'pages': 5
            }
        }

        result = schema.dump(data)
        assert result['pagination']['page'] == 2
        assert result['pagination']['per_page'] == 20
        assert result['pagination']['total'] == 100
        assert result['pagination']['pages'] == 5

    def test_nested_with_list(self):
        """
        Reference: pagination/app.py - PetsOut schema (pets field)
        Tests Nested field used within List field
        """
        class ItemSchema(Schema):
            id = Integer()
            value = String()

        class ContainerSchema(Schema):
            items = List(Nested(ItemSchema))

        schema = ContainerSchema()

        # Test list of nested objects
        data = {
            'items': [
                {'id': 1, 'value': 'First'},
                {'id': 2, 'value': 'Second'}
            ]
        }

        result = schema.dump(data)
        assert len(result['items']) == 2
        assert result['items'][0]['id'] == 1
        assert result['items'][1]['value'] == 'Second'


class TestCompleteExampleScenarios:
    """Integration tests combining multiple field types as in real examples"""

    def test_basic_pet_api_scenario(self):
        """
        Reference: basic/app.py - Complete pet API scenario
        Tests the full data flow of the basic pet API example
        """
        # Input schema with validation
        class PetIn(Schema):
            name = String(required=True, validate=Length(0, 10))
            category = String(required=True, validate=OneOf(['dog', 'cat']))

        # Output schema for responses
        class PetOut(Schema):
            id = Integer()
            name = String()
            category = String()

        # Test input validation
        input_schema = PetIn()

        # Valid input
        valid_pet = {'name': 'Fluffy', 'category': 'cat'}
        input_result = input_schema.load(valid_pet)
        assert input_result['name'] == 'Fluffy'
        assert input_result['category'] == 'cat'

        # Invalid input - name too long
        with pytest.raises(ValidationError) as exc:
            input_schema.load({'name': 'VeryLongName', 'category': 'cat'})
        assert 'name' in exc.value.messages

        # Invalid input - wrong category
        with pytest.raises(ValidationError) as exc:
            input_schema.load({'name': 'Bird', 'category': 'bird'})
        assert 'category' in exc.value.messages

        # Test output serialization
        output_schema = PetOut()
        pet_data = {'id': 1, 'name': 'Fluffy', 'category': 'cat'}
        output_result = output_schema.dump(pet_data)
        assert output_result == pet_data

    def test_pagination_scenario(self):
        """
        Reference: pagination/app.py - Complete pagination scenario
        Tests the pagination example with query parameters and nested response
        """
        # Query parameters schema
        class PetQuery(Schema):
            page = Integer(load_default=1)
            per_page = Integer(load_default=20, validate=Range(max=30))

        # Individual pet schema
        class PetOut(Schema):
            id = Integer()
            name = String()
            category = String()

        # Pagination metadata schema
        class PaginationSchema(Schema):
            page = Integer()
            per_page = Integer()
            pages = Integer()
            total = Integer()
            next = Integer(allow_none=True)
            prev = Integer(allow_none=True)

        # Complete response schema
        class PetsOut(Schema):
            pets = List(Nested(PetOut))
            pagination = Nested(PaginationSchema)

        # Test query parameter handling
        query_schema = PetQuery()

        # Default values
        query_result = query_schema.load({})
        assert query_result['page'] == 1
        assert query_result['per_page'] == 20

        # Custom values within range
        query_result = query_schema.load({'page': 3, 'per_page': 25})
        assert query_result['page'] == 3
        assert query_result['per_page'] == 25

        # Value exceeding range
        with pytest.raises(ValidationError):
            query_schema.load({'per_page': 50})

        # Test complete response
        response_schema = PetsOut()
        response_data = {
            'pets': [
                {'id': 1, 'name': 'Pet 1', 'category': 'dog'},
                {'id': 2, 'name': 'Pet 2', 'category': 'cat'}
            ],
            'pagination': {
                'page': 1,
                'per_page': 20,
                'pages': 5,
                'total': 100,
                'next': 2,
                'prev': None
            }
        }

        response_result = response_schema.dump(response_data)
        assert len(response_result['pets']) == 2
        assert response_result['pagination']['total'] == 100
        assert response_result['pagination']['next'] == 2
        assert response_result['pagination']['prev'] is None

    def test_base_response_wrapper_scenario(self):
        """
        Reference: base_response/app.py - Base response wrapper pattern
        Tests the base response wrapper pattern with generic data field
        """
        # Base response wrapper
        class BaseResponse(Schema):
            data = Field()  # Generic data field
            message = String()
            code = Integer()

        schema = BaseResponse()

        # Test with single object data
        single_response = {
            'data': {'id': 1, 'name': 'Kitty', 'category': 'cat'},
            'message': 'Pet retrieved successfully',
            'code': 200
        }
        result = schema.dump(single_response)
        assert result['data']['name'] == 'Kitty'
        assert result['message'] == 'Pet retrieved successfully'
        assert result['code'] == 200

        # Test with list data
        list_response = {
            'data': [
                {'id': 1, 'name': 'Pet 1'},
                {'id': 2, 'name': 'Pet 2'}
            ],
            'message': 'Pets retrieved successfully',
            'code': 200
        }
        result = schema.dump(list_response)
        assert len(result['data']) == 2
        assert result['data'][0]['name'] == 'Pet 1'

        # Test with empty data
        empty_response = {
            'data': {},
            'message': 'Pet deleted',
            'code': 204
        }
        result = schema.dump(empty_response)
        assert result['data'] == {}
        assert result['code'] == 204


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
