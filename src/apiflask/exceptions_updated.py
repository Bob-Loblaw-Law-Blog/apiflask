from __future__ import annotations

import typing as t

from flask import current_app
from werkzeug.exceptions import default_exceptions

from .helpers import get_reason_phrase
from .types import ResponseHeaderType

_bad_schema_message = 'The schema must be a marshmallow schema class or an OpenAPI schema dict.'


class HTTPError(Exception):
    """The exception to end the request handling and return an JSON error response.

    Examples:

    ```python
    from apiflask import APIFlask, HTTPError
    from markupsafe import escape

    app = APIFlask(__name__)

    @app.get('/<name>')
    def hello(name):
        if name == 'Foo':
            raise HTTPError(404, 'This man is missing.')
        return f'Hello, escape{name}'!
    ```
    """

    status_code: int = 500
    message: str | None = None
    detail: t.Any = {}
    headers: ResponseHeaderType = {}
    extra_data: t.Mapping[str, t.Any] = {}

    def __init__(
        self,
        status_code: int | None = 500,
        message: str | None = "Internal Server Error",
        detail: t.Any | None = {},
        headers: ResponseHeaderType | None = {},
        extra_data: t.Mapping[str, t.Any] | None = {},
    ) -> None:
        """Initialize the error response.

        Arguments:
            status_code: The status code of the error (4XX and 5xx), defaults to 500.
            message: The error message, defaults to None.
                If not provided, a default error message will be used.
            detail: The detailed error message/payload, defaults to None.
            headers: A dict of HTTP headers, defaults to None.
            extra_data: Extra data to include in the error response, defaults to None.
        """
        if status_code is not None:
            self.status_code = status_code
        if message is not None:
            self.message = message
        else:  # pragma: no cover
            self.message = get_reason_phrase(self.status_code, 'An error occurred.')
        if detail is not None:
            self.detail = detail
        if headers is not None:
            self.headers = headers
        if extra_data is not None:
            self.extra_data = extra_data
        super().__init__()
