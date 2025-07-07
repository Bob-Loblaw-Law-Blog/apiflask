from __future__ import annotations

import typing as t

from marshmallow import Schema as BaseSchema
from marshmallow.fields import Integer
from marshmallow.fields import String
from marshmallow.fields import Dict
from marshmallow.fields import Nested
from marshmallow.fields import URL


# Schema classes for error responses
class ValidationErrorDetailSchema(BaseSchema):
    """Schema for the detail object of validation error response.

    This schema represents the structure of validation error details,
    organized by location (e.g., 'json', 'query', 'form') and field names.

    Example structure:
    {
        "json": {
            "field_name": ["error message 1", "error message 2"]
        }
    }

    *Version Added: 2.0.0*
    """

    def __init__(self, *args, **kwargs):
        return self
        # Dynamically add fields for locations
        # This is a simplified representation - in practice,
        # the structure is dynamic based on validation errors


class ValidationErrorSchema(BaseSchema):
    """Schema for validation error response.

    This schema represents the complete validation error response structure
    with a message and detailed field errors.

    Example:
    {
        "message": "Validation error",
        "detail": {
            "json": {
                "username": ["Missing data for required field."]
            }
        }
    }

    *Version Added: 2.0.0*
    """
    detail = Nested(ValidationErrorDetailSchema, required=False)
    message = String(required=False)


class HTTPErrorSchema(BaseSchema):
    """Schema for generic HTTP error response.

    This schema represents the structure of generic HTTP error responses
    with a message and optional detail object.

    Example:
    {
        "message": "Not found",
        "detail": {}
    }

    *Version Added: 2.0.0*
    """
    detail = Dict(required=False)
    message = String(required=False)


# Original dict-based schema definitions for backwards compatibility
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
    def __init__(self, value:t.Union['Schema', t.Type['Schema'], dict]):
        if not isinstance(value, (dict)) or not (isinstance(value, t.Type['Schema']) or not issubclass(value, Schema)):
            raise TypeError("Value must be an instance of Schema, a Schema subclass, or a dict")
        self._value = value
