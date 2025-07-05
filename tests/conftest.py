import os

import pytest

from apiflask import APIFlask
from contextlib import contextmanager
import sys
from pathlib import Path


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

def pytest_addoption(parser):
    """Add custom command line options for implementation selection."""
    parser.addoption(
        "--impl",
        action="store",
        default="both",
        choices=["schema", "types", "both"],
        help="Which OpenAPISchemaType implementation to test"
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "schema_only: mark test to run only with schema implementation"
    )
    config.addinivalue_line(
        "markers", "types_only: mark test to run only with types implementation"
    )
    config.addinivalue_line(
        "markers", "dual_impl: mark test to run with both implementations"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection based on implementation choice."""
    impl = config.getoption("--impl")

    if impl == "both":
        # Run all tests
        return

    # Filter tests based on implementation
    use_schema = (impl == "schema")
    os.environ['APIFLASK_USE_SCHEMA_IMPL'] = 'true' if use_schema else 'false'

    skip_marker = pytest.mark.skip(reason=f"Not running with {impl} implementation")

    for item in items:
        if use_schema and "types_only" in item.keywords:
            item.add_marker(skip_marker)
        elif not use_schema and "schema_only" in item.keywords:
            item.add_marker(skip_marker)


@pytest.fixture(scope="session")
def implementation_type(request):
    """Fixture that provides the current implementation type."""
    impl = request.config.getoption("--impl")
    if impl == "both":
        # Default to schema for "both" option
        impl = "schema"
    return impl


@pytest.fixture
def set_implementation(implementation_type):
    """Fixture that sets the implementation for a test."""
    use_schema = (implementation_type == "schema")
    original = os.environ.get('APIFLASK_USE_SCHEMA_IMPL', 'true')

    os.environ['APIFLASK_USE_SCHEMA_IMPL'] = 'true' if use_schema else 'false'

    # Clear module cache to ensure fresh imports
    import sys
    modules_to_clear = [
        'apiflask.settings',
        'apiflask.scaffold',
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]

    yield implementation_type

    # Restore original
    os.environ['APIFLASK_USE_SCHEMA_IMPL'] = original


@pytest.fixture(params=["schema", "types"], ids=["schema_impl", "types_impl"])
def both_implementations(request):
    """Fixture that parametrizes tests to run with both implementations."""
    impl = request.param
    use_schema = (impl == "schema")

    original = os.environ.get('APIFLASK_USE_SCHEMA_IMPL', 'true')
    os.environ['APIFLASK_USE_SCHEMA_IMPL'] = 'true' if use_schema else 'false'

    # Clear module cache
    import sys
    modules_to_clear = [
        'apiflask.settings',
        'apiflask.scaffold',
    ]
    for module in modules_to_clear:
        if module in sys.modules:
            del sys.modules[module]

    yield impl

    # Restore
    os.environ['APIFLASK_USE_SCHEMA_IMPL'] = original


@pytest.fixture
def app_factory(set_implementation):
    """Factory fixture for creating APIFlask apps with current implementation."""
    def _create_app(**config):
        from apiflask import APIFlask
        app = APIFlask(__name__)
        app.config['TESTING'] = True
        for key, value in config.items():
            app.config[key] = value
        return app
    return _create_app


# Context manager for switching implementations in tests
@contextmanager
def switch_implementation(use_schema: bool):
    """
    Context manager to temporarily switch implementations.

    Usage:
        with switch_implementation(use_schema=True):
            # Test with schema implementation
            pass
    """
    original = os.environ.get('APIFLASK_USE_SCHEMA_IMPL', 'true')
    try:
        os.environ['APIFLASK_USE_SCHEMA_IMPL'] = 'true' if use_schema else 'false'

        # Clear module cache
        import sys
        modules_to_clear = [
            'apiflask.settings',
            'apiflask.scaffold',
        ]
        for module in modules_to_clear:
            if module in sys.modules:
                del sys.modules[module]

        yield
    finally:
        os.environ['APIFLASK_USE_SCHEMA_IMPL'] = original
