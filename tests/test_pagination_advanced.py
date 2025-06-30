import pytest
from flask import Flask, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import select

from apiflask.helpers import pagination_builder


class TestPaginationBuilderWithSQLAlchemy:
    @pytest.fixture
    def app(self):
        app = Flask(__name__)
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SERVER_NAME'] = 'example.com'
        app.config['TESTING'] = True
        return app

    @pytest.fixture
    def db(self, app):
        db = SQLAlchemy(app)
        return db

    @pytest.fixture
    def Item(self, db):
        class Item(db.Model):
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(50), nullable=False)
            category = db.Column(db.String(50))
        return Item

    @pytest.fixture
    def populated_db(self, app, db, Item):
        with app.app_context():
            db.create_all()
            # Create test data
            for i in range(1, 101):
                item = Item(name=f'Item {i}', category=f'Category {(i-1)//20 + 1}')
                db.session.add(item)
            db.session.commit()
        return db

    def test_pagination_builder_with_sqlalchemy(self, app, populated_db, Item):
        with app.test_request_context('/items?page=2&per_page=10'):
            request.endpoint = 'get_items'

            with app.app_context():
                query = select(Item)
                pagination = populated_db.paginate(query, page=2, per_page=10)
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

    def test_pagination_builder_with_filtering(self, app, populated_db, Item):
        with app.test_request_context('/items?page=1&per_page=10&category=Category%201'):
            request.endpoint = 'get_items'

            with app.app_context():
                query = select(Item).where(Item.category == 'Category 1')
                pagination = populated_db.paginate(query, page=1, per_page=10)
                result = pagination_builder(pagination, category='Category 1')

                # Should have 20 total items in Category 1
                assert result['total'] == 20
                assert result['pages'] == 2
                assert result['per_page'] == 10
                assert result['page'] == 1
                assert result['next'] == 'http://example.com/items?category=Category+1&page=2&per_page=10'
                assert result['prev'] == ''
                assert result['first'] == 'http://example.com/items?category=Category+1&page=1&per_page=10'
                assert result['last'] == 'http://example.com/items?category=Category+1&page=2&per_page=10'
                assert result['current'] == 'http://example.com/items?category=Category+1&page=1&per_page=10'

    def test_pagination_builder_with_empty_result(self, app, populated_db, Item):
        with app.test_request_context('/items?page=1&per_page=10&category=NonExistent'):
            request.endpoint = 'get_items'

            with app.app_context():
                query = select(Item).where(Item.category == 'NonExistent')
                pagination = populated_db.paginate(query, page=1, per_page=10)
                result = pagination_builder(pagination, category='NonExistent')

                assert result['total'] == 0
                assert result['pages'] == 0
                assert result['per_page'] == 10
                assert result['page'] == 1
                assert result['next'] == ''
                assert result['prev'] == ''
                assert result['first'] == 'http://example.com/items?category=NonExistent&page=1&per_page=10'
                assert result['last'] == 'http://example.com/items?category=NonExistent&page=0&per_page=10'
                assert result['current'] == 'http://example.com/items?category=NonExistent&page=1&per_page=10'

    def test_pagination_builder_with_complex_query_params(self, app, populated_db, Item):
        with app.test_request_context('/items?page=1&per_page=10&category=Category+1&sort=name&order=asc'):
            request.endpoint = 'get_items'

            with app.app_context():
                query = select(Item).where(Item.category == 'Category 1').order_by(Item.name)
                pagination = populated_db.paginate(query, page=1, per_page=10)
                result = pagination_builder(pagination, category='Category 1', sort='name', order='asc')

                assert 'category=Category+1' in result['next']
                assert 'sort=name' in result['next']
                assert 'order=asc' in result['next']
                assert 'category=Category+1' in result['first']
                assert 'sort=name' in result['first']
                assert 'order=asc' in result['first']

    def test_pagination_builder_with_different_page_sizes(self, app, populated_db, Item):
        # Test with small page size
        with app.test_request_context('/items?page=1&per_page=5'):
            request.endpoint = 'get_items'

            with app.app_context():
                query = select(Item)
                pagination = populated_db.paginate(query, page=1, per_page=5)
                result = pagination_builder(pagination)
                assert result['total'] == 100
                assert result['pages'] == 20
                assert result['per_page'] == 5

        # Test with large page size
        with app.test_request_context('/items?page=1&per_page=50'):
            request.endpoint = 'get_items'

            with app.app_context():
                query = select(Item)
                pagination = populated_db.paginate(query, page=1, per_page=50)
                result = pagination_builder(pagination)
                assert result['total'] == 100
                assert result['pages'] == 2
                assert result['per_page'] == 50


if __name__ == '__main__':
    pytest.main(['-xvs', __file__])
