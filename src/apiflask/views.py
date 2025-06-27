"""
This module provides a centralized import point for Flask's view classes.
It re-exports View and MethodView from flask.views to provide a consistent
API for class-based views in APIFlask applications.

These view classes work seamlessly with APIFlask's decorators for input validation,
output serialization, authentication, and OpenAPI documentation generation.
"""

from flask.views import MethodView as MethodView
from flask.views import View as View
