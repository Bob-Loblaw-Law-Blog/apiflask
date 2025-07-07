#!/usr/bin/env python3
"""
Verify the test files for the APIFlask file upload example.
"""

import os

def main():
    upload_dir = "upload"
    
    if not os.path.exists(upload_dir):
        print(f"Upload directory '{upload_dir}' not found!")
        return
    
    print("=== APIFlask File Upload Example - Test Files ===\n")
    
    expected_files = {
        'sample_image.jpg': 'Valid JPEG for /images endpoint',
        'sample_image.png': 'Valid PNG for /images endpoint', 
        'sample_image.gif': 'Valid GIF for /images endpoint',
        'avatar.jpg': 'Valid JPEG avatar for /profiles endpoint',
        'avatar.png': 'Valid PNG avatar for /profiles endpoint',
        'invalid_format.txt': 'Text file (should be rejected)',
        'invalid_avatar.gif': 'GIF file (rejected for avatars)', 
        'large_image.jpg': 'Large JPEG (may exceed avatar limit)'
    }
    
    print("Files found:")
    for filename in sorted(os.listdir(upload_dir)):
        if filename.startswith('.'):  # Skip hidden files
            continue
            
        filepath = os.path.join(upload_dir, filename)
        if os.path.isfile(filepath):
            size = os.path.getsize(filepath)
            
            if size > 1024 * 1024:
                size_str = f"{size:,} bytes ({size/(1024*1024):.1f} MB)"
            elif size > 1024:
                size_str = f"{size:,} bytes ({size/1024:.1f} KB)" 
            else:
                size_str = f"{size:,} bytes"
            
            if filename in expected_files:
                status = "✅"
                description = expected_files[filename]
            else:
                status = "?"
                description = "Unexpected file"
            
            print(f"  {status} {filename:<22} {size_str:<15} - {description}")
    
    print(f"\nTest files are ready! You can now:")
    print("1. Run 'flask run' to start the application")
    print("2. Visit http://localhost:5000/docs for interactive API documentation")  
    print("3. Use 'bash test_api.sh' to run automated tests")
    print("4. Test uploads manually with curl or the web interface")

if __name__ == "__main__":
    main()
