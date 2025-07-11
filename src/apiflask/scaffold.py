from __future__ import annotations

import os
import typing as t
from collections.abc import Mapping as ABCMapping
from functools import wraps

from flask import current_app
from flask import jsonify
from flask import request as flask_request
from flask import Response
from marshmallow import ValidationError as MarshmallowValidationError
from webargs.flaskparser import FlaskParser as BaseFlaskParser
from webargs.multidictproxy import MultiDictProxy

from .exceptions import _ValidationError
from .helpers import _sentinel
from .schemas import EmptySchema
from .schemas import FileSchema
from .schemas import Schema
from .types import DecoratedType
from .types import DictSchemaType
from .types import HTTPAuthType

# Dynamic import for OpenAPISchemaType
if os.environ.get('APIFLASK_USE_SCHEMA_IMPL', 'true').lower() == 'true':
    from .schemas import OpenAPISchemaType
else:
    from .types import OpenAPISchemaType

from .types import RequestType
from .types import ResponseReturnValueType
from .types import ResponsesType
from .types import SchemaType
from .views import MethodView

BODY_LOCATIONS = ['json', 'files', 'form', 'form_and_files', 'json_or_form']


class FlaskParser(BaseFlaskParser):
    """Overwrite the default `webargs.FlaskParser.handle_error`.

    Update the default status code and the error description from related
    configuration variables.
    """

    USE_ARGS_POSITIONAL = False

    def handle_error(  # type: ignore
        self,
        error: MarshmallowValidationError,
        req: RequestType,
        schema: Schema,
        *,
        error_status_code: int,
        error_headers: t.Mapping[str, str],
    ) -> None:
        # Now using the refactored _ValidationError that encapsulates the logic
        raise _ValidationError(error.messages, error_status_code, error_headers)

    def load_location_data(self, schema: Schema, location: str) -> t.Any:
        """
        Expose the internal `_load_location_data` method to support loading data without validation
        """
        return self._load_location_data(schema=schema, req=flask_request, location=location)


parser: FlaskParser = FlaskParser()


def _get_files_and_form(request, schema):
    form_and_files_data = request.files.copy()
    form_and_files_data.update(request.form)
    return MultiDictProxy(form_and_files_data, schema)


@parser.location_loader('form_and_files')
def load_form_and_files(request, schema):
    return _get_files_and_form(request, schema)


@parser.location_loader('files')
def load_files(request, schema):
    return _get_files_and_form(request, schema)


def _annotate(f: t.Any, **kwargs: t.Any) -> None:
    if not hasattr(f, '_spec'):
        f._spec = {}
    for key, value in kwargs.items():
        f._spec[key] = value


def _ensure_sync(f):
    if hasattr(f, '_sync_ensured'):
        return f

    @wraps(f)
    def wrapper(*args, **kwargs):
        return current_app.ensure_sync(f)(*args, **kwargs)

    wrapper._sync_ensured = True
    return wrapper


def _generate_schema_from_mapping(schema: DictSchemaType, schema_name: str | None) -> type[Schema]:
    if schema_name is None:
        schema_name = 'GeneratedSchema'
    return Schema.from_dict(schema, name=schema_name)()  # type: ignore


class APIScaffold:
    """A base class for [`APIFlask`][apiflask.app.APIFlask] and
    [`APIBlueprint`][apiflask.blueprint.APIBlueprint].

    This class contains the route shortcut decorators (i.e. `get`, `post`, etc.) and
    API-related decorators (i.e. `auth_required`, `input`, `output`, `doc`).

    *Version added: 1.0*
    """

    def _method_route(self, method: str, rule: str, options: t.Any):
        if 'methods' in options:
            raise RuntimeError('Use the "route" decorator to use the "methods" argument.')

        def decorator(f):
            if isinstance(f, type(MethodView)):
                raise RuntimeError(
                    'The route shortcuts cannot be used with "MethodView" classes, '
                    'use the "route" decorator instead.'
                )
            return self.route(rule, methods=[method], **options)(f)

        return decorator

    def get(self, rule: str, **options: t.Any):
        """Shortcut for `app.route()` or `app.route(methods=['GET'])`."""
        return self._method_route('GET', rule, options)

    def post(self, rule: str, **options: t.Any):
        """Shortcut for `app.route(methods=['POST'])`."""
        return self._method_route('POST', rule, options)

    def put(self, rule: str, **options: t.Any):
        """Shortcut for `app.route(methods=['PUT'])`."""
        return self._method_route('PUT', rule, options)

    def patch(self, rule: str, **options: t.Any):
        """Shortcut for `app.route(methods=['PATCH'])`."""
        return self._method_route('PATCH', rule, options)

    def delete(self, rule: str, **options: t.Any):
        """Shortcut for `app.route(methods=['DELETE'])`."""
        return self._method_route('DELETE', rule, options)

    def auth_required(
        self, auth: HTTPAuthType, roles: list | None = None, optional: str | None = None
    ) -> t.Callable[[DecoratedType], DecoratedType]:
        """Protect a view with provided authentication settings.

        > Be sure to put it under the routes decorators (i.e., `app.route`, `app.get`,
        `app.post`, etc.).

        Examples:

        ```python
        from apiflask import APIFlask, HTTPTokenAuth

        app = APIFlask(__name__)
        auth = HTTPTokenAuth()

        @app.get('/')
        @app.auth_required(auth)
        def hello():
            return 'Hello'!
        ```

        Arguments:
            auth: The `auth` object, an instance of
                [`HTTPBasicAuth`][apiflask.security.HTTPBasicAuth]
                or [`HTTPTokenAuth`][apiflask.security.HTTPTokenAuth].
            roles: The selected roles to allow to visit this view, accepts a list of role names.
                See [Flask-HTTPAuth's documentation][_role]{target:_blank} for more details.
                [_role]: https://flask-httpauth.readthedocs.io/en/latest/#user-roles
            optional: Set to `True` to allow the view to execute even the authentication
                information is not included with the request, in which case the attribute
                `auth.current_user` will be `None`.

        *Version changed: 2.0.0*

        - Remove the deprecated `role` parameter.

        *Version changed: 1.0.0*

        - The `role` parameter is deprecated.

        *Version changed: 0.12.0*

        - Move to `APIFlask` and `APIBlueprint` classes.

        *Version changed: 0.4.0*

        - Add parameter `roles`.
        """

        def decorator(f):
            f = _ensure_sync(f)
            _annotate(f, auth=auth, roles=roles or [])
            return auth.login_required(role=roles, optional=optional)(f)

        return decorator

    def input(
        self,
        schema: SchemaType,
        location: str = 'json',
        arg_name: str | None = None,
        schema_name: str | None = None,
        example: t.Any | None = None,
        examples: dict[str, t.Any] | None = None,
        validation: bool = True,
        **kwargs: t.Any,
    ) -> t.Callable[[DecoratedType], DecoratedType]:
        """Add input settings for view functions.

        If the validation passed, the data will be injected into the view
        function as a keyword argument in the form of `dict` and named `{location}_data`.
        Otherwise, an error response with the detail of the validation result will be
        returned.

        > Be sure to put it under the routes decorators (i.e., `app.route`, `app.get`,
        `app.post`, etc.).

        Examples:

        ```python
        from apiflask import APIFlask

        app = APIFlask(__name__)

        @app.get('/')
        @app.input(PetIn, location='json')
        def hello(json_data):
            print(json_data)
            return 'Hello'!
        ```

        Arguments:
            schema: The marshmallow schema of the input data.
            location: The location of the input data, one of `'json'` (default),
                `'files'`, `'form'`, `'cookies'`, `'headers'`, `'query'`
                (same as `'querystring'`).
            arg_name: The name of the argument passed to the view function,
                defaults to `{location}_data`.
            schema_name: The schema name for dict schema, only needed when you pass
                a schema dict (e.g., `{'name': String(required=True)}`) for `json`
                location.
            example: The example data in dict for request body, you should use either
                `example` or `examples`, not both.
            examples: Multiple examples for request body, you should pass a dict
                that contains multiple examples. Example:

                ```python
                {
                    'example foo': {  # example name
                        'summary': 'an example of foo',  # summary field is optional
                        'value': {'name': 'foo', 'id': 1}  # example value
                    },
                    'example bar': {
                        'summary': 'an example of bar',
                        'value': {'name': 'bar', 'id': 2}
                    },
                }
                ```
            validation: Flag to allow disabling of validation on input. Default to `True`.

        *Version changed: 2.2.2

        - Add parameter `validation` to allow disabling of validation on input.

        *Version changed: 2.0.0*

        - Always pass parsed data to view function as a keyword argument.
          The argument name will be in the form of `{location}_data`.

        *Version changed: 1.0*

        - Ensure only one input body location was used.
        - Add `form_and_files` and `json_or_form` (from webargs) location.
        - Rewrite `files` to act as `form_and_files`.
        - Use correct request content type for `form` and `files`.

        *Version changed: 0.12.0*

        - Move to APIFlask and APIBlueprint classes.

        *Version changed: 0.4.0*

        - Add parameter `examples`.
        """
        if isinstance(schema, ABCMapping):
            schema = _generate_schema_from_mapping(schema, schema_name)
        if isinstance(schema, type):  # pragma: no cover
            schema = schema()

        def decorator(f):
            f = _ensure_sync(f)

            is_body_location = location in BODY_LOCATIONS
            if is_body_location and hasattr(f, '_spec') and 'body' in f._spec:
                raise RuntimeError(
                    'When using the app.input() decorator, you can only declare one request '
                    'body location (one of "json", "form", "files", "form_and_files", '
                    'and "json_or_form").'
                )
            if location == 'json':
                _annotate(
                    f,
                    body=schema,
                    body_example=example,
                    body_examples=examples,
                    content_type='application/json',
                )
            elif location == 'form':
                _annotate(
                    f,
                    body=schema,
                    body_example=example,
                    body_examples=examples,
                    content_type='application/x-www-form-urlencoded',
                )
            elif location in ['files', 'form_and_files']:
                _annotate(
                    f,
                    body=schema,
                    body_example=example,
                    body_examples=examples,
                    content_type='multipart/form-data',
                )
            elif location == 'json_or_form':
                _annotate(
                    f,
                    body=schema,
                    body_example=example,
                    body_examples=examples,
                    content_type=['application/x-www-form-urlencoded', 'application/json'],
                )
            else:
                if not hasattr(f, '_spec') or f._spec.get('args') is None:
                    _annotate(f, args=[])
                if location == 'path':
                    _annotate(f, omit_default_path_parameters=True)
                # TODO: Support set example for request parameters
                f._spec['args'].append((schema, location))

            arg_name_val = arg_name or f'{location}_data'

            if not validation:

                @wraps(f)
                def wrapper(*args: t.Any, **kwargs: t.Any):
                    location_data = parser.load_location_data(schema=schema, location=location)
                    kwargs[arg_name_val] = location_data
                    return f(*args, **kwargs)

                return wrapper

            return parser.use_args(schema, location=location, arg_name=arg_name_val, **kwargs)(f)

        return decorator

    def output(
        self,
        schema: SchemaType,
        status_code: int = 200,
        description: str | None = None,
        schema_name: str | None = None,
        example: t.Any | None = None,
        examples: dict[str, t.Any] | None = None,
        links: dict[str, t.Any] | None = None,
        content_type: str | None = 'application/json',
        headers: SchemaType | None = None,
    ) -> t.Callable[[DecoratedType], DecoratedType]:
        """Add output settings for view functions.

        > Be sure to put it under the routes decorators (i.e., `app.route`, `app.get`,
        `app.post`, etc.).

        The decorator will format the return value of your view function with
        provided marshmallow schema. You can return a dict or an object (such
        as a model class instance of ORMs). APIFlask will handle the formatting
        and turn your return value into a JSON response.

        P.S. The output data will not be validated; it's a design choice of marshmallow.
        marshmallow 4.0 may be support the output validation.

        Examples:

        ```python
        from apiflask import APIFlask

        app = APIFlask(__name__)

        @app.get('/')
        @app.output(PetOut)
        def hello():
            return the_dict_or_object_match_petout_schema
        ```

        Arguments:
            schema: The schemas of the output data.
            status_code: The status code of the response, defaults to `200`.
            description: The description of the response.
            schema_name: The schema name for dict schema, only needed when you pass
                a schema dict (e.g., `{'name': String()}`).
            example: The example data in dict for response body, you should use either
                `example` or `examples`, not both.
            examples: Multiple examples for response body, you should pass a dict
                that contains multiple examples. Example:

                ```python
                {
                    'example foo': {  # example name
                        'summary': 'an example of foo',  # summary field is optional
                        'value': {'name': 'foo', 'id': 1}  # example value
                    },
                    'example bar': {
                        'summary': 'an example of bar',
                        'value': {'name': 'bar', 'id': 2}
                    },
                }
                ```
            links: The `links` of response. It accepts a dict which maps a link name to
                a link object. Example:

                ```python
                {
                    'getAddressByUserId': {
                        'operationId': 'getUserAddress',
                        'parameters': {
                            'userId': '$request.path.id'
                        }
                    }
                }
                ```

                See the [docs](https://apiflask.com/openapi/#response-links) for more details
                about setting response links.

            content_type: The content/media type of the response. It defaults to `application/json`.
            headers: The schemas of the headers.

        *Version changed: 2.1.0*

        - Add parameter `headers`.

        *Version changed: 2.0.0*

        - Don't change the status code to 204 for EmptySchema.

        *Version changed: 1.3.0*

        - Add parameter `content_type`.

        *Version changed: 0.12.0*

        - Move to APIFlask and APIBlueprint classes.

        *Version changed: 0.10.0*

        - Add `links` parameter.

        *Version changed: 0.9.0*

        - Add base response customization support.

        *Version changed: 0.6.0*

        - Support decorating async views.

        *Version changed: 0.5.2*

        - Return the `Response` object directly.

        *Version changed: 0.4.0*

        - Add parameter `examples`.
        """
        if schema == {}:
            schema = EmptySchema
        if isinstance(schema, ABCMapping):
            schema = _generate_schema_from_mapping(schema, schema_name)
        if isinstance(schema, type):  # pragma: no cover
            schema = schema()

        if headers is not None:
            if headers == {}:
                headers = EmptySchema
            if isinstance(headers, ABCMapping):
                headers = _generate_schema_from_mapping(headers, None)
            if isinstance(headers, type):
                headers = headers()

        def decorator(f):
            f = _ensure_sync(f)
            _annotate(
                f,
                response={
                    'schema': schema,
                    'status_code': status_code,
                    'description': description,
                    'example': example,
                    'examples': examples,
                    'links': links,
                    'content_type': content_type,
                    'headers': headers,
                },
            )

            def _jsonify(
                obj: t.Any,
                many: bool = _sentinel,  # type: ignore
                *args: t.Any,
                **kwargs: t.Any,
            ) -> Response:  # pragma: no cover
                """From Flask-Marshmallow, see the NOTICE file for license information."""
                if isinstance(schema, FileSchema):
                    return obj  # type: ignore
                if many is _sentinel:
                    many = schema.many  # type: ignore
                base_schema: OpenAPISchemaType = current_app.config['BASE_RESPONSE_SCHEMA']
                if base_schema is not None and status_code != 204:
                    data_key: str = current_app.config['BASE_RESPONSE_DATA_KEY']

                    if isinstance(obj, dict):
                        if data_key not in obj:
                            raise RuntimeError(
                                f'The data key {data_key!r} is not found in the returned dict.'
                            )
                        obj[data_key] = schema.dump(obj[data_key], many=many)  # type: ignore
                    else:
                        if not hasattr(obj, data_key):
                            raise RuntimeError(
                                f'The data key {data_key!r} is not found in the returned object.'
                            )
                        setattr(
                            obj,
                            data_key,
                            schema.dump(getattr(obj, data_key), many=many),  # type: ignore
                        )

                    data = base_schema().dump(obj)  # type: ignore
                else:
                    data = schema.dump(obj, many=many)  # type: ignore
                return jsonify(data, *args, **kwargs)

            @wraps(f)
            def _response(*args: t.Any, **kwargs: t.Any) -> ResponseReturnValueType:
                rv = f(*args, **kwargs)
                if isinstance(rv, Response):
                    return rv
                if not isinstance(rv, tuple):
                    return _jsonify(rv), status_code
                json = _jsonify(rv[0])
                if len(rv) == 2:
                    rv = (json, rv[1]) if isinstance(rv[1], int) else (json, status_code, rv[1])
                elif len(rv) >= 3:
                    rv = (json, rv[1], rv[2])
                else:
                    rv = (json, status_code)
                return rv  # type: ignore

            return _response

        return decorator

    def doc(
        self,
        summary: str | None = None,
        description: str | None = None,
        tags: list[str] | None = None,
        responses: ResponsesType | None = None,
        deprecated: bool | None = None,
        hide: bool | None = None,
        operation_id: str | None = None,
        security: str | list[str | dict[str, list]] | None = None,
        extensions: dict[str, t.Any] | None = None,
    ) -> t.Callable[[DecoratedType], DecoratedType]:
        """Set up the OpenAPI Spec for view functions.

        > Be sure to put it under the routes decorators (i.e., `app.route`, `app.get`,
        `app.post`, etc.).

        Examples:

        ```python
        from apiflask import APIFlask

        app = APIFlask(__name__)

        @app.get('/')
        @app.doc(summary='Say hello', tags=['Foo'])
        def hello():
            return 'Hello'
        ```

        Arguments:
            summary: The summary of this endpoint. If not set, the name of the view function
                will be used. If your view function is named with `get_pet`, then the summary
                will be "Get Pet". If the view function has a docstring, then the first
                line of the docstring will be used. The precedence will be:

                ```
                @app.doc(summary='blah') > the first line of docstring > the view function name
                ```

            description: The description of this endpoint. If not set, the lines after the empty
                line of the docstring will be used.
            tags: A list of tag names of this endpoint, map the tags you passed in the `app.tags`
                attribute. If `app.tags` is not set, the blueprint name will be used as tag name.
            responses: The other responses for this view function, accepts a list of status codes
                (`[404, 418]`) or a dict in a format of either `{404: 'Not Found'}` or
                `{404: {'description': 'Not Found', 'content': {'application/json':
                {'schema': FooSchema}}}}`. If a dict is passed and a response with the same status
                code is already present, the existing data will be overwritten.
            deprecated: Flag this endpoint as deprecated in API docs.
            hide: Hide this endpoint in API docs.
            operation_id: The `operationId` of this endpoint. Set config `AUTO_OPERATION_ID` to
                `True` to enable the auto-generating of operationId (in the format of
                `{method}_{endpoint}`).
            security: The `security` used for this endpoint. Match the security info specified in
                the `SECURITY_SCHEMES` configuration. If you don't need specify the scopes, just
                pass a security name (equals to `[{'foo': []}]`) or a list of security names (equals
                to `[{'foo': []}, {'bar': []}]`).
            extensions: The spec extensions of this endpoint (OpenAPI operation object). The fields
                in this extensions dict should start with "x-" prefix. See more details in the
                [Specification Extensions](https://spec.openapis.org/oas/v3.1.0#specification-extensions)
                chapter of OpenAPI docs.

        *Version changed: 2.2.0*

        - Add `extensions` parameter to support setting spec extensions.

        *Version changed: 2.0.0*

        - Remove the deprecated `tag` parameter.
        - Expand `responses` to support additional structure and parameters.

        *Version changed: 1.0*

        - Add `security` parameter to support customizing security info.
        - The `role` parameter is deprecated.

        *Version changed: 0.12.0*

        - Move to `APIFlask` and `APIBlueprint` classes.

        *Version changed: 0.10.0*

        - Add parameter `operation_id`.

        *Version changed: 0.5.0*

        - Change the default value of parameters `hide` and `deprecated` from `False` to `None`.

        *Version changed: 0.4.0*

        - Add parameter `tag`.

        *Version changed: 0.3.0*

        - Change the default value of `deprecated` from `None` to `False`.
        - Rename parameter `tags` to `tag`.

        *Version added: 0.2.0*
        """

        def decorator(f):
            f = _ensure_sync(f)
            _annotate(
                f,
                summary=summary,
                description=description,
                tags=tags,
                responses=responses,
                deprecated=deprecated,
                hide=hide,
                operation_id=operation_id,
                security=security,
                extensions=extensions,
            )
            return f

        return decorator
