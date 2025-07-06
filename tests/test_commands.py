"""Unit tests for commands.py functionality.

This module tests the OpenAPI 'spec' command's option handling and functionality,
including default behavior, custom configuration, and file output operations.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest
from click.testing import CliRunner

from apiflask import APIFlask
from apiflask.commands import spec_command
from tests.schemas import Foo, Bar, Query


@pytest.fixture
def test_app():
    """Create a test app with some basic routes and schemas."""
    app = APIFlask(__name__)
    app.config['TESTING'] = True
    
    # Add some test routes to generate meaningful OpenAPI spec
    @app.get('/users')
    @app.output(Foo)
    def get_users():
        """Get all users."""
        return {'id': 1, 'name': 'test'}
    
    @app.post('/users')
    @app.input(Foo)
    @app.output(Bar)
    def create_user(data):
        """Create a new user."""
        return {'id2': 2, 'name2': 'new_user'}
    
    @app.get('/users/<int:user_id>')
    @app.input(Query, location='query')
    @app.output(Foo)
    def get_user(user_id, query_data):
        """Get a specific user."""
        return {'id': user_id, 'name': 'user'}
    
    return app


class TestSpecCommandDefaults:
    """Test spec command with default configurations."""
    
    def test_default_format_json(self, test_app):
        """Test that default format is JSON as configured in settings."""
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command, ['--quiet'])
        
        assert result.exit_code == 0
        # Should not output anything to stdout when quiet flag is used
        assert result.output == ''
    
    def test_default_format_json_output(self, test_app):
        """Test default JSON format output to stdout."""
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command)
        
        assert result.exit_code == 0
        # Output should be valid JSON
        spec_data = json.loads(result.output)
        assert 'openapi' in spec_data
        assert 'info' in spec_data
        assert 'paths' in spec_data
        # Check that our test endpoints are included
        assert '/users' in spec_data['paths']
        assert '/users/{user_id}' in spec_data['paths']
    
    def test_default_indent_applied(self, test_app):
        """Test that default JSON indentation (2) is applied."""
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command)
        
        assert result.exit_code == 0
        # Should contain indented JSON (2 spaces by default)
        assert '{\n  "openapi":' in result.output
        # Should not be single-line JSON
        assert '{"openapi":' not in result.output
    
    def test_config_spec_format_used(self, test_app):
        """Test that SPEC_FORMAT config is respected when no format option provided."""
        # Test with default JSON
        assert test_app.config['SPEC_FORMAT'] == 'json'
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command)
        
        # Should be JSON format
        spec_data = json.loads(result.output)
        assert isinstance(spec_data, dict)
        
        # Test with YAML format
        test_app.config['SPEC_FORMAT'] = 'yaml'
        result = runner.invoke(spec_command)
        
        # Should be YAML format
        assert 'openapi:' in result.output
        assert 'info:' in result.output
        # Should not be JSON
        assert '{"openapi":' not in result.output


class TestSpecCommandCustomOptions:
    """Test spec command with custom option values."""
    
    @pytest.mark.parametrize('format_option', ['json', 'yaml', 'yml'])
    def test_format_option_override(self, test_app, format_option):
        """Test that --format option overrides config SPEC_FORMAT."""
        # Set config to different format
        test_app.config['SPEC_FORMAT'] = 'yaml' if format_option == 'json' else 'json'
        
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command, ['--format', format_option])
        
        assert result.exit_code == 0
        
        if format_option == 'json':
            # Should be JSON despite config being yaml
            spec_data = json.loads(result.output)
            assert isinstance(spec_data, dict)
            assert 'openapi' in spec_data
        else:  # yaml or yml
            # Should be YAML despite config being json
            assert 'openapi:' in result.output
            assert 'info:' in result.output
            # Should not be JSON format
            assert '{"openapi":' not in result.output
    
    @pytest.mark.parametrize('indent_value', [0, 1, 4, 8])
    def test_indent_option_override(self, test_app, indent_value):
        """Test that --indent option overrides config LOCAL_SPEC_JSON_INDENT."""
        # Set config to different indent
        test_app.config['LOCAL_SPEC_JSON_INDENT'] = 2 if indent_value != 2 else 4
        
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command, ['--format', 'json', '--indent', str(indent_value)])
        
        assert result.exit_code == 0
        
        if indent_value == 0:
            # Should be compact JSON
            assert '{"info": {' in result.output or '{"openapi":' in result.output
        else:
            # Should have proper indentation
            expected_start = f'{{\n{" " * indent_value}"'
            assert expected_start in result.output
    
    def test_quiet_flag_suppresses_stdout(self, test_app):
        """Test that --quiet flag suppresses output to stdout."""
        runner = test_app.test_cli_runner()
        
        # Without quiet flag
        result_normal = runner.invoke(spec_command)
        assert result_normal.exit_code == 0
        assert len(result_normal.output) > 0
        
        # With quiet flag
        result_quiet = runner.invoke(spec_command, ['--quiet'])
        assert result_quiet.exit_code == 0
        assert result_quiet.output == ''
    
    def test_output_option_file_creation(self, test_app):
        """Test that --output option creates file with spec content."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            runner = test_app.test_cli_runner()
            result = runner.invoke(spec_command, ['--output', tmp_path, '--format', 'json'])
            
            assert result.exit_code == 0
            
            # Check that file was created and contains valid spec
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                content = f.read()
                spec_data = json.loads(content)
                assert 'openapi' in spec_data
                assert 'paths' in spec_data
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestSpecCommandConfigIntegration:
    """Test spec command integration with various config options."""
    
    def test_local_spec_path_config_used(self, test_app):
        """Test that LOCAL_SPEC_PATH config is used when no --output provided."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            # Set config to use temp file
            test_app.config['LOCAL_SPEC_PATH'] = tmp_path
            
            runner = test_app.test_cli_runner()
            result = runner.invoke(spec_command, ['--quiet'])  # quiet to avoid stdout
            
            assert result.exit_code == 0
            
            # Check that file was created using config path
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                content = f.read()
                spec_data = json.loads(content)
                assert 'openapi' in spec_data
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
    
    def test_local_spec_json_indent_config_used(self, test_app):
        """Test that LOCAL_SPEC_JSON_INDENT config affects JSON formatting."""
        # Test with indent 4
        test_app.config['LOCAL_SPEC_JSON_INDENT'] = 4
        
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command, ['--format', 'json'])
        
        assert result.exit_code == 0
        # Should have 4-space indentation
        assert f'{{\n{"    "}"openapi":' in result.output
        
        # Test with indent 0 (compact)
        test_app.config['LOCAL_SPEC_JSON_INDENT'] = 0
        
        result = runner.invoke(spec_command, ['--format', 'json'])
        assert result.exit_code == 0
        # Should be compact JSON
        assert '{"openapi":' in result.output
    
    def test_spec_format_yaml_with_output_file(self, test_app):
        """Test YAML format with file output."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yaml') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            test_app.config['SPEC_FORMAT'] = 'yaml'
            
            runner = test_app.test_cli_runner()
            result = runner.invoke(spec_command, ['--output', tmp_path])
            
            assert result.exit_code == 0
            
            # Check file content is YAML
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                content = f.read()
                assert 'openapi:' in content
                assert 'info:' in content
                assert 'paths:' in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestSpecCommandEdgeCases:
    """Test edge cases and error conditions."""
    
    def test_zero_indent_explicit_vs_none(self, test_app):
        """Test difference between explicit 0 indent and None indent."""
        runner = test_app.test_cli_runner()
        
        # Explicit 0 should create compact JSON
        result_zero = runner.invoke(spec_command, ['--indent', '0'])
        assert result_zero.exit_code == 0
        assert '{"info": {' in result_zero.output or '{"openapi":' in result_zero.output
        
        # Default config indent should create formatted JSON
        test_app.config['LOCAL_SPEC_JSON_INDENT'] = 2
        result_default = runner.invoke(spec_command)
        assert result_default.exit_code == 0
        assert f'{{\n  "' in result_default.output
    
    def test_yaml_with_indent_option(self, test_app):
        """Test that indent option doesn't affect YAML output."""
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command, ['--format', 'yaml', '--indent', '8'])
        
        assert result.exit_code == 0
        # Should still be YAML format regardless of indent option
        assert 'openapi:' in result.output
        assert 'info:' in result.output
        # Should not be JSON
        assert '{"openapi":' not in result.output
    
    def test_output_without_path_uses_none(self, test_app):
        """Test behavior when LOCAL_SPEC_PATH is None."""
        # Set LOCAL_SPEC_PATH to None
        test_app.config['LOCAL_SPEC_PATH'] = None
        
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command)
        
        assert result.exit_code == 0
        # Should output to stdout only, no file created
        assert 'openapi' in result.output
    
    def test_combined_options(self, test_app):
        """Test multiple options used together."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            runner = test_app.test_cli_runner()
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
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)


class TestSpecCommandSchemaContent:
    """Test that spec command properly handles schema content from test routes."""
    
    def test_schema_definitions_included(self, test_app):
        """Test that schemas from routes are included in spec."""
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command, ['--format', 'json'])
        
        assert result.exit_code == 0
        spec_data = json.loads(result.output)
        
        # Check that schema components are included
        assert 'components' in spec_data
        assert 'schemas' in spec_data['components']
        
        # Should include schemas used in our test routes
        schemas = spec_data['components']['schemas']
        schema_names = list(schemas.keys())
        
        # At minimum should have some schema definitions
        assert len(schema_names) > 0
    
    def test_paths_from_routes_included(self, test_app):
        """Test that paths from decorated routes are included."""
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command, ['--format', 'json'])
        
        assert result.exit_code == 0
        spec_data = json.loads(result.output)
        
        # Check our test endpoints
        paths = spec_data['paths']
        assert '/users' in paths
        assert '/users/{user_id}' in paths
        
        # Check HTTP methods
        assert 'get' in paths['/users']
        assert 'post' in paths['/users']
        assert 'get' in paths['/users/{user_id}']
    
    def test_operation_details_included(self, test_app):
        """Test that operation details like summaries and descriptions are included."""
        runner = test_app.test_cli_runner()
        result = runner.invoke(spec_command, ['--format', 'json'])
        
        assert result.exit_code == 0
        spec_data = json.loads(result.output)
        
        # Check operation details
        get_users = spec_data['paths']['/users']['get']
        assert 'summary' in get_users or 'description' in get_users
        
        post_users = spec_data['paths']['/users']['post']
        assert 'summary' in post_users or 'description' in post_users


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
