"""
Comprehensive Error Handling Example for APIFlask
================================================

This example demonstrates advanced error handling patterns including:
- Custom exception classes
- Validation error formatting
- Global error handlers
- Error logging and monitoring
- Client-friendly error responses
"""

import logging
import traceback
from datetime import datetime
from enum import Enum
from typing import Dict, Any, Optional

from apiflask import APIFlask, Schema, HTTPError, abort
from apiflask.fields import Integer, String, Email, DateTime, List, Nested
from apiflask.validators import Length, Range, OneOf
from marshmallow import ValidationError, validates_schema, validate
from werkzeug.exceptions import HTTPException


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = APIFlask(__name__)
app.config['ERROR_INCLUDE_MESSAGE'] = True

# Simulated database
users_db = []
user_id_counter = 0


class ErrorCode(Enum):
    """Standardized error codes for the API."""
    VALIDATION_ERROR = "VALIDATION_ERROR"
    DUPLICATE_RESOURCE = "DUPLICATE_RESOURCE"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    BUSINESS_RULE_VIOLATION = "BUSINESS_RULE_VIOLATION"
    EXTERNAL_SERVICE_ERROR = "EXTERNAL_SERVICE_ERROR"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"
    AUTHENTICATION_REQUIRED = "AUTHENTICATION_REQUIRED"
    INSUFFICIENT_PERMISSIONS = "INSUFFICIENT_PERMISSIONS"
    INVALID_STATE = "INVALID_STATE"


class APIError(HTTPError):
    """Custom base exception for all API errors."""
    
    def __init__(
        self, 
        status_code: int, 
        message: str, 
        error_code: ErrorCode = None,
        details: Dict[str, Any] = None,
        suggestions: List[str] = None
    ):
        self.error_code = error_code or ErrorCode.VALIDATION_ERROR
        self.suggestions = suggestions or []
        
        extra_data = {
            'error_code': self.error_code.value,
            'suggestions': self.suggestions,
            'timestamp': datetime.utcnow().isoformat(),
        }
        
        if details:
            extra_data['details'] = details
            
        super().__init__(
            status_code=status_code,
            message=message,
            extra_data=extra_data
        )


class ValidationAPIError(APIError):
    """Specialized error for validation failures."""
    
    def __init__(self, field_errors: Dict[str, List[str]], message: str = "Validation failed"):
        super().__init__(
            status_code=422,
            message=message,
            error_code=ErrorCode.VALIDATION_ERROR,
            details={'field_errors': field_errors},
            suggestions=[
                "Check the required fields and their formats",
                "Ensure all data types match the expected format"
            ]
        )


class BusinessRuleError(APIError):
    """Error for business logic violations."""
    
    def __init__(self, message: str, rule_name: str, context: Dict[str, Any] = None):
        super().__init__(
            status_code=400,
            message=message,
            error_code=ErrorCode.BUSINESS_RULE_VIOLATION,
            details={
                'violated_rule': rule_name,
                'context': context or {}
            },
            suggestions=["Review the business rules and requirements"]
        )


class ResourceNotFoundError(APIError):
    """Error for missing resources."""
    
    def __init__(self, resource_type: str, resource_id: Any):
        super().__init__(
            status_code=404,
            message=f"{resource_type} with ID {resource_id} not found",
            error_code=ErrorCode.RESOURCE_NOT_FOUND,
            details={
                'resource_type': resource_type,
                'resource_id': str(resource_id)
            },
            suggestions=[
                f"Verify that the {resource_type.lower()} exists",
                "Check if the ID is correct"
            ]
        )


class DuplicateResourceError(APIError):
    """Error for duplicate resource creation attempts."""
    
    def __init__(self, resource_type: str, conflicting_field: str, value: Any):
        super().__init__(
            status_code=409,
            message=f"{resource_type} with {conflicting_field} '{value}' already exists",
            error_code=ErrorCode.DUPLICATE_RESOURCE,
            details={
                'resource_type': resource_type,
                'conflicting_field': conflicting_field,
                'conflicting_value': str(value)
            },
            suggestions=[
                f"Use a different {conflicting_field}",
                f"Update the existing {resource_type.lower()} instead"
            ]
        )


# Schemas with comprehensive validation
class UserCreateSchema(Schema):
    username = String(
        required=True, 
        validate=[
            Length(3, 20),
            validate.Regexp(
                r'^[a-zA-Z0-9_]+$',
                error='Username can only contain letters, numbers, and underscores'
            )
        ]
    )
    email = Email(required=True)
    age = Integer(validate=Range(13, 120), required=True)
    role = String(validate=OneOf(['admin', 'user', 'moderator']), load_default='user')
    
    @validates_schema
    def validate_business_rules(self, data, **kwargs):
        """Custom validation for business rules."""
        # Example: Admin users must be at least 18
        if data.get('role') == 'admin' and data.get('age', 0) < 18:
            raise ValidationError(
                'Admin users must be at least 18 years old',
                field_name='age'
            )
        
        # Example: Check for offensive usernames (simplified)
        offensive_words = ['badword', 'offensive']
        username = data.get('username', '').lower()
        if any(word in username for word in offensive_words):
            raise ValidationError(
                'Username contains inappropriate content',
                field_name='username'
            )


class UserUpdateSchema(UserCreateSchema):
    """Schema for updating users - all fields optional."""
    class Meta:
        partial = True
    
    username = String(validate=[
        Length(3, 20),
        validate.Regexp(
            r'^[a-zA-Z0-9_]+$',
            error='Username can only contain letters, numbers, and underscores'
        )
    ])
    email = Email()
    age = Integer(validate=Range(13, 120))
    role = String(validate=OneOf(['admin', 'user', 'moderator']))


class UserResponseSchema(Schema):
    id = Integer()
    username = String()
    email = String()
    age = Integer()
    role = String()
    created_at = DateTime()


class ErrorDetailSchema(Schema):
    """Schema for error response details."""
    field_errors = Dict(keys=String(), values=List(String()))
    violated_rule = String()
    context = Dict()
    resource_type = String()
    resource_id = String()
    conflicting_field = String()
    conflicting_value = String()


class ErrorResponseSchema(Schema):
    """Schema for all error responses."""
    message = String(required=True)
    error_code = String(required=True)
    suggestions = List(String())
    timestamp = DateTime(required=True)
    details = Nested(ErrorDetailSchema, allow_none=True)


# Routes with comprehensive error handling
@app.get('/')
def index():
    """Health check endpoint."""
    return {'message': 'Error handling example API is running', 'status': 'healthy'}


@app.get('/users')
@app.output(UserResponseSchema(many=True))
def get_users():
    """Get all users."""
    try:
        # Simulate potential error
        if len(users_db) > 100:  # Simulate too many users scenario
            raise APIError(
                status_code=507,
                message="Too many users in database",
                error_code=ErrorCode.EXTERNAL_SERVICE_ERROR,
                suggestions=["Implement pagination", "Contact administrator"]
            )
        
        return users_db
    except Exception as e:
        logger.error(f"Error fetching users: {str(e)}")
        raise


@app.get('/users/<int:user_id>')
@app.output(UserResponseSchema)
def get_user(user_id: int):
    """Get a specific user by ID."""
    user = next((u for u in users_db if u['id'] == user_id), None)
    if not user:
        raise ResourceNotFoundError('User', user_id)
    
    return user


@app.post('/users')
@app.input(UserCreateSchema)
@app.output(UserResponseSchema, status_code=201)
def create_user(json_data):
    """Create a new user with comprehensive validation."""
    global user_id_counter
    
    # Check for duplicate username
    if any(u['username'] == json_data['username'] for u in users_db):
        raise DuplicateResourceError('User', 'username', json_data['username'])
    
    # Check for duplicate email
    if any(u['email'] == json_data['email'] for u in users_db):
        raise DuplicateResourceError('User', 'email', json_data['email'])
    
    # Business rule: Only 3 admin users allowed
    if json_data['role'] == 'admin':
        admin_count = sum(1 for u in users_db if u['role'] == 'admin')
        if admin_count >= 3:
            raise BusinessRuleError(
                "Maximum number of admin users reached",
                rule_name="max_admin_users",
                context={'current_admin_count': admin_count, 'max_allowed': 3}
            )
    
    # Create user
    user_id_counter += 1
    new_user = {
        'id': user_id_counter,
        'username': json_data['username'],
        'email': json_data['email'],
        'age': json_data['age'],
        'role': json_data['role'],
        'created_at': datetime.utcnow()
    }
    
    users_db.append(new_user)
    logger.info(f"User created: {new_user['username']} (ID: {new_user['id']})")
    
    return new_user


@app.patch('/users/<int:user_id>')
@app.input(UserUpdateSchema)
@app.output(UserResponseSchema)
def update_user(user_id: int, json_data):
    """Update user with partial validation."""
    user = next((u for u in users_db if u['id'] == user_id), None)
    if not user:
        raise ResourceNotFoundError('User', user_id)
    
    # Check for duplicate username (if username is being updated)
    if 'username' in json_data:
        existing_user = next(
            (u for u in users_db if u['username'] == json_data['username'] and u['id'] != user_id),
            None
        )
        if existing_user:
            raise DuplicateResourceError('User', 'username', json_data['username'])
    
    # Check for duplicate email (if email is being updated)
    if 'email' in json_data:
        existing_user = next(
            (u for u in users_db if u['email'] == json_data['email'] and u['id'] != user_id),
            None
        )
        if existing_user:
            raise DuplicateResourceError('User', 'email', json_data['email'])
    
    # Business rule: Can't change role if user is the last admin
    if 'role' in json_data and user['role'] == 'admin' and json_data['role'] != 'admin':
        admin_count = sum(1 for u in users_db if u['role'] == 'admin')
        if admin_count <= 1:
            raise BusinessRuleError(
                "Cannot remove the last admin user",
                rule_name="preserve_last_admin",
                context={'current_admin_count': admin_count}
            )
    
    # Update user
    for field, value in json_data.items():
        user[field] = value
    
    logger.info(f"User updated: {user['username']} (ID: {user['id']})")
    return user


@app.delete('/users/<int:user_id>')
@app.output({}, status_code=204)
def delete_user(user_id: int):
    """Delete a user with business rule checks."""
    user = next((u for u in users_db if u['id'] == user_id), None)
    if not user:
        raise ResourceNotFoundError('User', user_id)
    
    # Business rule: Can't delete the last admin
    if user['role'] == 'admin':
        admin_count = sum(1 for u in users_db if u['role'] == 'admin')
        if admin_count <= 1:
            raise BusinessRuleError(
                "Cannot delete the last admin user",
                rule_name="preserve_last_admin",
                context={'current_admin_count': admin_count}
            )
    
    users_db.remove(user)
    logger.info(f"User deleted: {user['username']} (ID: {user['id']})")
    return ''


@app.get('/error-demo/<error_type>')
def demonstrate_error(error_type: str):
    """Endpoint to demonstrate different types of errors."""
    if error_type == 'validation':
        raise ValidationAPIError(
            {'email': ['Invalid email format'], 'age': ['Must be between 13 and 120']},
            "Multiple validation errors occurred"
        )
    elif error_type == 'not-found':
        raise ResourceNotFoundError('Product', 999)
    elif error_type == 'duplicate':
        raise DuplicateResourceError('User', 'email', 'test@example.com')
    elif error_type == 'business-rule':
        raise BusinessRuleError(
            "Cannot perform this action during maintenance mode",
            rule_name="maintenance_mode_restriction",
            context={'maintenance_until': '2024-01-01T12:00:00Z'}
        )
    elif error_type == 'custom':
        raise APIError(
            status_code=418,
            message="I'm a teapot",
            error_code=ErrorCode.INVALID_STATE,
            details={'teapot_type': 'ceramic'},
            suggestions=["Use a coffee maker instead", "Try again with a different beverage"]
        )
    else:
        raise APIError(
            status_code=400,
            message=f"Unknown error type: {error_type}",
            suggestions=["Use: validation, not-found, duplicate, business-rule, or custom"]
        )


# Global error handlers
@app.errorhandler(ValidationError)
def handle_validation_error(error):
    """Handle marshmallow validation errors."""
    logger.warning(f"Validation error: {error.messages}")
    
    # Transform marshmallow errors to our format
    field_errors = {}
    for field, messages in error.messages.items():
        if isinstance(messages, list):
            field_errors[field] = messages
        else:
            field_errors[field] = [str(messages)]
    
    raise ValidationAPIError(field_errors)


@app.errorhandler(APIError)
def handle_api_error(error):
    """Handle our custom API errors."""
    logger.error(
        f"API Error: {error.message}",
        extra={
            'error_code': error.error_code.value if hasattr(error, 'error_code') else 'UNKNOWN',
            'status_code': error.status_code
        }
    )
    
    response_data = {
        'message': error.message,
        **error.extra_data
    }
    
    return response_data, error.status_code


@app.errorhandler(HTTPException)
def handle_http_exception(error):
    """Handle standard HTTP exceptions."""
    logger.warning(f"HTTP Exception: {error}")
    
    return {
        'message': error.description,
        'error_code': 'HTTP_ERROR',
        'suggestions': ['Check your request format and try again'],
        'timestamp': datetime.utcnow().isoformat()
    }, error.code


@app.errorhandler(Exception)
def handle_unexpected_error(error):
    """Handle unexpected errors."""
    logger.error(
        f"Unexpected error: {str(error)}",
        extra={'traceback': traceback.format_exc()}
    )
    
    # Only include error details in debug mode
    if app.debug:
        details = {'error_type': type(error).__name__, 'traceback': traceback.format_exc()}
    else:
        details = None
    
    return {
        'message': 'An unexpected error occurred',
        'error_code': ErrorCode.EXTERNAL_SERVICE_ERROR.value,
        'suggestions': ['Contact support if this persists'],
        'timestamp': datetime.utcnow().isoformat(),
        'details': details
    }, 500


# Custom error documentation
@app.doc(
    responses={
        400: {'description': 'Business rule validation error', 'content': {'application/json': {'schema': ErrorResponseSchema}}},
        404: {'description': 'Resource not found', 'content': {'application/json': {'schema': ErrorResponseSchema}}},
        409: {'description': 'Duplicate resource error', 'content': {'application/json': {'schema': ErrorResponseSchema}}},
        422: {'description': 'Validation error', 'content': {'application/json': {'schema': ErrorResponseSchema}}},
        500: {'description': 'Internal server error', 'content': {'application/json': {'schema': ErrorResponseSchema}}}
    }
)
def add_error_documentation():
    """Add error response documentation to all endpoints."""
    pass


if __name__ == '__main__':
    # Create some sample data
    sample_users = [
        {'id': 1, 'username': 'admin', 'email': 'admin@example.com', 'age': 30, 'role': 'admin', 'created_at': datetime.utcnow()},
        {'id': 2, 'username': 'user1', 'email': 'user1@example.com', 'age': 25, 'role': 'user', 'created_at': datetime.utcnow()},
    ]
    users_db.extend(sample_users)
    user_id_counter = len(sample_users)
    
    app.run(debug=True)


"""
Usage Examples:

1. Test validation errors:
   POST /users {"username": "a", "email": "invalid-email", "age": 5}

2. Test duplicate resource error:
   POST /users {"username": "admin", "email": "test@example.com", "age": 25}

3. Test business rule error:
   POST /users {"username": "admin2", "email": "admin2@example.com", "age": 30, "role": "admin"}
   POST /users {"username": "admin3", "email": "admin3@example.com", "age": 30, "role": "admin"}
   ...continue until you hit the max admin limit

4. Test resource not found:
   GET /users/999

5. Test error demonstrations:
   GET /error-demo/validation
   GET /error-demo/not-found
   GET /error-demo/duplicate
   GET /error-demo/business-rule
   GET /error-demo/custom

Features demonstrated:
- Custom exception hierarchy
- Standardized error codes
- Detailed error responses with suggestions
- Business rule validation
- Comprehensive logging
- Global error handlers
- Client-friendly error messages
"""
