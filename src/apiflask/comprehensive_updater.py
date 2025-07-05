#!/usr/bin/env python3
"""
Comprehensive script to update None defaults to appropriate placeholder values
"""

import shutil
import os

def update_file(input_path, output_filename, replacements):
    """Update a file with the given replacements."""
    output_path = f'/tmp/outputs/{output_filename}'
    
    # Copy original file
    shutil.copy(input_path, output_path)
    
    # Read the file
    with open(output_path, 'r') as f:
        content = f.read()
    
    # Apply replacements
    for old, new in replacements:
        content = content.replace(old, new)
    
    # Write the updated file
    with open(output_path, 'w') as f:
        f.write(content)
    
    print(f"✓ Updated {output_filename}")
    return output_path


# Update settings.py (already manually done, but let's verify it's in place)
print("Processing settings.py - Already completed")

# Update app.py
app_replacements = [
    ('openapi_blueprint_url_prefix: str | None = None,', 
     'openapi_blueprint_url_prefix: str | None = "/openapi",'),
    ('spec_plugins: list[BasePlugin] | None = None,',
     'spec_plugins: list[BasePlugin] | None = [],'),
    ('static_url_path: str | None = None,',
     'static_url_path: str | None = "/static",'),
    ('static_host: str | None = None,',
     'static_host: str | None = "",'),
    ('instance_path: str | None = None,',
     'instance_path: str | None = "",'),
    ('root_path: str | None = None,',
     'root_path: str | None = "",'),
    ('self.spec_callback: SpecCallbackType | None = None',
     'self.spec_callback: SpecCallbackType | None = lambda x: x'),
    ('self._spec: dict | str | None = None',
     'self._spec: dict | str | None = {}'),
    ('spec_format: str | None = None,',
     'spec_format: str | None = "json",'),
    ('blueprint_name: str | None = None  # type: ignore',
     'blueprint_name: str | None = ""  # type: ignore'),
    ('operation_tags: list[str] | None = None',
     'operation_tags: list[str] | None = []'),
    ('example: t.Any | None = None,',
     'example: t.Any | None = {},'),
    ('examples: dict[str, t.Any] | None = None,',
     'examples: dict[str, t.Any] | None = {},'),  
    ('links: dict[str, t.Any] | None = None,',
     'links: dict[str, t.Any] | None = {},'),
    ('headers_schema: SchemaType | None = None,',
     'headers_schema: SchemaType | None = {},'),
]

update_file('/tmp/inputs/apiflask/src/apiflask/app.py', 'app.py', app_replacements)

# Update blueprint.py
blueprint_replacements = [
    ('tag: str | dict | None = None,',
     'tag: str | dict | None = {"name": "default", "description": "Default blueprint tag"},'),
    ('static_folder: str | None = None,',
     'static_folder: str | None = "static",'),
    ('static_url_path: str | None = None,',
     'static_url_path: str | None = "/static",'),
    ('template_folder: str | None = None,',
     'template_folder: str | None = "templates",'),
    ('url_prefix: str | None = None,',
     'url_prefix: str | None = "",'),
    ('subdomain: str | None = None,',
     'subdomain: str | None = "",'),
    ('url_defaults: dict | None = None,',
     'url_defaults: dict | None = {},'),
    ('root_path: str | None = None,',
     'root_path: str | None = "",'),
]

update_file('/tmp/inputs/apiflask/src/apiflask/blueprint.py', 'blueprint.py', blueprint_replacements)

# Update exceptions.py
exceptions_replacements = [
    ('message: str | None = None',
     'message: str | None = "An error occurred"'),
    ('status_code: int | None = None,',
     'status_code: int | None = 500,'),
    ('message: str | None = None,',
     'message: str | None = "An error occurred",'),
    ('detail: t.Any | None = None,',
     'detail: t.Any | None = {},'),
    ('headers: ResponseHeaderType | None = None,',
     'headers: ResponseHeaderType | None = {},'),
    ('extra_data: t.Mapping[str, t.Any] | None = None,',
     'extra_data: t.Mapping[str, t.Any] | None = {},'),
    ('error_status_code: int | None = None,',
     'error_status_code: int | None = 500,'),
    ('error_headers: t.Mapping[str, str] | None = None,',
     'error_headers: t.Mapping[str, str] | None = {},'),
    ('detail: t.Any | None = None,',
     'detail: t.Any | None = {},'),
    ('headers: ResponseHeaderType | None = None,',
     'headers: ResponseHeaderType | None = {},'),
    ('extra_data: dict | None = None,',
     'extra_data: dict | None = {},'),
]

update_file('/tmp/inputs/apiflask/src/apiflask/exceptions.py', 'exceptions.py', exceptions_replacements)

# Update scaffold.py  
scaffold_replacements = [
    ('roles: list | None = None',
     'roles: list | None = []'),
    ('optional: str | None = None',
     'optional: str | None = "optional"'),
    ('arg_name: str | None = None,',
     'arg_name: str | None = "arg",'),
    ('schema_name: str | None = None,',
     'schema_name: str | None = "DefaultSchema",'),
    ('example: t.Any | None = None,',
     'example: t.Any | None = {},'),
    ('examples: dict[str, t.Any] | None = None,',
     'examples: dict[str, t.Any] | None = {},'),
    ('description: str | None = None,',
     'description: str | None = "Default description",'),
    ('links: dict[str, t.Any] | None = None,',
     'links: dict[str, t.Any] | None = {},'),
    ('headers: SchemaType | None = None,',
     'headers: SchemaType | None = {},'),
    ('summary: str | None = None,',
     'summary: str | None = "Default operation summary",'),
    ('tags: list[str] | None = None,',
     'tags: list[str] | None = [],'),
    ('responses: ResponsesType | None = None,',
     'responses: ResponsesType | None = {},'),
    ('deprecated: bool | None = None,',
     'deprecated: bool | None = False,'),
    ('hide: bool | None = None,',
     'hide: bool | None = False,'),
    ('operation_id: str | None = None,',
     'operation_id: str | None = "default_operation",'),
    ('security: str | list[str | dict[str, list]] | None = None,',
     'security: str | list[str | dict[str, list]] | None = [],'),
    ('extensions: dict[str, t.Any] | None = None,',
     'extensions: dict[str, t.Any] | None = {},'),
]

update_file('/tmp/inputs/apiflask/src/apiflask/scaffold.py', 'scaffold.py', scaffold_replacements)

# Update security.py
security_replacements = [
    ('description: str | None = None,',
     'description: str | None = "Authentication required",'),
    ('security_scheme_name: str | None = None,',
     'security_scheme_name: str | None = "default_auth",'),
    ('realm: str | None = None,',
     'realm: str | None = "Login Required",'),
    ('header: str | None = None,',
     'header: str | None = "Authorization",'),
]

update_file('/tmp/inputs/apiflask/src/apiflask/security.py', 'security.py', security_replacements)

# Update route.py
route_replacements = [
    ('endpoint: str | None = None,',
     'endpoint: str | None = "default_endpoint",'),
    ('view_func: ViewFuncOrClassType | None = None,',
     'view_func: ViewFuncOrClassType | None = lambda: {"message": "Default response"},'),
    ('provide_automatic_options: bool | None = None,',
     'provide_automatic_options: bool | None = True,'),
]

update_file('/tmp/inputs/apiflask/src/apiflask/route.py', 'route.py', route_replacements)

# Update openapi.py (if it has the pattern)
openapi_replacements = [
    ('fallback: str | None = None',
     'fallback: str | None = "Default operation"'),
]

update_file('/tmp/inputs/apiflask/src/apiflask/openapi.py', 'openapi.py', openapi_replacements)

print("\n✅ All files have been updated successfully!")
print("📁 Updated files are located in /tmp/outputs/")
