"""Integration test for spec command that works with existing APIFlask test structure.

This test module is designed to work within the APIFlask test suite and uses
the existing test infrastructure and schemas.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

# Note: This test assumes it's run within the APIFlask test environment
# and can import from the main apiflask package and test schemas


class TestSpecCommand:
    """Test the spec CLI command functionality."""

    def test_spec_command_default_behavior(self, app, cli_runner):
        """Test spec command with default configuration."""
        # Use default configuration
        result = cli_runner.invoke("spec")
        
        assert result.exit_code == 0
        # Should output JSON by default
        spec_data = json.loads(result.output)
        assert "openapi" in spec_data
        assert "info" in spec_data
        # Should have default indentation (not compact)
        assert '{\n  "openapi":' in result.output or '{\n  "info":' in result.output

    def test_spec_command_quiet_flag(self, app, cli_runner):
        """Test that --quiet suppresses stdout output."""
        result = cli_runner.invoke("spec", ["--quiet"])
        
        assert result.exit_code == 0
        assert result.output == ""

    def test_spec_command_format_json(self, app, cli_runner):
        """Test explicit JSON format."""
        result = cli_runner.invoke("spec", ["--format", "json"])
        
        assert result.exit_code == 0
        spec_data = json.loads(result.output)
        assert "openapi" in spec_data

    def test_spec_command_format_yaml(self, app, cli_runner):
        """Test YAML format output."""
        result = cli_runner.invoke("spec", ["--format", "yaml"])
        
        assert result.exit_code == 0
        assert "openapi:" in result.output
        assert "info:" in result.output
        # Should not be JSON
        assert '{"openapi":' not in result.output

    def test_spec_command_format_yml(self, app, cli_runner):
        """Test YML format (alias for YAML)."""
        result = cli_runner.invoke("spec", ["--format", "yml"])
        
        assert result.exit_code == 0
        assert "openapi:" in result.output
        # Should not be JSON
        assert '{"openapi":' not in result.output

    def test_spec_command_indent_zero(self, app, cli_runner):
        """Test compact JSON with --indent 0."""
        result = cli_runner.invoke("spec", ["--indent", "0"])
        
        assert result.exit_code == 0
        # Should be compact JSON (no pretty printing)
        assert '{"openapi":' in result.output or '{"info":' in result.output
        # Should not have formatted indentation
        assert '{\n  "' not in result.output

    def test_spec_command_custom_indent(self, app, cli_runner):
        """Test custom indentation values."""
        result = cli_runner.invoke("spec", ["--indent", "4"])
        
        assert result.exit_code == 0
        # Should have 4-space indentation
        assert '{\n    "' in result.output

        # Test single space
        result = cli_runner.invoke("spec", ["--indent", "1"])
        assert result.exit_code == 0
        assert '{\n "' in result.output

    def test_spec_command_yaml_ignores_indent(self, app, cli_runner):
        """Test that YAML format ignores indent option."""
        result = cli_runner.invoke("spec", ["--format", "yaml", "--indent", "8"])
        
        assert result.exit_code == 0
        # Should still be YAML
        assert "openapi:" in result.output
        assert '{"openapi":' not in result.output

    def test_spec_command_output_file(self, app, cli_runner):
        """Test file output with --output option."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name

        try:
            result = cli_runner.invoke("spec", ["--output", tmp_path])
            
            assert result.exit_code == 0
            # Should still output to stdout
            spec_data = json.loads(result.output)
            assert "openapi" in spec_data
            
            # Should also create file
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                file_content = f.read()
                file_spec = json.loads(file_content)
                assert file_spec == spec_data
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_spec_command_output_yaml_file(self, app, cli_runner):
        """Test YAML file output."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.yaml') as tmp_file:
            tmp_path = tmp_file.name

        try:
            result = cli_runner.invoke("spec", ["--format", "yaml", "--output", tmp_path])
            
            assert result.exit_code == 0
            assert "openapi:" in result.output
            
            # Check file content
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                content = f.read()
                assert "openapi:" in content
                assert "info:" in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_spec_command_combined_options(self, app, cli_runner):
        """Test multiple options combined."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name

        try:
            result = cli_runner.invoke("spec", [
                "--format", "json",
                "--output", tmp_path,
                "--indent", "4",
                "--quiet"
            ])
            
            assert result.exit_code == 0
            # Should be quiet (no stdout)
            assert result.output == ""
            
            # Should create file with 4-space indentation
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                content = f.read()
                spec_data = json.loads(content)
                assert "openapi" in spec_data
                # Check indentation
                assert '{\n    "' in content
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_spec_command_config_override(self, app, cli_runner):
        """Test that command options override app config."""
        # Set app config to YAML
        app.config['SPEC_FORMAT'] = 'yaml'
        app.config['LOCAL_SPEC_JSON_INDENT'] = 0
        
        # Use JSON format option to override
        result = cli_runner.invoke("spec", ["--format", "json", "--indent", "2"])
        
        assert result.exit_code == 0
        # Should be JSON despite config being YAML
        spec_data = json.loads(result.output)
        assert "openapi" in spec_data
        # Should have 2-space indentation despite config being 0
        assert '{\n  "' in result.output

    def test_spec_command_uses_config_defaults(self, app, cli_runner):
        """Test that config values are used when options not provided."""
        # Set specific config values
        app.config['SPEC_FORMAT'] = 'yaml'
        app.config['LOCAL_SPEC_JSON_INDENT'] = 4
        
        result = cli_runner.invoke("spec")
        
        assert result.exit_code == 0
        # Should use YAML from config
        assert "openapi:" in result.output
        assert '{"openapi":' not in result.output

    def test_spec_command_invalid_format(self, cli_runner):
        """Test error handling for invalid format."""
        result = cli_runner.invoke("spec", ["--format", "invalid"])
        
        # Should fail with usage error
        assert result.exit_code == 2
        assert "Invalid value" in result.output or "Usage:" in result.output

    def test_spec_command_with_routes_and_schemas(self, app, cli_runner):
        """Test spec generation with actual routes and schemas."""
        from tests.schemas import Foo, Bar
        
        # Add test routes
        @app.get('/test-users')
        @app.output(Foo)
        def get_test_users():
            return {'id': 1, 'name': 'test'}
        
        @app.post('/test-users')
        @app.input(Foo)
        @app.output(Bar)
        def create_test_user(data):
            return {'id2': 2, 'name2': 'created'}
        
        result = cli_runner.invoke("spec", ["--format", "json"])
        
        assert result.exit_code == 0
        spec_data = json.loads(result.output)
        
        # Should include our test routes
        assert "paths" in spec_data
        paths = spec_data["paths"]
        assert any("/test-users" in path for path in paths.keys())
        
        # Should include schema components
        if "components" in spec_data and "schemas" in spec_data["components"]:
            schemas = spec_data["components"]["schemas"]
            # May include Foo and Bar schemas
            assert len(schemas) > 0

    def test_spec_command_local_spec_path_config(self, app, cli_runner):
        """Test LOCAL_SPEC_PATH config usage."""
        with tempfile.NamedTemporaryFile(mode='w+', delete=False, suffix='.json') as tmp_file:
            tmp_path = tmp_file.name

        try:
            # Set config to use temp file
            app.config['LOCAL_SPEC_PATH'] = tmp_path
            
            result = cli_runner.invoke("spec", ["--quiet"])
            
            assert result.exit_code == 0
            assert result.output == ""  # quiet mode
            
            # Should create file at config path
            assert os.path.exists(tmp_path)
            with open(tmp_path, 'r') as f:
                content = f.read()
                spec_data = json.loads(content)
                assert "openapi" in spec_data
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
