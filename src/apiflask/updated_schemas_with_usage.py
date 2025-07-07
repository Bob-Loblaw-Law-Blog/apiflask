"""
Updated schemas module with class-based error schemas while maintaining backwards compatibility.

This module provides both class-based and dict-based schema definitions to ensure
backwards compatibility while allowing for more flexible schema usage.
"""

from __future__ import annotations

import typing as t

from marshmallow import Schema as BaseSchema
from marshmallow import fields
from marshmallow.fields import Integer
from marshmallow.fields import URL


# ============================================================================
# CLASS-BASED ERROR SCHEMAS (New)
# ============================================================================

class ValidationErrorDetailSchema(BaseSchema):
    """Schema class for the detail object of validation error response.
    
    This schema represents the structure of validation error details,
    organized by location (e.g., 'json', 'query', 'form') and field names.
    
    The actual structure is dynamic and depends on where validation errors occur:
    - Keys are location names (e.g., 'json', 'query', 'form', 'headers')
    - Values are dicts mapping field names to lists of error messages
    
    Example structure:
    ```python
    {
        "json": {
            "username": ["Missing data for required field."],
            "email": ["Not a valid email address."]
        },
        "query": {
            "page": ["Must be greater than 0."]
        }
    }
    ```
    
    *Version Added: 2.0.0*
    """
    
    class Meta:
        # Allow unknown fields since locations are dynamic
        unknown = fields.INCLUDE
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # The schema is intentionally flexible to accept any location keys
        # with nested field errors


class ValidationErrorSchema(BaseSchema):
    """Schema class for validation error response.
    
    This schema represents the complete validation error response structure
    returned when request validation fails.
    
    Example:
    ```python
    {
        "message": "Validation error",
        "detail": {
            "json": {
                "username": ["Missing data for required field."],
                "password": ["Length must be between 8 and 128."]
            }
        }
    }
    ```
    
    Attributes:
        detail: Nested validation error details organized by location
        message: Human-readable error message
    
    *Version Added: 2.0.0*
    """
    detail = fields.Nested(ValidationErrorDetailSchema, required=False,
                          description="Detailed validation errors by location")
    message = fields.String(required=False, 
                           description="Human-readable error message")


class HTTPErrorSchema(BaseSchema):
    """Schema class for generic HTTP error response.
    
    This schema represents the structure of generic HTTP error responses
    for non-validation errors (404, 401, 403, 500, etc).
    
    Example:
    ```python
    {
        "message": "Not found",
        "detail": {"id": 123, "resource": "user"}
    }
    ```
    
    Attributes:
        detail: Optional details about the error (can be any dict)
        message: Human-readable error message
    
    *Version Added: 2.0.0*
    """
    detail = fields.Dict(required=False, 
                        description="Additional error details")
    message = fields.String(required=False,
                           description="Human-readable error message")


# ============================================================================
# DICT-BASED SCHEMAS (Original - Kept for backwards compatibility)
# ============================================================================

# schema for the detail object of validation error response
validation_error_detail_schema: dict[str, t.Any] = {
    'type': 'object',
    'properties': {
        '<location>': {
            'type': 'object',
            'properties': {'<field_name>': {'type': 'array', 'items': {'type': 'string'}}},
        }
    },
}


# schema for validation error response
validation_error_schema: dict[str, t.Any] = {
    'properties': {
        'detail': validation_error_detail_schema,
        'message': {'type': 'string'},
    },
    'type': 'object',
}


# schema for generic error response
http_error_schema: dict[str, t.Any] = {
    'properties': {
        'detail': {'type': 'object'},
        'message': {'type': 'string'},
    },
    'type': 'object',
}


# ============================================================================
# BASE SCHEMAS
# ============================================================================

class Schema(BaseSchema):
    """A base schema for all schemas. Equivalent to `marshmallow.Schema`.

    *Version Added: 1.2.0*
    """

    pass


class EmptySchema(Schema):
    """An empty schema used to generate empty response/schema.

    For 204 response, you can use this schema to
    generate an empty response body. For 200 response, you can use this schema
    to generate an empty response body schema.

    Example:

    ```python
    @app.delete('/foo')
    @app.output(EmptySchema, status_code=204)
    def delete_foo():
        return ''
    ```

    It equals to use `{}`:

    ```python
    @app.delete('/foo')
    @app.output({}, status_code=204)
    def delete_foo():
        return ''
    ```
    """

    pass


class PaginationSchema(Schema):
    """A schema for common pagination information."""

    page = Integer()
    per_page = Integer()
    pages = Integer()
    total = Integer()
    current = URL()
    next = URL()
    prev = URL()
    first = URL()
    last = URL()


class FileSchema(Schema):
    """A schema for file response.

    This is used to represent a file response in OpenAPI spec. If you want to
    embed a file as base64 string in the JSON body, you can use the
    `apiflask.fields.File` field instead.

    Example:

    ```python
    from apiflask.schemas import FileSchema
    from flask import send_from_directory

    @app.get('/images/<filename>')
    @app.output(
        FileSchema(type='string', format='binary'),
        content_type='image/png',
        description='An image file'
    )
    @app.doc(summary="Returns the image file")
    def get_image(filename):
        return send_from_directory(app.config['IMAGE_FOLDER'], filename)
    ```

    The output OpenAPI spec will be:

    ```yaml
    paths:
    /images/{filename}:
      get:
        summary: Returns the image file
        responses:
          '200':
            description: An image file
            content:
              image/png:
                schema:
                  type: string
                  format: binary
    ```

    *Version Added: 2.0.0*
    """

    def __init__(self, *, type: str = 'string', format: str = 'binary') -> None:
        """
        Arguments:
            type: The type of the file. Defaults to `string`.
            format: The format of the file, one of `binary` and `base64`. Defaults to `binary`.
        """
        self.type = type
        self.format = format

    def __repr__(self) -> str:
        return f'schema: \n  type: {self.type}\n  format: {self.format}'


class OpenAPISchemaType(Schema):
    """A type wrapper for OpenAPI schema types.
    
    This class wraps schema values that can be either Schema classes,
    Schema instances, or dict objects representing OpenAPI schemas.
    """
    
    def __init__(self, value: t.Union[Schema, t.Type[Schema], dict]):
        """Initialize with a schema value.
        
        Args:
            value: A Schema instance, Schema class, or dict representing an OpenAPI schema
            
        Raises:
            TypeError: If value is not a valid schema type
        """
        if isinstance(value, dict):
            self._value = value
        elif isinstance(value, Schema):
            self._value = value
        elif isinstance(value, type) and issubclass(value, Schema):
            self._value = value
        else:
            raise TypeError("Value must be an instance of Schema, a Schema subclass, or a dict")


# ============================================================================
# USAGE EXAMPLES AND MIGRATION GUIDE
# ============================================================================

"""
MIGRATION GUIDE: Using the new class-based schemas

The new class-based schemas can be used in place of the dict-based schemas
while maintaining full backwards compatibility.

## Example 1: Using in settings.py

### Old way (still works):
```python
from apiflask.schemas import validation_error_schema, http_error_schema

VALIDATION_ERROR_SCHEMA = validation_error_schema  # dict
HTTP_ERROR_SCHEMA = http_error_schema  # dict
```

### New way (recommended):
```python
from apiflask.schemas import ValidationErrorSchema, HTTPErrorSchema

VALIDATION_ERROR_SCHEMA = ValidationErrorSchema  # class
HTTP_ERROR_SCHEMA = HTTPErrorSchema  # class
```

## Example 2: Custom error schemas

### Old way (dict-based):
```python
custom_error_schema = {
    'properties': {
        'code': {'type': 'string'},
        'message': {'type': 'string'},
        'details': {'type': 'object'}
    },
    'type': 'object'
}
```

### New way (class-based):
```python
class CustomErrorSchema(Schema):
    code = fields.String(required=True)
    message = fields.String(required=True)
    details = fields.Dict()
```

## Example 3: Extending error schemas

With class-based schemas, you can now easily extend and customize:

```python
class ExtendedValidationErrorSchema(ValidationErrorSchema):
    '''Extended validation error with additional fields'''
    request_id = fields.String(dump_only=True)
    timestamp = fields.DateTime(dump_only=True)
    
class CustomHTTPErrorSchema(HTTPErrorSchema):
    '''Custom HTTP error with error codes'''
    error_code = fields.String(required=True)
    help_url = fields.URL()
```

## Example 4: Using with APIFlask

Both old and new formats work seamlessly:

```python
from apiflask import APIFlask
from apiflask.schemas import ValidationErrorSchema, HTTPErrorSchema

app = APIFlask(__name__)

# Using class-based schemas
app.config['VALIDATION_ERROR_SCHEMA'] = ValidationErrorSchema
app.config['HTTP_ERROR_SCHEMA'] = HTTPErrorSchema

# Or continue using dict-based (backwards compatible)
app.config['VALIDATION_ERROR_SCHEMA'] = validation_error_schema
app.config['HTTP_ERROR_SCHEMA'] = http_error_schema
```
"""
