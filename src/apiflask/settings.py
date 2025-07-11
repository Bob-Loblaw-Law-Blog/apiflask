from __future__ import annotations

import typing as t

from .schemas import http_error_schema
from .schemas import HTTPErrorSchema
from .schemas import validation_error_schema
from .schemas import ValidationErrorSchema
from .types import OpenAPISchemaType
from .types import TagsType


# OpenAPI fields
OPENAPI_VERSION: str = '3.0.3'
SERVERS: list[dict[str, str]] | None = None
TAGS: TagsType | None = None
EXTERNAL_DOCS: dict[str, str] | None = None
INFO: dict[str, str | dict] | None = None
DESCRIPTION: str | None = None
TERMS_OF_SERVICE: str | None = None
CONTACT: dict[str, str] | None = None
LICENSE: dict[str, str] | None = None
SECURITY_SCHEMES: dict[str, t.Any] | None = None
# OpenAPI spec
SPEC_FORMAT: str = 'json'
YAML_SPEC_MIMETYPE: str = 'text/vnd.yaml'
JSON_SPEC_MIMETYPE: str = 'application/json'
LOCAL_SPEC_PATH: str | None = None
LOCAL_SPEC_JSON_INDENT: int = 2
SYNC_LOCAL_SPEC: bool | None = None
SPEC_PROCESSOR_PASS_OBJECT: bool = False
SPEC_DECORATORS: list[t.Callable] | None = None
DOCS_DECORATORS: list[t.Callable] | None = None
SWAGGER_UI_OAUTH_REDIRECT_DECORATORS: list[t.Callable] | None = None
# Automation behavior control
AUTO_TAGS: bool = True
AUTO_SERVERS: bool = True
AUTO_OPERATION_SUMMARY: bool = True
AUTO_OPERATION_DESCRIPTION: bool = True
AUTO_OPERATION_ID: bool = False
AUTO_200_RESPONSE: bool = True
AUTO_404_RESPONSE: bool = True
AUTO_VALIDATION_ERROR_RESPONSE: bool = True
AUTO_AUTH_ERROR_RESPONSE: bool = True
# Response customization
SUCCESS_DESCRIPTION: str = 'Successful response'
NOT_FOUND_DESCRIPTION: str = 'Not found'
VALIDATION_ERROR_DESCRIPTION: str = 'Validation error'
AUTH_ERROR_DESCRIPTION: str = 'Authentication error'
VALIDATION_ERROR_STATUS_CODE: int = 422
AUTH_ERROR_STATUS_CODE: int = 401
# For backwards compatibility, we use the dict-based schemas by default
# Users can override these with the new class-based schemas if desired:
# VALIDATION_ERROR_SCHEMA = ValidationErrorSchema
# HTTP_ERROR_SCHEMA = HTTPErrorSchema
VALIDATION_ERROR_SCHEMA: OpenAPISchemaType = validation_error_schema
HTTP_ERROR_SCHEMA: OpenAPISchemaType = http_error_schema
BASE_RESPONSE_SCHEMA: OpenAPISchemaType | None = None
BASE_RESPONSE_DATA_KEY: str = 'data'
# API docs
DOCS_FAVICON: str = 'https://apiflask.com/_assets/favicon.png'
REDOC_USE_GOOGLE_FONT: bool = True
REDOC_STANDALONE_JS: str = 'https://cdn.redoc.ly/redoc/latest/bundles/\
redoc.standalone.js'  # TODO: rename to REDOC_JS
REDOC_CONFIG: dict | None = None
SWAGGER_UI_CSS: str = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/swagger-ui.css'
SWAGGER_UI_BUNDLE_JS: str = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/\
swagger-ui-bundle.js'  # TODO: rename to SWAGGER_UI_JS
SWAGGER_UI_STANDALONE_PRESET_JS: str = 'https://cdn.jsdelivr.net/npm/swagger-ui-dist/\
swagger-ui-standalone-preset.js'  # TODO: rename to SWAGGER_UI_STANDALONE_JS
SWAGGER_UI_LAYOUT: str = 'BaseLayout'
SWAGGER_UI_CONFIG: dict | None = None
SWAGGER_UI_OAUTH_CONFIG: dict | None = None
ELEMENTS_JS: str = 'https://cdn.jsdelivr.net/npm/@stoplight/elements/web-components.min.js'
ELEMENTS_CSS: str = 'https://cdn.jsdelivr.net/npm/@stoplight/elements/styles.min.css'
ELEMENTS_LAYOUT: str = 'sidebar'
ELEMENTS_CONFIG: dict | None = None
RAPIDOC_JS: str = 'https://cdn.jsdelivr.net/npm/rapidoc/dist/rapidoc-min.js'
RAPIDOC_THEME: str = 'light'
RAPIDOC_CONFIG: dict | None = None
RAPIPDF_JS: str = 'https://cdn.jsdelivr.net/npm/rapipdf/dist/rapipdf-min.js'
RAPIPDF_CONFIG: dict | None = None

# Version changed: 1.2.0
# Change VALIDATION_ERROR_STATUS_CODE from 400 to 422.

# Version added: 1.3.0
# SPEC_PROCESSOR_PASS_OBJECT
