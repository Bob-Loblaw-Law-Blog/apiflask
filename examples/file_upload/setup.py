#!/usr/bin/env python3
"""
Setup script for the APIFlask file upload example with functional test data.
This script creates all necessary files and structure for a complete working example.
"""

import os
import shutil

def create_directory_structure():
    """Create the necessary directory structure"""
    directories = [
        'upload'
    ]
    
    for dir_name in directories:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name) 
            print(f"Created directory: {dir_name}/")
        else:
            print(f"Directory already exists: {dir_name}/")

def check_example_files():
    """Check if all example files are present"""
    required_files = [
        'app.py',
        'file_upload_README.md',
        'test_api.sh',
        'verify_files.py'
    ]
    
    missing_files = []
    for filename in required_files:
        if not os.path.exists(filename):
            missing_files.append(filename)
    
    if missing_files:
        print(f"Missing files: {', '.join(missing_files)}")
        print("Please ensure all example files are in the current directory.")
        return False
    return True

def show_file_overview():
    """Display overview of created files"""
    print("\n=== File Upload Example Structure ===")
    
    # Show main files
    main_files = {
        'app.py': 'Enhanced Flask application with file upload endpoints',
        'file_upload_README.md': 'Comprehensive documentation and usage guide', 
        'test_api.sh': 'Automated testing script using curl',
        'verify_files.py': 'Script to verify test files are present',
        'setup.py': 'This setup script'
    }
    
    print("\nMain files:")
    for filename, description in main_files.items():
        status = "✅" if os.path.exists(filename) else "❌"
        print(f"  {status} {filename:<25} - {description}")
    
    # Show upload directory contents
    print("\nUpload directory (test files):")
    upload_dir = "upload"
    if os.path.exists(upload_dir):
        for filename in sorted(os.listdir(upload_dir)):
            if not filename.startswith('.'):
                filepath = os.path.join(upload_dir, filename)
                if os.path.isfile(filepath):
                    size = os.path.getsize(filepath)
                    if size > 1024:
                        size_str = f"({size/1024:.1f} KB)"
                    else:
                        size_str = f"({size} bytes)"
                    print(f"  ✅ {filename:<22} {size_str}")

def print_usage_instructions():
    """Print instructions for using the example"""
    print("\n" + "="*60)
    print("🚀 APIFlask File Upload Example Setup Complete!")
    print("="*60)
    
    print("\n📋 Next Steps:")
    print("1. Install dependencies (if not done already):")
    print("   pip install apiflask")
    print()
    print("2. Start the application:")
    print("   flask run")
    print()
    print("3. Open your browser and visit:")
    print("   📖 http://localhost:5000/docs (Interactive API documentation)")
    print("   🏠 http://localhost:5000 (Welcome page)")
    print()
    print("4. Test the API:")
    print("   📁 Use the test files in upload/ directory")
    print("   🧪 Run: bash test_api.sh (automated testing)")
    print("   ✅ Run: python3 verify_files.py (verify setup)")
    
    print("\n🎯 Available Endpoints:")
    endpoints = [
        ("GET /", "Welcome message and API overview"),
        ("GET /files", "List uploaded files"),
        ("POST /images", "Upload image (PNG/JPG/JPEG/GIF, max 5MB)"),
        ("POST /profiles", "Create profile with avatar (PNG/JPG/JPEG, max 2MB)")
    ]
    
    for endpoint, description in endpoints:
        print(f"   {endpoint:<15} - {description}")
    
    print("\n📝 Example curl commands:")
    print("   # Upload an image")
    print("   curl -X POST http://localhost:5000/images \\")
    print("        -F 'image=@upload/sample_image.jpg'")
    print()
    print("   # Create a profile")
    print("   curl -X POST http://localhost:5000/profiles \\")
    print("        -F 'name=John Doe' \\")
    print("        -F 'avatar=@upload/avatar.jpg'")
    
    print(f"\n📚 Documentation: See file_upload_README.md for detailed guide")

def main():
    """Main setup function"""
    print("Setting up APIFlask File Upload Example with functional test data...")
    print("="*70)
    
    # Create directory structure
    create_directory_structure()
    
    # Check if we have the necessary files in place
    if not check_example_files():
        print("\n❌ Setup incomplete: Missing required files")
        return
    
    # Show overview of what was created
    show_file_overview()
    
    # Print usage instructions
    print_usage_instructions()

if __name__ == "__main__":
    main()
