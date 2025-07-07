#!/usr/bin/env python3
"""
Script to generate sample test files for the APIFlask file upload example.
This creates small valid images in various formats for testing the upload endpoints.
"""

import os
from PIL import Image
import io

def create_upload_dir():
    """Create the upload directory if it doesn't exist"""
    upload_dir = "upload"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    return upload_dir

def create_small_image(filename, format, size=(100, 100), color=(0, 128, 255)):
    """Create a small image file in the specified format"""
    # Create a simple colored rectangle image
    img = Image.new('RGB', size, color)
    img.save(filename, format=format.upper())
    print(f"Created {filename} ({format.upper()}) - Size: {os.path.getsize(filename)} bytes")

def create_sample_text_file(filename, content):
    """Create a text file (for testing invalid format validation)"""
    with open(filename, 'w') as f:
        f.write(content)
    print(f"Created {filename} - Size: {os.path.getsize(filename)} bytes")

def create_large_image(filename, format, size=(1000, 1000)):
    """Create a larger image file for testing size limits"""
    # Create a larger image with a gradient effect
    img = Image.new('RGB', size, (255, 255, 255))
    pixels = img.load()
    
    # Create a simple gradient
    for i in range(size[0]):
        for j in range(size[1]):
            r = int(255 * i / size[0])
            g = int(255 * j / size[1]) 
            b = 128
            pixels[i, j] = (r, g, b)
    
    img.save(filename, format=format.upper())
    print(f"Created {filename} ({format.upper()}) - Size: {os.path.getsize(filename)} bytes")

def main():
    upload_dir = create_upload_dir()
    
    # Change to upload directory
    os.chdir(upload_dir)
    
    print("Creating sample files for APIFlask file upload example...\n")
    
    # Small valid images for testing (< 1MB each)
    create_small_image("sample_image.jpg", "jpeg", (200, 150), (255, 100, 100))
    create_small_image("sample_image.png", "png", (200, 150), (100, 255, 100))  
    create_small_image("sample_image.gif", "gif", (200, 150), (100, 100, 255))
    
    # Small avatar images (< 500KB each)
    create_small_image("avatar.jpg", "jpeg", (128, 128), (255, 200, 150))
    create_small_image("avatar.png", "png", (128, 128), (150, 200, 255))
    
    # Invalid format file for testing validation
    create_sample_text_file("invalid_format.txt", 
                           "This is a text file, not an image. It should be rejected by the file type validator.")
    
    # GIF avatar (invalid for profiles endpoint - only JPG/PNG allowed)
    create_small_image("invalid_avatar.gif", "gif", (128, 128), (255, 150, 200))
    
    # Larger image for testing size limits (may exceed 2MB limit for avatars)
    create_large_image("large_image.jpg", "jpeg", (800, 600))
    
    print(f"\nSample files created in '{upload_dir}' directory!")
    print("Use these files to test the file upload endpoints.")
    
    # List all files with their sizes
    print("\nFiles created:")
    for filename in sorted(os.listdir('.')):
        if os.path.isfile(filename):
            size = os.path.getsize(filename)
            size_str = f"{size:,} bytes"
            if size > 1024:
                size_str += f" ({size/1024:.1f} KB)"
            if size > 1024*1024:
                size_str += f" ({size/(1024*1024):.1f} MB)"
            print(f"  - {filename:<20} {size_str}")

if __name__ == "__main__":
    main()
