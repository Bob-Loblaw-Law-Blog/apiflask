import pytest

from apiflask.exceptions import abort
from marshmallow import ValidationError as MarshmallowValidationError
from apiflask import APIFlask
from apiflask.exceptions import HTTPError, _ValidationError
from apiflask.fields import String
from apiflask import Schema


@pytest.mark.parametrize(
    'kwargs',
    [
        {},
        {'message': 'bad'},
        {'message': 'bad', 'detail': {'location': 'json'}},
        {'message': 'bad', 'detail': {'location': 'json'}, 'headers': {'X-FOO': 'bar'}},
    ],
)
def test_httperror(app, client, kwargs):
    @app.get('/foo')
    def foo():
        raise HTTPError(400, **kwargs)

    @app.get('/bar')
    def bar():
        raise HTTPError

    rv = client.get('/foo')
    assert rv.status_code == 400
    if 'message' not in kwargs:
        assert rv.json['message'] == 'Bad Request'
    else:
        assert rv.json['message'] == 'bad'
    if 'detail' not in kwargs:
        assert rv.json['detail'] == {}
    else:
        assert rv.json['detail'] == {'location': 'json'}
    if 'headers' in kwargs:
        assert rv.headers['X-FOO'] == 'bar'

    # test default error status code
    rv = client.get('/bar')
    assert rv.status_code == 500
    assert rv.json['message'] == 'Internal Server Error'
    assert rv.json['detail'] == {}


@pytest.mark.parametrize(
    'kwargs',
    [
        {},
        {'message': 'missing'},
        {'message': 'missing', 'detail': {'location': 'query'}},
        {'message': 'missing', 'detail': {'location': 'query'}, 'headers': {'X-BAR': 'foo'}},
        {'message': 'missing', 'extra_data': {'code': 123, 'status': 'not_found'}},
    ],
)
def test_abort(app, client, kwargs):
    @app.get('/bar')
    def bar():
        abort(404, **kwargs)

    rv = client.get('/bar')
    assert rv.status_code == 404
    if 'message' not in kwargs:
        assert rv.json['message'] == 'Not Found'
    else:
        assert rv.json['message'] == 'missing'
    if 'detail' not in kwargs:
        assert rv.json['detail'] == {}
    else:
        assert rv.json['detail'] == {'location': 'query'}
    if 'headers' in kwargs:
        assert rv.headers['X-BAR'] == 'foo'
    if 'extra_data' in kwargs:
        assert rv.json['code'] == 123
        assert rv.json['status'] == 'not_found'


@pytest.mark.parametrize(
    'kwargs',
    [
        {},
        {'message': 'bad'},
        {'message': 'bad', 'detail': {'location': 'json'}},
        {'message': 'bad', 'detail': {'location': 'json'}, 'headers': {'X-FOO': 'bar'}},
    ],
)
def test_default_error_handler(app, kwargs):
    error = HTTPError(400, **kwargs)
    rv = app._error_handler(error)
    assert rv[1] == 400
    if 'message' not in kwargs:
        assert rv[0]['message'] == 'Bad Request'
    else:
        assert rv[0]['message'] == 'bad'
    if 'detail' not in kwargs:
        assert rv[0]['detail'] == {}
    else:
        assert rv[0]['detail'] == {'location': 'json'}
    if 'headers' in kwargs:
        assert rv[2]['X-FOO'] == 'bar'


def test_invalid_error_status_code():
    with pytest.raises(LookupError):
        abort(200)

    with pytest.raises(LookupError):
        raise HTTPError(204)


def test_custom_error_classes(app, client):
    class PetDown(HTTPError):
        status_code = 400
        message = 'The pet is down.'
        extra_data = {'error_code': '123', 'error_docs': 'https://example.com/docs/down'}
        headers = {'X-Foo': 'bar'}

    class PetNotFound(HTTPError):
        status_code = 404
        message = 'The pet is gone.'
        extra_data = {'error_code': '345', 'error_docs': 'https://example.com/docs/gone'}

    @app.get('/foo')
    def foo():
        raise PetDown

    @app.get('/bar')
    def bar():
        raise PetNotFound

    rv = client.get('/foo')
    assert rv.status_code == 400
    assert rv.json['message'] == 'The pet is down.'
    assert rv.json['error_code'] == '123'
    assert rv.json['error_docs'] == 'https://example.com/docs/down'
    assert rv.json['detail'] == {}
    assert rv.headers['X-FOO'] == 'bar'

    rv = client.get('/bar')
    assert rv.status_code == 404
    assert rv.json['message'] == 'The pet is gone.'
    assert rv.json['error_code'] == '345'
    assert rv.json['error_docs'] == 'https://example.com/docs/gone'
    assert rv.json['detail'] == {}

class TestValidationError:
    """Test suite for _ValidationError exception class."""

    @pytest.fixture
    def app(self):
        """Create a test app."""
        return APIFlask(__name__)

    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()

    def test_validation_error_basic_initialization(self, app):
        """Test basic initialization of _ValidationError with default config values."""
        with app.app_context():
            # Create a marshmallow validation error
            marshmallow_error = MarshmallowValidationError({'field1': ['This field is required.']})

            # Initialize _ValidationError
            validation_error = _ValidationError(marshmallow_error)

            # Check that it inherits from HTTPError properly
            assert isinstance(validation_error, HTTPError)
            assert isinstance(validation_error, _ValidationError)

            # Check default values from config
            assert validation_error.status_code == 422  # VALIDATION_ERROR_STATUS_CODE
            assert validation_error.message == 'Validation error'  # VALIDATION_ERROR_DESCRIPTION
            assert validation_error.detail == {'field1': ['This field is required.']}
            assert validation_error.headers == {}
            assert validation_error.extra_data == {}

    def test_validation_error_custom_status_code(self, app):
        """Test _ValidationError with custom status code override."""
        with app.app_context():
            marshmallow_error = MarshmallowValidationError({'name': ['Invalid name format.']})

            # Override status code
            validation_error = _ValidationError(marshmallow_error, error_status_code=400)

            assert validation_error.status_code == 400
            assert validation_error.message == 'Validation error'  # Still uses config message
            assert validation_error.detail == {'name': ['Invalid name format.']}

    def test_validation_error_custom_headers(self, app):
        """Test _ValidationError with custom headers."""
        with app.app_context():
            marshmallow_error = MarshmallowValidationError({'email': ['Invalid email address.']})
            custom_headers = {'X-Validation-Version': '1.0', 'X-Error-Source': 'marshmallow'}

            validation_error = _ValidationError(marshmallow_error, error_headers=custom_headers)

            assert validation_error.status_code == 422
            assert validation_error.message == 'Validation error'
            assert validation_error.detail == {'email': ['Invalid email address.']}
            assert validation_error.headers == custom_headers

    def test_validation_error_both_custom_params(self, app):
        """Test _ValidationError with both custom status code and headers."""
        with app.app_context():
            marshmallow_error = MarshmallowValidationError({
                'age': ['Must be at least 18.'],
                'password': ['Password too weak.']
            })
            custom_headers = {'X-Custom': 'test'}

            validation_error = _ValidationError(
                marshmallow_error,
                error_status_code=400,
                error_headers=custom_headers
            )

            assert validation_error.status_code == 400
            assert validation_error.message == 'Validation error'
            assert validation_error.detail == {
                'age': ['Must be at least 18.'],
                'password': ['Password too weak.']
            }
            assert validation_error.headers == custom_headers

    def test_validation_error_empty_marshmallow_error(self, app):
        """Test _ValidationError with empty marshmallow error messages."""
        with app.app_context():
            marshmallow_error = MarshmallowValidationError({})

            validation_error = _ValidationError(marshmallow_error)

            assert validation_error.status_code == 422
            assert validation_error.message == 'Validation error'
            assert validation_error.detail == {}

    def test_validation_error_complex_marshmallow_error(self, app):
        """Test _ValidationError with complex nested validation error structure."""
        with app.app_context():
            # Complex validation error with nested fields
            complex_error = MarshmallowValidationError({
                'user': {
                    'profile': {
                        'name': ['Name is required.'],
                        'age': ['Must be a positive integer.']
                    },
                    'contact': ['Invalid contact information.']
                },
                'settings': ['Invalid settings format.']
            })

            validation_error = _ValidationError(complex_error)

            assert validation_error.status_code == 422
            assert validation_error.detail == {
                'user': {
                    'profile': {
                        'name': ['Name is required.'],
                        'age': ['Must be a positive integer.']
                    },
                    'contact': ['Invalid contact information.']
                },
                'settings': ['Invalid settings format.']
            }

    def test_validation_error_with_custom_config(self, app):
        """Test _ValidationError behavior with custom app configuration."""
        # Set custom config values
        app.config['VALIDATION_ERROR_STATUS_CODE'] = 400
        app.config['VALIDATION_ERROR_DESCRIPTION'] = 'Custom validation failed'

        with app.app_context():
            marshmallow_error = MarshmallowValidationError({'test': ['Test error.']})

            validation_error = _ValidationError(marshmallow_error)

            assert validation_error.status_code == 400
            assert validation_error.message == 'Custom validation failed'
            assert validation_error.detail == {'test': ['Test error.']}

        # Reset to defaults
        app.config['VALIDATION_ERROR_STATUS_CODE'] = 422
        app.config['VALIDATION_ERROR_DESCRIPTION'] = 'Validation error'

    def test_validation_error_override_takes_precedence(self, app):
        """Test that status code override takes precedence over config."""
        # Set custom config value
        app.config['VALIDATION_ERROR_STATUS_CODE'] = 400

        with app.app_context():
            marshmallow_error = MarshmallowValidationError({'field': ['Error.']})

            # Override should take precedence
            validation_error = _ValidationError(marshmallow_error, error_status_code=418)

            assert validation_error.status_code == 418  # Override value, not config value
            assert validation_error.message == 'Validation error'  # Still uses config message

        # Reset to default
        app.config['VALIDATION_ERROR_STATUS_CODE'] = 422

    def test_validation_error_none_headers(self, app):
        """Test _ValidationError with explicitly None headers."""
        with app.app_context():
            marshmallow_error = MarshmallowValidationError({'test': ['Test error.']})

            validation_error = _ValidationError(marshmallow_error, error_headers=None)

            assert validation_error.headers == {}

    def test_validation_error_inheritance_properties(self, app):
        """Test that _ValidationError properly inherits HTTPError properties."""
        with app.app_context():
            marshmallow_error = MarshmallowValidationError({'field': ['Error message.']})

            validation_error = _ValidationError(marshmallow_error)

            # Should have all HTTPError properties
            assert hasattr(validation_error, 'status_code')
            assert hasattr(validation_error, 'message')
            assert hasattr(validation_error, 'detail')
            assert hasattr(validation_error, 'headers')
            assert hasattr(validation_error, 'extra_data')

            # extra_data should be empty dict by default
            assert validation_error.extra_data == {}

    def test_validation_error_list_errors(self, app):
        """Test _ValidationError with list-based validation errors."""
        with app.app_context():
            marshmallow_error = MarshmallowValidationError({
                'items': {
                    0: {'name': ['Required field missing.']},
                    1: {'age': ['Must be positive.']}
                }
            })

            validation_error = _ValidationError(marshmallow_error)

            assert validation_error.detail == {
                'items': {
                    0: {'name': ['Required field missing.']},
                    1: {'age': ['Must be positive.']}
                }
            }

    def test_validation_error_integration_with_flask_parser(self, app, client):
        """Test _ValidationError integration in a real Flask request context."""

        class UserSchema(Schema):
            name = String(required=True)
            email = String(required=True)

        @app.post('/test-validation')
        @app.input(UserSchema, location='json')
        def test_validation_endpoint(json_data):
            return {'received': json_data}

        # Test with missing required fields
        rv = client.post('/test-validation', json={})
        assert rv.status_code == 422
        assert rv.json['message'] == 'Validation error'
        assert 'detail' in rv.json
        assert 'json' in rv.json['detail']
        assert 'name' in rv.json['detail']['json']
        assert 'email' in rv.json['detail']['json']

        # Test with partial data
        rv = client.post('/test-validation', json={'name': 'John'})
        assert rv.status_code == 422
        assert 'email' in rv.json['detail']['json']

        # Test with valid data
        rv = client.post('/test-validation', json={'name': 'John', 'email': 'john@example.com'})
        assert rv.status_code == 200

    def test_validation_error_raised_by_handle_error(self, app):
        """Test that FlaskParser.handle_error specifically raises _ValidationError."""
        from apiflask.scaffold import FlaskParser
        from flask import request as flask_request

        class TestSchema(Schema):
            required_field = String(required=True)

        parser = FlaskParser()

        with app.test_request_context('/test', method='POST', json={}, content_type='application/json'):
            # Create a validation error like webargs would
            # Note: webargs wraps field errors with the location
            error_dict = {'json': {'required_field': ['Missing data for required field.']}}
            marshmallow_error = MarshmallowValidationError(error_dict)

            # Test that handle_error raises _ValidationError
            with pytest.raises(_ValidationError) as exc_info:
                parser.handle_error(
                    marshmallow_error,
                    flask_request,
                    TestSchema(),
                    error_status_code=None,  # webargs passes None by default
                    error_headers=None  # webargs passes None by default
                )

            # Verify the raised exception
            raised_error = exc_info.value
            assert isinstance(raised_error, _ValidationError)
            assert isinstance(raised_error, HTTPError)
            assert raised_error.status_code == 422  # From config since None was passed
            assert raised_error.message == 'Validation error'
            assert raised_error.detail == error_dict

    def test_validation_error_with_different_locations(self, app):
        """Test that _ValidationError works correctly with different webargs locations."""
        from apiflask.scaffold import FlaskParser
        from apiflask.fields import Integer
        from flask import request as flask_request

        parser = FlaskParser()

        # Test query location error format
        with app.test_request_context('/test?incomplete=true'):
            # Simulate webargs query validation error
            error_dict = {'query': {
                'page': ['Missing data for required field.'],
                'size': ['Missing data for required field.']
            }}
            marshmallow_error = MarshmallowValidationError(error_dict)

            with pytest.raises(_ValidationError) as exc_info:
                parser.handle_error(
                    marshmallow_error,
                    flask_request,
                    Schema(),
                    error_status_code=None,
                    error_headers=None
                )

            raised_error = exc_info.value
            assert raised_error.status_code == 422
            assert raised_error.detail == error_dict
            assert 'query' in raised_error.detail
            assert 'page' in raised_error.detail['query']
            assert 'size' in raised_error.detail['query']

    def test_validation_error_with_complex_validation(self, app):
        """Test _ValidationError with complex validation scenarios."""
        from apiflask.scaffold import FlaskParser
        from flask import request as flask_request

        parser = FlaskParser()

        # Simulate complex validation errors that webargs would produce
        error_dict = {'json': {
            'username': ['Shorter than minimum length 3.'],
            'email': ['Not a valid email address.'],
            'password': ['Shorter than minimum length 8.']
        }}
        marshmallow_error = MarshmallowValidationError(error_dict)

        with app.test_request_context('/test', method='POST', json={}, content_type='application/json'):
            with pytest.raises(_ValidationError) as exc_info:
                parser.handle_error(
                    marshmallow_error,
                    flask_request,
                    Schema(),
                    error_status_code=None,
                    error_headers=None
                )

            raised_error = exc_info.value
            assert isinstance(raised_error, _ValidationError)

            # Check that all validation errors are captured
            assert raised_error.detail == error_dict
            json_errors = raised_error.detail.get('json', {})
            assert 'username' in json_errors
            assert 'email' in json_errors
            assert 'password' in json_errors

            # Verify it uses the configured status code and message
            assert raised_error.status_code == 422
            assert raised_error.message == 'Validation error'

