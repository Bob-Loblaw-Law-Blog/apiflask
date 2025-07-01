import pytest
from apiflask.schemas import PaginationSchema


def test_pagination_schema_structure():
    schema = PaginationSchema()
    field_names = schema.fields.keys()
    
    # Check all expected fields exist
    assert all(name in field_names for name in [
        'page', 'per_page', 'pages', 'total', 
        'current', 'next', 'prev', 'first', 'last'
    ])
    
    # Check field types
    assert schema.fields['page'].__class__.__name__ == 'Integer'
    assert schema.fields['per_page'].__class__.__name__ == 'Integer'
    assert schema.fields['pages'].__class__.__name__ == 'Integer'
    assert schema.fields['total'].__class__.__name__ == 'Integer'
    assert schema.fields['current'].__class__.__name__ == 'URL'
    assert schema.fields['next'].__class__.__name__ == 'URL'
    assert schema.fields['prev'].__class__.__name__ == 'URL'
    assert schema.fields['first'].__class__.__name__ == 'URL'
    assert schema.fields['last'].__class__.__name__ == 'URL'


def test_pagination_schema_serialization():
    schema = PaginationSchema()
    data = {
        'page': 2,
        'per_page': 25,
        'pages': 10,
        'total': 248,
        'current': 'https://api.example.com/items?page=2&per_page=25',
        'next': 'https://api.example.com/items?page=3&per_page=25',
        'prev': 'https://api.example.com/items?page=1&per_page=25',
        'first': 'https://api.example.com/items?page=1&per_page=25',
        'last': 'https://api.example.com/items?page=10&per_page=25',
    }
    
    result = schema.dump(data)
    assert result == data


def test_pagination_schema_deserialization():
    schema = PaginationSchema()
    data = {
        'page': 2,
        'per_page': 25,
        'pages': 10,
        'total': 248,
        'current': 'https://api.example.com/items?page=2&per_page=25',
        'next': 'https://api.example.com/items?page=3&per_page=25',
        'prev': 'https://api.example.com/items?page=1&per_page=25',
        'first': 'https://api.example.com/items?page=1&per_page=25',
        'last': 'https://api.example.com/items?page=10&per_page=25',
    }
    
    result = schema.load(data)
    assert result == data


def test_pagination_schema_null_links():
    schema = PaginationSchema()
    data = {
        'page': 1,
        'per_page': 25,
        'pages': 1,
        'total': 20,
        'current': 'https://api.example.com/items?page=1&per_page=25',
        'next': None,  # No next page
        'prev': None,  # No previous page
        'first': 'https://api.example.com/items?page=1&per_page=25',
        'last': 'https://api.example.com/items?page=1&per_page=25',
    }
    
    result = schema.dump(data)
    assert result['next'] is None
    assert result['prev'] is None


def test_pagination_schema_in_api(app, client):
    @app.get('/items')
    @app.output(PaginationSchema)
    def get_paginated_items():
        return {
            'page': 2,
            'per_page': 25,
            'pages': 10,
            'total': 248,
            'current': 'https://api.example.com/items?page=2&per_page=25',
            'next': 'https://api.example.com/items?page=3&per_page=25',
            'prev': 'https://api.example.com/items?page=1&per_page=25',
            'first': 'https://api.example.com/items?page=1&per_page=25',
            'last': 'https://api.example.com/items?page=10&per_page=25',
        }
    
    # Verify OpenAPI spec contains PaginationSchema
    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    schema = rv.json['paths']['/items']['get']['responses']['200']['content']['application/json']['schema']
    assert '$ref' in schema
    assert schema['$ref'].endswith('/PaginationSchema')
    
    # Check the actual response
    rv = client.get('/items')
    assert rv.status_code == 200
    data = rv.json
    
    assert data['page'] == 2
    assert data['per_page'] == 25
    assert data['pages'] == 10
    assert data['total'] == 248
    assert data['current'] == 'https://api.example.com/items?page=2&per_page=25'
    assert data['next'] == 'https://api.example.com/items?page=3&per_page=25'
    assert data['prev'] == 'https://api.example.com/items?page=1&per_page=25'
    assert data['first'] == 'https://api.example.com/items?page=1&per_page=25'
    assert data['last'] == 'https://api.example.com/items?page=10&per_page=25'


def test_pagination_schema_partial_outputs(app, client):
    @app.get('/minimal-pagination')
    @app.output(PaginationSchema)
    def get_minimal_pagination():
        # Return only required fields
        return {
            'page': 1,
            'per_page': 10,
            'pages': 5,
            'total': 45,
            'current': 'https://api.example.com/items?page=1',
        }
    
    rv = client.get('/minimal-pagination')
    assert rv.status_code == 200
    data = rv.json
    
    assert data['page'] == 1
    assert data['per_page'] == 10
    assert data['pages'] == 5
    assert data['total'] == 45
    assert data['current'] == 'https://api.example.com/items?page=1'
    # Optional fields may be None or not present
