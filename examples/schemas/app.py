"""
Advanced Schema Examples for APIFlask

This example demonstrates:
1. Schema inheritance and composition
2. Nested schemas with relationships
3. Custom field validation
4. Polymorphic schemas
5. Dynamic schema generation
6. Schema method fields
7. Pre/post processing hooks
8. Custom error messages
9. Conditional validation
10. Schema context usage

Requirements:
- apiflask
- marshmallow (comes with apiflask)
"""

from datetime import datetime, date
from typing import Optional, List, Dict, Any
from enum import Enum

from apiflask import APIFlask, Schema, abort
from apiflask.fields import (
    Integer, String, Float, Boolean, DateTime, Date, Email,
    Nested, List as ListField, Dict as DictField, Enum as EnumField,
    Method, Function, Raw, Field
)
from apiflask.validators import Length, Range, Regexp, OneOf, ContainsOnly
from marshmallow import validates, validates_schema, ValidationError, pre_load, post_load, pre_dump

app = APIFlask(__name__)
app.config['SPEC_TITLE'] = 'Advanced Schemas Example'
app.config['SPEC_VERSION'] = '1.0.0'


# Enums
class UserRole(str, Enum):
    ADMIN = 'admin'
    MODERATOR = 'moderator'
    USER = 'user'
    GUEST = 'guest'


class ProductCategory(str, Enum):
    ELECTRONICS = 'electronics'
    CLOTHING = 'clothing'
    FOOD = 'food'
    BOOKS = 'books'


class OrderStatus(str, Enum):
    PENDING = 'pending'
    PROCESSING = 'processing'
    SHIPPED = 'shipped'
    DELIVERED = 'delivered'
    CANCELLED = 'cancelled'


# Base Schemas
class TimestampMixin(Schema):
    """Mixin for adding timestamp fields"""
    created_at = DateTime(dump_only=True)
    updated_at = DateTime(dump_only=True)
    
    @pre_dump
    def add_timestamps(self, data, **kwargs):
        """Add timestamps if not present"""
        if not hasattr(data, 'get'):
            # Handle objects
            if not hasattr(data, 'created_at'):
                data.created_at = datetime.utcnow()
            if not hasattr(data, 'updated_at'):
                data.updated_at = datetime.utcnow()
        return data


class AuditMixin(TimestampMixin):
    """Mixin for audit fields"""
    created_by = String(dump_only=True)
    updated_by = String(dump_only=True)
    version = Integer(dump_only=True, load_default=1)


# Address Schema with custom validation
class AddressSchema(Schema):
    street = String(required=True, validate=Length(min=5, max=100))
    city = String(required=True, validate=Length(min=2, max=50))
    state = String(validate=Length(equal=2))  # US state code
    country = String(required=True, validate=Length(equal=2))  # ISO country code
    postal_code = String(required=True)
    
    @validates('postal_code')
    def validate_postal_code(self, value, **kwargs):
        """Custom postal code validation based on country"""
        country = self.context.get('country') or kwargs.get('data', {}).get('country')
        
        if country == 'US':
            # US ZIP code validation
            if not Regexp(r'^\d{5}(-\d{4})?$').validate(value):
                raise ValidationError('Invalid US ZIP code format')
        elif country == 'CA':
            # Canadian postal code validation
            if not Regexp(r'^[A-Z]\d[A-Z]\s?\d[A-Z]\d$', flags=0).validate(value):
                raise ValidationError('Invalid Canadian postal code format')
        elif country == 'UK':
            # UK postcode validation (simplified)
            if len(value) < 6 or len(value) > 8:
                raise ValidationError('Invalid UK postcode format')
    
    @validates_schema
    def validate_address(self, data, **kwargs):
        """Cross-field validation"""
        if data.get('country') == 'US' and not data.get('state'):
            raise ValidationError('State is required for US addresses')


# User schemas with inheritance
class BaseUserSchema(Schema):
    id = Integer(dump_only=True)
    username = String(required=True, validate=[
        Length(min=3, max=20),
        Regexp(r'^[a-zA-Z0-9_]+$', error='Username can only contain letters, numbers, and underscores')
    ])
    email = Email(required=True)
    role = EnumField(UserRole, load_default=UserRole.USER)
    is_active = Boolean(load_default=True)
    
    # Method field
    display_name = Method('get_display_name', dump_only=True)
    
    def get_display_name(self, obj):
        """Generate display name from username and role"""
        return f"{obj.get('username')} ({obj.get('role', 'user')})"


class UserProfileSchema(BaseUserSchema, AuditMixin):
    """Extended user schema with profile information"""
    first_name = String(validate=Length(max=50))
    last_name = String(validate=Length(max=50))
    bio = String(validate=Length(max=500))
    birth_date = Date()
    phone = String(validate=Regexp(r'^\+?1?\d{9,15}$'))
    
    # Nested schema
    addresses = ListField(Nested(AddressSchema), validate=Length(max=5))
    
    # Function field
    age = Function(lambda obj: calculate_age(obj.get('birth_date')))
    
    @validates('birth_date')
    def validate_birth_date(self, value):
        """Ensure user is at least 13 years old"""
        if value:
            age = calculate_age(value)
            if age < 13:
                raise ValidationError('User must be at least 13 years old')
    
    @pre_load
    def process_name(self, data, **kwargs):
        """Process full_name into first_name and last_name"""
        if 'full_name' in data and 'first_name' not in data:
            parts = data['full_name'].split(' ', 1)
            data['first_name'] = parts[0]
            if len(parts) > 1:
                data['last_name'] = parts[1]
            del data['full_name']
        return data


# Product schemas with polymorphism
class BaseProductSchema(Schema):
    id = Integer(dump_only=True)
    name = String(required=True, validate=Length(min=2, max=200))
    description = String(validate=Length(max=1000))
    price = Float(required=True, validate=Range(min=0.01))
    category = EnumField(ProductCategory, required=True)
    in_stock = Boolean(load_default=True)
    
    # Dynamic field based on category
    category_specific = Field()
    
    @post_load
    def add_category_specific(self, data, **kwargs):
        """Add category-specific data"""
        category = data.get('category')
        if category == ProductCategory.ELECTRONICS:
            data['category_specific'] = {
                'warranty_months': 12,
                'power_consumption': '50W'
            }
        elif category == ProductCategory.CLOTHING:
            data['category_specific'] = {
                'sizes': ['S', 'M', 'L', 'XL'],
                'materials': ['cotton', 'polyester']
            }
        return data


class ElectronicsProductSchema(BaseProductSchema):
    """Schema for electronics products"""
    warranty_months = Integer(validate=Range(min=0, max=60))
    voltage = String(validate=OneOf(['110V', '220V', 'USB']))
    specifications = DictField()
    
    class Meta:
        # Exclude category_specific as we have specific fields
        exclude = ['category_specific']


class ClothingProductSchema(BaseProductSchema):
    """Schema for clothing products"""
    sizes = ListField(String(validate=OneOf(['XS', 'S', 'M', 'L', 'XL', 'XXL'])))
    colors = ListField(String())
    material = String(validate=Length(max=50))
    care_instructions = String()
    
    class Meta:
        exclude = ['category_specific']


# Polymorphic schema handler
class ProductSchema(Schema):
    """Polymorphic schema that chooses the right schema based on category"""
    
    @classmethod
    def from_category(cls, category: ProductCategory) -> Schema:
        """Factory method to get the right schema class"""
        schema_map = {
            ProductCategory.ELECTRONICS: ElectronicsProductSchema,
            ProductCategory.CLOTHING: ClothingProductSchema,
        }
        return schema_map.get(category, BaseProductSchema)()


# Order schemas with complex relationships
class OrderItemSchema(Schema):
    product_id = Integer(required=True)
    quantity = Integer(required=True, validate=Range(min=1))
    unit_price = Float(dump_only=True)
    
    # Nested product details (read-only)
    product = Nested(BaseProductSchema, dump_only=True)
    
    # Calculated field
    total_price = Method('calculate_total', dump_only=True)
    
    def calculate_total(self, obj):
        """Calculate total price for the item"""
        return obj.get('quantity', 0) * obj.get('unit_price', 0)


class OrderSchema(TimestampMixin):
    id = Integer(dump_only=True)
    order_number = String(dump_only=True)
    customer_id = Integer(required=True)
    status = EnumField(OrderStatus, load_default=OrderStatus.PENDING)
    
    # Nested items
    items = ListField(Nested(OrderItemSchema), required=True, validate=Length(min=1))
    
    # Nested address
    shipping_address = Nested(AddressSchema, required=True)
    billing_address = Nested(AddressSchema)
    
    # Calculated fields
    subtotal = Method('calculate_subtotal', dump_only=True)
    tax = Method('calculate_tax', dump_only=True)
    total = Method('calculate_total', dump_only=True)
    
    # Custom validation
    notes = String(validate=Length(max=500))
    metadata = DictField()  # Flexible field for additional data
    
    def calculate_subtotal(self, obj):
        """Calculate order subtotal"""
        return sum(item.get('quantity', 0) * item.get('unit_price', 0) 
                   for item in obj.get('items', []))
    
    def calculate_tax(self, obj):
        """Calculate tax based on shipping address"""
        subtotal = self.calculate_subtotal(obj)
        # Simplified tax calculation
        return round(subtotal * 0.08, 2)
    
    def calculate_total(self, obj):
        """Calculate order total"""
        return self.calculate_subtotal(obj) + self.calculate_tax(obj)
    
    @validates_schema
    def validate_order(self, data, **kwargs):
        """Complex order validation"""
        # Ensure billing address is provided for orders over $100
        if 'items' in data:
            subtotal = sum(item.get('quantity', 0) * item.get('unit_price', 0) 
                          for item in data['items'])
            if subtotal > 100 and not data.get('billing_address'):
                raise ValidationError('Billing address required for orders over $100')
        
        # Validate shipping address for physical products
        # (simplified - in real app, check product types)
        if not data.get('shipping_address'):
            raise ValidationError('Shipping address is required')


# Dynamic schema generation example
def create_filter_schema(model_fields: Dict[str, type]) -> Schema:
    """Dynamically create a filter schema based on model fields"""
    class DynamicFilterSchema(Schema):
        pass
    
    for field_name, field_type in model_fields.items():
        if field_type == int:
            # Add min/max filters for integers
            setattr(DynamicFilterSchema, f'{field_name}_min', Integer())
            setattr(DynamicFilterSchema, f'{field_name}_max', Integer())
        elif field_type == str:
            # Add contains filter for strings
            setattr(DynamicFilterSchema, f'{field_name}_contains', String())
        elif field_type == bool:
            # Add boolean filter
            setattr(DynamicFilterSchema, f'{field_name}', Boolean())
    
    return DynamicFilterSchema()


# Utility functions
def calculate_age(birth_date):
    """Calculate age from birth date"""
    if not birth_date:
        return None
    today = date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


# Mock data
users_db = {}
products_db = {}
orders_db = {}


# Routes demonstrating schema usage
@app.post('/users')
@app.input(UserProfileSchema)
@app.output(UserProfileSchema, status_code=201)
def create_user(json_data):
    """Create a new user with profile"""
    user_id = len(users_db) + 1
    json_data['id'] = user_id
    json_data['created_at'] = datetime.utcnow()
    json_data['updated_at'] = datetime.utcnow()
    
    users_db[user_id] = json_data
    return json_data


@app.post('/products')
@app.input(BaseProductSchema)
@app.output(BaseProductSchema, status_code=201)
def create_product(json_data):
    """Create a product - demonstrates polymorphic handling"""
    # In a real app, you might choose schema based on category
    category = json_data.get('category')
    
    # Validate with specific schema if needed
    if category == ProductCategory.ELECTRONICS:
        # Additional electronics-specific validation
        pass
    elif category == ProductCategory.CLOTHING:
        # Additional clothing-specific validation
        pass
    
    product_id = len(products_db) + 1
    json_data['id'] = product_id
    
    products_db[product_id] = json_data
    return json_data


@app.post('/orders')
@app.input(OrderSchema)
@app.output(OrderSchema, status_code=201)
def create_order(json_data):
    """Create an order with complex validation"""
    # Add product details and prices
    for item in json_data['items']:
        product = products_db.get(item['product_id'])
        if not product:
            abort(404, f"Product {item['product_id']} not found")
        
        item['unit_price'] = product['price']
        item['product'] = product
    
    order_id = len(orders_db) + 1
    json_data['id'] = order_id
    json_data['order_number'] = f'ORD-{order_id:06d}'
    json_data['created_at'] = datetime.utcnow()
    
    orders_db[order_id] = json_data
    return json_data


@app.get('/products/filter')
def filter_products():
    """Demonstrate dynamic schema generation"""
    # Define filterable fields
    product_fields = {
        'price': float,
        'name': str,
        'in_stock': bool
    }
    
    # Create dynamic schema
    FilterSchema = create_filter_schema(product_fields)
    
    # In a real app, use this for filtering
    return {
        'message': 'Dynamic filter schema created',
        'available_filters': list(product_fields.keys())
    }


@app.post('/validate-address')
@app.input(AddressSchema)
def validate_address(json_data):
    """Validate an address independently"""
    return {
        'valid': True,
        'address': json_data
    }


if __name__ == '__main__':
    app.run(debug=True)
