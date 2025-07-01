import sys
import os
import json
import pytest
from io import BytesIO
from unittest.mock import patch

# Add the examples directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples', 'file_upload')))

from app import app, upload_dir


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


@pytest.fixture
def cleanup_upload_dir():
    # Create upload directory if it doesn't exist
    os.makedirs(upload_dir, exist_ok=True)
    yield
    # Clean up uploaded files after test
    for file in os.listdir(upload_dir):
        file_path = os.path.join(upload_dir, file)
        if os.path.isfile(file_path):
            os.unlink(file_path)


class TestFileUploadExample:
    def test_upload_image_success(self, client, cleanup_upload_dir):
        data = {'image': (BytesIO(b'dummy image content'), 'test.png')}
        response = client.post(
            '/images',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == 'file test.png saved.'
        
        # Verify file was saved
        assert os.path.exists(os.path.join(upload_dir, 'test.png'))

    def test_upload_image_invalid_type(self, client):
        data = {'image': (BytesIO(b'dummy content'), 'test.txt')}
        response = client.post(
            '/images',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 422

    def test_upload_image_too_large(self, client):
        # Create a file larger than 5MB
        large_data = BytesIO(b'x' * (5 * 1024 * 1024 + 1))
        data = {'image': (large_data, 'large.png')}
        response = client.post(
            '/images',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 422

    def test_create_profile_success(self, client, cleanup_upload_dir):
        data = {
            'name': 'John Doe',
            'avatar': (BytesIO(b'dummy avatar content'), 'avatar.png')
        }
        response = client.post(
            '/profiles',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['message'] == "John Doe's profile created."
        
        # Verify file was saved
        assert os.path.exists(os.path.join(upload_dir, 'avatar.png'))

    def test_create_profile_invalid_avatar_type(self, client):
        data = {
            'name': 'John Doe',
            'avatar': (BytesIO(b'dummy content'), 'avatar.txt')
        }
        response = client.post(
            '/profiles',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 422

    def test_create_profile_avatar_too_large(self, client):
        # Create a file larger than 2MB
        large_data = BytesIO(b'x' * (2 * 1024 * 1024 + 1))
        data = {
            'name': 'John Doe',
            'avatar': (large_data, 'large.png')
        }
        response = client.post(
            '/profiles',
            data=data,
            content_type='multipart/form-data'
        )
        assert response.status_code == 422

if __name__ == '__main__':
    pytest.main()
