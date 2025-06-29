import os

import pytest

from apiflask import APIFlask


@pytest.fixture
def app():
    app = APIFlask(__name__)
    app.config['TESTING'] = True
    app.config['DEBUG'] = False
    # Set default json_errors to True for APIFlask
    app.json_errors = True

    # Register a basic route
    @app.route('/ping')
    def ping():
        return {'message': 'pong'}

    return app


@pytest.fixture
def client(app):
    return app.test_client()
