import sys
import os
import json
import pytest
from unittest.mock import patch

# Add the examples directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples', 'orm')))

from app import app, db, PetModel, init_database


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        # Establish application context
        with app.app_context():
            # Create all tables and initialize data
            db.create_all()
            init_database()
            yield client
            # Clean up after test
            db.session.remove()
            db.drop_all()


class TestOrmExample:
    def test_say_hello(self, client):
        response = client.get('/')
        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['message'] == 'Hello!'

    def test_get_pet_success(self, client):
        response = client.get('/pets/1')
        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['id'] == 1
        assert data['name'] == 'Coco'
        assert data['category'] == 'dog'

    def test_get_pet_not_found(self, client):
        response = client.get('/pets/99')
        assert response.status_code == 404

    def test_get_pets(self, client):
        response = client.get('/pets')
        data = json.loads(response.data)
        assert response.status_code == 200
        assert len(data) == 3
        assert data[0]['name'] == 'Kitty'
        assert data[1]['name'] == 'Coco'
        assert data[2]['name'] == 'Flash'

    def test_create_pet_success(self, client):
        response = client.post(
            '/pets',
            json={'name': 'Buddy', 'category': 'dog'}
        )
        data = json.loads(response.data)
        assert response.status_code == 201
        assert data['id'] == 4  # First three were created in init_database
        assert data['name'] == 'Buddy'
        assert data['category'] == 'dog'

        # Verify it was added to database
        response = client.get('/pets/4')
        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['name'] == 'Buddy'

    def test_create_pet_invalid_data(self, client):
        # Invalid category
        response = client.post(
            '/pets',
            json={'name': 'Buddy', 'category': 'bird'}
        )
        assert response.status_code == 422

        # Name too long
        response = client.post(
            '/pets',
            json={'name': 'ThisNameIsTooLong', 'category': 'dog'}
        )
        assert response.status_code == 422

    def test_update_pet_success(self, client):
        response = client.patch(
            '/pets/1',
            json={'name': 'Rex'}
        )
        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['id'] == 1
        assert data['name'] == 'Rex'
        assert data['category'] == 'dog'  # Unchanged

        # Verify it was updated
        response = client.get('/pets/1')
        data = json.loads(response.data)
        assert data['name'] == 'Rex'

    def test_update_pet_not_found(self, client):
        response = client.patch(
            '/pets/99',
            json={'name': 'Rex'}
        )
        assert response.status_code == 404

    def test_update_pet_invalid_data(self, client):
        response = client.patch(
            '/pets/1',
            json={'category': 'bird'}
        )
        assert response.status_code == 422

    def test_delete_pet_success(self, client):
        # First verify pet exists
        response = client.get('/pets/1')
        assert response.status_code == 200
        
        # Delete the pet
        response = client.delete('/pets/1')
        assert response.status_code == 204
        assert response.data == b''

        # Verify it was deleted
        response = client.get('/pets/1')
        assert response.status_code == 404

    def test_delete_pet_not_found(self, client):
        response = client.delete('/pets/99')
        assert response.status_code == 404

if __name__ == '__main__':
    pytest.main()
