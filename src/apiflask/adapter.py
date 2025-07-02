"""OpenAPISchemaType adapter for testing."""

from __future__ import annotations

import typing as t
from functools import wraps
import sys
import os

from apiflask.schemas import Schema, OpenAPISchemaType as SchemaOpenAPIType
from apiflask.types import OpenAPISchemaType as TypesOpenAPIType


class SchemaTypeAdapter:
    """Adapter that allows for either the types or schemas version of OpenAPISchemaType to be used.
    
    This class provides a context manager to temporarily switch between implementations
    for testing purposes.
    """
    
    _implementation = 'types'  # Default implementation
    
    @classmethod
    def using_schema_implementation(cls) -> bool:
        """Check if we're using the schema implementation."""
        return cls._implementation == 'schema'
    
    @classmethod
    def using_types_implementation(cls) -> bool:
        """Check if we're using the types implementation."""
        return cls._implementation == 'types'
    
    @classmethod
    def set_implementation(cls, impl: str) -> None:
        """Set the implementation to use.
        
        Args:
            impl: Either 'types' or 'schema'
        """
        if impl not in ('types', 'schema'):
            raise ValueError("Implementation must be 'types' or 'schema'")
        cls._implementation = impl
    
    @classmethod
    def create_openapi_schema_type(cls, value: t.Union[Schema, t.Type[Schema], dict]) -> t.Any:
        """Create an OpenAPISchemaType from the value based on current implementation."""
        if cls.using_schema_implementation():
            return SchemaOpenAPIType(value)
        return value  # For types, just return the value as is
    
    @classmethod
    def is_valid_openapi_schema_type(cls, value: t.Any) -> bool:
        """Check if the value is a valid OpenAPISchemaType for current implementation."""
        if cls.using_schema_implementation():
            return isinstance(value, SchemaOpenAPIType)
        return isinstance(value, (Schema, t.Type[Schema], dict))


class using_schema_implementation:
    """Context manager to temporarily use schema implementation."""
    
    def __init__(self):
        self._previous_implementation = SchemaTypeAdapter._implementation
    
    def __enter__(self):
        SchemaTypeAdapter.set_implementation('schema')
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        SchemaTypeAdapter.set_implementation(self._previous_implementation)


class using_types_implementation:
    """Context manager to temporarily use types implementation."""
    
    def __init__(self):
        self._previous_implementation = SchemaTypeAdapter._implementation
    
    def __enter__(self):
        SchemaTypeAdapter.set_implementation('types')
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        SchemaTypeAdapter.set_implementation(self._previous_implementation)


def schema_type_aware(func):
    """Decorator to make functions aware of schema type implementation."""
    
    @wraps(func)
    def wrapper(*args, **kwargs):
        # Check if any OpenAPISchemaType arguments need conversion
        new_args = []
        for arg in args:
            if isinstance(arg, (Schema, t.Type[Schema], dict)) or isinstance(arg, SchemaOpenAPIType):
                new_args.append(SchemaTypeAdapter.create_openapi_schema_type(arg))
            else:
                new_args.append(arg)
                
        new_kwargs = {}
        for key, value in kwargs.items():
            if isinstance(value, (Schema, t.Type[Schema], dict)) or isinstance(value, SchemaOpenAPIType):
                new_kwargs[key] = SchemaTypeAdapter.create_openapi_schema_type(value)
            else:
                new_kwargs[key] = value
        
        return func(*new_args, **new_kwargs)
    
    return wrapper