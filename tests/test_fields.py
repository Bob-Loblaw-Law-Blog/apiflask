"""
Unit tests for APIFlask field imports validation.

This module tests the field types imported from apiflask.fields to ensure they work
properly for validation and serialization. Each test references the specific example
file where the field type is used.

Test coverage includes:
- Basic field types (String, Integer)
- Special field types (File, Field, List, Nested)
- Validation behavior
- Serialization/Deserialization
- Error handling
"""

import pytest
import io
from datetime import datetime, date, time
from decimal import Decimal
from uuid import uuid4
from ipaddress import IPv4Address, IPv6Address
from werkzeug.datastructures import FileStorage
from marshmallow import ValidationError
from apiflask import Schema
from apiflask.fields import (
    String, Integer, Boolean, Float, Decimal as DecimalField,
    Date, DateTime, Time, Email, URL, UUID,
    List, Nested, Dict, Field, File, Raw, Function, Method,
    Constant, IP, IPv4, IPv6, Tuple
)
from apiflask.validators import Length, OneOf, Range

class TestStringField:
    """
    Test String field type validation and serialization.

    References: Used in all example files:
    - examples/basic/app.py (PetIn.name, PetIn.category, PetOut.name, PetOut.category)
    - examples/orm/app.py (PetIn.name, PetIn.category, PetOut.name, PetOut.category)
    - examples/file_upload/app.py (ProfileIn.name)
    - examples/pagination/app.py (PetOut.name, PetOut.category)
    - examples/auth/token_auth/app.py (Token.token)
    - examples/base_response/app.py (BaseResponse.message)
    """

    def test_string_field_basic_validation(self):
        """Test basic String field validation"""
        class TestSchema(Schema):
            name = String()

        schema = TestSchema()

        # Valid string
        result = schema.load({'name': 'test'})
        assert result == {'name': 'test'}

        # Valid empty string
        result = schema.load({'name': ''})
        assert result == {'name': ''}

        # Test serialization
        dumped = schema.dump({'name': 'test'})
        assert dumped == {'name': 'test'}

    def test_string_field_required_validation(self):
        """Test String field with required=True (basic/app.py PetIn.name)"""
        class PetIn(Schema):
            name = String(required=True)

        schema = PetIn()

        # Missing required field should raise error
        with pytest.raises(ValidationError) as exc_info:
            schema.load({})
        assert 'name' in exc_info.value.messages
        assert 'required' in str(exc_info.value.messages['name'][0]).lower()

        # Verify the positive case works with the require flag
        result = schema.load({'name': 'test'})
        assert result == {'name': 'test'}

    def test_string_field_with_length_validator(self):
        """Test String field with Length validator (basic/app.py PetIn.name)"""
        class PetIn(Schema):
            name = String(required=True, validate=Length(0, 10))

        schema = PetIn()

        # Valid length
        result = schema.load({'name': 'Kitty'})
        assert result == {'name': 'Kitty'}

        # Too long
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'name': 'A very long pet name'})
        assert 'name' in exc_info.value.messages

    def test_string_field_with_oneof_validator(self):
        """Test String field with OneOf validator (basic/app.py PetIn.category)"""
        class PetIn(Schema):
            category = String(required=True, validate=OneOf(['dog', 'cat']))

        schema = PetIn()

        # Valid choice
        result = schema.load({'category': 'cat'})
        assert result == {'category': 'cat'}

        # Invalid choice
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'category': 'bird'})
        assert 'category' in exc_info.value.messages


class TestIntegerField:
    """
    Test Integer field type validation and serialization.

    References: Used in most example files:
    - examples/basic/app.py (PetOut.id)
    - examples/orm/app.py (PetOut.id)
    - examples/pagination/app.py (PetQuery.page, PetQuery.per_page, PetOut.id)
    - examples/base_response/app.py (BaseResponse.code, PetOut.id)
    """

    def test_integer_field_basic_validation(self):
        """Test basic Integer field validation"""
        class TestSchema(Schema):
            id = Integer()

        schema = TestSchema()

        # Valid integer
        result = schema.load({'id': 123})
        assert result == {'id': 123}

        # String representation of integer
        result = schema.load({'id': '456'})
        assert result == {'id': 456}

        # Test serialization
        dumped = schema.dump({'id': 789})
        assert dumped == {'id': 789}

    def test_integer_field_with_default_value(self):
        """Test Integer field with default value (pagination/app.py PetQuery.page)"""
        class PetQuery(Schema):
            page = Integer(load_default=1)

        schema = PetQuery()

        # No value provided, should use default
        result = schema.load({})
        assert result == {'page': 1}

        # Value provided, should use provided value
        result = schema.load({'page': 5})
        assert result == {'page': 5}

    def test_integer_field_with_range_validator(self):
        """Test Integer field with Range validator (pagination/app.py PetQuery.per_page)"""
        class PetQuery(Schema):
            per_page = Integer(load_default=20, validate=Range(max=30))

        schema = PetQuery()

        # Valid value within range
        result = schema.load({'per_page': 25})
        assert result == {'per_page': 25}

        # Value exceeding max
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'per_page': 50})
        assert 'per_page' in exc_info.value.messages

    def test_integer_field_invalid_type(self):
        """Test Integer field with invalid type"""
        class TestSchema(Schema):
            id = Integer()

        schema = TestSchema()

        # Non-numeric string
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'id': 'not_a_number'})
        assert 'id' in exc_info.value.messages

class TestFileField:
    """
    Test File field type validation and serialization.

    References: Used in file upload example:
    - examples/file_upload/app.py (Image.image, ProfileIn.avatar)
    """

    def test_file_field_basic_validation(self):
        """Test basic File field validation (file_upload/app.py Image.image)"""
        class ImageSchema(Schema):
            image = File()

        schema = ImageSchema()

        # Create mock file
        test_file = FileStorage(
            stream=io.BytesIO(b"fake image data"),
            filename="test.png",
            content_type="image/png"
        )

        # Valid file
        result = schema.load({'image': test_file})
        assert 'image' in result
        assert isinstance(result['image'], FileStorage)
        assert result['image'].filename == "test.png"

    def test_file_field_with_validators(self):
        """Test File field with custom validators (file_upload/app.py ProfileIn.avatar)"""
        from apiflask.validators import FileSize, FileType

        class ProfileIn(Schema):
            avatar = File(validate=[FileType(['.png', '.jpg', '.jpeg']), FileSize(max='2 MB')])

        schema = ProfileIn()

        # Valid file
        test_file = FileStorage(
            stream=io.BytesIO(b"fake image data"),
            filename="avatar.jpg",
            content_type="image/jpeg"
        )

        result = schema.load({'avatar': test_file})
        assert 'avatar' in result
        assert result['avatar'].filename == "avatar.jpg"


class TestListField:
    """
    Test List field type validation and serialization.

    References: Used in pagination example:
    - examples/pagination/app.py (PetsOut.pets)
    """

    def test_list_field_with_nested_schema(self):
        """Test List field with Nested schema (pagination/app.py PetsOut.pets)"""
        class PetOut(Schema):
            id = Integer()
            name = String()
            category = String()

        class PetsOut(Schema):
            pets = List(Nested(PetOut))

        schema = PetsOut()

        # Valid list of pets
        pets_data = {
            'pets': [
                {'id': 1, 'name': 'Kitty', 'category': 'cat'},
                {'id': 2, 'name': 'Coco', 'category': 'dog'}
            ]
        }

        result = schema.load(pets_data)
        assert len(result['pets']) == 2
        assert result['pets'][0]['name'] == 'Kitty'
        assert result['pets'][1]['name'] == 'Coco'

        # Test serialization
        dumped = schema.dump(result)
        assert dumped == pets_data

    def test_list_field_with_simple_types(self):
        """Test List field with simple types"""
        class TestSchema(Schema):
            tags = List(String())

        schema = TestSchema()

        # Valid list of strings
        result = schema.load({'tags': ['cat', 'pet', 'animal']})
        assert result == {'tags': ['cat', 'pet', 'animal']}

        # Empty list
        result = schema.load({'tags': []})
        assert result == {'tags': []}


class TestNestedField:
    """
    Test Nested field type validation and serialization.

    References: Used in pagination example:
    - examples/pagination/app.py (PetsOut.pagination)
    """

    def test_nested_field_basic(self):
        """Test basic Nested field (pagination/app.py PetsOut.pagination)"""
        from apiflask import PaginationSchema

        class PetsOut(Schema):
            pagination = Nested(PaginationSchema)

        schema = PetsOut()

        # Valid pagination data
        pagination_data = {
            'pagination': {
                'page': 1,
                'per_page': 20,
                'pages': 5,
                'total': 100,
                'next': 'http://example.com/pets?page=4',
                'prev': 'http://example.com/pets?page=2',
                'first': 'http://example.com/pets?page=1',
                'last': 'http://example.com/pets?page=5'
            }
        }

        result = schema.load(pagination_data)
        assert 'pagination' in result
        assert result['pagination']['page'] == 1
        assert result['pagination']['total'] == 100

    def test_nested_field_validation_error(self):
        """Test Nested field validation errors"""
        class InnerSchema(Schema):
            name = String(required=True)

        class OuterSchema(Schema):
            inner = Nested(InnerSchema)

        schema = OuterSchema()

        # Missing required field in nested schema
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'inner': {'missing'}})
        assert 'inner' in exc_info.value.messages


class TestFieldField:
    """
    Test base Field type validation and serialization.

    References: Used in base response example:
    - examples/base_response/app.py (BaseResponse.data)
    """

    def test_field_basic_raw_data(self):
        """Test base Field accepts any data type (base_response/app.py BaseResponse.data)"""
        class BaseResponse(Schema):
            data = Field()
            message = String()
            code = Integer()

        schema = BaseResponse()

        # Test with different data types
        test_cases = [
            {'data': 'string', 'message': 'Success', 'code': 200},
            {'data': 123, 'message': 'Success', 'code': 200},
            {'data': {'nested': 'object'}, 'message': 'Success', 'code': 200},
            {'data': [1, 2, 3], 'message': 'Success', 'code': 200},
            {'data': '', 'message': 'Success', 'code': 200},
        ]

        for test_data in test_cases:
            result = schema.load(test_data)
            assert result['data'] == test_data['data']

            # Test serialization
            dumped = schema.dump(result)
            assert dumped == test_data


class TestAdditionalFieldTypes:
    """
    Test additional field types available in APIFlask for comprehensive coverage.
    These are not directly used in examples but are available for import.
    """

    def test_boolean_field(self):
        """Test Boolean field validation"""
        class TestSchema(Schema):
            active = Boolean()

        schema = TestSchema()

        # Valid boolean values
        result = schema.load({'active': True})
        assert result == {'active': True}

        result = schema.load({'active': False})
        assert result == {'active': False}

        # String representations
        result = schema.load({'active': 'true'})
        assert result == {'active': True}

        result = schema.load({'active': 'false'})
        assert result == {'active': False}

    def test_float_field(self):
        """Test Float field validation"""
        class TestSchema(Schema):
            price = Float()

        schema = TestSchema()

        # Valid float
        result = schema.load({'price': 19.99})
        assert result == {'price': 19.99}

        # Integer converted to float
        result = schema.load({'price': 20})
        assert result == {'price': 20.0}

        # String representation
        result = schema.load({'price': '15.50'})
        assert result == {'price': 15.50}

    def test_decimal_field(self):
        """Test Decimal field validation"""
        class TestSchema(Schema):
            amount = DecimalField()

        schema = TestSchema()

        # Valid decimal
        result = schema.load({'amount': '19.99'})
        assert isinstance(result['amount'], Decimal)
        assert result['amount'] == Decimal('19.99')

    def test_date_field(self):
        """Test Date field validation"""
        class TestSchema(Schema):
            birth_date = Date()

        schema = TestSchema()

        # Valid ISO date string
        result = schema.load({'birth_date': '2023-01-01'})
        assert isinstance(result['birth_date'], date)
        assert result['birth_date'] == date(2023, 1, 1)

        # Test serialization
        test_date = date(2023, 12, 25)
        dumped = schema.dump({'birth_date': test_date})
        assert dumped == {'birth_date': '2023-12-25'}

    def test_datetime_field(self):
        """Test DateTime field validation"""
        class TestSchema(Schema):
            created_at = DateTime()

        schema = TestSchema()

        # Valid ISO datetime string
        result = schema.load({'created_at': '2023-01-01T12:00:00'})
        assert isinstance(result['created_at'], datetime)

        # Test serialization
        test_datetime = datetime(2023, 1, 1, 12, 0, 0)
        dumped = schema.dump({'created_at': test_datetime})
        assert '2023-01-01T12:00:00' in dumped['created_at']

    def test_time_field(self):
        """Test Time field validation"""
        class TestSchema(Schema):
            start_time = Time()

        schema = TestSchema()

        # Valid time string
        result = schema.load({'start_time': '14:30:00'})
        assert isinstance(result['start_time'], time)
        assert result['start_time'] == time(14, 30, 0)

    def test_email_field(self):
        """Test Email field validation"""
        class TestSchema(Schema):
            email = Email()

        schema = TestSchema()

        # Valid email
        result = schema.load({'email': 'test@example.com'})
        assert result == {'email': 'test@example.com'}

        # Invalid email format
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'email': 'invalid-email'})
        assert 'email' in exc_info.value.messages

    def test_url_field(self):
        """Test URL field validation"""
        class TestSchema(Schema):
            website = URL()

        schema = TestSchema()

        # Valid URL
        result = schema.load({'website': 'https://example.com'})
        assert result == {'website': 'https://example.com'}

        # Invalid URL format
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'website': 'not-a-url'})
        assert 'website' in exc_info.value.messages

    def test_uuid_field(self):
        """Test UUID field validation"""
        class TestSchema(Schema):
            id = UUID()

        schema = TestSchema()

        # Valid UUID string
        test_uuid = uuid4()
        result = schema.load({'id': str(test_uuid)})
        assert result == {'id': test_uuid}

        # Invalid UUID format
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'id': 'not-a-uuid'})
        assert 'id' in exc_info.value.messages

    def test_dict_field(self):
        """Test Dict field validation"""
        class TestSchema(Schema):
            metadata = Dict()

        schema = TestSchema()

        # Valid dictionary
        test_dict = {'key1': 'value1', 'key2': 42}
        result = schema.load({'metadata': test_dict})
        assert result == {'metadata': test_dict}

        # Empty dictionary
        result = schema.load({'metadata': {}})
        assert result == {'metadata': {}}

    def test_raw_field(self):
        """Test Raw field validation"""
        class TestSchema(Schema):
            raw_data = Raw()

        schema = TestSchema()

        # Raw field accepts any data type without validation
        test_cases = [
            {'raw_data': 'string'},
            {'raw_data': 123},
            {'raw_data': {'nested': 'object'}},
            {'raw_data': [1, 2, 3]},
            {'raw_data': False},
        ]

        for test_data in test_cases:
            result = schema.load(test_data)
            assert result == test_data

    def test_function_field(self):
        """Test Function field"""
        class TestSchema(Schema):
            computed = Function(lambda obj: obj.get('value', 0) * 2)

        schema = TestSchema()

        # Function field is for serialization only
        dumped = schema.dump({'value': 10})
        assert dumped == {'computed': 20}

    def test_method_field(self):
        """Test Method field"""
        class TestSchema(Schema):
            computed = Method('compute_value')

            def compute_value(self, obj):
                return obj.get('value', 0) * 3

        schema = TestSchema()

        # Method field is for serialization only
        dumped = schema.dump({'value': 5})
        assert dumped == {'computed': 15}

    def test_constant_field(self):
        """Test Constant field"""
        class TestSchema(Schema):
            version = Constant('1.0.0')

        schema = TestSchema()

        # Constant field always returns the same value
        dumped = schema.dump({})
        assert dumped == {'version': '1.0.0'}

    def test_ip_fields(self):
        """Test IP, IPv4, and IPv6 fields"""
        class TestSchema(Schema):
            ip_any = IP()
            ipv4 = IPv4()
            ipv6 = IPv6()

        schema = TestSchema()

        # Valid IPv4
        result = schema.load({'ip_any': '192.168.1.1', 'ipv4': '10.0.0.1'})
        assert result['ip_any'] == IPv4Address('192.168.1.1')
        assert result['ipv4'] == IPv4Address('10.0.0.1')

        # Valid IPv6
        result = schema.load({'ip_any': '2001:db8::1', 'ipv6': '::1'})
        assert result['ip_any'] == IPv6Address('2001:db8::1')
        assert result['ipv6'] == IPv6Address('::1')

        # Invalid IP formats
        with pytest.raises(ValidationError):
            schema.load({'ipv4': 'invalid-ip'})

    def test_tuple_field(self):
        """Test Tuple field"""
        class TestSchema(Schema):
            coordinates = Tuple([Float(), Float()])

        schema = TestSchema()

        # Valid tuple
        result = schema.load({'coordinates': [10.5, 20.3]})
        assert result == {'coordinates': (10.5, 20.3)}

        # Wrong number of elements
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'coordinates': [10.5]})
        assert 'coordinates' in exc_info.value.messages


class TestFieldValidationErrorHandling:
    """
    Test proper error handling for field validation failures.
    """

    def test_multiple_field_validation_errors(self):
        """Test handling multiple validation errors across different fields"""
        class TestSchema(Schema):
            name = String(required=True, validate=Length(min=3))
            age = Integer(required=True, validate=Range(min=18))
            email = Email(required=True)

        schema = TestSchema()

        # Multiple validation errors
        with pytest.raises(ValidationError) as exc_info:
            schema.load({
                'name': 'AB',  # Too short
                'age': 15,     # Too young
                'email': 'invalid'  # Invalid format
            })

        errors = exc_info.value.messages
        assert 'name' in errors
        assert 'age' in errors
        assert 'email' in errors

    def test_nested_field_validation_errors(self):
        """Test validation errors in nested fields"""
        class AddressSchema(Schema):
            street = String(required=True)
            city = String(required=True)

        class PersonSchema(Schema):
            name = String(required=True)
            address = Nested(AddressSchema)

        schema = PersonSchema()

        # Error in nested field
        with pytest.raises(ValidationError) as exc_info:
            schema.load({
                'name': 'John',
                'address': {'street': 'Main St'}  # Missing city
            })

        assert 'address' in exc_info.value.messages

    def test_list_field_validation_errors(self):
        """Test validation errors in list fields"""
        class TestSchema(Schema):
            numbers = List(Integer(validate=Range(min=0)))

        schema = TestSchema()

        # Invalid items in list
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'numbers': [1, -5, 'invalid', 3]})

        assert 'numbers' in exc_info.value.messages

