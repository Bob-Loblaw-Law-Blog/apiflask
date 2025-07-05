from __future__ import annotations

from flask import Blueprint

from .helpers import _sentinel
from .route import route_patch
from .scaffold import APIScaffold


@route_patch
class APIBlueprint(APIScaffold, Blueprint):
    """Flask's `Blueprint` object with some web API support.

    Examples:

    ```python
    from apiflask import APIBlueprint

    bp = APIBlueprint('foo', __name__)
    ```

    *Version changed: 0.5.0*

    - Add `enable_openapi` parameter.

    *Version added: 0.2.0*
    """

    def __init__(
        self,
        name: str,
        import_name: str,
        tag: str | dict | None = "default",
        enable_openapi: bool = True,
        static_folder: str | None = "static",
        static_url_path: str | None = "/static",
        template_folder: str | None = "templates",
        url_prefix: str | None = "/",
        subdomain: str | None = "",
        url_defaults: dict | None = {},
        root_path: str | None = "",
        cli_group: str | None = _sentinel,  # type: ignore
    ) -> None:
        """Make a blueprint instance.

        Arguments:
            name: The name of the blueprint. Will be prepended to
                each endpoint name.
            import_name: The name of the blueprint package, usually
                `__name__`. This helps locate the `root_path` for the
                blueprint.
            tag: The tag of this blueprint, accepts string or dict.
                APIFlask will use this tag to group the routes defined
                in this blueprint. When a dict is passed, it will be used to
                update a specific tag object. Valid keys are `name`,
                `description`, `externalDocs` and `x-*`. Defaults to None.
            enable_openapi: Enable/disable OpenAPI support for this blueprint.
                Defaults to True.
            static_folder: The folder with static files that should be served
                at `static_url_path`. Relative to the blueprint's root path,
                or an absolute path. Defaults to None.
            static_url_path: URL path for the static folder. If it's not set,
                the app's static folder is used, or if that is not set, it is
                the same as `static_folder`. Defaults to None.
            template_folder: The folder that contains the templates that should
                be used by the blueprint. Defaults to None, which means that
                the blueprint will use the app's template folder.
            url_prefix: A path to prepend to all of the blueprint's URLs, to
                make them distinct from the rest of the app's routes. If not
                provided, an explicit path component is required in the
                `route()` decorator. Defaults to None.
            subdomain: A subdomain that blueprint routes will match on by
                default. Defaults to None.
            url_defaults: A dict of default values that blueprint routes will
                receive. Defaults to None.
            root_path: By default, the blueprint will automatically set this
                based on `import_name`. In certain situations this automatic
                detection can fail, so the path can be specified manually
                instead. Defaults to None.
            cli_group: Name of the Click group to create in the CLI for this
                blueprint. The name is used as the name of the group in the
                commands help output. This is only used for Flask >= 2.0.
                Defaults to the blueprint's name.
        """