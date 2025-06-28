"""
Unit tests for Field type imports used in APIFlask examples.

This module tests the functionality of various field types imported from apiflask.fields
as used in the example applications.
"""

import io
import json
import uuid
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum

import pytest
from marshmallow import ValidationError, Schema as MarshmallowSchema
from werkzeug.datastructures import FileStorage

from apiflask import Schema
from apiflask.fields import (
    # Basic field types used in examples
    Integer, String, Field,
    # Field types from file_upload example
    File,
    # Collection field types from pagination example
    List, Nested,
    # Additional field types from the fields module
    Boolean, Constant, Date, DateTime, Decimal as DecimalField,
    Dict, Email, Float, Function, Method, Number,
    Time, TimeDelta, UUID, URL, IP, IPv4, IPv6,
    AwareDateTime, NaiveDateTime, Tuple, Pluck, Raw,
    Enum as EnumField,
    # Webargs fields
    DelimitedList, DelimitedTuple,
    # Flask-marshmallow fields
    AbsoluteURLFor, URLFor, Hyperlinks, Config
)
from apiflask.validators import Length, OneOf, FileSize, FileType, Range


# Test classes representing example use cases

class TestBasicFieldsExample:
    """Tests for String and Integer fields as used in basic/app.py and orm/app.py examples"""

    def test_string_field_basic(self):
        """Test String field - used in PetIn and PetOut schemas (basic/app.py, orm/app.py)"""
        class PetSchema(Schema):
            name = String(required=True, validate=Length(0, 10))
            category = String(required=True, validate=OneOf(['dog', 'cat']))

        schema = PetSchema()

        # Valid data
        valid_data = {'name': 'Kitty', 'category': 'cat'}
        result = schema.load(valid_data)
        assert result['name'] == 'Kitty'
        assert result['category'] == 'cat'

        # Invalid length
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'name': 'VeryLongPetName', 'category': 'cat'})
        assert 'name' in exc_info.value.messages

        # Invalid choice
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'name': 'Birdy', 'category': 'bird'})
        assert 'category' in exc_info.value.messages

    def test_integer_field_basic(self):
        """Test Integer field - used in PetOut schema (basic/app.py, orm/app.py)"""
        class PetOutSchema(Schema):
            id = Integer()
            name = String()

        schema = PetOutSchema()

        # Test serialization
        pet_data = {'id': 1, 'name': 'Coco'}
        result = schema.dump(pet_data)
        assert result['id'] == 1
        assert isinstance(result['id'], int)

        # Test deserialization with type conversion
        string_id_data = {'id': '42', 'name': 'Flash'}
        result = schema.load(string_id_data)
        assert result['id'] == 42
        assert isinstance(result['id'], int)


class TestBaseResponseFieldExample:
    """Tests for Field usage in base_response/app.py example"""

    def test_generic_field(self):
        """Test generic Field - used as 'data' field in BaseResponse (base_response/app.py)"""
        class BaseResponse(Schema):
            data = Field()  # Generic field that accepts any data
            message = String()
            code = Integer()

        schema = BaseResponse()

        # Test with dict data
        response_dict = {
            'data': {'id': 1, 'name': 'Test'},
            'message': 'Success',
            'code': 200
        }
        result = schema.dump(response_dict)
        assert result['data'] == {'id': 1, 'name': 'Test'}

        # Test with list data
        response_list = {
            'data': [1, 2, 3],
            'message': 'Success',
            'code': 200
        }
        result = schema.dump(response_list)
        assert result['data'] == [1, 2, 3]

        # Test with string data
        response_str = {
            'data': 'simple string',
            'message': 'Success',
            'code': 200
        }
        result = schema.dump(response_str)
        assert result['data'] == 'simple string'


class TestFileUploadFieldExample:
    """Tests for File field as used in file_upload/app.py example"""

    def test_file_field(self):
        """Test File field - used in Image and ProfileIn schemas (file_upload/app.py)"""
        class ImageSchema(Schema):
            image = File(validate=[
                FileType(['.png', '.jpg', '.jpeg', '.gif']),
                FileSize(max='5 MB')
            ])

        schema = ImageSchema()

        # Create a mock file
        file_data = b'fake image data'
        file_obj = io.BytesIO(file_data)
        file_storage = FileStorage(
            stream=file_obj,
            filename='test.jpg',
            content_type='image/jpeg'
        )

        # File field doesn't perform validation during load
        # Validation is typically done by validators
        result = schema.load({'image': file_storage})
        assert result['image'] == file_storage

    def test_file_field_with_string_field(self):
        """Test File field combined with String - ProfileIn schema (file_upload/app.py)"""
        class ProfileInSchema(Schema):
            name = String()
            avatar = File(validate=[
                FileType(['.png', '.jpg', '.jpeg']),
                FileSize(max='2 MB')
            ])

        schema = ProfileInSchema()

        # Create mock file
        file_obj = io.BytesIO(b'avatar data')
        file_storage = FileStorage(
            stream=file_obj,
            filename='avatar.png',
            content_type='image/png'
        )

        # Test combined data
        data = {
            'name': 'John Doe',
            'avatar': file_storage
        }
        result = schema.load(data)
        assert result['name'] == 'John Doe'
        assert result['avatar'] == file_storage


class TestPaginationFieldsExample:
    """Tests for List and Nested fields as used in pagination/app.py example"""

    def test_nested_field(self):
        """Test Nested field - used in PetsOut schema (pagination/app.py)"""
        class PetOut(Schema):
            id = Integer()
            name = String()
            category = String()

        class PetsOut(Schema):
            pets = List(Nested(PetOut))

        schema = PetsOut()

        # Test serialization of nested list
        data = {
            'pets': [
                {'id': 1, 'name': 'Pet 1', 'category': 'dog'},
                {'id': 2, 'name': 'Pet 2', 'category': 'cat'}
            ]
        }
        result = schema.dump(data)
        assert len(result['pets']) == 2
        assert result['pets'][0]['name'] == 'Pet 1'
        assert result['pets'][1]['category'] == 'cat'

    def test_integer_with_range_validation(self):
        """Test Integer field with Range validator - PetQuery schema (pagination/app.py)"""
        class PetQuery(Schema):
            page = Integer(load_default=1)
            per_page = Integer(load_default=20, validate=Range(max=30))

        schema = PetQuery()

        # Test defaults
        result = schema.load({})
        assert result['page'] == 1
        assert result['per_page'] == 20

        # Test valid range
        result = schema.load({'per_page': 25})
        assert result['per_page'] == 25

        # Test invalid range
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'per_page': 50})
        assert 'per_page' in exc_info.value.messages

    def test_list_field(self):
        """Test List field - used for pets collection (pagination/app.py)"""
        class SimpleList(Schema):
            items = List(String())

        schema = SimpleList()

        # Test list serialization
        data = {'items': ['cat', 'dog', 'bird']}
        result = schema.dump(data)
        assert result['items'] == ['cat', 'dog', 'bird']

        # Test list deserialization
        result = schema.load(data)
        assert len(result['items']) == 3


class TestTokenAuthFieldExample:
    """Tests for String field in authentication context (auth/token_auth/app.py)"""

    def test_token_field(self):
        """Test String field for token - Token schema (auth/token_auth/app.py)"""
        class Token(Schema):
            token = String()

        schema = Token()

        # Test token serialization
        token_data = {'token': 'Bearer eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9'}
        result = schema.dump(token_data)
        assert result['token'].startswith('Bearer ')

        # Test token deserialization
        result = schema.load(token_data)
        assert result['token'] == token_data['token']


class TestAdditionalFieldTypes:
    """Tests for additional field types available in apiflask.fields"""

    def test_boolean_field(self):
        """Test Boolean field type"""
        class BoolSchema(Schema):
            is_active = Boolean()
            is_verified = Boolean(required=True)

        schema = BoolSchema()

        # Test boolean values
        result = schema.load({'is_active': True, 'is_verified': False})
        assert result['is_active'] is True
        assert result['is_verified'] is False

        # Test string to boolean conversion
        result = schema.load({'is_active': 'true', 'is_verified': 'false'})
        assert result['is_active'] is True
        assert result['is_verified'] is False

    def test_date_field(self):
        """Test Date field type"""
        class DateSchema(Schema):
            birth_date = Date()

        schema = DateSchema()

        # Test date serialization
        today = date.today()
        result = schema.dump({'birth_date': today})
        assert result['birth_date'] == today.isoformat()

        # Test date deserialization
        result = schema.load({'birth_date': '2023-01-15'})
        assert result['birth_date'] == date(2023, 1, 15)

    def test_datetime_field(self):
        """Test DateTime field type"""
        class DateTimeSchema(Schema):
            created_at = DateTime()

        schema = DateTimeSchema()

        # Test datetime
        now = datetime.now()
        result = schema.dump({'created_at': now})
        # Result should be ISO format string
        assert isinstance(result['created_at'], str)

        # Test deserialization
        result = schema.load({'created_at': '2023-01-15T10:30:00'})
        assert isinstance(result['created_at'], datetime)

    def test_decimal_field(self):
        """Test Decimal field type"""
        class DecimalSchema(Schema):
            price = DecimalField(places=2)

        schema = DecimalSchema()

        # Test decimal handling
        result = schema.load({'price': '19.99'})
        assert result['price'] == Decimal('19.99')
        assert isinstance(result['price'], Decimal)

        # Test serialization
        result = schema.dump({'price': Decimal('29.99')})
        assert result['price'] == '29.99'

    def test_dict_field(self):
        """Test Dict field type"""
        class DictSchema(Schema):
            metadata = Dict()

        schema = DictSchema()

        # Test dict field
        data = {'metadata': {'key1': 'value1', 'key2': 123}}
        result = schema.load(data)
        assert result['metadata'] == {'key1': 'value1', 'key2': 123}

    def test_email_field(self):
        """Test Email field type"""
        class EmailSchema(Schema):
            email_address = Email()

        schema = EmailSchema()

        # Valid email
        result = schema.load({'email_address': 'user@example.com'})
        assert result['email_address'] == 'user@example.com'

        # Invalid email
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'email_address': 'not-an-email'})
        assert 'email_address' in exc_info.value.messages

    def test_float_field(self):
        """Test Float field type"""
        class FloatSchema(Schema):
            temperature = Float()

        schema = FloatSchema()

        # Test float conversion
        result = schema.load({'temperature': '98.6'})
        assert result['temperature'] == 98.6
        assert isinstance(result['temperature'], float)

    def test_uuid_field(self):
        """Test UUID field type"""
        class UUIDSchema(Schema):
            id = UUID()

        schema = UUIDSchema()

        # Test UUID
        test_uuid = uuid.uuid4()
        result = schema.dump({'id': test_uuid})
        assert result['id'] == str(test_uuid)

        # Test deserialization
        uuid_str = 'f47ac10b-58cc-4372-a567-0e02b2c3d479'
        result = schema.load({'id': uuid_str})
        assert isinstance(result['id'], uuid.UUID)

    def test_url_field(self):
        """Test URL field type"""
        class URLSchema(Schema):
            website = URL()

        schema = URLSchema()

        # Valid URL
        result = schema.load({'website': 'https://example.com'})
        assert result['website'] == 'https://example.com'

        # Invalid URL
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'website': 'not a url'})
        assert 'website' in exc_info.value.messages

    def test_ip_fields(self):
        """Test IP, IPv4, and IPv6 field types"""
        class IPSchema(Schema):
            any_ip = IP()
            ipv4_addr = IPv4()
            ipv6_addr = IPv6()

        schema = IPSchema()

        # Test IPv4
        result = schema.load({
            'any_ip': '192.168.1.1',
            'ipv4_addr': '10.0.0.1',
            'ipv6_addr': '2001:db8::8a2e:370:7334'
        })
        assert result['any_ip'] == '192.168.1.1'
        assert result['ipv4_addr'] == '10.0.0.1'
        assert result['ipv6_addr'] == '2001:db8::8a2e:370:7334'

        # Invalid IPv4 in IPv6 field
        with pytest.raises(ValidationError) as exc_info:
            schema.load({'ipv6_addr': '192.168.1.1'})
        assert 'ipv6_addr' in exc_info.value.messages

    def test_time_field(self):
        """Test Time field type"""
        class TimeSchema(Schema):
            meeting_time = Time()

        schema = TimeSchema()

        # Test time
        test_time = time(14, 30, 0)
        result = schema.dump({'meeting_time': test_time})
        assert result['meeting_time'] == '14:30:00'

        # Test deserialization
        result = schema.load({'meeting_time': '09:15:00'})
        assert isinstance(result['meeting_time'], time)
        assert result['meeting_time'].hour == 9
        assert result['meeting_time'].minute == 15

    def test_timedelta_field(self):
        """Test TimeDelta field type"""
        class TimeDeltaSchema(Schema):
            duration = TimeDelta()

        schema = TimeDeltaSchema()

        # Test timedelta
        delta = timedelta(hours=2, minutes=30)
        result = schema.dump({'duration': delta})
        # TimeDelta serializes to total seconds
        assert result['duration'] == 9000  # 2.5 hours in seconds

        # Test deserialization
        result = schema.load({'duration': 3600})  # 1 hour
        assert isinstance(result['duration'], timedelta)
        assert result['duration'].total_seconds() == 3600

    def test_tuple_field(self):
        """Test Tuple field type"""
        class TupleSchema(Schema):
            coordinates = Tuple((Float(), Float()))

        schema = TupleSchema()

        # Test tuple
        result = schema.load({'coordinates': [40.7128, -74.0060]})
        assert result['coordinates'] == (40.7128, -74.0060)
        assert isinstance(result['coordinates'], tuple)

    def test_constant_field(self):
        """Test Constant field type"""
        class ConstantSchema(Schema):
            version = Constant('1.0')
            api_type = Constant('REST')

        schema = ConstantSchema()

        # Constant fields always return their constant value
        result = schema.dump({})
        assert result['version'] == '1.0'
        assert result['api_type'] == 'REST'

        # Loading ignores input for constant fields
        result = schema.load({'version': '2.0', 'api_type': 'GraphQL'})
        assert result['version'] == '1.0'
        assert result['api_type'] == 'REST'

    def test_raw_field(self):
        """Test Raw field type"""
        class RawSchema(Schema):
            raw_data = Raw()

        schema = RawSchema()

        # Raw field passes data through unchanged
        test_data = {'nested': {'complex': 'data'}, 'list': [1, 2, 3]}
        result = schema.load({'raw_data': test_data})
        assert result['raw_data'] == test_data

    def test_function_field(self):
        """Test Function field type"""
        class FunctionSchema(Schema):
            full_name = Function(lambda obj: f"{obj.get('first')} {obj.get('last')}")

        schema = FunctionSchema()

        # Function field uses callable for serialization
        result = schema.dump({'first': 'John', 'last': 'Doe'})
        assert result['full_name'] == 'John Doe'

    def test_method_field(self):
        """Test Method field type"""
        class MethodSchema(Schema):
            display_name = Method('get_display_name')

            def get_display_name(self, obj):
                return f"{obj.get('name')} ({obj.get('role')})"

        schema = MethodSchema()

        # Method field calls schema method
        result = schema.dump({'name': 'Alice', 'role': 'Admin'})
        assert result['display_name'] == 'Alice (Admin)'

    def test_enum_field(self):
        """Test Enum field type"""
        class Status(Enum):
            PENDING = 'pending'
            APPROVED = 'approved'
            REJECTED = 'rejected'

        class EnumSchema(Schema):
            status = EnumField(Status)

        schema = EnumSchema()

        # Test enum serialization
        result = schema.dump({'status': Status.APPROVED})
        assert result['status'] == 'approved'

        # Test enum deserialization
        result = schema.load({'status': 'pending'})
        assert result['status'] == Status.PENDING
        assert isinstance(result['status'], Status)

    def test_pluck_field(self):
        """Test Pluck field type"""
        class Author(Schema):
            id = Integer()
            name = String()
            email = Email()

        class BookSchema(Schema):
            title = String()
            author_names = Pluck(Author, 'name', many=True)

        schema = BookSchema()

        # Pluck extracts specific field from nested objects
        book_data = {
            'title': 'Test Book',
            'author_names': [
                {'id': 1, 'name': 'Author 1', 'email': 'a1@example.com'},
                {'id': 2, 'name': 'Author 2', 'email': 'a2@example.com'}
            ]
        }
        result = schema.dump(book_data)
        assert result['author_names'] == ['Author 1', 'Author 2']


class TestWebArgsFields:
    """Tests for webargs-specific field types"""

    def test_delimited_list_field(self):
        """Test DelimitedList field type from webargs"""
        class QuerySchema(Schema):
            tags = DelimitedList(String())

        schema = QuerySchema()

        # Test comma-separated list
        result = schema.load({'tags': 'python,flask,api'})
        assert result['tags'] == ['python', 'flask', 'api']

        # Test already a list
        result = schema.load({'tags': ['tag1', 'tag2']})
        assert result['tags'] == ['tag1', 'tag2']

    def test_delimited_tuple_field(self):
        """Test DelimitedTuple field type from webargs"""
        class QuerySchema(Schema):
            range = DelimitedTuple((Integer(), Integer()))

        schema = QuerySchema()

        # Test comma-separated tuple
        result = schema.load({'range': '10,20'})
        assert result['range'] == (10, 20)
        assert isinstance(result['range'], tuple)


class TestFlaskMarshmallowFields:
    """Tests for Flask-Marshmallow specific field types"""

    @pytest.fixture
    def app(self):
        """Create a Flask app for testing Flask-specific fields"""
        from flask import Flask
        app = Flask(__name__)
        app.config['SERVER_NAME'] = 'localhost'
        return app

    def test_config_field(self, app):
        """Test Config field type"""
        class ConfigSchema(Schema):
            debug = Config('DEBUG')
            server_name = Config('SERVER_NAME')

        with app.app_context():
            schema = ConfigSchema()

            # Config field reads from Flask config
            result = schema.dump({})
            assert result['debug'] == app.config['DEBUG']
            assert result['server_name'] == 'localhost'

    def test_url_for_field(self, app):
        """Test URLFor field type"""
        @app.route('/user/<int:id>')
        def user(id):
            return str(id)

        class UserSchema(Schema):
            url = URLFor('user', values={'id': '<id>'})

        with app.test_request_context():
            schema = UserSchema()

            # URLFor generates URLs
            result = schema.dump({'id': 123})
            assert '/user/123' in result['url']

    def test_absolute_url_for_field(self, app):
        """Test AbsoluteURLFor field type"""
        @app.route('/api/resource/<int:id>')
        def resource(id):
            return str(id)

        class ResourceSchema(Schema):
            absolute_url = AbsoluteURLFor('resource', values={'id': '<id>'})

        with app.test_request_context():
            schema = ResourceSchema()

            # AbsoluteURLFor generates absolute URLs
            result = schema.dump({'id': 456})
            assert result['absolute_url'].startswith('http://')
            assert '/api/resource/456' in result['absolute_url']


class TestFieldCombinations:
    """Tests for complex field combinations used in real scenarios"""

    def test_nested_with_many(self):
        """Test Nested field with many=True for collections"""
        class ItemSchema(Schema):
            id = Integer()
            name = String()

        class OrderSchema(Schema):
            order_id = Integer()
            items = Nested(ItemSchema, many=True)

        schema = OrderSchema()

        order_data = {
            'order_id': 1001,
            'items': [
                {'id': 1, 'name': 'Item 1'},
                {'id': 2, 'name': 'Item 2'}
            ]
        }

        result = schema.dump(order_data)
        assert result['order_id'] == 1001
        assert len(result['items']) == 2

    def test_field_with_load_and_dump_defaults(self):
        """Test fields with load_default and dump_default"""
        class DefaultSchema(Schema):
            page = Integer(load_default=1)
            per_page = Integer(load_default=20)
            status = String(dump_default='active')

        schema = DefaultSchema()

        # Test load defaults
        result = schema.load({})
        assert result['page'] == 1
        assert result['per_page'] == 20

        # Test dump defaults
        result = schema.dump({'page': 2})
        assert result['status'] == 'active'

    def test_required_and_allow_none(self):
        """Test required fields that allow None values"""
        class NullableSchema(Schema):
            required_field = String(required=True)
            optional_nullable = String(allow_none=True)
            required_nullable = String(required=True, allow_none=True)

        schema = NullableSchema()

        # Required field must be present
        with pytest.raises(ValidationError) as exc_info:
            schema.load({})
        assert 'required_field' in exc_info.value.messages

        # Required nullable can be None
        result = schema.load({
            'required_field': 'value',
            'required_nullable': None
        })
        assert result['required_nullable'] is None

        # Optional nullable
        result = schema.load({
            'required_field': 'value',
            'optional_nullable': None
        })
        assert result['optional_nullable'] is None


# Integration test simulating real example scenarios
class TestRealWorldScenarios:
    """Integration tests based on actual example usage patterns"""

    def test_pet_api_scenario(self):
        """Complete test mimicking basic/app.py pet API"""
        class PetIn(Schema):
            name = String(required=True, validate=Length(0, 10))
            category = String(required=True, validate=OneOf(['dog', 'cat']))

        class PetOut(Schema):
            id = Integer()
            name = String()
            category = String()

        # Test input validation
        input_schema = PetIn()
        valid_pet = {'name': 'Fluffy', 'category': 'cat'}
        result = input_schema.load(valid_pet)
        assert result['name'] == 'Fluffy'

        # Test output serialization
        output_schema = PetOut()
        pet_data = {'id': 1, 'name': 'Fluffy', 'category': 'cat'}
        result = output_schema.dump(pet_data)
        assert result['id'] == 1
        assert result['name'] == 'Fluffy'

    def test_pagination_scenario(self):
        """Complete test mimicking pagination/app.py"""
        class PetOut(Schema):
            id = Integer()
            name = String()
            category = String()

        class PaginationSchema(Schema):
            page = Integer()
            per_page = Integer()
            pages = Integer()
            total = Integer()
            next = Integer(allow_none=True)
            prev = Integer(allow_none=True)

        class PetsOut(Schema):
            pets = List(Nested(PetOut))
            pagination = Nested(PaginationSchema)

        # Test paginated response
        schema = PetsOut()
        paginated_data = {
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

        result = schema.dump(paginated_data)
        assert len(result['pets']) == 2
        assert result['pagination']['total'] == 100
        assert result['pagination']['prev'] is None

    def test_file_upload_scenario(self):
        """Complete test mimicking file_upload/app.py"""
        class ProfileIn(Schema):
            name = String()
            avatar = File()

        schema = ProfileIn()

        # Create mock file
        file_obj = io.BytesIO(b'fake avatar image data')
        file_storage = FileStorage(
            stream=file_obj,
            filename='avatar.jpg',
            content_type='image/jpeg'
        )

        # Test form with file
        form_data = {
            'name': 'John Smith',
            'avatar': file_storage
        }

        result = schema.load(form_data)
        assert result['name'] == 'John Smith'
        assert result['avatar'] == file_storage
        assert result['avatar'].filename == 'avatar.jpg'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
