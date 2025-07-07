import os

from werkzeug.utils import secure_filename
from apiflask import APIFlask, Schema
from apiflask.fields import File, String
from apiflask.validators import FileSize, FileType

app = APIFlask(__name__)

upload_dir = './upload'

# Ensure upload directory exists
if not os.path.exists(upload_dir):
    os.makedirs(upload_dir)


class Image(Schema):
    """Schema for image uploads via /images endpoint"""
    image = File(validate=[FileType(['.png', '.jpg', '.jpeg', '.gif']), FileSize(max='5 MB')])


class ProfileIn(Schema):
    """Schema for profile creation with avatar upload via /profiles endpoint"""
    name = String(required=True, metadata={'description': 'Profile name'})
    avatar = File(validate=[FileType(['.png', '.jpg', '.jpeg']), FileSize(max='2 MB')])


class FileListResponse(Schema):
    """Schema for file listing response"""
    files = String(many=True, metadata={'description': 'List of uploaded files'})
    count = String(metadata={'description': 'Total number of files'})


@app.get('/')
def index():
    """Welcome message with API documentation"""
    return {
        'message': 'APIFlask File Upload Example',
        'endpoints': {
            'GET /': 'This welcome message',
            'GET /files': 'List all uploaded files',
            'POST /images': 'Upload an image (PNG, JPG, JPEG, GIF up to 5MB)',
            'POST /profiles': 'Create profile with name and avatar (PNG, JPG, JPEG up to 2MB)'
        },
        'test_files': 'Check the /upload directory for sample files to test with',
        'docs': 'Visit /docs for interactive API documentation'
    }


@app.get('/files')
@app.output(FileListResponse)
def list_files():
    """List all uploaded files"""
    try:
        files = [f for f in os.listdir(upload_dir) if os.path.isfile(os.path.join(upload_dir, f))]
        # Filter out hidden files and .gitkeep
        files = [f for f in files if not f.startswith('.')]
        return {
            'files': files,
            'count': str(len(files))
        }
    except FileNotFoundError:
        return {
            'files': [],
            'count': '0'
        }


@app.post('/images')
@app.input(Image, location='files', example={
    'image': 'sample_image.jpg (use files from /upload directory for testing)'
})
@app.doc(summary='Upload an image file', 
         description='Upload an image file. Accepts PNG, JPG, JPEG, or GIF files up to 5MB in size.')
def upload_image(files_data):
    """Upload an image file"""
    f = files_data['image']

    filename = secure_filename(f.filename)
    file_path = os.path.join(upload_dir, filename)
    f.save(file_path)

    # Get file size for response
    file_size = os.path.getsize(file_path)
    
    return {
        'message': f'Image "{filename}" uploaded successfully.',
        'filename': filename,
        'size_bytes': file_size,
        'size_kb': round(file_size / 1024, 1)
    }


@app.post('/profiles')
@app.input(ProfileIn, location='form_and_files', example={
    'name': 'John Doe',
    'avatar': 'avatar.jpg (use files from /upload directory for testing)'
})
@app.doc(summary='Create a user profile with avatar',
         description='Create a user profile with a name and avatar image. Avatar must be PNG, JPG, or JPEG up to 2MB.')
def create_profile(form_and_files_data):
    """Create a user profile with avatar"""
    avatar_file = form_and_files_data['avatar']
    name = form_and_files_data['name']

    avatar_filename = secure_filename(avatar_file.filename)
    avatar_path = os.path.join(upload_dir, avatar_filename)
    avatar_file.save(avatar_path)

    # Get file size for response
    file_size = os.path.getsize(avatar_path)

    return {
        'message': f"Profile for '{name}' created successfully.",
        'name': name,
        'avatar_filename': avatar_filename,
        'avatar_size_bytes': file_size,
        'avatar_size_kb': round(file_size / 1024, 1)
    }


if __name__ == '__main__':
    app.run(debug=True)
