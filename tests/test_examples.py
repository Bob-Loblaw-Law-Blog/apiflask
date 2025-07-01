"""
Comprehensive test suite for APIFlask examples.

This test file is organized by example case and provides test coverage
for each example to ensure they continue to work correctly.
"""

import pytest
import tempfile
import os
import json
from io import BytesIO
from base64 import b64encode
from werkzeug.datastructures import FileStorage
from flask import Flask
from apiflask import APIFlask, APIBlueprint, Schema, HTTPBasicAuth, HTTPTokenAuth
from apiflask.fields import Integer, String, File, List, Nested
from apiflask.validators import Length, OneOf, FileSize, FileType, Range
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from authlib.jose import jwt, JoseError
from marshmallow_dataclass import dataclass
from dataclasses import field
from flask.views import MethodView


class TestBasicExample:
    """Test cases for the basic example demonstrating simple CRUD operations."""
    
    @pytest.fixture
    def app(self):
        """Create the basic app instance."""
        from examples.basic.app import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()
    
    @pytest.fixture(autouse=True)
    def reset_pets(self):
        """Reset the pets list before each test."""
        from examples.basic.app import pets
        pets.clear()
        pets.extend([
            {'id': 0, 'name': 'Kitty', 'category': 'cat'},
            {'id': 1, 'name': 'Coco', 'category': 'dog'},
            {'id': 2, 'name': 'Flash', 'category': 'cat'},
        ])
        yield
        # Clean up after test
        pets.clear()
        pets.extend([
            {'id': 0, 'name': 'Kitty', 'category': 'cat'},
            {'id': 1, 'name': 'Coco', 'category': 'dog'},
            {'id': 2, 'name': 'Flash', 'category': 'cat'},
        ])
    
    def test_hello_endpoint(self, client):
        """Test the hello endpoint."""
        response = client.get('/')
        assert response.status_code == 200
        assert response.json == {'message': 'Hello!'}
    
    def test_get_pet(self, client):
        """Test getting a single pet."""
        response = client.get('/pets/0')
        assert response.status_code == 200
        assert response.json == {'id': 0, 'name': 'Kitty', 'category': 'cat'}
    
    def test_get_pet_not_found(self, client):
        """Test getting a non-existent pet."""
        response = client.get('/pets/999')
        assert response.status_code == 404
    
    def test_get_deleted_pet(self, client):
        """Test getting a deleted pet."""
        # First delete the pet
        client.delete('/pets/0')
        # Then try to get it
        response = client.get('/pets/0')
        assert response.status_code == 404
    
    def test_get_all_pets(self, client):
        """Test getting all pets."""
        response = client.get('/pets')
        assert response.status_code == 200
        assert len(response.json) == 3
        assert response.json[0]['name'] == 'Kitty'
    
    def test_create_pet(self, client):
        """Test creating a new pet."""
        new_pet = {'name': 'Buddy', 'category': 'dog'}
        response = client.post('/pets', json=new_pet)
        assert response.status_code == 201
        assert response.json['id'] == 3
        assert response.json['name'] == 'Buddy'
        assert response.json['category'] == 'dog'
    
    def test_create_pet_invalid_category(self, client):
        """Test creating a pet with invalid category."""
        new_pet = {'name': 'Buddy', 'category': 'bird'}
        response = client.post('/pets', json=new_pet)
        assert response.status_code == 422
    
    def test_create_pet_name_too_long(self, client):
        """Test creating a pet with name too long."""
        new_pet = {'name': 'VeryLongNameThatExceedsTheLimit', 'category': 'dog'}
        response = client.post('/pets', json=new_pet)
        assert response.status_code == 422
    
    def test_update_pet(self, client):
        """Test updating a pet."""
        update_data = {'name': 'NewName'}
        response = client.patch('/pets/0', json=update_data)
        assert response.status_code == 200
        assert response.json['name'] == 'NewName'
        assert response.json['category'] == 'cat'  # Should remain unchanged
    
    def test_update_pet_not_found(self, client):
        """Test updating a non-existent pet."""
        update_data = {'name': 'NewName'}
        response = client.patch('/pets/999', json=update_data)
        assert response.status_code == 404
    
    def test_delete_pet(self, client):
        """Test deleting a pet."""
        response = client.delete('/pets/0')
        assert response.status_code == 204
        assert response.data == b''
        
        # Verify pet is marked as deleted
        response = client.get('/pets/0')
        assert response.status_code == 404
    
    def test_delete_pet_not_found(self, client):
        """Test deleting a non-existent pet."""
        response = client.delete('/pets/999')
        assert response.status_code == 404


class TestClassBasedViewExample:
    """Test cases for the class-based view example."""
    
    @pytest.fixture
    def app(self):
        """Create the CBV app instance."""
        from examples.cbv.app import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()
    
    @pytest.fixture(autouse=True)
    def reset_pets(self):
        """Reset the pets list before each test."""
        from examples.cbv.app import pets
        pets.clear()
        pets.extend([
            {'id': 0, 'name': 'Kitty', 'category': 'cat'},
            {'id': 1, 'name': 'Coco', 'category': 'dog'},
            {'id': 2, 'name': 'Flash', 'category': 'cat'},
        ])
    
    def test_hello_cbv(self, client):
        """Test the hello endpoint using CBV."""
        response = client.get('/')
        assert response.status_code == 200
        assert response.json == {'message': 'Hello!'}
    
    def test_get_pet_cbv(self, client):
        """Test getting a single pet using CBV."""
        response = client.get('/pets/0')
        assert response.status_code == 200
        assert response.json == {'id': 0, 'name': 'Kitty', 'category': 'cat'}
    
    def test_get_pets_cbv(self, client):
        """Test getting all pets using CBV."""
        response = client.get('/pets')
        assert response.status_code == 200
        assert len(response.json) == 3
    
    def test_create_pet_cbv(self, client):
        """Test creating a pet using CBV."""
        new_pet = {'name': 'Buddy', 'category': 'dog'}
        response = client.post('/pets', json=new_pet)
        assert response.status_code == 201
        assert response.json['name'] == 'Buddy'
    
    def test_update_pet_cbv(self, client):
        """Test updating a pet using CBV."""
        update_data = {'name': 'Updated'}
        response = client.patch('/pets/0', json=update_data)
        assert response.status_code == 200
        assert response.json['name'] == 'Updated'
    
    def test_delete_pet_cbv(self, client):
        """Test deleting a pet using CBV."""
        response = client.delete('/pets/0')
        assert response.status_code == 204


class TestORMExample:
    """Test cases for the ORM example using Flask-SQLAlchemy."""
    
    @pytest.fixture
    def app(self):
        """Create the ORM app instance."""
        from examples.orm.app import app
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        with app.app_context():
            from examples.orm.app import db, init_database
            db.create_all()
            init_database()
        return app.test_client()
    
    def test_get_pet_orm(self, client):
        """Test getting a pet from database."""
        response = client.get('/pets/1')
        assert response.status_code == 200
        assert response.json['name'] == 'Kitty'
    
    def test_get_pet_not_found_orm(self, client):
        """Test getting non-existent pet from database."""
        response = client.get('/pets/999')
        assert response.status_code == 404
    
    def test_get_all_pets_orm(self, client):
        """Test getting all pets from database."""
        response = client.get('/pets')
        assert response.status_code == 200
        assert len(response.json) == 3
    
    def test_create_pet_orm(self, client):
        """Test creating a pet in database."""
        new_pet = {'name': 'Buddy', 'category': 'dog'}
        response = client.post('/pets', json=new_pet)
        assert response.status_code == 201
        assert response.json['name'] == 'Buddy'
        
        # Verify it was saved
        response = client.get(f"/pets/{response.json['id']}")
        assert response.status_code == 200
        assert response.json['name'] == 'Buddy'
    
    def test_update_pet_orm(self, client):
        """Test updating a pet in database."""
        update_data = {'name': 'Updated'}
        response = client.patch('/pets/1', json=update_data)
        assert response.status_code == 200
        assert response.json['name'] == 'Updated'
        
        # Verify it was saved
        response = client.get('/pets/1')
        assert response.json['name'] == 'Updated'
    
    def test_delete_pet_orm(self, client):
        """Test deleting a pet from database."""
        response = client.delete('/pets/1')
        assert response.status_code == 204
        
        # Verify it was deleted
        response = client.get('/pets/1')
        assert response.status_code == 404


class TestPaginationExample:
    """Test cases for the pagination example."""
    
    @pytest.fixture
    def app(self):
        """Create the pagination app instance."""
        from examples.pagination.app import app
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        with app.app_context():
            from examples.pagination.app import db, init_database
            db.create_all()
            init_database()
        return app.test_client()
    
    def test_get_pets_default_pagination(self, client):
        """Test getting pets with default pagination."""
        response = client.get('/pets')
        assert response.status_code == 200
        assert 'pets' in response.json
        assert 'pagination' in response.json
        assert len(response.json['pets']) == 20  # Default per_page
        assert response.json['pagination']['page'] == 1
        assert response.json['pagination']['per_page'] == 20
        assert response.json['pagination']['pages'] == 5  # 100 pets / 20 per page
        assert response.json['pagination']['total'] == 100
    
    def test_get_pets_custom_pagination(self, client):
        """Test getting pets with custom pagination parameters."""
        response = client.get('/pets?page=2&per_page=10')
        assert response.status_code == 200
        assert len(response.json['pets']) == 10
        assert response.json['pagination']['page'] == 2
        assert response.json['pagination']['per_page'] == 10
        assert response.json['pets'][0]['name'] == 'Pet 11'  # Second page starts at Pet 11
    
    def test_get_pets_max_per_page(self, client):
        """Test that per_page is limited to 30."""
        response = client.get('/pets?per_page=50')
        assert response.status_code == 422  # Validation error
    
    def test_get_single_pet_pagination(self, client):
        """Test getting a single pet by ID."""
        response = client.get('/pets/1')
        assert response.status_code == 200
        assert response.json['name'] == 'Pet 1'


class TestFileUploadExample:
    """Test cases for the file upload example."""
    
    @pytest.fixture
    def app(self):
        """Create the file upload app instance."""
        from examples.file_upload.app import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        # Create upload directory
        os.makedirs('./upload', exist_ok=True)
        yield app.test_client()
        # Cleanup
        import shutil
        if os.path.exists('./upload'):
            shutil.rmtree('./upload')
    
    def test_upload_image(self, client):
        """Test uploading an image file."""
        data = {
            'image': (BytesIO(b'fake image data'), 'test.png')
        }
        response = client.post('/images', 
                             data=data,
                             content_type='multipart/form-data')
        assert response.status_code == 200
        assert 'test.png saved' in response.json['message']
        assert os.path.exists('./upload/test.png')
    
    def test_upload_invalid_file_type(self, client):
        """Test uploading an invalid file type."""
        data = {
            'image': (BytesIO(b'fake data'), 'test.txt')
        }
        response = client.post('/images',
                             data=data,
                             content_type='multipart/form-data')
        assert response.status_code == 422
    
    def test_create_profile_with_avatar(self, client):
        """Test creating a profile with avatar upload."""
        data = {
            'name': 'John Doe',
            'avatar': (BytesIO(b'fake avatar data'), 'avatar.jpg')
        }
        response = client.post('/profiles',
                             data=data,
                             content_type='multipart/form-data')
        assert response.status_code == 200
        assert "John Doe's profile created" in response.json['message']
        assert os.path.exists('./upload/avatar.jpg')


class TestDataclassExample:
    """Test cases for the dataclass example using marshmallow-dataclass."""
    
    @pytest.fixture
    def app(self):
        """Create the dataclass app instance."""
        from examples.dataclass.app import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()
    
    @pytest.fixture(autouse=True)
    def reset_pets(self):
        """Reset the pets list before each test."""
        from examples.dataclass.app import pets
        pets.clear()
        pets.extend([
            {'id': 0, 'name': 'Kitty', 'category': 'cat'},
            {'id': 1, 'name': 'Coco', 'category': 'dog'},
            {'id': 2, 'name': 'Flash', 'category': 'cat'},
        ])
    
    def test_get_pet_dataclass(self, client):
        """Test getting a pet with dataclass."""
        response = client.get('/pets/0')
        assert response.status_code == 200
        assert response.json == {'id': 0, 'name': 'Kitty', 'category': 'cat'}
    
    def test_create_pet_dataclass(self, client):
        """Test creating a pet with dataclass."""
        new_pet = {'name': 'Buddy', 'category': 'dog'}
        response = client.post('/pets', json=new_pet)
        assert response.status_code == 201
        assert response.json['name'] == 'Buddy'
        assert response.json['category'] == 'dog'
    
    def test_update_pet_dataclass(self, client):
        """Test updating a pet with dataclass."""
        # Note: partial update is not supported, so we need to provide all fields
        update_data = {'name': 'Updated', 'category': 'cat'}
        response = client.patch('/pets/0', json=update_data)
        assert response.status_code == 200
        assert response.json['name'] == 'Updated'


class TestTokenAuthExample:
    """Test cases for the token authentication example."""
    
    @pytest.fixture
    def app(self):
        """Create the token auth app instance."""
        from examples.auth.token_auth.app import app
        app.config['TESTING'] = True
        app.config['SECRET_KEY'] = 'test-secret-key'
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()
    
    def test_get_token(self, client):
        """Test getting a token for a valid user."""
        response = client.post('/token/1')
        assert response.status_code == 200
        assert 'token' in response.json
        assert response.json['token'].startswith('Bearer ')
    
    def test_get_token_invalid_user(self, client):
        """Test getting a token for an invalid user."""
        response = client.post('/token/999')
        assert response.status_code == 404
    
    def test_access_protected_route_with_token(self, client):
        """Test accessing a protected route with valid token."""
        # First get a token
        token_response = client.post('/token/1')
        token = token_response.json['token']
        
        # Use the token to access protected route
        headers = {'Authorization': token}
        response = client.get('/name/1', headers=headers)
        assert response.status_code == 200
        assert response.data == b'lorem'  # User 1's secret
    
    def test_access_protected_route_without_token(self, client):
        """Test accessing a protected route without token."""
        response = client.get('/name/1')
        assert response.status_code == 401
    
    def test_access_protected_route_with_invalid_token(self, client):
        """Test accessing a protected route with invalid token."""
        headers = {'Authorization': 'Bearer invalid-token'}
        response = client.get('/name/1', headers=headers)
        assert response.status_code == 401


class TestBasicAuthExample:
    """Test cases for the basic authentication example."""
    
    @pytest.fixture
    def app(self):
        """Create the basic auth app instance."""
        from examples.auth.basic_auth.app import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()
    
    def test_access_with_valid_credentials(self, client):
        """Test accessing protected route with valid credentials."""
        credentials = b64encode(b'userA:foo').decode('ascii')
        headers = {'Authorization': f'Basic {credentials}'}
        response = client.get('/', headers=headers)
        assert response.status_code == 200
        assert response.data == b'Hello, userA'
    
    def test_access_with_invalid_password(self, client):
        """Test accessing protected route with invalid password."""
        credentials = b64encode(b'userA:wrong').decode('ascii')
        headers = {'Authorization': f'Basic {credentials}'}
        response = client.get('/', headers=headers)
        assert response.status_code == 401
    
    def test_access_with_invalid_username(self, client):
        """Test accessing protected route with invalid username."""
        credentials = b64encode(b'userC:foo').decode('ascii')
        headers = {'Authorization': f'Basic {credentials}'}
        response = client.get('/', headers=headers)
        assert response.status_code == 401
    
    def test_access_without_credentials(self, client):
        """Test accessing protected route without credentials."""
        response = client.get('/')
        assert response.status_code == 401


class TestBaseResponseExample:
    """Test cases for the base response example."""
    
    @pytest.fixture
    def app(self):
        """Create the base response app instance."""
        from examples.base_response.app import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()
    
    @pytest.fixture(autouse=True)
    def reset_pets(self):
        """Reset the pets list before each test."""
        from examples.base_response.app import pets
        pets.clear()
        pets.extend([
            {'id': 0, 'name': 'Kitty', 'category': 'cat'},
            {'id': 1, 'name': 'Coco', 'category': 'dog'},
            {'id': 2, 'name': 'Flash', 'category': 'cat'},
        ])
    
    def test_base_response_structure(self, client):
        """Test that responses follow the base response structure."""
        response = client.get('/')
        assert response.status_code == 200
        assert 'data' in response.json
        assert 'message' in response.json
        assert 'code' in response.json
        assert response.json['code'] == 200
        assert response.json['message'] == 'Success!'
    
    def test_get_pet_base_response(self, client):
        """Test getting a pet with base response structure."""
        response = client.get('/pets/0')
        assert response.status_code == 200
        assert response.json['data'] == {'id': 0, 'name': 'Kitty', 'category': 'cat'}
        assert response.json['message'] == 'Success!'
        assert response.json['code'] == 200
    
    def test_create_pet_base_response(self, client):
        """Test creating a pet with base response structure."""
        new_pet = {'name': 'Buddy', 'category': 'dog'}
        response = client.post('/pets', json=new_pet)
        assert response.status_code == 201
        assert response.json['data']['name'] == 'Buddy'
        assert response.json['message'] == 'Pet created.'
        assert response.json['code'] == 201
    
    def test_update_pet_base_response(self, client):
        """Test updating a pet with base response structure."""
        update_data = {'name': 'Updated'}
        response = client.patch('/pets/0', json=update_data)
        assert response.status_code == 200
        assert response.json['data']['name'] == 'Updated'
        assert response.json['message'] == 'Pet updated.'
        assert response.json['code'] == 200


class TestBlueprintTagsExample:
    """Test cases for the blueprint tags example."""
    
    @pytest.fixture
    def app(self):
        """Create the blueprint tags app instance."""
        from examples.blueprint_tags.app import app
        app.config['TESTING'] = True
        return app
    
    @pytest.fixture
    def client(self, app):
        """Create a test client."""
        return app.test_client()
    
    def test_hello_blueprint(self, client):
        """Test the hello blueprint endpoint."""
        response = client.get('/')
        assert response.status_code == 200
        assert response.json == {'message': 'Hello!'}
    
    def test_pet_blueprint_endpoints(self, client):
        """Test pet blueprint endpoints."""
        # Get all pets
        response = client.get('/pets')
        assert response.status_code == 200
        assert len(response.json) == 3
        
        # Get single pet
        response = client.get('/pets/0')
        assert response.status_code == 200
        assert response.json['name'] == 'Kitty'
        
        # Create pet
        new_pet = {'name': 'Buddy', 'category': 'dog'}
        response = client.post('/pets', json=new_pet)
        assert response.status_code == 201
        assert response.json['name'] == 'Buddy'
    
    def test_openapi_tags(self, app, client):
        """Test that blueprints create proper OpenAPI tags."""
        response = client.get('/openapi.json')
        assert response.status_code == 200
        openapi_spec = response.json
        
        # Check that tags are created
        tags = openapi_spec.get('tags', [])
        tag_names = [tag['name'] for tag in tags]
        assert 'Hello' in tag_names
        assert 'Pet' in tag_names


# Integration tests that verify the examples can be imported and run
class TestExampleImports:
    """Test that all examples can be imported without errors."""
    
    def test_import_basic_example(self):
        """Test importing basic example."""
        try:
            from examples.basic.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")
    
    def test_import_cbv_example(self):
        """Test importing CBV example."""
        try:
            from examples.cbv.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")
    
    def test_import_orm_example(self):
        """Test importing ORM example."""
        try:
            from examples.orm.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")
    
    def test_import_pagination_example(self):
        """Test importing pagination example."""
        try:
            from examples.pagination.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")
    
    def test_import_file_upload_example(self):
        """Test importing file upload example."""
        try:
            from examples.file_upload.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")
    
    def test_import_dataclass_example(self):
        """Test importing dataclass example."""
        try:
            from examples.dataclass.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")
    
    def test_import_token_auth_example(self):
        """Test importing token auth example."""
        try:
            from examples.auth.token_auth.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")
    
    def test_import_basic_auth_example(self):
        """Test importing basic auth example."""
        try:
            from examples.auth.basic_auth.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")
    
    def test_import_base_response_example(self):
        """Test importing base response example."""
        try:
            from examples.base_response.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")
    
    def test_import_blueprint_tags_example(self):
        """Test importing blueprint tags example."""
        try:
            from examples.blueprint_tags.app import app
            assert isinstance(app, APIFlask)
        except ImportError:
            pytest.skip("Example not in Python path")


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
