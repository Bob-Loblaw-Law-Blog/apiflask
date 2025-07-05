#!/usr/bin/env python3
"""Script to update None defaults to placeholder values in type hints."""

import re
import os
from pathlib import Path

# Dictionary mapping type patterns to default values
type_defaults = {
    'str': '"default_value"',
    'dict': '{}',
    'list': '[]',
    'bool': 'False',
    'int': '0',
    't.Any': '{}',
    't.Callable': '[]',
    't.Mapping': '{}',
}

# Pattern to match: type_hint | None = None
# This captures the type hint before | None
pattern = r'(\w+(?:\[[\w\[\], |.]+\])?)\s*\|\s*None\s*=\s*None'

def get_default_for_type(type_hint):
    """Return appropriate default value for a given type hint."""
    
    # Clean up the type hint
    type_hint = type_hint.strip()
    
    # Special cases for specific variable names and types
    type_specific_defaults = {
        # OpenAPI related
        'SERVERS': '[]',
        'TAGS': '[]', 
        'EXTERNAL_DOCS': '{"url": "https://example.com/docs"}',
        'INFO': '{"title": "API", "version": "1.0.0"}',
        'DESCRIPTION': '"Default API Description"',
        'TERMS_OF_SERVICE': '"https://example.com/terms"',
        'CONTACT': '{"name": "API Support", "email": "support@example.com"}',
        'LICENSE': '{"name": "MIT", "url": "https://opensource.org/licenses/MIT"}',
        'SECURITY_SCHEMES': '{}',
        'LOCAL_SPEC_PATH': '"openapi.json"',
        'SYNC_LOCAL_SPEC': 'False',
        'SPEC_DECORATORS': '[]',
        'DOCS_DECORATORS': '[]',
        'SWAGGER_UI_OAUTH_REDIRECT_DECORATORS': '[]',
        'BASE_RESPONSE_SCHEMA': '{}',
        'REDOC_CONFIG': '{}',
        'SWAGGER_UI_CONFIG': '{}',
        'SWAGGER_UI_OAUTH_CONFIG': '{}',
        'ELEMENTS_CONFIG': '{}',
        'RAPIDOC_CONFIG': '{}',
        'RAPIPDF_CONFIG': '{}',
        
        # Path/URL related
        'openapi_blueprint_url_prefix': '"/api"',
        'static_url_path': '"/static"',
        'static_host': '"localhost"',
        'instance_path': '"/tmp/instance"',
        'root_path': '"/"',
        'static_folder': '"static"',
        'template_folder': '"templates"',
        'url_prefix': '"/"',
        'subdomain': '"www"',
        'url_defaults': '{}',
        'tag': '{"name": "default", "description": "Default tag"}',
        
        # Auth/Security related
        'realm': '"Login Required"',
        'header': '"Authorization"',
        'description': '"Default description"',
        'security_scheme_name': '"default_auth"',
        
        # Error/Exception related
        'message': '"Default error message"',
        'detail': '{}',
        'headers': '{}',
        'extra_data': '{}',
        'error_headers': '{}',
        'status_code': '200',
        'error_status_code': '500',
        
        # Function/View related
        'endpoint': '"default_endpoint"',
        'view_func': 'lambda: None',
        'provide_automatic_options': 'True',
        'roles': '[]',
        'optional': '"optional"',
        'arg_name': '"arg"',
        'schema_name': '"DefaultSchema"',
        'example': '{"example": "value"}',
        'examples': '{}',
        'links': '{}',
        'summary': '"Default summary"',
        'tags': '[]',
        'responses': '{}',
        'deprecated': 'False',
        'hide': 'False',
        'operation_id': '"default_operation"',
        'security': '[]',
        'extensions': '{}',
        'spec_callback': 'lambda x: x',
        '_spec': '{}',
        'operation_tags': '[]',
        'headers_schema': '{}',
        'spec_plugins': '[]',
        'spec_format': '"json"',
        'headers': '{}',
    }
    
    # Extract variable name from context (would need to be passed in)
    # For now, check common type patterns
    
    # Handle generic types
    if type_hint.startswith('list'):
        return '[]'
    elif type_hint.startswith('dict'):
        return '{}'
    elif type_hint.startswith('t.List'):
        return '[]'
    elif type_hint.startswith('t.Dict'):
        return '{}'
    elif type_hint.startswith('t.Mapping'):
        return '{}'
    elif type_hint == 'str':
        return '"default_value"'
    elif type_hint == 'bool':
        return 'False'
    elif type_hint == 'int':
        return '0'
    elif 'Callable' in type_hint:
        return '[]'
    elif 'SchemaType' in type_hint:
        return '{}'
    elif 'ResponseHeaderType' in type_hint:
        return '{}'
    elif 'ViewFuncOrClassType' in type_hint:
        return 'lambda: None'
    elif 'TagsType' in type_hint:
        return '[]'
    elif 'ResponsesType' in type_hint:
        return '{}'
    elif 'HTTPAuthType' in type_hint:
        return 'None'  # Keep None for auth types
    elif 'BasePlugin' in type_hint:
        return '[]'
    elif 'SpecCallbackType' in type_hint:
        return 'lambda x: x'
    else:
        # Default fallback
        return '{}'


def process_file(file_path, output_dir):
    """Process a single file and write updated version to output directory."""
    
    with open(file_path, 'r') as f:
        content = f.read()
    
    lines = content.split('\n')
    updated_lines = []
    
    for line in lines:
        # Check if line contains the pattern
        if ' | None = None' in line:
            # Extract variable name if it's an assignment
            var_match = re.search(r'(\w+):\s*(.+?)\s*\|\s*None\s*=\s*None', line)
            if var_match:
                var_name = var_match.group(1)
                type_hint = var_match.group(2).strip()
                
                # Get specific default based on variable name
                if var_name in type_specific_defaults:
                    default_value = type_specific_defaults[var_name]
                else:
                    default_value = get_default_for_type(type_hint)
                
                # Replace None with the default value
                updated_line = line.replace(' = None', f' = {default_value}')
                updated_lines.append(updated_line)
            else:
                updated_lines.append(line)
        else:
            updated_lines.append(line)
    
    # Create output path
    relative_path = Path(file_path).relative_to('/tmp/inputs/apiflask/src/apiflask')
    output_path = Path(output_dir) / relative_path
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write updated content
    with open(output_path, 'w') as f:
        f.write('\n'.join(updated_lines))
    
    return output_path


# List of files to process based on grep results
files_to_process = [
    '/tmp/inputs/apiflask/src/apiflask/settings.py',
    '/tmp/inputs/apiflask/src/apiflask/app.py',
    '/tmp/inputs/apiflask/src/apiflask/blueprint.py',
    '/tmp/inputs/apiflask/src/apiflask/exceptions.py',
    '/tmp/inputs/apiflask/src/apiflask/scaffold.py',
    '/tmp/inputs/apiflask/src/apiflask/security.py',
    '/tmp/inputs/apiflask/src/apiflask/route.py',
]

if __name__ == '__main__':
    output_dir = '/tmp/outputs'
    
    print("Processing files...")
    for file_path in files_to_process:
        if os.path.exists(file_path):
            output_path = process_file(file_path, output_dir)
            print(f"Processed: {file_path} -> {output_path}")
        else:
            print(f"File not found: {file_path}")
