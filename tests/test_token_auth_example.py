import sys
import os
import json
import pytest
from unittest.mock import patch

# Add the examples directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'examples', 'auth', 'token_auth')))

from app import app, User, get_user_by_id, verify_token


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


class TestTokenAuthExample:
    def test_get_token_success(self, client):
        response = client.post('/token/1')
        data = json.loads(response.data)
        assert response.status_code == 200
        assert data['token'].startswith('Bearer ')
        token = data['token'].split(' ')[1]
        assert verify_token(token) is not None
        
    def test_get_token_user_not_found(self, client):
        response = client.post('/token/99')
        assert response.status_code == 404
    
    def test_get_secret_with_valid_token(self, client):
        # First get a token
        response = client.post('/token/1')
        token = json.loads(response.data)['token']
        
        # Use the token to access protected endpoint
        response = client.get(
            '/name/1',
            headers={'Authorization': token}
        )
        assert response.status_code == 200
        assert response.data.decode() == 'lorem'
    
    def test_get_secret_with_invalid_token(self, client):
        response = client.get(
            '/name/1',
            headers={'Authorization': 'Bearer invalid-token'}
        )
        assert response.status_code == 401
    
    def test_get_secret_without_token(self, client):
        response = client.get('/name/1')
        assert response.status_code == 401

    def test_verify_token_success(self):
        user = get_user_by_id(1)
        token = user.get_token()
        verified_user = verify_token(token)
        assert verified_user is not None
        assert verified_user.id == 1
        assert verified_user.secret == 'lorem'
    
    def test_verify_token_invalid(self):
        assert verify_token('invalid-token') is None
    
    def test_get_user_by_id_success(self):
        user = get_user_by_id(1)
        assert user is not None
        assert user.id == 1
        assert user.secret == 'lorem'
    
    def test_get_user_by_id_not_found(self):
        with pytest.raises(IndexError):
            get_user_by_id(99)

if __name__ == '__main__':
    pytest.main()
