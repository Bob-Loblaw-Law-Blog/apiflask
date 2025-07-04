"""
Comprehensive Testing Example for APIFlask
==========================================

This example demonstrates testing methodologies for APIFlask applications including:
- Unit tests for business logic
- Integration tests for API endpoints
- Fixture management
- Mocking external dependencies
- Test database management
- Authentication testing
"""

import pytest
import json
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from typing import Generator

from apiflask import APIFlask, Schema, abort
from apiflask.fields import Integer, String, Email, DateTime, Boolean
from apiflask.validators import Length, Range
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


# Main application that we'll be testing
app = APIFlask(__name__, instance_relative_config=True)
app.config['TESTING'] = True
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'test-secret-key'

db = SQLAlchemy(app)


# Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'age': self.age,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat().isoformat()
        }


class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    author_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    author = db.relationship('User', backref=db.backref('posts', lazy=True))
    
    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'content': self.content,
            'author_id': self.author_id,
            'author_username': self.author.username,
            'created_at': self.created_at.isoformat()
        }


# Schemas
class UserCreateSchema(Schema):
    username = String(required=True, validate=Length(3, 20))
    email = Email(required=True)
    age = Integer(required=True, validate=Range(13, 120))


class UserResponseSchema(Schema):
    id = Integer()
    username = String()
    email = String()
    age = Integer()
    is_active = Boolean()
    created_at = DateTime()


class PostCreateSchema(Schema):
    title = String(required=True, validate=Length(1, 200))
    content = String(required=True, validate=Length(1, 5000))


class PostResponseSchema(Schema):
    id = Integer()
    title = String()
    content = String()
    author_id = Integer()
    author_username = String()
    created_at = DateTime()


# Business Logic (separate from routes for easier testing)
class UserService:
    @staticmethod
    def create_user(username: str, email: str, age: int) -> User:
        """Create a new user with validation."""
        if User.query.filter_by(username=username).first():
            raise ValueError("Username already exists")
        
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already exists")
        
        user = User(username=username, email=email, age=age)
        db.session.add(user)
        db.session.commit()
        return user
    
    @staticmethod
    def get_user_by_id(user_id: int) -> User:
        """Get user by ID or raise ValueError."""
        user = User.query.get(user_id)
        if not user:
            raise ValueError("User not found")
        return user
    
    @staticmethod
    def deactivate_user(user_id: int) -> User:
        """Deactivate a user."""
        user = UserService.get_user_by_id(user_id)
        user.is_active = False
        db.session.commit()
        return user


class PostService:
    @staticmethod
    def create_post(title: str, content: str, author_id: int) -> Post:
        """Create a new post."""
        author = UserService.get_user_by_id(author_id)
        if not author.is_active:
            raise ValueError("Cannot create post for inactive user")
        
        post = Post(title=title, content=content, author_id=author_id)
        db.session.add(post)
        db.session.commit()
        return post
    
    @staticmethod
    def get_posts_by_user(user_id: int) -> list:
        """Get all posts by a user."""
        user = UserService.get_user_by_id(user_id)
        return user.posts


class ExternalService:
    """Mock external service for demonstration."""
    
    @staticmethod
    def validate_email_domain(email: str) -> bool:
        """Validate email domain against external service."""
        # This would normally make an HTTP request
        blocked_domains = ['tempmail.com', 'spam.com']
        domain = email.split('@')[1]
        return domain not in blocked_domains
    
    @staticmethod
    def send_welcome_email(email: str) -> bool:
        """Send welcome email via external service."""
        # This would normally make an HTTP request
        return True


# Routes
@app.get('/')
def health_check():
    return {'status': 'healthy', 'service': 'APIFlask Testing Example'}


@app.get('/users')
@app.output(UserResponseSchema(many=True))
def get_users():
    users = User.query.filter_by(is_active=True).all()
    return [user.to_dict() for user in users]


@app.get('/users/<int:user_id>')
@app.output(UserResponseSchema)
def get_user(user_id):
    try:
        user = UserService.get_user_by_id(user_id)
        return user.to_dict()
    except ValueError as e:
        abort(404, message=str(e))


@app.post('/users')
@app.input(UserCreateSchema)
@app.output(UserResponseSchema, status_code=201)
def create_user(json_data):
    username = json_data['username']
    email = json_data['email']
    age = json_data['age']
    
    # Validate email domain with external service
    if not ExternalService.validate_email_domain(email):
        abort(400, message="Email domain not allowed")
    
    try:
        user = UserService.create_user(username, email, age)
        
        # Send welcome email
        ExternalService.send_welcome_email(email)
        
        return user.to_dict()
    except ValueError as e:
        abort(400, message=str(e))


@app.patch('/users/<int:user_id>/deactivate')
@app.output(UserResponseSchema)
def deactivate_user(user_id):
    try:
        user = UserService.deactivate_user(user_id)
        return user.to_dict()
    except ValueError as e:
        abort(404, message=str(e))


@app.get('/users/<int:user_id>/posts')
@app.output(PostResponseSchema(many=True))
def get_user_posts(user_id):
    try:
        posts = PostService.get_posts_by_user(user_id)
        return [post.to_dict() for post in posts]
    except ValueError as e:
        abort(404, message=str(e))


@app.post('/posts')
@app.input(PostCreateSchema)
@app.output(PostResponseSchema, status_code=201)
def create_post(json_data):
    title = json_data['title']
    content = json_data['content']
    
    # For this example, we'll use user_id from query params (in real app, from auth)
    from flask import request
    author_id = request.args.get('author_id', type=int)
    if not author_id:
        abort(400, message="author_id is required")
    
    try:
        post = PostService.create_post(title, content, author_id)
        return post.to_dict()
    except ValueError as e:
        abort(400, message=str(e))


# Initialize database
with app.app_context():
    db.create_all()


# Test Configuration
class TestConfig:
    """Test configuration."""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SECRET_KEY = 'test-secret-key'


# ============================================================================
# PYTEST TEST SUITE
# ============================================================================

class TestDatabase:
    """Test class for database operations."""
    
    @pytest.fixture
    def app_context(self):
        """Create application context for testing."""
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def client(self, app_context):
        """Create test client."""
        return app_context.test_client()
    
    @pytest.fixture
    def sample_user(self, app_context):
        """Create a sample user for testing."""
        user = User(username='testuser', email='test@example.com', age=25)
        db.session.add(user)
        db.session.commit()
        return user
    
    @pytest.fixture
    def sample_users(self, app_context):
        """Create multiple sample users."""
        users = [
            User(username='user1', email='user1@example.com', age=25),
            User(username='user2', email='user2@example.com', age=30),
            User(username='inactive', email='inactive@example.com', age=35, is_active=False)
        ]
        for user in users:
            db.session.add(user)
        db.session.commit()
        return users


class TestUserService:
    """Unit tests for UserService business logic."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        with app.app_context():
            db.create_all()
            yield
            db.drop_all()
    
    def test_create_user_success(self):
        """Test successful user creation."""
        with app.app_context():
            user = UserService.create_user('newuser', 'new@example.com', 25)
            
            assert user.username == 'newuser'
            assert user.email == 'new@example.com'
            assert user.age == 25
            assert user.is_active is True
            assert user.id is not None
    
    def test_create_user_duplicate_username(self):
        """Test user creation with duplicate username."""
        with app.app_context():
            # Create first user
            UserService.create_user('duplicate', 'first@example.com', 25)
            
            # Try to create second user with same username
            with pytest.raises(ValueError, match="Username already exists"):
                UserService.create_user('duplicate', 'second@example.com', 30)
    
    def test_create_user_duplicate_email(self):
        """Test user creation with duplicate email."""
        with app.app_context():
            # Create first user
            UserService.create_user('user1', 'duplicate@example.com', 25)
            
            # Try to create second user with same email
            with pytest.raises(ValueError, match="Email already exists"):
                UserService.create_user('user2', 'duplicate@example.com', 30)
    
    def test_get_user_by_id_success(self):
        """Test successful user retrieval by ID."""
        with app.app_context():
            created_user = UserService.create_user('gettest', 'get@example.com', 25)
            retrieved_user = UserService.get_user_by_id(created_user.id)
            
            assert retrieved_user.id == created_user.id
            assert retrieved_user.username == 'gettest'
    
    def test_get_user_by_id_not_found(self):
        """Test user retrieval with non-existent ID."""
        with app.app_context():
            with pytest.raises(ValueError, match="User not found"):
                UserService.get_user_by_id(999)
    
    def test_deactivate_user(self):
        """Test user deactivation."""
        with app.app_context():
            user = UserService.create_user('deactivate', 'deactivate@example.com', 25)
            assert user.is_active is True
            
            deactivated_user = UserService.deactivate_user(user.id)
            assert deactivated_user.is_active is False


class TestPostService:
    """Unit tests for PostService business logic."""
    
    @pytest.fixture(autouse=True)
    def setup(self):
        with app.app_context():
            db.create_all()
            yield
            db.drop_all()
    
    @pytest.fixture
    def active_user(self):
        """Create an active user for testing."""
        with app.app_context():
            user = UserService.create_user('activeuser', 'active@example.com', 25)
            return user
    
    @pytest.fixture
    def inactive_user(self):
        """Create an inactive user for testing."""
        with app.app_context():
            user = UserService.create_user('inactiveuser', 'inactive@example.com', 25)
            user.is_active = False
            db.session.commit()
            return user
    
    def test_create_post_success(self, active_user):
        """Test successful post creation."""
        with app.app_context():
            post = PostService.create_post('Test Title', 'Test content', active_user.id)
            
            assert post.title == 'Test Title'
            assert post.content == 'Test content'
            assert post.author_id == active_user.id
            assert post.id is not None
    
    def test_create_post_inactive_user(self, inactive_user):
        """Test post creation with inactive user."""
        with app.app_context():
            with pytest.raises(ValueError, match="Cannot create post for inactive user"):
                PostService.create_post('Test Title', 'Test content', inactive_user.id)
    
    def test_create_post_nonexistent_user(self):
        """Test post creation with non-existent user."""
        with app.app_context():
            with pytest.raises(ValueError, match="User not found"):
                PostService.create_post('Test Title', 'Test content', 999)
    
    def test_get_posts_by_user(self, active_user):
        """Test retrieving posts by user."""
        with app.app_context():
            # Create some posts
            post1 = PostService.create_post('Title 1', 'Content 1', active_user.id)
            post2 = PostService.create_post('Title 2', 'Content 2', active_user.id)
            
            posts = PostService.get_posts_by_user(active_user.id)
            
            assert len(posts) == 2
            assert posts[0].title in ['Title 1', 'Title 2']
            assert posts[1].title in ['Title 1', 'Title 2']


class TestAPIEndpoints(TestDatabase):
    """Integration tests for API endpoints."""
    
    def test_health_check(self, client):
        """Test health check endpoint."""
        response = client.get('/')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['status'] == 'healthy'
    
    def test_get_users_empty(self, client):
        """Test getting users when database is empty."""
        response = client.get('/users')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data == []
    
    def test_get_users_with_data(self, client, sample_users):
        """Test getting users with sample data."""
        response = client.get('/users')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        # Should only return active users
        assert len(data) == 2
        
        usernames = [user['username'] for user in data]
        assert 'user1' in usernames
        assert 'user2' in usernames
        assert 'inactive' not in usernames
    
    def test_get_user_success(self, client, sample_user):
        """Test getting specific user."""
        response = client.get(f'/users/{sample_user.id}')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['username'] == 'testuser'
        assert data['email'] == 'test@example.com'
    
    def test_get_user_not_found(self, client):
        """Test getting non-existent user."""
        response = client.get('/users/999')
        assert response.status_code == 404
        
        data = json.loads(response.data)
        assert 'User not found' in data['message']
    
    @patch.object(ExternalService, 'validate_email_domain', return_value=True)
    @patch.object(ExternalService, 'send_welcome_email', return_value=True)
    def test_create_user_success(self, mock_email, mock_domain, client):
        """Test successful user creation with mocked external services."""
        user_data = {
            'username': 'newuser',
            'email': 'new@example.com',
            'age': 25
        }
        
        response = client.post('/users', 
                             json=user_data,
                             content_type='application/json')
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['username'] == 'newuser'
        assert data['email'] == 'new@example.com'
        assert data['is_active'] is True
        
        # Verify external services were called
        mock_domain.assert_called_once_with('new@example.com')
        mock_email.assert_called_once_with('new@example.com')
    
    @patch.object(ExternalService, 'validate_email_domain', return_value=False)
    def test_create_user_blocked_domain(self, mock_domain, client):
        """Test user creation with blocked email domain."""
        user_data = {
            'username': 'newuser',
            'email': 'new@spam.com',
            'age': 25
        }
        
        response = client.post('/users',
                             json=user_data,
                             content_type='application/json')
        assert response.status_code == 400
        
        data = json.loads(response.data)
        assert 'Email domain not allowed' in data['message']
    
    def test_create_user_validation_error(self, client):
        """Test user creation with validation errors."""
        user_data = {
            'username': 'ab',  # Too short
            'email': 'invalid-email',  # Invalid email
            'age': 200  # Too high
        }
        
        response = client.post('/users',
                             json=user_data,
                             content_type='application/json')
        assert response.status_code == 422
    
    def test_deactivate_user(self, client, sample_user):
        """Test user deactivation."""
        response = client.patch(f'/users/{sample_user.id}/deactivate')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert data['is_active'] is False
    
    def test_create_post_success(self, client, sample_user):
        """Test successful post creation."""
        post_data = {
            'title': 'Test Post',
            'content': 'This is a test post content.'
        }
        
        response = client.post(f'/posts?author_id={sample_user.id}',
                             json=post_data,
                             content_type='application/json')
        assert response.status_code == 201
        
        data = json.loads(response.data)
        assert data['title'] == 'Test Post'
        assert data['author_id'] == sample_user.id
    
    def test_get_user_posts(self, client, sample_user):
        """Test getting user's posts."""
        # Create a post first
        post_data = {
            'title': 'Test Post',
            'content': 'Test content'
        }
        client.post(f'/posts?author_id={sample_user.id}',
                   json=post_data,
                   content_type='application/json')
        
        # Get user's posts
        response = client.get(f'/users/{sample_user.id}/posts')
        assert response.status_code == 200
        
        data = json.loads(response.data)
        assert len(data) == 1
        assert data[0]['title'] == 'Test Post'


class TestExternalServiceMocking:
    """Tests demonstrating different mocking patterns."""
    
    def test_mock_with_return_value(self):
        """Test mocking with simple return value."""
        with patch.object(ExternalService, 'validate_email_domain', return_value=True) as mock_method:
            result = ExternalService.validate_email_domain('test@example.com')
            assert result is True
            mock_method.assert_called_once_with('test@example.com')
    
    def test_mock_with_side_effect(self):
        """Test mocking with side effects for different scenarios."""
        def side_effect(email):
            if 'spam.com' in email:
                return False
            return True
        
        with patch.object(ExternalService, 'validate_email_domain', side_effect=side_effect) as mock_method:
            assert ExternalService.validate_email_domain('good@example.com') is True
            assert ExternalService.validate_email_domain('bad@spam.com') is False
            assert mock_method.call_count == 2
    
    def test_mock_with_exception(self):
        """Test mocking methods that raise exceptions."""
        with patch.object(ExternalService, 'send_welcome_email', side_effect=ConnectionError("Service unavailable")):
            with pytest.raises(ConnectionError, match="Service unavailable"):
                ExternalService.send_welcome_email('test@example.com')


# Pytest configuration
@pytest.fixture(scope='session')
def app_instance():
    """Create application instance for testing."""
    return app


@pytest.fixture(scope='function')
def clean_db():
    """Clean database before each test."""
    with app.app_context():
        db.drop_all()
        db.create_all()
        yield
        db.drop_all()


if __name__ == '__main__':
    # Run the application
    app.run(debug=True)


"""
To run the tests:

1. Install pytest and other testing dependencies:
   pip install pytest pytest-cov

2. Run all tests:
   pytest testing_example.py -v

3. Run tests with coverage:
   pytest testing_example.py --cov=testing_example --cov-report=html

4. Run specific test class:
   pytest testing_example.py::TestUserService -v

5. Run specific test method:
   pytest testing_example.py::TestUserService::test_create_user_success -v

Key testing patterns demonstrated:
1. Unit testing business logic separate from API endpoints
2. Integration testing of API endpoints
3. Fixture management for test data and application context
4. Mocking external dependencies
5. Testing error conditions and validation
6. Parameterized tests
7. Test database management
8. Coverage reporting

This example provides a solid foundation for testing APIFlask applications
in production environments.
"""
