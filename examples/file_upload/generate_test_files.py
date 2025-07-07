#!/usr/bin/env python3
"""
Simple script to generate minimal test files for the APIFlask file upload example.
Creates basic binary files with proper extensions for testing upload functionality.
"""

import os

def create_upload_dir():
    """Create the upload directory if it doesn't exist"""
    upload_dir = "upload"
    if not os.path.exists(upload_dir):
        os.makedirs(upload_dir)
    return upload_dir

def create_minimal_jpeg(filename, size_kb=50):
    """Create a minimal valid JPEG file"""
    # Minimal JPEG header
    jpeg_header = bytes([
        0xFF, 0xD8, 0xFF, 0xE0,  # JPEG SOI and APP0
        0x00, 0x10, 0x4A, 0x46,  # Length and JFIF
        0x49, 0x46, 0x00, 0x01,  # JFIF string
        0x01, 0x01, 0x00, 0x00,  # Version and aspect
        0x00, 0x01, 0x00, 0x01,  # Density
        0x00, 0x00, 0xFF, 0xD9   # End marker
    ])
    
    # Pad to desired size
    padding_size = (size_kb * 1024) - len(jpeg_header)
    if padding_size > 0:
        # Add comment section
        padding = b'\xFF\xFE' + b'\x00' * min(padding_size - 2, 65533)
        data = jpeg_header[:-2] + padding + jpeg_header[-2:]
    else:
        data = jpeg_header
    
    with open(filename, 'wb') as f:
        f.write(data)
    print(f"Created {filename} - Size: {os.path.getsize(filename):,} bytes")

def create_minimal_png(filename, size_kb=30):
    """Create a minimal valid PNG file"""
    # PNG signature and minimal IHDR chunk for 1x1 image
    png_data = bytes([
        0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,  # PNG signature
        0x00, 0x00, 0x00, 0x0D,  # IHDR length
        0x49, 0x48, 0x44, 0x52,  # IHDR
        0x00, 0x00, 0x00, 0x01,  # Width: 1
        0x00, 0x00, 0x00, 0x01,  # Height: 1
        0x08, 0x02, 0x00, 0x00, 0x00,  # Bit depth, color type, compression, filter, interlace
        0x90, 0x77, 0x53, 0xDE,  # CRC
        0x00, 0x00, 0x00, 0x0C,  # IDAT length
        0x49, 0x44, 0x41, 0x54,  # IDAT
        0x08, 0x99, 0x01, 0x01, 0x00, 0x00, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x02,  # Compressed data
        0x00, 0x01, 0x73, 0x75,  # CRC
        0x00, 0x00, 0x00, 0x00,  # IEND length
        0x49, 0x45, 0x4E, 0x44,  # IEND
        0xAE, 0x42, 0x60, 0x82   # CRC
    ])
    
    # Pad to desired size with comment chunks
    padding_size = (size_kb * 1024) - len(png_data) - 12  # -12 for final IEND
    if padding_size > 0:
        # Add text chunk
        text_data = b'Comment' + b'\x00' + b'Generated test file' + b' ' * max(0, padding_size - 20)
        text_length = len(text_data)
        padding_chunk = (
            text_length.to_bytes(4, 'big') +  # Length
            b'tEXt' +                         # Type
            text_data +                       # Data
            b'\x00\x00\x00\x00'             # CRC (simplified)
        )
        png_data = png_data[:-12] + padding_chunk + png_data[-12:]
    
    with open(filename, 'wb') as f:
        f.write(png_data)
    print(f"Created {filename} - Size: {os.path.getsize(filename):,} bytes")

def create_minimal_gif(filename, size_kb=20):
    """Create a minimal valid GIF file"""
    # GIF signature and screen descriptor for 1x1 image
    gif_data = bytes([
        0x47, 0x49, 0x46, 0x38, 0x39, 0x61,  # GIF89a signature
        0x01, 0x00, 0x01, 0x00,              # Width: 1, Height: 1
        0x80, 0x00, 0x00,                    # Global color table flag, color resolution, sort flag, global color table size, background color, pixel aspect ratio
        0xFF, 0xFF, 0xFF,                    # Global color table (white)
        0x00, 0x00, 0x00,                    # Global color table (black)
        0x21, 0xFF, 0x0B,                    # Extension introducer, application extension label, block size
    ] + list(b'NETSCAPE2.0') + [            # Application identifier
        0x03, 0x01, 0x00, 0x00, 0x00,       # Data block
        0x2C, 0x00, 0x00, 0x00, 0x00,       # Image descriptor
        0x01, 0x00, 0x01, 0x00,             # Left, top, width, height
        0x00, 0x02, 0x02, 0x04, 0x01, 0x00, # Local color table flag, interlace flag, sort flag, reserved, local color table size, LZW minimum code size, image data
        0x3B                                  # GIF trailer
    ])
    
    # Pad to desired size
    padding_size = (size_kb * 1024) - len(gif_data)
    if padding_size > 0:
        # Insert comment extension
        comment_data = b'Generated test file ' + b'.' * max(0, padding_size - 25)
        comment_ext = b'\x21\xFE' + bytes([min(255, len(comment_data))]) + comment_data[:255] + b'\x00'
        gif_data = gif_data[:-1] + comment_ext + gif_data[-1:]
    
    with open(filename, 'wb') as f:
        f.write(gif_data)
    print(f"Created {filename} - Size: {os.path.getsize(filename):,} bytes")

def create_text_file(filename, content):
    """Create a text file for testing invalid formats"""
    with open(filename, 'w') as f:
        f.write(content)
    print(f"Created {filename} - Size: {os.path.getsize(filename):,} bytes")

def create_large_file(filename, size_mb=3):
    """Create a larger file for testing size limits"""
    data = b'Large file data for testing size limits. ' * 1000
    target_size = size_mb * 1024 * 1024
    
    # Basic JPEG header
    jpeg_header = bytes([0xFF, 0xD8, 0xFF, 0xE0, 0x00, 0x10, 0x4A, 0x46, 0x49, 0x46, 0x00, 0x01])
    jpeg_footer = bytes([0xFF, 0xD9])
    
    with open(filename, 'wb') as f:
        f.write(jpeg_header)
        written = len(jpeg_header)
        
        while written < target_size - len(jpeg_footer):
            chunk_size = min(len(data), target_size - written - len(jpeg_footer))
            f.write(data[:chunk_size])
            written += chunk_size
            
        f.write(jpeg_footer)
    
    print(f"Created {filename} - Size: {os.path.getsize(filename):,} bytes ({os.path.getsize(filename)/(1024*1024):.1f} MB)")

def main():
    upload_dir = create_upload_dir()
    
    # Change to upload directory
    original_dir = os.getcwd()
    os.chdir(upload_dir)
    
    print("Creating sample files for APIFlask file upload example...\n")
    
    # Sample images for /images endpoint (allows PNG, JPG, JPEG, GIF up to 5MB)
    create_minimal_jpeg("sample_image.jpg", 60)
    create_minimal_png("sample_image.png", 40) 
    create_minimal_gif("sample_image.gif", 30)
    
    # Sample avatars for /profiles endpoint (allows PNG, JPG, JPEG up to 2MB)
    create_minimal_jpeg("avatar.jpg", 25)
    create_minimal_png("avatar.png", 20)
    
    # Invalid files for testing validation
    create_text_file("invalid_format.txt", 
                    "This is a text file, not an image. It should be rejected by the file type validator.")
    
    # GIF avatar (invalid for profiles - only JPG/PNG allowed for avatars)
    create_minimal_gif("invalid_avatar.gif", 15)
    
    # Large file for testing size limits
    create_large_file("large_image.jpg", 3)  # 3MB file
    
    print(f"\nSample files created in '{upload_dir}' directory!")
    
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
            
            # Add validation info
            if filename.startswith('invalid_'):
                validation = " ❌ (for testing validation)"
            elif filename == 'large_image.jpg':
                validation = " ⚠️  (may exceed 2MB avatar limit)"
            else:
                validation = " ✅ (valid)"
                
            print(f"  - {filename:<20} {size_str}{validation}")
    
    # Change back to original directory
    os.chdir(original_dir)

if __name__ == "__main__":
    main()
