import pytest
from flask import Flask, request
from marshmallow import Schema, fields

from apiflask.schemas import PaginationSchema
from apiflask.helpers import pagination_builder


class MockPagination:
    def __init__(self, page=1, per_page=10, total=100):
        self.page = page
        self.per_page = per_page
        self.total = total
        self.pages = (total + per_page - 1) // per_page
        self.has_next = page < self.pages
        self.has_prev = page > 1
        self.next_num = page + 1 if self.has_next else page
        self.prev_num = page - 1 if self.has_prev else page


class ItemSchema(Schema):
    id = fields.Integer()
    name = fields.String()


class ItemsResponseSchema(Schema):
    items = fields.List(fields.Nested(ItemSchema))
    pagination = fields.Nested(PaginationSchema)


class TestPaginationSchemaIntegration:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config['SERVER_NAME'] = 'example.com'
        return app
    
    def test_pagination_builder_with_pagination_schema(self, app):
        with app.test_request_context('/items?page=2&per_page=10'):
            request.endpoint = 'get_items'
            
            pagination = MockPagination(page=2, per_page=10, total=100)
            pagination_data = pagination_builder(pagination)
            
            # Validate the output against PaginationSchema
            schema = PaginationSchema()
            result = schema.load(pagination_data)
            
            # Ensure all fields are properly deserialized
            assert result['total'] == 100
            assert result['pages'] == 10
            assert result['per_page'] == 10
            assert result['page'] == 2
            assert result['next'] == 'http://example.com/items?page=3&per_page=10'
            assert result['prev'] == 'http://example.com/items?page=1&per_page=10'
            assert result['first'] == 'http://example.com/items?page=1&per_page=10'
            assert result['last'] == 'http://example.com/items?page=10&per_page=10'
            assert result['current'] == 'http://example.com/items?page=2&per_page=10'
    
    def test_pagination_builder_in_full_response(self, app):
        with app.test_request_context('/items?page=2&per_page=10'):
            request.endpoint = 'get_items'
            
            # Create mock data
            pagination = MockPagination(page=2, per_page=10, total=100)
            items = [{'id': i, 'name': f'Item {i}'} for i in range(11, 21)]
            
            # Create response data structure
            response_data = {
                'items': items,
                'pagination': pagination_builder(pagination)
            }
            
            # Validate with response schema
            schema = ItemsResponseSchema()
            result = schema.load(response_data)
            
            assert len(result['items']) == 10
            assert result['pagination']['total'] == 100
            assert result['pagination']['page'] == 2
            assert result['pagination']['next'] == 'http://example.com/items?page=3&per_page=10'
            
            # Dump back to JSON
            dumped_result = schema.dump(result)
            assert dumped_result['pagination']['total'] == 100
            assert dumped_result['pagination']['page'] == 2
            assert dumped_result['pagination']['next'] == 'http://example.com/items?page=3&per_page=10'
    
    def test_pagination_schema_validation(self, app):
        with app.test_request_context('/items?page=2&per_page=10'):
            request.endpoint = 'get_items'
            
            # Test with missing fields
            invalid_data = {
                'total': 100,
                'page': 2,
                # Missing required fields
            }
            
            schema = PaginationSchema()
            errors = schema.validate(invalid_data)
            assert 'pages' in errors
            assert 'per_page' in errors
            assert 'next' in errors
            assert 'prev' in errors
            assert 'first' in errors
            assert 'last' in errors
            
            # Test with valid data from pagination_builder
            pagination = MockPagination(page=2, per_page=10, total=100)
            valid_data = pagination_builder(pagination)
            
            errors = schema.validate(valid_data)
            assert not errors  # No validation errors
    
    def test_pagination_builder_edge_cases_with_schema(self, app):
        with app.test_request_context('/items?page=1&per_page=10'):
            request.endpoint = 'get_items'
            
            # Test with empty result set
            pagination = MockPagination(page=1, per_page=10, total=0)
            data = pagination_builder(pagination)
            
            schema = PaginationSchema()
            result = schema.load(data)
            
            assert result['total'] == 0
            assert result['pages'] == 0
            assert result['next'] == ''
            assert result['prev'] == ''
            
            # Schema should accept empty strings for URLs
            assert not schema.validate(data)


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])
