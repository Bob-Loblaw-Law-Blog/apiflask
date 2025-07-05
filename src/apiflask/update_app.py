import shutil
import re

# Copy the original file
shutil.copy('/tmp/inputs/apiflask/src/apiflask/app.py', '/tmp/outputs/app.py')

# Read the file
with open('/tmp/outputs/app.py', 'r') as f:
    content = f.read()

# Define replacements with context-appropriate defaults
replacements = [
    # Constructor parameters
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
    
    # Instance attributes
    ('self.spec_callback: SpecCallbackType | None = None',
     'self.spec_callback: SpecCallbackType | None = lambda x: x'),
    ('self._spec: dict | str | None = None',
     'self._spec: dict | str | None = {}'),
     
    # Method parameters
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

# Apply replacements
for old, new in replacements:
    content = content.replace(old, new)

# Write the updated file
with open('/tmp/outputs/app.py', 'w') as f:
    f.write(content)

print("Updated app.py successfully")
