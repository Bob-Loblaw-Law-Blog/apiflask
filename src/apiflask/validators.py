"""Validator re-exports for APIFlask.

This module provides a centralized import point for all validator classes used in APIFlask.
It re-exports validator classes from marshmallow.validate and flask-marshmallow.validate
to provide a consistent validation API for users.

The validators available include:
- String validators: Length, Regexp, Email, URL
- Numeric validators: Range, Equal
- Collection validators: OneOf, NoneOf, ContainsOnly, ContainsNoneOf
- Conditional validators: Predicate
- File validators: FileSize, FileType (from flask-marshmallow)

Example usage:
    ```python
    from apiflask import fields, validators

    class UserSchema(Schema):
        name = fields.String(validate=validators.Length(min=2, max=50))
        email = fields.String(validate=validators.Email())
        age = fields.Integer(validate=validators.Range(min=0, max=150))
        role = fields.String(validate=validators.OneOf(['admin', 'user', 'guest']))
    ```

All validators follow the marshmallow validation pattern and can be used with any
marshmallow field that supports validation.
"""

import os
import typing as t

from flask_marshmallow.validate import FileSize as FileSize
from flask_marshmallow.validate import FileType as FileType
from marshmallow.exceptions import ValidationError
from marshmallow.validate import ContainsNoneOf as ContainsNoneOf
from marshmallow.validate import ContainsOnly as ContainsOnly
from marshmallow.validate import Email as Email
from marshmallow.validate import Equal as Equal
from marshmallow.validate import Length as Length
from marshmallow.validate import NoneOf as NoneOf
from marshmallow.validate import OneOf as OneOf
from marshmallow.validate import Predicate as Predicate
from marshmallow.validate import Range as Range
from marshmallow.validate import Regexp as Regexp
from marshmallow.validate import URL as URL
from marshmallow.validate import Validator as Validator
