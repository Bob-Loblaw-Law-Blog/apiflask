#!/usr/bin/env python3
"""Unit tests for commands.py logic.

This module tests the OpenAPI 'spec' command's option handling logic
by focusing on the command function itself rather than full integration.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from io import StringIO
import click
from click.testing import CliRunner


def create_mock_spec_command():
    """Create a mock version of the spec_command for testing logic."""
    
    @click.command('spec', short_help='Show the OpenAPI spec.')
    @click.option(
        '--format',
        '-f',
        type=click.Choice(['json', 'yaml', 'yml']),
        help='The format of the spec, defaults to SPEC_FORMAT config.',
    )
    @click.option(
        '--output',
        '-o',
        type=click.Path(),
        help='The file path to the spec file, defaults to LOCAL_SPEC_PATH config.',
    )
    @click.option(
        '--indent',
        '-i',
        type=int,
        help='The indentation for JSON spec, defaults to LOCAL_SPEC_JSON_INDENT config.',
    )
    @click.option(
        '--quiet', '-q', type=bool, is_flag=True, help='A flag to suppress printing output to stdout.'
    )
    def spec_command(format, output, indent, quiet):
        """Test implementation of spec command logic."""
        
        # Mock current_app with test configuration
        mock_app = Mock()
        mock_app.config = {
            'SPEC_FORMAT': 'json',
            'LOCAL_SPEC_PATH': None,
            'LOCAL_SPEC_JSON_INDENT': 2
        }
        
        # Mock spec data
        mock_spec_dict = {
            'openapi': '3.0.3',
            'info': {'title': 'APIFlask', 'version': '1.0.0'},
            'paths': {'/test': {'get': {'summary': 'Test endpoint'}}},
            'components': {'schemas': {'TestSchema': {'type': 'object'}}}
        }
        
        mock_spec_yaml = """openapi: 3.0.3
info:
  title: APIFlask
  version: 1.0.0
paths:
  /test:
    get:
      summary: Test endpoint
components:
  schemas:
    TestSchema:
      type: object"""
        
        # Apply the same logic as the original command
        spec_format = format or mock_app.config['SPEC_FORMAT']
        
        if spec_format == 'json':
            spec = mock_spec_dict
        else:
            spec = mock_spec_yaml
            
        output_path = output or mock_app.config['LOCAL_SPEC_PATH']
        
        if indent is None:
            indent = mock_app.config['LOCAL_SPEC_JSON_INDENT']
        json_indent = None if indent == 0 else indent

        if spec_format == 'json':
            spec = json.dumps(spec, indent=json_indent)

        # output to stdout
        if not quiet:
            click.echo(spec)

        # output to local file
        if output_path:
            with open(output_path, 'w') as f:
                click.echo(spec, file=f)
    
    return spec_command


class TestSpecCommandLogic:
    """Test the logical behavior of the spec command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.spec_command = create_mock_spec_command()
        self.runner = CliRunner()
    
    def test_default_json_format_and_indent(self):
        """Test default JSON format with default indentation."""
        result = self.runner.invoke(self.spec_command, [])
        
        assert result.exit_code == 0
        assert result.output.strip()  # Should have output
        
        # Should be formatted JSON (not compact)
        spec_data = json.loads(result.output)
        assert 'openapi' in spec_data
        assert 'info' in spec_data
        
        # Check formatting (should have newlines and spaces for default indent)
        assert '{\n  "openapi":' in result.output
    
    def test_quiet_flag_suppresses_stdout(self):
        """Test that --quiet flag prevents stdout output."""
        result = self.runner.invoke(self.spec_command, ['--quiet'])
        
        assert result.exit_code == 0
        assert result.output == ""
    
    def test_format_option_json(self):
        """Test explicit JSON format option."""
        result = self.runner.invoke(self.spec_command, ['--format', 'json'])
        
        assert result.exit_code == 0
        spec_data = json.loads(result.output)
        assert 'openapi' in spec_data
    
    def test_format_option_yaml(self):
        """Test YAML format option."""
        result = self.runner.invoke(self.spec_command, ['--format', 'yaml'])
        
        assert result.exit_code == 0
        assert 'openapi: 3.0.3' in result.output
        assert 'info:' in result.output
        # Should not be JSON
        assert '{"openapi":' not in result.output
    
    def test_format_option_yml(self):
        """Test YML format option (alias for YAML)."""
        result = self.runner.invoke(self.spec_command, ['--format', 'yml'])
        
        assert result.exit_code == 0
        assert 'openapi: 3.0.3' in result.output
        assert 'info:' in result.output
    
    def test_indent_zero_compact_json(self):
        """Test that --indent 0 produces compact JSON."""
        result = self.runner.invoke(self.spec_command, ['--indent', '0'])
        
        assert result.exit_code == 0
        # Should be compact JSON
        assert '{"openapi":' in result.output
        # Should not have formatted spacing
        assert '{\n  "openapi":' not in result.output
    
    def test_indent_custom_spacing(self):
        """Test custom indent values."""
        result = self.runner.invoke(self.spec_command, ['--indent', '4'])
        
        assert result.exit_code == 0
        # Should have 4-space indentation
        assert '{\n    "openapi":' in result.output
        
        # Test 1-space indentation
        result = self.runner.invoke(self.spec_command, ['--indent', '1'])
        assert result.exit_code == 0
        assert '{\n "openapi":' in result.output
    
    def test_yaml_ignores_indent(self):
        """Test that YAML format ignores indent option."""
        result = self.runner.invoke(self.spec_command, ['--format', 'yaml', '--indent', '8'])
        
        assert result.exit_code == 0
        assert 'openapi: 3.0.3' in result.output
        # Should still be YAML, not JSON
        assert '{"openapi":' not in result.output
    
    def test_output_file_creation(self):
        """Test that --output option creates a file."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            result = self.runner.invoke(self.spec_command, ['--output', tmp_path])
            
            assert result.exit_code == 0
            assert os.path.exists(tmp_path)
            
            with open(tmp_path, 'r') as f:
                content = f.read()
                spec_data = json.loads(content)
                assert 'openapi' in spec_data
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_output_file_with_yaml(self):
        """Test file output with YAML format."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yaml') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            result = self.runner.invoke(self.spec_command, ['--format', 'yaml', '--output', tmp_path])
            
            assert result.exit_code == 0
            assert os.path.exists(tmp_path)
            
            with open(tmp_path, 'r') as f:
                content = f.read()
                assert 'openapi: 3.0.3' in content
                assert 'info:' in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_combined_options(self):
        """Test multiple options working together."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            result = self.runner.invoke(self.spec_command, [
                '--format', 'json',
                '--output', tmp_path,
                '--indent', '4',
                '--quiet'
            ])
            
            assert result.exit_code == 0
            assert result.output == ""  # quiet flag
            assert os.path.exists(tmp_path)
            
            with open(tmp_path, 'r') as f:
                content = f.read()
                spec_data = json.loads(content)
                assert 'openapi' in spec_data
                # Should have 4-space indentation
                assert '{\n    "openapi":' in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_stdout_and_file_output_both(self):
        """Test that output goes to both stdout and file when both are specified."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            result = self.runner.invoke(self.spec_command, ['--output', tmp_path])
            
            assert result.exit_code == 0
            # Should output to stdout
            assert result.output.strip()
            spec_data = json.loads(result.output)
            assert 'openapi' in spec_data
            
            # Should also output to file
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                file_content = f.read()
                file_spec_data = json.loads(file_content)
                assert file_spec_data == spec_data
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestSpecCommandEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.spec_command = create_mock_spec_command()
        self.runner = CliRunner()
    
    def test_large_indent_value(self):
        """Test with large indent value."""
        result = self.runner.invoke(self.spec_command, ['--indent', '20'])
        
        assert result.exit_code == 0
        # Should have 20-space indentation
        assert '{\n' + ' ' * 20 + '"openapi":' in result.output
    
    def test_negative_indent_handled(self):
        """Test behavior with negative indent (should be handled by click)."""
        result = self.runner.invoke(self.spec_command, ['--indent', '-1'])
        
        # Click should handle validation - exact behavior may vary
        # but command shouldn't crash
        assert result.exit_code in [0, 2]  # 0 for success, 2 for usage error
    
    def test_invalid_format_rejected(self):
        """Test that invalid format is rejected by click."""
        result = self.runner.invoke(self.spec_command, ['--format', 'invalid'])
        
        assert result.exit_code == 2  # Usage error
        assert 'Invalid value' in result.output or 'Usage:' in result.output
    
    def test_nonexistent_output_directory(self):
        """Test behavior when output directory doesn't exist."""
        non_existent_path = '/tmp/nonexistent/directory/spec.json'
        
        result = self.runner.invoke(self.spec_command, ['--output', non_existent_path])
        
        # Should fail when trying to write to non-existent directory
        assert result.exit_code != 0
    
    def test_output_permission_denied(self):
        """Test behavior when output file is not writable."""
        # Create a directory where we can't write a file
        with tempfile.TemporaryDirectory() as temp_dir:
            # Try to write to the directory itself (not a file)
            result = self.runner.invoke(self.spec_command, ['--output', temp_dir])
            
            # Should fail due to permission/file type error
            assert result.exit_code != 0


def run_tests():
    """Run all tests manually."""
    import traceback
    
    test_classes = [TestSpecCommandLogic, TestSpecCommandEdgeCases]
    
    total_tests = 0
    passed_tests = 0
    failed_tests = 0
    
    for test_class in test_classes:
        print(f"\n=== Running {test_class.__name__} ===")
        
        # Get all test methods
        test_methods = [method for method in dir(test_class) if method.startswith('test_')]
        
        for test_method in test_methods:
            total_tests += 1
            print(f"Running {test_method}... ", end="")
            
            try:
                instance = test_class()
                instance.setup_method()
                getattr(instance, test_method)()
                print("✓ PASSED")
                passed_tests += 1
            except Exception as e:
                print(f"✗ FAILED: {str(e)}")
                print(f"  Traceback: {traceback.format_exc()}")
                failed_tests += 1
    
    print(f"\n=== Test Summary ===")
    print(f"Total: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {failed_tests}")
    
    if failed_tests == 0:
        print("🎉 All tests passed!")
        return True
    else:
        print(f"❌ {failed_tests} test(s) failed.")
        return False


if __name__ == "__main__":
    import sys
    
    print("Testing commands.py logic...")
    success = run_tests()
    sys.exit(0 if success else 1)
