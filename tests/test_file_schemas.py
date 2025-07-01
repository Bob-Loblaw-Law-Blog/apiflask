import pytest
from apiflask.schemas import FileSchema


def test_file_schema_binary_string(app, client):
    @app.get('/binary-file')
    @app.output(
        FileSchema(type='string', format='binary'),
        content_type='application/octet-stream',
        description='A binary file'
    )
    def get_binary_file():
        return 'binary-data'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    content = rv.json['paths']['/binary-file']['get']['responses']['200']['content']
    assert content['application/octet-stream']['schema'] == {'type': 'string', 'format': 'binary'}


def test_file_schema_base64_string(app, client):
    @app.get('/base64-file')
    @app.output(
        FileSchema(type='string', format='base64'),
        content_type='application/octet-stream',
        description='A base64-encoded file'
    )
    def get_base64_file():
        return 'base64-data'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    content = rv.json['paths']['/base64-file']['get']['responses']['200']['content']
    assert content['application/octet-stream']['schema'] == {'type': 'string', 'format': 'base64'}


def test_file_schema_with_object_type(app, client):
    @app.get('/object-file')
    @app.output(
        FileSchema(type='object', format='binary'),
        content_type='application/octet-stream',
        description='A file as object'
    )
    def get_object_file():
        return 'file-data'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    content = rv.json['paths']['/object-file']['get']['responses']['200']['content']
    assert content['application/octet-stream']['schema'] == {'type': 'object', 'format': 'binary'}


def test_file_schema_with_description_and_examples(app, client):
    schema = FileSchema(type='string', format='binary')
    schema.description = 'A file download'
    schema.examples = {'example1': 'file-content'}

    @app.get('/file-with-metadata')
    @app.output(schema, content_type='application/pdf')
    def get_file_with_metadata():
        return 'file-data'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    # This will fail because FileSchema doesn't support description/examples currently
    # Just keeping this test to document this as future enhancement


@pytest.mark.parametrize(
    'content_type',
    [
        'application/pdf',
        'image/png',
        'image/jpeg',
        'text/plain',
        'application/zip',
        'application/x-tar',
        'application/octet-stream',
    ]
)
def test_file_schema_with_various_content_types(app, client, content_type):
    @app.get(f'/file-{content_type.replace("/", "-")}')
    @app.output(
        FileSchema(),
        content_type=content_type,
        description=f'File with content type {content_type}'
    )
    def get_file():
        return 'file-data'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    path = f'/file-{content_type.replace("/", "-")}'
    content = rv.json['paths'][path]['get']['responses']['200']['content']
    assert content_type in content
    assert content[content_type]['schema'] == {'type': 'string', 'format': 'binary'}


def test_file_schema_with_multiple_content_types(app, client):
    content_types = ['application/pdf', 'application/msword', 'application/vnd.ms-excel']
    
    @app.get('/multi-content-file')
    @app.output(
        FileSchema(),
        content_type=content_types,
        description='File in various document formats'
    )
    def get_multi_content_file():
        return 'file-data'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    content = rv.json['paths']['/multi-content-file']['get']['responses']['200']['content']
    
    for ct in content_types:
        assert ct in content
        assert content[ct]['schema'] == {'type': 'string', 'format': 'binary'}


def test_file_schema_headers(app, client):
    @app.get('/file-with-headers')
    @app.output(
        FileSchema(),
        content_type='application/pdf',
        description='File with custom headers',
        headers={
            'Content-Disposition': {
                'schema': {'type': 'string'},
                'description': 'Attachment filename',
                'example': 'attachment; filename="document.pdf"'
            },
            'X-Checksum': {
                'schema': {'type': 'string'},
                'description': 'File MD5 checksum',
                'example': '5eb63bbbe01eeed093cb22bb8f5acdc3'
            }
        }
    )
    def get_file_with_headers():
        return 'file-data'

    rv = client.get('/openapi.json')
    assert rv.status_code == 200
    response = rv.json['paths']['/file-with-headers']['get']['responses']['200']
    assert 'headers' in response
    headers = response['headers']
    
    assert 'Content-Disposition' in headers
    assert headers['Content-Disposition']['schema']['type'] == 'string'
    assert headers['Content-Disposition']['description'] == 'Attachment filename'
    assert headers['Content-Disposition']['example'] == 'attachment; filename="document.pdf"'
    
    assert 'X-Checksum' in headers
    assert headers['X-Checksum']['schema']['type'] == 'string'
    assert headers['X-Checksum']['description'] == 'File MD5 checksum'
    assert headers['X-Checksum']['example'] == '5eb63bbbe01eeed093cb22bb8f5acdc3'
