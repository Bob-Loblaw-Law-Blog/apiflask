import os

import pytest

from apiflask import APIFlask, APIBlueprint
from flask import request as flask_request


@pytest.fixture
def app():
    app = APIFlask(__name__)
    return app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def cli_runner(app):
    return app.test_cli_runner()


@pytest.fixture
def test_apps(monkeypatch):
    monkeypatch.syspath_prepend(
        os.path.abspath(os.path.join(os.path.dirname(__file__), 'test_apps'))
    )

@pytest.fixture
def app():
    """Create and configure a test APIFlask application."""
    app = APIFlask(__name__)
    app.config.update({
        'TESTING': True,
        'DEBUG': False,
        'JSON_SORT_KEYS': False,
        'OPENAPI_VERSION': '3.0.3',
    })

    # Ensure app context is available
    with app.app_context():
        yield app


@pytest.fixture
def client(app):
    """Create a test client for the app."""
    return app.test_client()


@pytest.fixture
def runner(app):
    """Create a test CLI runner for the app."""
    return app.test_cli_runner()


@pytest.fixture
def blueprint():
    """Create a test APIBlueprint."""
    bp = APIBlueprint('test_bp', __name__)
    return bp


@pytest.fixture
def app_with_blueprint(app, blueprint):
    """Create an app with a registered blueprint."""
    app.register_blueprint(blueprint)
    return app


@pytest.fixture
def request_context(app):
    """Create a request context."""
    with app.test_request_context():
        yield flask_request


@pytest.fixture
def openapi_app():
    """Create an app with OpenAPI explicitly enabled."""
    app = APIFlask(__name__)
    app.config['TESTING'] = True
    app.enable_openapi = True
    return app


@pytest.fixture
def no_openapi_app():
    """Create an app with OpenAPI disabled."""
    app = APIFlask(__name__)
    app.config['TESTING'] = True
    app.enable_openapi = False
    return app


@pytest.fixture
def mock_view_class():
    """Create a mock view class for testing."""
    from flask.views import MethodView

    class MockView(MethodView):
        def get(self):
            return {'method': 'GET'}

        def post(self):
            return {'method': 'POST'}

    return MockView


@pytest.fixture
def mock_view_instance(mock_view_class):
    """Create an instance of the mock view class."""
    return mock_view_class.as_view('mock_view')


# Markers for test organization
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "route: mark test as a route test"
    )
    config.addinivalue_line(
        "markers", "methodview: mark test as MethodView-specific"
    )
    config.addinivalue_line(
        "markers", "view: mark test as View-specific"
    )
    config.addinivalue_line(
        "markers", "parametrized: mark test as parametrized"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "spec: mark test as OpenAPI spec test"
    )
    config.addinivalue_line(
        "markers", "blueprint: mark test as blueprint-specific"
    )


# Test helpers
class RequestContextManager:
    """Helper for managing request contexts in tests."""

    def __init__(self, app, path='/', method='GET', **kwargs):
        self.app = app
        self.path = path
        self.method = method
        self.kwargs = kwargs

    def __enter__(self):
        self.ctx = self.app.test_request_context(
            self.path,
            method=self.method,
            **self.kwargs
        )
        self.ctx.push()
        return flask_request

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.ctx.pop()


@pytest.fixture
def request_ctx_manager(app):
    """Provide a request context manager."""
    def _make_context(path='/', method='GET', **kwargs):
        return RequestContextManager(app, path, method, **kwargs)
    return _make_context
