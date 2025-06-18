"""Test that imports work correctly after reorganization."""

import unittest
import sys
import os

# Add project root to path for testing
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

class TestImports(unittest.TestCase):
    """Test that all imports work correctly."""
    
    def test_config_manager_import(self):
        """Test that ConfigManager can be imported."""
        from orchestrator.core.config_manager import ConfigManager
        self.assertTrue(ConfigManager)
    
    def test_web_app_import(self):
        """Test that web app can be imported."""
        from orchestrator.web.app import create_app
        self.assertTrue(create_app)
    
    def test_config_settings_import(self):
        """Test that config settings can be imported."""
        from config.settings import PROJECT_ROOT
        self.assertTrue(PROJECT_ROOT)

if __name__ == '__main__':
    unittest.main()