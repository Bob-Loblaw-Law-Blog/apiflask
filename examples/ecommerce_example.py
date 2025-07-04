"""
E-commerce API Example for APIFlask
==================================

This example demonstrates a complex real-world domain with:
- Product catalog management
- User management with roles
- Shopping cart functionality
- Order processing workflow
- Inventory management
- Advanced business rules
- Complex relationships
- Transaction handling
"""

import uuid
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import List, Optional
from dataclasses import dataclass

from apiflask import APIFlask, Schema, abort
from apiflask.fields import Integer, String, Email, DateTime, Float, Boolean, List as ListField, Nested, Enum as EnumField
from apiflask.validators import Length, Range, OneOf
from flask_sqlalchemy import SQLAlchemy
from marshmallow import validates_schema, ValidationError, post_load
from sqlalchemy.orm import relationship
from sqlalchemy import event
from werkzeug.security import generate_password_hash, check_password_hash


app = APIFlask(__name__, title='E-commerce API', version='1.0')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///ecommerce.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'ecommerce-secret-key'

db = SQLAlchemy(app)


# Enums
class UserRole(Enum):
    CUSTOMER = "customer"
    ADMIN = "admin"
    VENDOR = "vendor"


class OrderStatus(Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


class ProductCategory(Enum):
    ELECTRONICS = "electronics"
    CLOTHING = "clothing"
    BOOKS = "books"
    HOME = "home"
    SPORTS = "sports"


# Models
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    role = db.Column(db.Enum(UserRole), default=UserRole.CUSTOMER)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    addresses = relationship("Address", back_populates="user", lazy='dynamic')
    orders = relationship("Order", back_populates="user", lazy='dynamic')
    cart_items = relationship("CartItem", back_populates="user", lazy='dynamic')
    reviews = relationship("Review", back_populates="user", lazy='dynamic')
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'role': self.role.value,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat()
        }


class Address(db.Model):
    __tablename__ = 'addresses'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    street = db.Column(db.String(200), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    state = db.Column(db.String(50), nullable=False)
    zip_code = db.Column(db.String(20), nullable=False)
    country = db.Column(db.String(50), nullable=False)
    is_default = db.Column(db.Boolean, default=False)
    
    user = relationship("User", back_populates="addresses")


class Product(db.Model):
    __tablename__ = 'products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category = db.Column(db.Enum(ProductCategory), nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    brand = db.Column(db.String(100))
    weight_kg = db.Column(db.Float)
    dimensions = db.Column(db.String(50))  # Format: "LxWxH"
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    inventory = relationship("Inventory", back_populates="product", uselist=False)
    reviews = relationship("Review", back_populates="product", lazy='dynamic')
    order_items = relationship("OrderItem", back_populates="product", lazy='dynamic')
    cart_items = relationship("CartItem", back_populates="product", lazy='dynamic')
    
    @property
    def average_rating(self):
        reviews = self.reviews.all()
        if not reviews:
            return 0
        return sum(r.rating for r in reviews) / len(reviews)
    
    @property
    def stock_quantity(self):
        return self.inventory.quantity if self.inventory else 0
    
    def to_dict(self, include_inventory=False):
        data = {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category': self.category.value,
            'price': float(self.price),
            'sku': self.sku,
            'brand': self.brand,
            'weight_kg': self.weight_kg,
            'dimensions': self.dimensions,
            'is_active': self.is_active,
            'average_rating': self.average_rating,
            'created_at': self.created_at.isoformat()
        }
        
        if include_inventory:
            data['stock_quantity'] = self.stock_quantity
            data['low_stock_threshold'] = self.inventory.low_stock_threshold if self.inventory else 0
        
        return data


class Inventory(db.Model):
    __tablename__ = 'inventory'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    reserved_quantity = db.Column(db.Integer, default=0)  # For pending orders
    low_stock_threshold = db.Column(db.Integer, default=10)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow)
    
    product = relationship("Product", back_populates="inventory")
    
    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity
    
    @property
    def is_low_stock(self):
        return self.available_quantity <= self.low_stock_threshold


class CartItem(db.Model):
    __tablename__ = 'cart_items'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="cart_items")
    product = relationship("Product", back_populates="cart_items")
    
    @property
    def total_price(self):
        return self.product.price * self.quantity


class Order(db.Model):
    __tablename__ = 'orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(20), unique=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    status = db.Column(db.Enum(OrderStatus), default=OrderStatus.PENDING)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    shipping_cost = db.Column(db.Numeric(10, 2), default=0)
    tax_amount = db.Column(db.Numeric(10, 2), default=0)
    
    # Address information (snapshot at order time)
    shipping_address = db.Column(db.JSON)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    shipped_at = db.Column(db.DateTime)
    delivered_at = db.Column(db.DateTime)
    
    # Relationships
    user = relationship("User", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", lazy='dynamic')
    
    def calculate_total(self):
        """Calculate order total including tax and shipping."""
        subtotal = sum(item.total_price for item in self.items)
        return subtotal + self.shipping_cost + self.tax_amount
    
    def to_dict(self, include_items=False):
        data = {
            'id': self.id,
            'order_number': self.order_number,
            'user_id': self.user_id,
            'status': self.status.value,
            'total_amount': float(self.total_amount),
            'shipping_cost': float(self.shipping_cost),
            'tax_amount': float(self.tax_amount),
            'shipping_address': self.shipping_address,
            'created_at': self.created_at.isoformat(),
            'shipped_at': self.shipped_at.isoformat() if self.shipped_at else None,
            'delivered_at': self.delivered_at.isoformat() if self.delivered_at else None
        }
        
        if include_items:
            data['items'] = [item.to_dict() for item in self.items]
        
        return data


class OrderItem(db.Model):
    __tablename__ = 'order_items'
    
    id = db.Column(db.Integer, primary_key=True)
    order_id = db.Column(db.Integer, db.ForeignKey('orders.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)  # Price at order time
    
    order = relationship("Order", back_populates="items")
    product = relationship("Product", back_populates="order_items")
    
    @property
    def total_price(self):
        return self.unit_price * self.quantity
    
    def to_dict(self):
        return {
            'id': self.id,
            'order_id': self.order_id,
            'product_id': self.product_id,
            'product_name': self.product.name,
            'quantity': self.quantity,
            'unit_price': float(self.unit_price),
            'total_price': float(self.total_price)
        }


class Review(db.Model):
    __tablename__ = 'reviews'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)  # 1-5
    title = db.Column(db.String(200))
    comment = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = relationship("User", back_populates="reviews")
    product = relationship("Product", back_populates="reviews")


# Business Logic Services
class InventoryService:
    """Service for inventory management."""
    
    @staticmethod
    def check_availability(product_id: int, quantity: int) -> bool:
        """Check if product has sufficient stock."""
        inventory = Inventory.query.filter_by(product_id=product_id).first()
        if not inventory:
            return False
        return inventory.available_quantity >= quantity
    
    @staticmethod
    def reserve_stock(product_id: int, quantity: int) -> bool:
        """Reserve stock for an order."""
        inventory = Inventory.query.filter_by(product_id=product_id).first()
        if not inventory or inventory.available_quantity < quantity:
            return False
        
        inventory.reserved_quantity += quantity
        inventory.last_updated = datetime.utcnow()
        db.session.commit()
        return True
    
    @staticmethod
    def release_reserved_stock(product_id: int, quantity: int):
        """Release reserved stock (e.g., when order is cancelled)."""
        inventory = Inventory.query.filter_by(product_id=product_id).first()
        if inventory:
            inventory.reserved_quantity = max(0, inventory.reserved_quantity - quantity)
            inventory.last_updated = datetime.utcnow()
            db.session.commit()
    
    @staticmethod
    def confirm_stock_usage(product_id: int, quantity: int):
        """Confirm stock usage (e.g., when order is shipped)."""
        inventory = Inventory.query.filter_by(product_id=product_id).first()
        if inventory:
            inventory.quantity -= quantity
            inventory.reserved_quantity -= quantity
            inventory.last_updated = datetime.utcnow()
            db.session.commit()


class OrderService:
    """Service for order management."""
    
    @staticmethod
    def create_order(user_id: int, shipping_address: dict) -> Order:
        """Create order from user's cart."""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        
        cart_items = user.cart_items.all()
        if not cart_items:
            raise ValueError("Cart is empty")
        
        # Check stock availability for all items
        for item in cart_items:
            if not InventoryService.check_availability(item.product_id, item.quantity):
                raise ValueError(f"Insufficient stock for product: {item.product.name}")
        
        # Calculate totals
        subtotal = sum(item.total_price for item in cart_items)
        shipping_cost = OrderService.calculate_shipping_cost(cart_items, shipping_address)
        tax_amount = OrderService.calculate_tax(subtotal, shipping_address)
        total_amount = subtotal + shipping_cost + tax_amount
        
        # Create order
        order = Order(
            order_number=OrderService.generate_order_number(),
            user_id=user_id,
            total_amount=total_amount,
            shipping_cost=shipping_cost,
            tax_amount=tax_amount,
            shipping_address=shipping_address
        )
        db.session.add(order)
        db.session.flush()  # Get order ID
        
        # Create order items and reserve stock
        for cart_item in cart_items:
            order_item = OrderItem(
                order_id=order.id,
                product_id=cart_item.product_id,
                quantity=cart_item.quantity,
                unit_price=cart_item.product.price
            )
            db.session.add(order_item)
            
            # Reserve stock
            InventoryService.reserve_stock(cart_item.product_id, cart_item.quantity)
        
        # Clear cart
        for cart_item in cart_items:
            db.session.delete(cart_item)
        
        db.session.commit()
        return order
    
    @staticmethod
    def update_order_status(order_id: int, new_status: OrderStatus) -> Order:
        """Update order status with business logic."""
        order = Order.query.get(order_id)
        if not order:
            raise ValueError("Order not found")
        
        # Business rules for status transitions
        allowed_transitions = {
            OrderStatus.PENDING: [OrderStatus.CONFIRMED, OrderStatus.CANCELLED],
            OrderStatus.CONFIRMED: [OrderStatus.PROCESSING, OrderStatus.CANCELLED],
            OrderStatus.PROCESSING: [OrderStatus.SHIPPED, OrderStatus.CANCELLED],
            OrderStatus.SHIPPED: [OrderStatus.DELIVERED],
            OrderStatus.DELIVERED: [OrderStatus.REFUNDED],
            OrderStatus.CANCELLED: [],  # Cannot transition from cancelled
            OrderStatus.REFUNDED: []   # Cannot transition from refunded
        }
        
        if new_status not in allowed_transitions[order.status]:
            raise ValueError(f"Cannot transition from {order.status.value} to {new_status.value}")
        
        old_status = order.status
        order.status = new_status
        
        # Handle status-specific logic
        if new_status == OrderStatus.SHIPPED:
            order.shipped_at = datetime.utcnow()
            # Confirm stock usage
            for item in order.items:
                InventoryService.confirm_stock_usage(item.product_id, item.quantity)
        
        elif new_status == OrderStatus.DELIVERED:
            order.delivered_at = datetime.utcnow()
        
        elif new_status == OrderStatus.CANCELLED:
            # Release reserved stock
            for item in order.items:
                InventoryService.release_reserved_stock(item.product_id, item.quantity)
        
        db.session.commit()
        return order
    
    @staticmethod
    def generate_order_number() -> str:
        """Generate unique order number."""
        timestamp = datetime.utcnow().strftime("%Y%m%d")
        unique_id = str(uuid.uuid4()).split('-')[0].upper()
        return f"ORD-{timestamp}-{unique_id}"
    
    @staticmethod
    def calculate_shipping_cost(cart_items: List[CartItem], address: dict) -> Decimal:
        """Calculate shipping cost based on weight and destination."""
        total_weight = sum(item.product.weight_kg * item.quantity for item in cart_items if item.product.weight_kg)
        
        # Simplified shipping calculation
        base_cost = Decimal('5.00')
        weight_cost = Decimal(str(total_weight)) * Decimal('0.50')
        
        # International shipping
        if address.get('country') != 'US':
            base_cost += Decimal('15.00')
        
        return base_cost + weight_cost
    
    @staticmethod
    def calculate_tax(subtotal: Decimal, address: dict) -> Decimal:
        """Calculate tax based on shipping address."""
        # Simplified tax calculation (normally would use tax service)
        tax_rates = {
            'CA': 0.08,  # California
            'NY': 0.07,  # New York
            'TX': 0.06   # Texas
        }
        
        state = address.get('state', '')
        tax_rate = tax_rates.get(state, 0.05)  # Default 5%
        return subtotal * Decimal(str(tax_rate))


# Schemas
class UserCreateSchema(Schema):
    username = String(required=True, validate=Length(3, 80))
    email = Email(required=True)
    password = String(required=True, validate=Length(8, 255))
    first_name = String(required=True, validate=Length(1, 50))
    last_name = String(required=True, validate=Length(1, 50))
    role = EnumField(UserRole, by_value=True, missing=UserRole.CUSTOMER)


class UserResponseSchema(Schema):
    id = Integer()
    username = String()
    email = String()
    first_name = String()
    last_name = String()
    role = String()
    is_active = Boolean()
    created_at = DateTime()


class AddressSchema(Schema):
    street = String(required=True, validate=Length(1, 200))
    city = String(required=True, validate=Length(1, 100))
    state = String(required=True, validate=Length(2, 50))
    zip_code = String(required=True, validate=Length(3, 20))
    country = String(required=True, validate=Length(2, 50))
    is_default = Boolean(missing=False)


class ProductCreateSchema(Schema):
    name = String(required=True, validate=Length(1, 200))
    description = String()
    category = EnumField(ProductCategory, by_value=True, required=True)
    price = Float(required=True, validate=Range(min=0.01))
    sku = String(required=True, validate=Length(1, 50))
    brand = String()
    weight_kg = Float(validate=Range(min=0))
    dimensions = String()
    initial_stock = Integer(validate=Range(min=0), missing=0)
    low_stock_threshold = Integer(validate=Range(min=0), missing=10)


class ProductResponseSchema(Schema):
    id = Integer()
    name = String()
    description = String()
    category = String()
    price = Float()
    sku = String()
    brand = String()
    weight_kg = Float()
    dimensions = String()
    is_active = Boolean()
    average_rating = Float()
    stock_quantity = Integer(missing=0)
    created_at = DateTime()


class CartItemCreateSchema(Schema):
    product_id = Integer(required=True)
    quantity = Integer(required=True, validate=Range(min=1))


class CartItemResponseSchema(Schema):
    id = Integer()
    product_id = Integer()
    product_name = String()
    quantity = Integer()
    unit_price = Float()
    total_price = Float()
    added_at = DateTime()


class OrderCreateSchema(Schema):
    shipping_address = Nested(AddressSchema, required=True)


class OrderResponseSchema(Schema):
    id = Integer()
    order_number = String()
    user_id = Integer()
    status = String()
    total_amount = Float()
    shipping_cost = Float()
    tax_amount = Float()
    shipping_address = Nested(AddressSchema)
    created_at = DateTime()
    shipped_at = DateTime(allow_none=True)
    delivered_at = DateTime(allow_none=True)


class OrderItemResponseSchema(Schema):
    id = Integer()
    product_id = Integer()
    product_name = String()
    quantity = Integer()
    unit_price = Float()
    total_price = Float()


class OrderDetailResponseSchema(OrderResponseSchema):
    items = ListField(Nested(OrderItemResponseSchema))


# API Routes
@app.get('/')
def index():
    """API information."""
    return {
        'name': 'E-commerce API',
        'version': '1.0',
        'description': 'Comprehensive e-commerce API with product catalog, shopping cart, and order management'
    }


# User Management
@app.post('/api/users')
@app.input(UserCreateSchema)
@app.output(UserResponseSchema, status_code=201)
def create_user(json_data):
    """Create a new user."""
    # Check for duplicate username
    if User.query.filter_by(username=json_data['username']).first():
        abort(409, message='Username already exists')
    
    # Check for duplicate email
    if User.query.filter_by(email=json_data['email']).first():
        abort(409, message='Email already exists')
    
    user = User(
        username=json_data['username'],
        email=json_data['email'],
        first_name=json_data['first_name'],
        last_name=json_data['last_name'],
        role=json_data['role']
    )
    user.set_password(json_data['password'])
    
    db.session.add(user)
    db.session.commit()
    
    return user.to_dict()


@app.get('/api/users/<int:user_id>')
@app.output(UserResponseSchema)
def get_user(user_id: int):
    """Get user details."""
    user = User.query.get_or_404(user_id)
    return user.to_dict()


# Product Management
@app.get('/api/products')
@app.output(ProductResponseSchema(many=True))
def get_products():
    """Get all products with optional filtering."""
    from flask import request
    
    category = request.args.get('category')
    min_price = request.args.get('min_price', type=float)
    max_price = request.args.get('max_price', type=float)
    search = request.args.get('search')
    
    query = Product.query.filter_by(is_active=True)
    
    if category:
        try:
            category_enum = ProductCategory(category)
            query = query.filter_by(category=category_enum)
        except ValueError:
            abort(400, message=f'Invalid category: {category}')
    
    if min_price is not None:
        query = query.filter(Product.price >= min_price)
    
    if max_price is not None:
        query = query.filter(Product.price <= max_price)
    
    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))
    
    products = query.all()
    return [product.to_dict(include_inventory=True) for product in products]


@app.post('/api/products')
@app.input(ProductCreateSchema)
@app.output(ProductResponseSchema, status_code=201)
def create_product(json_data):
    """Create a new product."""
    # Check for duplicate SKU
    if Product.query.filter_by(sku=json_data['sku']).first():
        abort(409, message='SKU already exists')
    
    product = Product(
        name=json_data['name'],
        description=json_data.get('description'),
        category=json_data['category'],
        price=json_data['price'],
        sku=json_data['sku'],
        brand=json_data.get('brand'),
        weight_kg=json_data.get('weight_kg'),
        dimensions=json_data.get('dimensions')
    )
    
    db.session.add(product)
    db.session.flush()  # Get product ID
    
    # Create inventory record
    inventory = Inventory(
        product_id=product.id,
        quantity=json_data['initial_stock'],
        low_stock_threshold=json_data['low_stock_threshold']
    )
    db.session.add(inventory)
    db.session.commit()
    
    return product.to_dict(include_inventory=True)


@app.get('/api/products/<int:product_id>')
@app.output(ProductResponseSchema)
def get_product(product_id: int):
    """Get product details."""
    product = Product.query.get_or_404(product_id)
    return product.to_dict(include_inventory=True)


# Shopping Cart Management
@app.get('/api/users/<int:user_id>/cart')
@app.output(CartItemResponseSchema(many=True))
def get_cart(user_id: int):
    """Get user's shopping cart."""
    user = User.query.get_or_404(user_id)
    cart_items = user.cart_items.all()
    
    return [{
        'id': item.id,
        'product_id': item.product_id,
        'product_name': item.product.name,
        'quantity': item.quantity,
        'unit_price': float(item.product.price),
        'total_price': float(item.total_price),
        'added_at': item.added_at.isoformat()
    } for item in cart_items]


@app.post('/api/users/<int:user_id>/cart')
@app.input(CartItemCreateSchema)
@app.output(CartItemResponseSchema, status_code=201)
def add_to_cart(user_id: int, json_data):
    """Add item to shopping cart."""
    user = User.query.get_or_404(user_id)
    product = Product.query.get_or_404(json_data['product_id'])
    
    if not product.is_active:
        abort(400, message='Product is not available')
    
    # Check stock availability
    if not InventoryService.check_availability(product.id, json_data['quantity']):
        abort(400, message='Insufficient stock')
    
    # Check if item already in cart
    existing_cart_item = CartItem.query.filter_by(
        user_id=user_id,
        product_id=product.id
    ).first()
    
    if existing_cart_item:
        # Update quantity
        new_quantity = existing_cart_item.quantity + json_data['quantity']
        if not InventoryService.check_availability(product.id, new_quantity):
            abort(400, message='Insufficient stock for requested quantity')
        
        existing_cart_item.quantity = new_quantity
        cart_item = existing_cart_item
    else:
        # Create new cart item
        cart_item = CartItem(
            user_id=user_id,
            product_id=product.id,
            quantity=json_data['quantity']
        )
        db.session.add(cart_item)
    
    db.session.commit()
    
    return {
        'id': cart_item.id,
        'product_id': cart_item.product_id,
        'product_name': cart_item.product.name,
        'quantity': cart_item.quantity,
        'unit_price': float(cart_item.product.price),
        'total_price': float(cart_item.total_price),
        'added_at': cart_item.added_at.isoformat()
    }


@app.delete('/api/users/<int:user_id>/cart/<int:item_id>')
@app.output({}, status_code=204)
def remove_from_cart(user_id: int, item_id: int):
    """Remove item from cart."""
    cart_item = CartItem.query.filter_by(id=item_id, user_id=user_id).first_or_404()
    db.session.delete(cart_item)
    db.session.commit()
    return ''


# Order Management
@app.post('/api/users/<int:user_id>/orders')
@app.input(OrderCreateSchema)
@app.output(OrderResponseSchema, status_code=201)
def create_order(user_id: int, json_data):
    """Create order from user's cart."""
    try:
        order = OrderService.create_order(user_id, json_data['shipping_address'])
        return order.to_dict()
    except ValueError as e:
        abort(400, message=str(e))


@app.get('/api/users/<int:user_id>/orders')
@app.output(OrderResponseSchema(many=True))
def get_user_orders(user_id: int):
    """Get user's orders."""
    user = User.query.get_or_404(user_id)
    orders = user.orders.order_by(Order.created_at.desc()).all()
    return [order.to_dict() for order in orders]


@app.get('/api/orders/<int:order_id>')
@app.output(OrderDetailResponseSchema)
def get_order(order_id: int):
    """Get order details."""
    order = Order.query.get_or_404(order_id)
    return order.to_dict(include_items=True)


@app.patch('/api/orders/<int:order_id>/status')
@app.input({'status': EnumField(OrderStatus, by_value=True, required=True)})
@app.output(OrderResponseSchema)
def update_order_status(order_id: int, json_data):
    """Update order status."""
    try:
        order = OrderService.update_order_status(order_id, json_data['status'])
        return order.to_dict()
    except ValueError as e:
        abort(400, message=str(e))


# Analytics and Admin
@app.get('/api/admin/inventory/low-stock')
@app.output({
    'products': ListField(Nested(ProductResponseSchema))
})
def get_low_stock_products():
    """Get products with low stock levels."""
    low_stock_products = []
    
    for inventory in Inventory.query.all():
        if inventory.is_low_stock:
            product_data = inventory.product.to_dict(include_inventory=True)
            low_stock_products.append(product_data)
    
    return {'products': low_stock_products}


@app.get('/api/admin/orders/summary')
def get_order_summary():
    """Get order summary statistics."""
    from sqlalchemy import func
    
    # Order status counts
    status_counts = db.session.query(
        Order.status,
        func.count(Order.id)
    ).group_by(Order.status).all()
    
    # Revenue by date (last 30 days)
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    revenue = db.session.query(
        func.sum(Order.total_amount)
    ).filter(
        Order.created_at >= thirty_days_ago,
        Order.status.in_([OrderStatus.DELIVERED, OrderStatus.SHIPPED])
    ).scalar() or 0
    
    return {
        'status_counts': {status.value: count for status, count in status_counts},
        'revenue_30_days': float(revenue),
        'total_orders': Order.query.count(),
        'total_users': User.query.count(),
        'total_products': Product.query.filter_by(is_active=True).count()
    }


# Initialize database
with app.app_context():
    db.create_all()
    
    # Create sample data
    if User.query.count() == 0:
        # Create admin user
        admin = User(
            username='admin',
            email='admin@ecommerce.com',
            first_name='Admin',
            last_name='User',
            role=UserRole.ADMIN
        )
        admin.set_password('admin123')
        db.session.add(admin)
        
        # Create sample products
        products_data = [
            {
                'name': 'Wireless Headphones',
                'description': 'High-quality wireless headphones with noise cancellation',
                'category': ProductCategory.ELECTRONICS,
                'price': 299.99,
                'sku': 'WH-001',
                'brand': 'TechBrand',
                'weight_kg': 0.5
            },
            {
                'name': 'Cotton T-Shirt',
                'description': '100% organic cotton t-shirt',
                'category': ProductCategory.CLOTHING,
                'price': 29.99,
                'sku': 'TS-001',
                'brand': 'FashionCorp',
                'weight_kg': 0.2
            },
            {
                'name': 'Python Programming Book',
                'description': 'Learn Python programming from scratch',
                'category': ProductCategory.BOOKS,
                'price': 49.99,
                'sku': 'BK-001',
                'brand': 'TechPublisher',
                'weight_kg': 0.8
            }
        ]
        
        for product_data in products_data:
            product = Product(**product_data)
            db.session.add(product)
            db.session.flush()
            
            # Add inventory
            inventory = Inventory(
                product_id=product.id,
                quantity=100,
                low_stock_threshold=10
            )
            db.session.add(inventory)
        
        db.session.commit()


if __name__ == '__main__':
    app.run(debug=True)


"""
E-commerce API Features Demonstrated:
=====================================

1. Complex Domain Model:
   - Users with roles (Customer, Admin, Vendor)
   - Products with categories and inventory
   - Shopping cart functionality
   - Order lifecycle management
   - Reviews and ratings

2. Business Logic:
   - Stock reservation system
   - Order status state machine
   - Price calculations (tax, shipping)
   - Inventory management
   - Business rule validation

3. Advanced Relationships:
   - One-to-Many: User -> Orders, Product -> Reviews
   - Many-to-Many: Users <-> Products (through Cart, Orders)
   - Complex queries and aggregations

4. Real-world Scenarios:
   - Cart management with stock checking
   - Order workflow with status transitions
   - Inventory tracking and low stock alerts
   - Multi-step checkout process

5. API Design Patterns:
   - Resource-based URLs
   - Proper HTTP status codes
   - Nested resources (/users/{id}/cart)
   - Filtering and search capabilities

Usage Examples:

1. Create user:
   POST /api/users
   {"username": "john", "email": "john@example.com", "password": "password123", "first_name": "John", "last_name": "Doe"}

2. Add products to cart:
   POST /api/users/1/cart
   {"product_id": 1, "quantity": 2}

3. Create order:
   POST /api/users/1/orders
   {"shipping_address": {"street": "123 Main St", "city": "Anytown", "state": "CA", "zip_code": "12345", "country": "US"}}

4. Update order status:
   PATCH /api/orders/1/status
   {"status": "shipped"}

This example provides a solid foundation for building production-grade
e-commerce APIs with complex business logic and relationships.
"""
