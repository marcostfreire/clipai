"""Test configuration and fixtures."""

import pytest
import os
import sys

# Add parent directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    """Setup test environment variables."""
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
    os.environ["REDIS_URL"] = "redis://localhost:6379/1"
    os.environ["GEMINI_API_KEY"] = "test_key"
    os.environ["STORAGE_PATH"] = "./test_storage"
    os.environ["DEBUG"] = "true"
