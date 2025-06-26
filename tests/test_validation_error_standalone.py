"""
Standalone test script for _ValidationError exception.
This can be run independently to verify the test coverage.
"""

import sys
import os

# Add the source to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'inputs', 'apiflask', 'src'))

from unittest.mock import Mock, patch
from marshmallow import ValidationError as MarshmallowValidationError


def test_validation_error_basic():
    """Test basic _ValidationError functionality."""
    # Mock flask's current_app
    mock_app = Mock()
    mock_app.config = {
        'VALIDATION_ERROR_STATUS_CODE': 422,
        'VALIDATION_ERROR_DESCRIPTION': 'Validation error'
    }

    with patch('apiflask.exceptions.current_app', mock_app):
        from apiflask.exceptions import _ValidationError, HTTPError

        # Test 1: Basic validation error
        marshmallow_error = MarshmallowValidationError({'field1': ['Required field']})
        val_error = _ValidationError(marshmallow_error)

        assert isinstance(val_error, HTTPError)
        assert val_error.status_code == 422
        assert val_error.message == 'Validation error'
        assert val_error.detail == {'field1': ['Required field']}
        print("✓ Test 1 passed: Basic validation error")

        # Test 2: Custom status code override
        val_error2 = _ValidationError(marshmallow_error, error_status_code=400)
        assert val_error2.status_code == 400
        print("✓ Test 2 passed: Status code override")

        # Test 3: Custom headers
        custom_headers = {'X-Custom': 'test'}
        val_error3 = _ValidationError(marshmallow_error, error_headers=custom_headers)
        assert val_error3.headers == custom_headers
        print("✓ Test 3 passed: Custom headers")

        # Test 4: Both status code and headers
        val_error4 = _ValidationError(
            marshmallow_error,
            error_status_code=403,
            error_headers={'X-Test': 'value'}
        )
        assert val_error4.status_code == 403
        assert val_error4.headers == {'X-Test': 'value'}
        print("✓ Test 4 passed: Both status code and headers")

        # Test 5: Nested validation errors
        nested_errors = {
            'user': {
                'name': ['Missing required field'],
                'email': ['Invalid email']
            }
        }
        nested_marshmallow_error = MarshmallowValidationError(nested_errors)
        val_error5 = _ValidationError(nested_marshmallow_error)
        assert val_error5.detail == nested_errors
        print("✓ Test 5 passed: Nested validation errors")

        # Test 6: Empty validation errors
        empty_error = MarshmallowValidationError({})
        val_error6 = _ValidationError(empty_error)
        assert val_error6.detail == {}
        print("✓ Test 6 passed: Empty validation errors")

        # Test 7: String validation error
        string_error = MarshmallowValidationError('Invalid format')
        val_error7 = _ValidationError(string_error)
        assert val_error7.detail == 'Invalid format'
        print("✓ Test 7 passed: String validation error")

        # Test 8: Config changes
        mock_app.config['VALIDATION_ERROR_STATUS_CODE'] = 400
        mock_app.config['VALIDATION_ERROR_DESCRIPTION'] = 'Bad Request'

        val_error8 = _ValidationError(marshmallow_error)
        assert val_error8.status_code == 400
        assert val_error8.message == 'Bad Request'
        print("✓ Test 8 passed: Config changes")

        print("\n✅ All tests passed successfully!")


if __name__ == "__main__":
    test_validation_error_basic()
