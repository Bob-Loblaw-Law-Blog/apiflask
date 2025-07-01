import sys
import os
import json
import pytest
from unittest.mock import patch

# Add the examples directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples', 'base_response')))

from app import app, pets as initial_pets


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def reset_pets():
    # Save the initial state
    original_pets = initial_pets.copy()
    yield
    # Restore the initial state after test
    initial_pets.clear()
    initial_pets.extend(original_pets)


class TestBaseResponseExample:
    def test_say_hello(self, client):
        response = client.get('/')
        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['data']['message'] == 'Hello!'
        assert data['message'] == 'Success!'
        assert data['code'] == 200

    def test_get_pet_success(self, client):
        response = client.get('/pets/1')
        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['data']['id'] == 1
        assert data['data']['name'] == 'Coco'
        assert data['data']['category'] == 'dog'
        assert data['message'] == 'Success!'
        assert data['code'] == 200

    def test_get_pet_not_found(self, client):
        response = client.get('/pets/99')
        assert response.status_code == 404

    def test_get_deleted_pet(self, client, reset_pets):
        # First delete a pet
        client.delete('/pets/1')
        # Then try to get it
        response = client.get('/pets/1')
        assert response.status_code == 404

    def test_get_pets(self, client):
        response = client.get('/pets')
        data = json.loads(response.data)
        assert response.status_code == 200
        assert len(data['data']) == 3
        assert data['data'][0]['name'] == 'Kitty'
        assert data['data'][1]['name'] == 'Coco'
        assert data['data'][2]['name'] == 'Flash'
        assert data['message'] == 'Success!'
        assert data['code'] == 200

    def test_create_pet_success(self, client, reset_pets):
        response = client.post(
            '/pets',
            json={'name': 'Buddy', 'category': 'dog'}
        )
        data = json.loads(response.data)
        assert response.status_code == 201
        assert data['data']['id'] == 3
        assert data['data']['name'] == 'Buddy'
        assert data['data']['category'] == 'dog'
        assert data['message'] == 'Pet created.'
        assert data['code'] == 201

        # Verify it was added to pets
        response = client.get('/pets/3')
        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['data']['name'] == 'Buddy'

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

    def test_update_pet_success(self, client, reset_pets):
        response = client.patch(
            '/pets/1',
            json={'name': 'Rex'}
        )
        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['data']['id'] == 1
        assert data['data']['name'] == 'Rex'
        assert data['data']['category'] == 'dog'  # Unchanged
        assert data['message'] == 'Pet updated.'
        assert data['code'] == 200

        # Verify it was updated
        response = client.get('/pets/1')
        data = json.loads(response.data)
        assert data['data']['name'] == 'Rex'

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

    def test_delete_pet_success(self, client, reset_pets):
        response = client.delete('/pets/1')
        assert response.status_code == 204
        assert response.data == b''

        # Verify it was "deleted" (marked as deleted)
        response = client.get('/pets/1')
        assert response.status_code == 404

if __name__ == '__main__':
    pytest.main()
