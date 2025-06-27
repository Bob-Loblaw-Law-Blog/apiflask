"""APIFlask test package.

This package contains the test suite for APIFlask. It includes tests for all major
functionality including:

- Core APIFlask features (app.py, blueprint.py)
- Input/output decorators and validation
- OpenAPI documentation generation
- Authentication and security
- Configuration and settings
- CLI commands
- Schema handling
- Helper functions

The tests are organized into modules by functionality and use pytest as the
testing framework along with Flask's test client for integration testing.

To run the tests:
    ```bash
    pytest tests/
    ```

For coverage report:
    ```bash
    pytest --cov=apiflask tests/
    ```
"""
