import pytest
from unittest.mock import MagicMock, patch

from flask import Flask, request

from apiflask.helpers import get_reason_phrase, pagination_builder


class CustomPagination:
    """A custom pagination class that doesn't match Flask-SQLAlchemy's interface"""
    def __init__(self, page=1, per_page=10, total=100):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page
        self.next_num = page + 1 if page < self.pages else page
        self.has_next = page < self.pages
        self.prev_num = page - 1 if page > 1 else page
        self.has_prev = page > 1


class IncompleteCustomPagination:
    """A custom pagination class missing some required attributes"""
    def __init__(self):
        self.page = 1
        self.per_page = 10
        # Missing attributes: pages, total, next_num, has_next, prev_num, has_prev


class TestGetReasonPhraseEdgeCases:
    def test_get_reason_phrase_with_negative_code(self):
        assert get_reason_phrase(-1) == 'Unknown'
    
    def test_get_reason_phrase_with_zero_code(self):
        assert get_reason_phrase(0) == 'Unknown'
    
    def test_get_reason_phrase_with_non_integer(self):
        with pytest.raises(TypeError):
            get_reason_phrase('200')
        
        with pytest.raises(TypeError):
            get_reason_phrase(200.0)


class TestPaginationBuilderEdgeCases:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config['SERVER_NAME'] = 'example.com'
        app.config['TESTING'] = True
        return app
    
    def test_pagination_builder_with_custom_pagination_class(self, app):
        with app.test_request_context('/items?page=2&per_page=10'):
            request.endpoint = 'get_items'
            
            pagination = CustomPagination(page=2, per_page=10, total=100)
            result = pagination_builder(pagination)
            
            assert result['total'] == 100
            assert result['pages'] == 10
            assert result['per_page'] == 10
            assert result['page'] == 2
            assert result['next'] == 'http://example.com/items?page=3&per_page=10'
            assert result['prev'] == 'http://example.com/items?page=1&per_page=10'

    def test_pagination_builder_with_incomplete_pagination_class(self, app):
        with app.test_request_context('/items?page=1&per_page=10'):
            request.endpoint = 'get_items'
            
            pagination = IncompleteCustomPagination()
            
            # Should raise AttributeError since some required attributes are missing
            with pytest.raises(AttributeError):
                pagination_builder(pagination)

    def test_pagination_builder_with_invalid_pagination_object(self, app):
        with app.test_request_context('/items?page=1&per_page=10'):
            request.endpoint = 'get_items'
            
            # Test with non-pagination object
            with pytest.raises(AttributeError):
                pagination_builder({})
            
            with pytest.raises(AttributeError):
                pagination_builder("not_a_pagination_object")
            
            with pytest.raises(AttributeError):
                pagination_builder(None)

    def test_pagination_builder_with_none_endpoint(self, app):
        with app.test_request_context('/items?page=1&per_page=10'):
            request.endpoint = None
            
            pagination = CustomPagination(page=1, per_page=10, total=100)
            result = pagination_builder(pagination)
            
            # All URLs should be empty strings when endpoint is None
            assert result['next'] == ''
            assert result['prev'] == ''
            assert result['first'] == ''
            assert result['last'] == ''
            assert result['current'] == ''

    @patch('apiflask.helpers.url_for')
    def test_pagination_builder_with_url_for_errors(self, mock_url_for, app):
        with app.test_request_context('/items?page=1&per_page=10'):
            request.endpoint = 'get_items'
            
            # Simulate url_for raising an exception
            mock_url_for.side_effect = Exception("URL generation error")
            
            pagination = CustomPagination(page=1, per_page=10, total=100)
            
            # Should propagate the exception
            with pytest.raises(Exception, match="URL generation error"):
                pagination_builder(pagination)

    def test_pagination_builder_with_extreme_values(self, app):
        with app.test_request_context('/items?page=1&per_page=10'):
            request.endpoint = 'get_items'
            
            # Test with extreme page values
            pagination = CustomPagination(page=2**31-1, per_page=10, total=100)  # Max 32-bit int
            result = pagination_builder(pagination)
            assert result['page'] == 2**31-1
            assert result['next'] == ''  # No next page as we're beyond total
            
            # Test with extreme per_page values
            pagination = CustomPagination(page=1, per_page=2**31-1, total=100)
            result = pagination_builder(pagination)
            assert result['per_page'] == 2**31-1
            assert result['pages'] == 1  # Just one page needed with this huge per_page
            
            # Test with extreme total values
            pagination = CustomPagination(page=1, per_page=10, total=2**63-1)  # Very large total
            result = pagination_builder(pagination)
            assert result['total'] == 2**63-1
            assert result['pages'] > 10**18  # Very large number of pages

    def test_pagination_builder_with_unicode_params(self, app):
        with app.test_request_context('/items?page=1&per_page=10&category=électronique'):
            request.endpoint = 'get_items'
            
            pagination = CustomPagination(page=1, per_page=10, total=100)
            result = pagination_builder(pagination, category='électronique')
            
            assert 'category=%C3%A9lectronique' in result['next']
            assert 'category=%C3%A9lectronique' in result['first']
            assert 'category=%C3%A9lectronique' in result['last']

    def test_pagination_builder_with_special_chars_in_endpoint(self, app):
        with app.test_request_context('/api/v1/items?page=1&per_page=10'):
            request.endpoint = 'api.v1.get-items'  # Endpoint with dots and dashes
            
            pagination = CustomPagination(page=1, per_page=10, total=100)
            result = pagination_builder(pagination)
            
            # url_for should correctly handle the endpoint name
            assert 'http://example.com/' in result['next']


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])
