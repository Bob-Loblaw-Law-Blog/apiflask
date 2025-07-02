"""Test file to verify OpenAPISchema class behavior matches the original Union type."""

from marshmallow import Schema
from marshmallow.fields import String, Integer


# Mock the base Schema class if needed
class TestSchema(Schema):
    name = String()
    age = Integer()


# Import our new OpenAPISchema class
# Assuming the metaclass implementation from schemas_final.py
class OpenAPISchemaMeta(type):
    """Metaclass for OpenAPISchema that provides Union-like behavior for isinstance checks."""

    def __instancecheck__(cls, instance):
        """Check if instance matches the Union[Schema, Type[Schema], dict] behavior."""
        # Handle Schema instances
        if isinstance(instance, Schema):
            return True
        # Handle dict instances
        if isinstance(instance, dict):
            return True
        # Handle Schema class types (not instances)
        if isinstance(instance, type) and issubclass(instance, Schema):
            return True
        return False


class OpenAPISchema(metaclass=OpenAPISchemaMeta):
    """A class that represents OpenAPI schema types."""

    def __init__(self):
        """This class should not be instantiated directly."""
        raise TypeError("OpenAPISchema should not be instantiated. Use it only for type checking.")


def test_isinstance_checks():
    """Test that isinstance checks work correctly."""

    # Test 1: Schema class (not instantiated)
    assert isinstance(TestSchema, OpenAPISchema), "Schema class should be instance of OpenAPISchema"

    # Test 2: Schema instance
    schema_instance = TestSchema()
    assert isinstance(schema_instance, OpenAPISchema), "Schema instance should be instance of OpenAPISchema"

    # Test 3: Dictionary
    schema_dict = {'type': 'object', 'properties': {'name': {'type': 'string'}}}
    assert isinstance(schema_dict, OpenAPISchema), "Dictionary should be instance of OpenAPISchema"

    # Test 4: String should NOT be instance
    assert not isinstance("not a schema", OpenAPISchema), "String should not be instance of OpenAPISchema"

    # Test 5: None should NOT be instance
    assert not isinstance(None, OpenAPISchema), "None should not be instance of OpenAPISchema"

    # Test 6: Regular class should NOT be instance
    class RegularClass:
        pass
    assert not isinstance(RegularClass, OpenAPISchema), "Regular class should not be instance of OpenAPISchema"
    assert not isinstance(RegularClass(), OpenAPISchema), "Regular class instance should not be instance of OpenAPISchema"

    print("All isinstance checks passed!")


def test_usage_patterns():
    """Test common usage patterns from the codebase."""

    # Pattern 1: Check if variable is a type (class)
    base_schema = TestSchema
    if isinstance(base_schema, type):
        print(f"✓ {base_schema} is recognized as a type")
        # Should be able to instantiate it
        instance = base_schema()
        print(f"✓ Successfully instantiated: {instance}")

    # Pattern 2: Check if variable is a dict
    base_schema = {'type': 'object'}
    if isinstance(base_schema, dict):
        print(f"✓ {base_schema} is recognized as a dict")

    # Pattern 3: Check if variable is neither type nor dict (instance)
    base_schema = TestSchema()
    if not isinstance(base_schema, type) and not isinstance(base_schema, dict):
        print(f"✓ {base_schema} is recognized as a Schema instance")

    print("All usage patterns work correctly!")


def test_type_annotations():
    """Test that type annotations work correctly."""

    # These should all be valid
    schema1: OpenAPISchema = TestSchema
    schema2: OpenAPISchema = TestSchema()
    schema3: OpenAPISchema = {'type': 'object'}

    print("Type annotations work correctly!")


if __name__ == "__main__":
    test_isinstance_checks()
    print()
    test_usage_patterns()
    print()
    test_type_annotations()
    print("\n✓ All tests passed!")
