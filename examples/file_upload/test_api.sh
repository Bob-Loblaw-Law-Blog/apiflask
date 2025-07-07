#!/bin/bash

# APIFlask File Upload Example - Test Script
# This script demonstrates how to test the file upload endpoints using curl

BASE_URL="http://localhost:5000"
UPLOAD_DIR="upload"

echo "=== APIFlask File Upload Example Test Script ==="
echo "Make sure the Flask app is running on $BASE_URL"
echo

# Check if upload directory exists
if [ ! -d "$UPLOAD_DIR" ]; then
    echo "Upload directory not found. Creating sample files..."
    python3 generate_test_files.py
    echo
fi

echo "=== Testing GET / (Welcome Message) ==="
curl -s "$BASE_URL/" | python3 -m json.tool
echo -e "\n"

echo "=== Testing GET /files (List Files) ==="
curl -s "$BASE_URL/files" | python3 -m json.tool
echo -e "\n"

echo "=== Testing POST /images (Upload Image) ==="
if [ -f "$UPLOAD_DIR/sample_image.jpg" ]; then
    echo "Uploading sample_image.jpg..."
    curl -s -X POST "$BASE_URL/images" \
         -F "image=@$UPLOAD_DIR/sample_image.jpg" | python3 -m json.tool
else
    echo "Sample file not found. Run 'python3 generate_test_files.py' first."
fi
echo -e "\n"

echo "=== Testing POST /images with PNG ==="
if [ -f "$UPLOAD_DIR/sample_image.png" ]; then
    echo "Uploading sample_image.png..."
    curl -s -X POST "$BASE_URL/images" \
         -F "image=@$UPLOAD_DIR/sample_image.png" | python3 -m json.tool
else
    echo "Sample PNG file not found."
fi
echo -e "\n"

echo "=== Testing POST /profiles (Create Profile) ==="
if [ -f "$UPLOAD_DIR/avatar.jpg" ]; then
    echo "Creating profile with avatar.jpg..."
    curl -s -X POST "$BASE_URL/profiles" \
         -F "name=John Doe" \
         -F "avatar=@$UPLOAD_DIR/avatar.jpg" | python3 -m json.tool
else
    echo "Avatar file not found. Run 'python3 generate_test_files.py' first."
fi
echo -e "\n"

echo "=== Testing Validation: Invalid File Format ==="
if [ -f "$UPLOAD_DIR/invalid_format.txt" ]; then
    echo "Trying to upload text file as image (should fail)..."
    curl -s -X POST "$BASE_URL/images" \
         -F "image=@$UPLOAD_DIR/invalid_format.txt" | python3 -m json.tool
else
    echo "Invalid format test file not found."
fi
echo -e "\n"

echo "=== Testing Validation: Invalid Avatar Format ==="
if [ -f "$UPLOAD_DIR/invalid_avatar.gif" ]; then
    echo "Trying to upload GIF as avatar (should fail - only JPG/PNG allowed)..."
    curl -s -X POST "$BASE_URL/profiles" \
         -F "name=Jane Doe" \
         -F "avatar=@$UPLOAD_DIR/invalid_avatar.gif" | python3 -m json.tool
else
    echo "Invalid avatar test file not found."
fi
echo -e "\n"

echo "=== Testing File Size Limit ==="
if [ -f "$UPLOAD_DIR/large_image.jpg" ]; then
    echo "Trying to upload large file as avatar (may fail if > 2MB)..."
    curl -s -X POST "$BASE_URL/profiles" \
         -F "name=Big Picture User" \
         -F "avatar=@$UPLOAD_DIR/large_image.jpg" | python3 -m json.tool
else
    echo "Large image test file not found."
fi
echo -e "\n"

echo "=== Final File List ==="
curl -s "$BASE_URL/files" | python3 -m json.tool
echo -e "\n"

echo "Test completed! Check the API documentation at $BASE_URL/docs"
