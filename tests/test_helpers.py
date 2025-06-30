import pytest
from unittest.mock import MagicMock, patch

from flask import Flask, request, url_for
from werkzeug.http import HTTP_STATUS_CODES

from apiflask.helpers import get_reason_phrase, pagination_builder


class MockPagination:
    def __init__(self, page=1, per_page=10, total=100, items=None):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.items = items or []
        
        # Calculate additional attributes
        self.pages = (total + per_page - 1) // per_page
        self.has_next = page < self.pages
        self.has_prev = page > 1
        self.next_num = page + 1 if self.has_next else page
        self.prev_num = page - 1 if self.has_prev else page


class TestGetReasonPhrase:
    def test_get_reason_phrase_valid_code(self):
        assert get_reason_phrase(200) == 'OK'
        assert get_reason_phrase(404) == 'Not Found'
        assert get_reason_phrase(500) == 'Internal Server Error'

    def test_get_reason_phrase_invalid_code(self):
        assert get_reason_phrase(999) == 'Unknown'

    def test_get_reason_phrase_custom_default(self):
        assert get_reason_phrase(999, default='Custom Default') == 'Custom Default'

    def test_get_reason_phrase_with_edge_cases(self):
        # Test edge cases
        assert get_reason_phrase(100) == 'Continue'
        assert get_reason_phrase(599) == 'Unknown'


class TestPaginationBuilder:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config['SERVER_NAME'] = 'example.com'
        return app
    
    def test_pagination_builder_basic(self, app):
        with app.test_request_context('/items?page=2&per_page=10'):
            request.endpoint = 'get_items'
            
            pagination = MockPagination(page=2, per_page=10, total=100)
            result = pagination_builder(pagination)
            
            assert result['total'] == 100
            assert result['pages'] == 10
            assert result['per_page'] == 10
            assert result['page'] == 2
            assert result['next'] == 'http://example.com/items?page=3&per_page=10'
            assert result['prev'] == 'http://example.com/items?page=1&per_page=10'
            assert result['first'] == 'http://example.com/items?page=1&per_page=10'
            assert result['last'] == 'http://example.com/items?page=10&per_page=10'
            assert result['current'] == 'http://example.com/items?page=2&per_page=10'

    def test_pagination_builder_first_page(self, app):
        with app.test_request_context('/items?page=1&per_page=10'):
            request.endpoint = 'get_items'
            
            pagination = MockPagination(page=1, per_page=10, total=100)
            result = pagination_builder(pagination)
            
            assert result['prev'] == ''  # No previous page
            assert result['next'] == 'http://example.com/items?page=2&per_page=10'

    def test_pagination_builder_last_page(self, app):
        with app.test_request_context('/items?page=10&per_page=10'):
            request.endpoint = 'get_items'
            
            pagination = MockPagination(page=10, per_page=10, total=100)
            result = pagination_builder(pagination)
            
            assert result['next'] == ''  # No next page
            assert result['prev'] == 'http://example.com/items?page=9&per_page=10'

    def test_pagination_builder_single_page(self, app):
        with app.test_request_context('/items?page=1&per_page=20'):
            request.endpoint = 'get_items'
            
            pagination = MockPagination(page=1, per_page=20, total=15)  # Total less than per_page
            result = pagination_builder(pagination)
            
            assert result['pages'] == 1
            assert result['next'] == ''
            assert result['prev'] == ''
            assert result['first'] == 'http://example.com/items?page=1&per_page=20'
            assert result['last'] == 'http://example.com/items?page=1&per_page=20'

    def test_pagination_builder_with_additional_query_params(self, app):
        with app.test_request_context('/items?page=2&per_page=10&category=books'):
            request.endpoint = 'get_items'
            
            pagination = MockPagination(page=2, per_page=10, total=100)
            result = pagination_builder(pagination, category='books')
            
            assert 'category=books' in result['next']
            assert 'category=books' in result['prev']
            assert 'category=books' in result['first']
            assert 'category=books' in result['last']
            assert 'category=books' in result['current']

    def test_pagination_builder_with_zero_results(self, app):
        with app.test_request_context('/items?page=1&per_page=10'):
            request.endpoint = 'get_items'
            
            pagination = MockPagination(page=1, per_page=10, total=0)
            result = pagination_builder(pagination)
            
            assert result['total'] == 0
            assert result['pages'] == 0
            assert result['next'] == ''
            assert result['prev'] == ''
            assert result['first'] == 'http://example.com/items?page=1&per_page=10'
            assert result['last'] == 'http://example.com/items?page=0&per_page=10'  # Edge case: last page is 0 when no results
            assert result['current'] == 'http://example.com/items?page=1&per_page=10'

    def test_pagination_builder_with_custom_endpoint(self, app):
        with app.test_request_context('/api/v1/items?page=2&per_page=10'):
            request.endpoint = 'api.get_items'  # Blueprint endpoint
            
            pagination = MockPagination(page=2, per_page=10, total=100)
            result = pagination_builder(pagination)
            
            assert result['next'].startswith('http://example.com/')
            assert 'api.get_items' not in result['next']  # url_for resolves the endpoint

    def test_pagination_builder_with_no_endpoint(self, app):
        with app.test_request_context('/items?page=1&per_page=10'):
            request.endpoint = None  # Simulating a request with no endpoint
            
            pagination = MockPagination(page=1, per_page=10, total=100)
            result = pagination_builder(pagination)
            
            assert result['next'] == ''
            assert result['prev'] == ''
            assert result['first'] == ''
            assert result['last'] == ''
            assert result['current'] == ''

    def test_pagination_builder_edge_cases(self, app):
        with app.test_request_context('/items?page=99999&per_page=10'):
            request.endpoint = 'get_items'
            
            # Testing with a page number that exceeds available pages
            pagination = MockPagination(page=99999, per_page=10, total=100)
            # This should still work since the pagination object sets its own has_next/has_prev properties
            result = pagination_builder(pagination)
            
            assert result['next'] == ''  # No next page
            assert result['prev'] != ''  # Should have a previous page
            
        with app.test_request_context('/items?page=0&per_page=10'):
            request.endpoint = 'get_items'
            
            # Testing with an invalid page number (0)
            pagination = MockPagination(page=0, per_page=10, total=100)
            result = pagination_builder(pagination)
            
            assert result['page'] == 0  # Function doesn't validate page numbers
            assert result['current'] == 'http://example.com/items?page=0&per_page=10'

    def test_pagination_builder_with_large_dataset(self, app):
        with app.test_request_context('/items?page=50&per_page=100'):
            request.endpoint = 'get_items'
            
            pagination = MockPagination(page=50, per_page=100, total=10000)
            result = pagination_builder(pagination)
            
            assert result['total'] == 10000
            assert result['pages'] == 100
            assert result['page'] == 50
            assert result['next'] == 'http://example.com/items?page=51&per_page=100'
            assert result['prev'] == 'http://example.com/items?page=49&per_page=100'


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])
