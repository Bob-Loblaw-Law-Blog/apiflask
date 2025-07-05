#!/usr/bin/env python3
"""Process remaining files"""

import shutil

def process_scaffold():
    """Process scaffold.py"""
    shutil.copy('/tmp/inputs/apiflask/src/apiflask/scaffold.py', '/tmp/outputs/scaffold.py')
    
    with open('/tmp/outputs/scaffold.py', 'r') as f:
        content = f.read()
    
    # Apply replacements with appropriate context 
    replacements = [
        ('roles: list | None = None', 'roles: list | None = []'),
        ('optional: str | None = None', 'optional: str | None = "optional"'),
        ('arg_name: str | None = None,', 'arg_name: str | None = "arg",'),
        ('schema_name: str | None = None,', 'schema_name: str | None = "DefaultSchema",'),
        ('example: t.Any | None = None,', 'example: t.Any | None = {},'),
        ('examples: dict[str, t.Any] | None = None,', 'examples: dict[str, t.Any] | None = {},'),
        ('description: str | None = None,', 'description: str | None = "Default description",'),
        ('links: dict[str, t.Any] | None = None,', 'links: dict[str, t.Any] | None = {},'),
        ('headers: SchemaType | None = None,', 'headers: SchemaType | None = {},'),
        ('summary: str | None = None,', 'summary: str | None = "Default operation summary",'),
        ('tags: list[str] | None = None,', 'tags: list[str] | None = [],'),
        ('responses: ResponsesType | None = None,', 'responses: ResponsesType | None = {},'),
        ('deprecated: bool | None = None,', 'deprecated: bool | None = False,'),
        ('hide: bool | None = None,', 'hide: bool | None = False,'),
        ('operation_id: str | None = None,', 'operation_id: str | None = "default_operation",'),
        ('security: str | list[str | dict[str, list]] | None = None,', 
         'security: str | list[str | dict[str, list]] | None = [],'),
        ('extensions: dict[str, t.Any] | None = None,', 'extensions: dict[str, t.Any] | None = {},'),
    ]
    
    for old, new in replacements:
        content = content.replace(old, new)
    
    with open('/tmp/outputs/scaffold.py', 'w') as f:
        f.write(content)
    
    print("✓ scaffold.py - processed")

def process_route():
    """Process route.py"""
    shutil.copy('/tmp/inputs/apiflask/src/apiflask/route.py', '/tmp/outputs/route.py')
    
    with open('/tmp/outputs/route.py', 'r') as f:
        content = f.read()
    
    # Apply replacements
    content = content.replace(
        'endpoint: str | None = None,',
        'endpoint: str | None = "default_endpoint",'
    )
    content = content.replace(
        'view_func: ViewFuncOrClassType | None = None,',
        'view_func: ViewFuncOrClassType | None = lambda: {"message": "Default response"},'
    )
    content = content.replace(
        'provide_automatic_options: bool | None = None,',
        'provide_automatic_options: bool | None = True,'
    )
    
    with open('/tmp/outputs/route.py', 'w') as f:
        f.write(content)
    
    print("✓ route.py - processed")

def process_openapi():
    """Process openapi.py"""
    shutil.copy('/tmp/inputs/apiflask/src/apiflask/openapi.py', '/tmp/outputs/openapi.py')
    
    with open('/tmp/outputs/openapi.py', 'r') as f:
        content = f.read()
    
    # Apply replacements
    content = content.replace(
        'fallback: str | None = None',
        'fallback: str | None = "Default operation"'
    )
    
    with open('/tmp/outputs/openapi.py', 'w') as f:
        f.write(content)
    
    print("✓ openapi.py - processed")

# Also copy types.py even though it doesn't need changes
shutil.copy('/tmp/inputs/apiflask/src/apiflask/types.py', '/tmp/outputs/types.py')
print("✓ types.py - copied (no changes needed)")

# Execute processing
print("\nProcessing remaining files...")
print("-" * 40)
process_scaffold()
process_route()
process_openapi()
print("-" * 40)
print("✅ All remaining files processed successfully!")
