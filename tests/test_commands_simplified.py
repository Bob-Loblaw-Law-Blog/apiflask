#!/usr/bin/env python3
"""Simplified unit tests for commands.py functionality.

This module tests the OpenAPI 'spec' command's option handling and functionality,
using a manual test approach to verify the command logic.
"""

import sys
import os

# Add source path for imports
sys.path.insert(0, '/tmp/inputs/apiflask/src')

import json
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open, MagicMock
from io import StringIO

# Mock the dependencies that aren't available
sys.modules['flask_marshmallow'] = MagicMock()
sys.modules['flask_marshmallow.fields'] = MagicMock()
sys.modules['webargs'] = MagicMock()
sys.modules['flask_httpauth'] = MagicMock()

# Mock marshmallow with basic functionality
class MockField:
    def __init__(self, **kwargs):
        self.kwargs = kwargs

class MockSchema:
    pass

marshmallow_mock = MagicMock()
marshmallow_mock.fields = MagicMock()
marshmallow_mock.fields.String = MockField
marshmallow_mock.fields.Integer = MockField
marshmallow_mock.Schema = MockSchema
marshmallow_mock.EXCLUDE = 'exclude'
sys.modules['marshmallow'] = marshmallow_mock
sys.modules['marshmallow.validate'] = MagicMock()

# Now import after mocking
from apiflask.commands import spec_command
import click
from click.testing import CliRunner


class MockApp:
    """Mock Flask app for testing."""
    
    def __init__(self):
        self.config = {
            'SPEC_FORMAT': 'json',
            'LOCAL_SPEC_PATH': None,
            'LOCAL_SPEC_JSON_INDENT': 2,
            'TESTING': True
        }
        self._spec = {
            'openapi': '3.0.3',
            'info': {'title': 'APIFlask', 'version': '1.0.0'},
            'paths': {
                '/users': {
                    'get': {'summary': 'Get all users'},
                    'post': {'summary': 'Create a user'}
                },
                '/users/{user_id}': {
                    'get': {'summary': 'Get a specific user'}
                }
            },
            'components': {
                'schemas': {
                    'User': {'type': 'object', 'properties': {'id': {'type': 'integer'}}}
                }
            }
        }
    
    def _get_spec(self, spec_format):
        """Mock _get_spec method."""
        if spec_format == 'json':
            return self._spec
        else:  # yaml
            return """openapi: 3.0.3
info:
  title: APIFlask
  version: 1.0.0
paths:
  /users:
    get:
      summary: Get all users
    post:
      summary: Create a user
  /users/{user_id}:
    get:
      summary: Get a specific user
components:
  schemas:
    User:
      type: object
      properties:
        id:
          type: integer"""
    
    def test_cli_runner(self):
        """Return a CLI runner for this app."""
        return CliRunner()


def test_default_behavior():
    """Test spec command with default configurations."""
    print("Testing default behavior...")
    
    app = MockApp()
    
    # Mock click context and Flask current_app
    with patch('apiflask.commands.current_app', app):
        runner = CliRunner()
        result = runner.invoke(spec_command, [])
        
        assert result.exit_code == 0
        # Should output JSON to stdout
        spec_data = json.loads(result.output)
        assert 'openapi' in spec_data
        assert 'paths' in spec_data
        print("✓ Default behavior test passed")


def test_quiet_flag():
    """Test --quiet flag suppresses stdout."""
    print("Testing quiet flag...")
    
    app = MockApp()
    
    with patch('apiflask.commands.current_app', app):
        runner = CliRunner()
        result = runner.invoke(spec_command, ['--quiet'])
        
        assert result.exit_code == 0
        # Should not output anything to stdout
        assert result.output == ''
        print("✓ Quiet flag test passed")


def test_format_options():
    """Test --format option overrides."""
    print("Testing format options...")
    
    app = MockApp()
    app.config['SPEC_FORMAT'] = 'yaml'  # Different from what we'll request
    
    with patch('apiflask.commands.current_app', app):
        runner = CliRunner()
        
        # Test explicit JSON format
        result = runner.invoke(spec_command, ['--format', 'json'])
        assert result.exit_code == 0
        spec_data = json.loads(result.output)
        assert 'openapi' in spec_data
        
        # Test YAML format
        result = runner.invoke(spec_command, ['--format', 'yaml'])
        assert result.exit_code == 0
        assert 'openapi:' in result.output
        assert '{"openapi":' not in result.output
        
        print("✓ Format options test passed")


def test_indent_options():
    """Test --indent option handling."""
    print("Testing indent options...")
    
    app = MockApp()
    app.config['LOCAL_SPEC_JSON_INDENT'] = 4  # Different from what we'll request
    
    with patch('apiflask.commands.current_app', app):
        runner = CliRunner()
        
        # Test explicit 0 indent (compact)
        result = runner.invoke(spec_command, ['--indent', '0'])
        assert result.exit_code == 0
        # Should be compact JSON
        assert '{"info": {' in result.output or '{"openapi":' in result.output
        
        # Test explicit 4 indent
        result = runner.invoke(spec_command, ['--indent', '4'])
        assert result.exit_code == 0
        # Should have 4-space indentation
        assert f'{{\n    "' in result.output
        
        print("✓ Indent options test passed")


def test_output_file():
    """Test --output option creates file."""
    print("Testing output file...")
    
    app = MockApp()
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        # Mock file opening to check content
        with patch('apiflask.commands.current_app', app):
            runner = CliRunner()
            result = runner.invoke(spec_command, ['--output', tmp_path, '--format', 'json'])
            
            assert result.exit_code == 0
            
            # Check file was created
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                content = f.read()
                spec_data = json.loads(content)
                assert 'openapi' in spec_data
                assert 'paths' in spec_data
                
        print("✓ Output file test passed")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_config_usage():
    """Test that config values are used when options not provided."""
    print("Testing config usage...")
    
    app = MockApp()
    app.config['SPEC_FORMAT'] = 'yaml'
    app.config['LOCAL_SPEC_JSON_INDENT'] = 0
    
    with patch('apiflask.commands.current_app', app):
        runner = CliRunner()
        result = runner.invoke(spec_command, [])
        
        assert result.exit_code == 0
        # Should use YAML format from config
        assert 'openapi:' in result.output
        assert '{"openapi":' not in result.output
        
        print("✓ Config usage test passed")


def test_combined_options():
    """Test multiple options used together."""
    print("Testing combined options...")
    
    app = MockApp()
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        with patch('apiflask.commands.current_app', app):
            runner = CliRunner()
            result = runner.invoke(spec_command, [
                '--format', 'json',
                '--output', tmp_path,
                '--indent', '4',
                '--quiet'
            ])
            
            assert result.exit_code == 0
            assert result.output == ''  # quiet flag
            
            # Check file was created with correct formatting
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                content = f.read()
                spec_data = json.loads(content)
                assert 'openapi' in spec_data
                # Should have 4-space indentation
                assert f'{{\n    "openapi":' in content
                
        print("✓ Combined options test passed")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_none_indent_handling():
    """Test handling of None vs 0 indent values."""
    print("Testing None indent handling...")
    
    app = MockApp()
    app.config['LOCAL_SPEC_JSON_INDENT'] = 2
    
    with patch('apiflask.commands.current_app', app):
        runner = CliRunner()
        
        # Test with config value (should use 2)
        result = runner.invoke(spec_command, [])
        assert result.exit_code == 0
        assert f'{{\n  "' in result.output  # 2-space indent
        
        # Test with explicit 0 (should be compact)
        result = runner.invoke(spec_command, ['--indent', '0'])
        assert result.exit_code == 0
        assert '{"' in result.output and f'{{\n  "' not in result.output
        
        print("✓ None indent handling test passed")


def test_yaml_with_indent_ignored():
    """Test that indent option doesn't affect YAML output."""
    print("Testing YAML indent ignored...")
    
    app = MockApp()
    
    with patch('apiflask.commands.current_app', app):
        runner = CliRunner()
        result = runner.invoke(spec_command, ['--format', 'yaml', '--indent', '8'])
        
        assert result.exit_code == 0
        # Should still be YAML format regardless of indent
        assert 'openapi:' in result.output
        assert '{"openapi":' not in result.output
        
        print("✓ YAML indent ignored test passed")


def test_local_spec_path_config():
    """Test LOCAL_SPEC_PATH config usage."""
    print("Testing LOCAL_SPEC_PATH config...")
    
    app = MockApp()
    
    with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
        tmp_path = tmp_file.name
    
    try:
        app.config['LOCAL_SPEC_PATH'] = tmp_path
        
        with patch('apiflask.commands.current_app', app):
            runner = CliRunner()
            result = runner.invoke(spec_command, ['--quiet'])  # quiet to only write file
            
            assert result.exit_code == 0
            
            # Check file was created using config path
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                content = f.read()
                spec_data = json.loads(content)
                assert 'openapi' in spec_data
                
        print("✓ LOCAL_SPEC_PATH config test passed")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def run_all_tests():
    """Run all tests and report results."""
    tests = [
        test_default_behavior,
        test_quiet_flag,
        test_format_options,
        test_indent_options,
        test_output_file,
        test_config_usage,
        test_combined_options,
        test_none_indent_handling,
        test_yaml_with_indent_ignored,
        test_local_spec_path_config,
    ]
    
    print("Running commands.py unit tests...\n")
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"✗ {test_func.__name__} failed: {e}")
            failed += 1
    
    print(f"\n=== Test Results ===")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Total: {len(tests)}")
    
    if failed == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print("❌ Some tests failed.")
        return False


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
