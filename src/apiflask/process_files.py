#!/usr/bin/env python3
"""Process each file to update None defaults"""

import shutil
import re

def process_settings():
    """Settings.py has already been manually processed"""
    print("✓ settings.py - already processed")

def process_app():
    """Process app.py"""
    shutil.copy('/tmp/inputs/apiflask/src/apiflask/app.py', '/tmp/outputs/app.py')
    
    with open('/tmp/outputs/app.py', 'r') as f:
        lines = f.readlines()
    
    # Process line by line
    for i, line in enumerate(lines):
        if 'openapi_blueprint_url_prefix: str | None = None' in line:
            lines[i] = line.replace('= None', '= "/openapi"')
        elif 'spec_plugins: list[BasePlugin] | None = None' in line:
            lines[i] = line.replace('= None', '= []')
        elif 'static_url_path: str | None = None' in line:
            lines[i] = line.replace('= None', '= "/static"')
        elif 'static_host: str | None = None' in line:
            lines[i] = line.replace('= None', '= ""')
        elif 'instance_path: str | None = None' in line:
            lines[i] = line.replace('= None', '= ""')
        elif 'root_path: str | None = None' in line:
            lines[i] = line.replace('= None', '= ""')
        elif 'self.spec_callback: SpecCallbackType | None = None' in line:
            lines[i] = line.replace('= None', '= lambda x: x')
        elif 'self._spec: dict | str | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
        elif 'spec_format: str | None = None' in line:
            lines[i] = line.replace('= None', '= "json"')
        elif 'blueprint_name: str | None = None' in line:
            lines[i] = line.replace('= None', '= ""')
        elif 'operation_tags: list[str] | None = None' in line:
            lines[i] = line.replace('= None', '= []')
        elif 'example: t.Any | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
        elif 'examples: dict[str, t.Any] | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
        elif 'links: dict[str, t.Any] | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
        elif 'headers_schema: SchemaType | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
    
    with open('/tmp/outputs/app.py', 'w') as f:
        f.writelines(lines)
    
    print("✓ app.py - processed")

def process_blueprint():
    """Process blueprint.py"""
    shutil.copy('/tmp/inputs/apiflask/src/apiflask/blueprint.py', '/tmp/outputs/blueprint.py')
    
    with open('/tmp/outputs/blueprint.py', 'r') as f:
        content = f.read()
    
    # Apply replacements
    content = content.replace(
        'tag: str | dict | None = None,',
        'tag: str | dict | None = {"name": "default", "description": "Default blueprint tag"},'
    )
    content = content.replace(
        'static_folder: str | None = None,',
        'static_folder: str | None = "static",'
    )
    content = content.replace(
        'static_url_path: str | None = None,',
        'static_url_path: str | None = "/static",'
    )
    content = content.replace(
        'template_folder: str | None = None,',
        'template_folder: str | None = "templates",'
    )
    content = content.replace(
        'url_prefix: str | None = None,',
        'url_prefix: str | None = "",'
    )
    content = content.replace(
        'subdomain: str | None = None,',
        'subdomain: str | None = "",'
    )
    content = content.replace(
        'url_defaults: dict | None = None,',
        'url_defaults: dict | None = {},'
    )
    content = content.replace(
        'root_path: str | None = None,',
        'root_path: str | None = "",'
    )
    
    with open('/tmp/outputs/blueprint.py', 'w') as f:
        f.write(content)
    
    print("✓ blueprint.py - processed")

def process_exceptions():
    """Process exceptions.py"""
    shutil.copy('/tmp/inputs/apiflask/src/apiflask/exceptions.py', '/tmp/outputs/exceptions.py')
    
    with open('/tmp/outputs/exceptions.py', 'r') as f:
        lines = f.readlines()
    
    # Process line by line for better control
    for i, line in enumerate(lines):
        # Check for specific patterns and replace appropriately
        if 'message: str | None = None' in line and 'class' not in lines[max(0, i-3):i]:
            lines[i] = line.replace('= None', '= "An error occurred"')
        elif 'status_code: int | None = None' in line:
            lines[i] = line.replace('= None', '= 500')
        elif 'detail: t.Any | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
        elif 'headers: ResponseHeaderType | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
        elif 'extra_data: t.Mapping[str, t.Any] | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
        elif 'extra_data: dict | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
        elif 'error_status_code: int | None = None' in line:
            lines[i] = line.replace('= None', '= 500')
        elif 'error_headers: t.Mapping[str, str] | None = None' in line:
            lines[i] = line.replace('= None', '= {}')
    
    with open('/tmp/outputs/exceptions.py', 'w') as f:
        f.writelines(lines)
    
    print("✓ exceptions.py - processed")

def process_security():
    """Process security.py"""
    shutil.copy('/tmp/inputs/apiflask/src/apiflask/security.py', '/tmp/outputs/security.py')
    
    with open('/tmp/outputs/security.py', 'r') as f:
        content = f.read()
    
    # Apply replacements
    content = content.replace(
        'description: str | None = None,',
        'description: str | None = "Authentication required",'
    )
    content = content.replace(
        'security_scheme_name: str | None = None,',
        'security_scheme_name: str | None = "default_auth",'
    )
    content = content.replace(
        'realm: str | None = None,',
        'realm: str | None = "Login Required",'
    )
    content = content.replace(
        'header: str | None = None,',
        'header: str | None = "Authorization",'
    )
    
    with open('/tmp/outputs/security.py', 'w') as f:
        f.write(content)
    
    print("✓ security.py - processed")

# Execute all processing functions
print("Processing files...")
print("-" * 40)
process_settings()
process_app()
process_blueprint()
process_exceptions()
process_security()
print("-" * 40)
print("✅ All main files processed successfully!")
