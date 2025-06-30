"""
Unit tests for APIFlask helper functions.

This module provides comprehensive test coverage for the helper functions in
apiflask.helpers, with a particular emphasis on the pagination_builder function.

Test coverage includes:
- get_reason_phrase function with various status codes
- pagination_builder function with comprehensive edge cases
- URL generation in different contexts
- Error handling and edge cases
"""

import pytest
from unittest.mock import Mock, patch
from flask import Flask, request

from apiflask import APIFlask
from apiflask.helpers import get_reason_phrase, pagination_builder


class TestGetReasonPhrase:
    """Test cases for the get_reason_phrase helper function."""

    def test_valid_status_codes(self):
        """Test with standard HTTP status codes."""
        assert get_reason_phrase(200) == 'OK'
        assert get_reason_phrase(201) == 'Created'
        assert get_reason_phrase(204) == 'No Content'
        assert get_reason_phrase(400) == 'Bad Request'
        assert get_reason_phrase(401) == 'Unauthorized'
        assert get_reason_phrase(403) == 'Forbidden'
        assert get_reason_phrase(404) == 'Not Found'
        assert get_reason_phrase(405) == 'Method Not Allowed'
        assert get_reason_phrase(500) == 'Internal Server Error'
        assert get_reason_phrase(502) == 'Bad Gateway'
        assert get_reason_phrase(503) == 'Service Unavailable'

    def test_invalid_status_code_default(self):
        """Test with invalid status codes using default."""
        assert get_reason_phrase(999) == 'Unknown'
        assert get_reason_phrase(0) == 'Unknown'
        assert get_reason_phrase(-1) == 'Unknown'
        assert get_reason_phrase(600) == 'Unknown'

    def test_custom_default(self):
        """Test with custom default value."""
        assert get_reason_phrase(999, default='Custom Error') == 'Custom Error'
        assert get_reason_phrase(0, default='Invalid Code') == 'Invalid Code'

        # Test informational codes (1xx)
        assert get_reason_phrase(100) == 'Continue'
        assert get_reason_phrase(101) == 'Switching Protocols'

        # Test redirection codes (3xx)
        assert get_reason_phrase(301) == 'Moved Permanently'
        assert get_reason_phrase(302) == 'Found'
        assert get_reason_phrase(304) == 'Not Modified'


class MockPagination:
    """Mock pagination object that mimics Flask-SQLAlchemy's Pagination class."""

    def __init__(self, page=1, per_page=20, total=100, pages=5,
                 has_next=True, has_prev=True, next_num=2, prev_num=0):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = pages
        self.has_next = has_next
        self.has_prev = has_prev
        self.next_num = next_num
        self.prev_num = prev_num


class TestPaginationBuilder:
    """Test cases for the pagination_builder helper function."""

    @pytest.fixture
    def app(self):
        """Create a test Flask application."""
        app = APIFlask(__name__)

        @app.route('/items')
        def get_items():
            return 'items'

        @app.route('/products')
        def get_products():
            return 'products'

        return app

    def test_basic_pagination(self, app):
        """Test basic pagination with default values."""
        with app.test_request_context('/items?page=2&per_page=20'):
            pagination = MockPagination(
                page=2,
                per_page=20,
                total=100,
                pages=5,
                has_next=True,
                has_prev=True,
                next_num=3,
                prev_num=1
            )

            result = pagination_builder(pagination)

            assert result['total'] == 100
            assert result['pages'] == 5
            assert result['per_page'] == 20
            assert result['page'] == 2
            assert 'page=3' in result['next']
            assert 'page=1' in result['prev']
            assert 'page=1' in result['first']
            assert 'page=5' in result['last']
            assert 'page=2' in result['current']
            assert 'per_page=20' in result['next']
            assert 'per_page=20' in result['prev']

    def test_first_page_pagination(self, app):
        """Test pagination on the first page."""
        with app.test_request_context('/items?page=1&per_page=20'):
            pagination = MockPagination(
                page=1,
                per_page=20,
                total=100,
                pages=5,
                has_next=True,
                has_prev=False,
                next_num=2,
                prev_num=0
            )

            result = pagination_builder(pagination)

            assert result['page'] == 1
            assert result['prev'] == ''  # No previous page
            assert 'page=2' in result['next']
            assert 'page=1' in result['first']
            assert 'page=1' in result['current']

    def test_last_page_pagination(self, app):
        """Test pagination on the last page."""
        with app.test_request_context('/items?page=5&per_page=20'):
            pagination = MockPagination(
                page=5,
                per_page=20,
                total=100,
                pages=5,
                has_next=False,
                has_prev=True,
                next_num=6,
                prev_num=4
            )

            result = pagination_builder(pagination)

            assert result['page'] == 5
            assert result['next'] == ''  # No next page
            assert 'page=4' in result['prev']
            assert 'page=5' in result['last']
            assert 'page=5' in result['current']

    def test_single_page_pagination(self, app):
        """Test pagination with only one page."""
        with app.test_request_context('/items?page=1&per_page=100'):
            pagination = MockPagination(
                page=1,
                per_page=100,
                total=50,
                pages=1,
                has_next=False,
                has_prev=False,
                next_num=2,
                prev_num=0
            )

            result = pagination_builder(pagination)

            assert result['total'] == 50
            assert result['pages'] == 1
            assert result['page'] == 1
            assert result['next'] == ''
            assert result['prev'] == ''
            assert 'page=1' in result['first']
            assert 'page=1' in result['last']
            assert result['first'] == result['last'] == result['current']

    def test_empty_pagination(self, app):
        """Test pagination with no items."""
        with app.test_request_context('/items?page=1&per_page=20'):
            pagination = MockPagination(
                page=1,
                per_page=20,
                total=0,
                pages=0,
                has_next=False,
                has_prev=False,
                next_num=2,
                prev_num=0
            )

            result = pagination_builder(pagination)

            assert result['total'] == 0
            assert result['pages'] == 0
            assert result['page'] == 1
            assert result['next'] == ''
            assert result['prev'] == ''

    def test_pagination_with_additional_kwargs(self, app):
        """Test pagination with additional URL parameters."""
        with app.test_request_context('/items?page=2&per_page=20&category=electronics&sort=price'):
            pagination = MockPagination(
                page=2,
                per_page=20,
                total=100,
                pages=5,
                has_next=True,
                has_prev=True,
                next_num=3,
                prev_num=1
            )

            result = pagination_builder(
                pagination,
                category='electronics',
                sort='price',
                filter='active'
            )

            # Check that additional parameters are included in URLs
            assert 'category=electronics' in result['next']
            assert 'sort=price' in result['next']
            assert 'filter=active' in result['next']
            assert 'category=electronics' in result['prev']
            assert 'sort=price' in result['prev']
            assert 'filter=active' in result['prev']

    def test_pagination_different_per_page_values(self, app):
        """Test pagination with various per_page values."""
        test_cases = [
            (10, 1, 100, 10),  # per_page, page, total, expected_pages
            (25, 2, 100, 4),
            (50, 1, 100, 2),
            (100, 1, 100, 1),
            (15, 3, 47, 4),  # Edge case: not evenly divisible
        ]

        for per_page, page, total, expected_pages in test_cases:
            with app.test_request_context(f'/items?page={page}&per_page={per_page}'):
                pagination = MockPagination(
                    page=page,
                    per_page=per_page,
                    total=total,
                    pages=expected_pages,
                    has_next=page < expected_pages,
                    has_prev=page > 1,
                    next_num=page + 1,
                    prev_num=page - 1
                )

                result = pagination_builder(pagination)

                assert result['per_page'] == per_page
                assert result['pages'] == expected_pages
                assert f'per_page={per_page}' in result['first']

    def test_pagination_with_external_urls(self, app):
        """Test that pagination URLs are external (absolute)."""
        with app.test_request_context('/items?page=2&per_page=20'):
            pagination = MockPagination(
                page=2,
                per_page=20,
                total=100,
                pages=5,
                has_next=True,
                has_prev=True,
                next_num=3,
                prev_num=1
            )

            result = pagination_builder(pagination)

            # Check that URLs are absolute (contain http)
            assert result['next'].startswith('http')
            assert result['prev'].startswith('http')
            assert result['first'].startswith('http')
            assert result['last'].startswith('http')
            assert result['current'].startswith('http')

    def test_pagination_boundary_conditions(self, app):
        """Test pagination with boundary conditions."""
        # Test with page number at boundaries
        with app.test_request_context('/items?page=1&per_page=1'):
            # Extreme case: 1 item per page
            pagination = MockPagination(
                page=1,
                per_page=1,
                total=1000,
                pages=1000,
                has_next=True,
                has_prev=False,
                next_num=2,
                prev_num=0
            )

            result = pagination_builder(pagination)

            assert result['pages'] == 1000
            assert result['per_page'] == 1
            assert 'page=1000' in result['last']

    def test_pagination_url_encoding(self, app):
        """Test pagination with special characters in kwargs."""
        with app.test_request_context('/items?page=1&per_page=20'):
            pagination = MockPagination(
                page=1,
                per_page=20,
                total=100,
                pages=5,
                has_next=True,
                has_prev=False,
                next_num=2,
                prev_num=0
            )

            result = pagination_builder(
                pagination,
                search='hello world',
                tag='c++',
                filter='price > 100'
            )

            # Check URL encoding
            assert 'hello+world' in result['next'] or 'hello%20world' in result['next']
            assert 'c%2B%2B' in result['next']
            assert 'price' in result['next']

    def test_pagination_with_invalid_values(self, app):
        """Test pagination with invalid/edge case values."""
        with app.test_request_context('/items'):
            # Test with negative values
            pagination = MockPagination(
                page=-1,  # Invalid page
                per_page=20,
                total=100,
                pages=5,
                has_next=True,
                has_prev=False,
                next_num=0,
                prev_num=-2
            )

            result = pagination_builder(pagination)

            # Should still generate URLs even with invalid values
            assert result['page'] == -1
            assert 'page=-1' in result['current']

    def test_pagination_data_structure(self, app):
        """Test the complete structure of returned pagination data."""
        with app.test_request_context('/items?page=3&per_page=25'):
            pagination = MockPagination(
                page=3,
                per_page=25,
                total=150,
                pages=6,
                has_next=True,
                has_prev=True,
                next_num=4,
                prev_num=2
            )

            result = pagination_builder(pagination)

            # Verify all expected keys are present
            expected_keys = {
                'total', 'pages', 'per_page', 'page',
                'next', 'prev', 'first', 'last', 'current'
            }
            assert set(result.keys()) == expected_keys

            # Verify data types
            assert isinstance(result['total'], int)
            assert isinstance(result['pages'], int)
            assert isinstance(result['per_page'], int)
            assert isinstance(result['page'], int)
            assert isinstance(result['next'], str)
            assert isinstance(result['prev'], str)
            assert isinstance(result['first'], str)
            assert isinstance(result['last'], str)
            assert isinstance(result['current'], str)

    def test_pagination_consistency(self, app):
        """Test consistency of pagination URLs."""
        with app.test_request_context('/items?page=2&per_page=30'):
            pagination = MockPagination(
                page=2,
                per_page=30,
                total=300,
                pages=10,
                has_next=True,
                has_prev=True,
                next_num=3,
                prev_num=1
            )

            result = pagination_builder(pagination, sort='date', order='desc')

            # All URLs should have consistent parameters
            for url_key in ['next', 'prev', 'first', 'last', 'current']:
                if result[url_key]:  # Skip empty URLs
                    assert 'per_page=30' in result[url_key]
                    assert 'sort=date' in result[url_key]
                    assert 'order=desc' in result[url_key]
                    assert '/items' in result[url_key]


class TestPaginationIntegration:
    """Integration tests for pagination_builder with real Flask-SQLAlchemy-like scenarios."""

    @pytest.fixture
    def app(self):
        """Create a test Flask application with more complex routes."""
        app = APIFlask(__name__)

        @app.route('/api/v1/users')
        def get_users():
            return 'users'

        @app.route('/api/v1/posts/<int:user_id>')
        def get_user_posts(user_id):
            return f'posts for user {user_id}'

        return app

    def test_pagination_with_route_parameters(self, app):
        """Test pagination with routes that have parameters."""
        with app.test_request_context('/api/v1/posts/123?page=2&per_page=15'):
            pagination = MockPagination(
                page=2,
                per_page=15,
                total=45,
                pages=3,
                has_next=True,
                has_prev=True,
                next_num=3,
                prev_num=1
            )

            # This should fail as url_for would need the user_id parameter
            # This tests the robustness of pagination_builder
            with pytest.raises(Exception):  # Would raise werkzeug.routing.BuildError
                pagination_builder(pagination)

    def test_pagination_performance_large_dataset(self, app):
        """Test pagination performance with large dataset parameters."""
        with app.test_request_context('/api/v1/users?page=5000&per_page=100'):
            pagination = MockPagination(
                page=5000,
                per_page=100,
                total=1000000,  # 1 million records
                pages=10000,
                has_next=True,
                has_prev=True,
                next_num=5001,
                prev_num=4999
            )

            result = pagination_builder(pagination)

            assert result['page'] == 5000
            assert result['total'] == 1000000
            assert result['pages'] == 10000
            assert 'page=5001' in result['next']
            assert 'page=4999' in result['prev']
            assert 'page=10000' in result['last']
