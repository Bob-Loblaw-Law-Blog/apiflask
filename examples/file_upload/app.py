import os
from pathlib import Path

from werkzeug.utils import secure_filename
from apiflask import APIFlask, Schema
from apiflask.fields import File, String
from apiflask.validators import FileSize, FileType

app = APIFlask(__name__)

# Define upload directory
UPLOAD_DIR = Path('./upload')

class Image(Schema):
    image = File(validate=[FileType(['.png', '.jpg', '.jpeg', '.gif']), FileSize(max='5 MB')])


class ProfileIn(Schema):
    name = String(required=True)
    avatar = File(validate=[FileType(['.png', '.jpg', '.jpeg']), FileSize(max='2 MB')])


class DocumentSchema(Schema):
    document = File(validate=[FileType(['.pdf', '.doc', '.docx', '.txt']), FileSize(max='10 MB')])


@app.post('/images')
@app.input(Image, location='files')
@app.doc(summary='Upload an image file')
def upload_image(files_data):
    """Upload an image file (PNG, JPG, JPEG, or GIF)."""
    f = files_data['image']

    if not f:
        return {'error': 'No file provided'}, 400

    filename = secure_filename(f.filename)
    if not filename:
        return {'error': 'Invalid filename'}, 400

    # Ensure unique filename
    file_path = UPLOAD_DIR / filename
    if file_path.exists():
        base, ext = os.path.splitext(filename)
        counter = 1
        while file_path.exists():
            filename = f"{base}_{counter}{ext}"
            file_path = UPLOAD_DIR / filename
            counter += 1

    f.save(file_path)

    return {
        'message': f'Image {filename} uploaded successfully',
        'filename': filename,
        'size': f"{file_path.stat().st_size / 1024:.1f} KB"
    }


@app.post('/profiles')
@app.input(ProfileIn, location='form_and_files')
@app.doc(summary='Create a profile with avatar')
def create_profile(form_and_files_data):
    """Create a user profile with name and avatar image."""
    avatar_file = form_and_files_data.get('avatar')
    name = form_and_files_data.get('name')

    if not name:
        return {'error': 'Name is required'}, 400

    profile_info = {'name': name}

    if avatar_file:
        avatar_filename = secure_filename(avatar_file.filename)
        if avatar_filename:
            # Prefix with username for organization
            avatar_filename = f"{secure_filename(name)}_{avatar_filename}"
            avatar_path = UPLOAD_DIR / avatar_filename

            # Handle duplicates
            if avatar_path.exists():
                base, ext = os.path.splitext(avatar_filename)
                counter = 1
                while avatar_path.exists():
                    avatar_filename = f"{base}_{counter}{ext}"
                    avatar_path = UPLOAD_DIR / avatar_filename
                    counter += 1

            avatar_file.save(avatar_path)
            profile_info['avatar'] = avatar_filename
            profile_info['avatar_size'] = f"{avatar_path.stat().st_size / 1024:.1f} KB"

    return {
        'message': f"{name}'s profile created successfully",
        'profile': profile_info
    }

