"""
Integration tests for API endpoints.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import os

from app.main import app
from app.database import Base, get_db
from app.config import Settings


# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override database dependency."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="function")
def test_db():
    """Create test database."""
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(test_db):
    """Create test client."""
    return TestClient(app)


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_root_endpoint(self, client):
        """Test root endpoint."""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Welcome to ClipAI API"
        assert "version" in data

    def test_health_check(self, client):
        """Test basic health check."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_liveness_check(self, client):
        """Test liveness endpoint."""
        response = client.get("/health/live")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"


class TestVideoEndpoints:
    """Test video-related endpoints."""

    def test_upload_video_no_file(self, client):
        """Test upload without file."""
        response = client.post("/api/videos/upload")
        assert response.status_code == 422  # Validation error

    def test_upload_video_with_invalid_url(self, client):
        """Test upload with invalid YouTube URL via form field."""
        response = client.post(
            "/api/videos/upload", data={"url": "not_a_valid_url"}
        )
        assert response.status_code in [400, 422]

    def test_get_video_not_found(self, client):
        """Test getting non-existent video."""
        response = client.get("/api/videos/999")
        assert response.status_code == 404

    def test_delete_video_not_found(self, client):
        """Test deleting non-existent video."""
        response = client.delete("/api/videos/999")
        assert response.status_code == 404


class TestClipEndpoints:
    """Test clip-related endpoints."""

    def test_get_clips_for_nonexistent_video(self, client):
        """Test getting clips for non-existent video."""
        response = client.get("/api/videos/999/clips")
        assert response.status_code == 404

    def test_get_clip_not_found(self, client):
        """Test getting non-existent clip."""
        response = client.get("/api/clips/999")
        assert response.status_code == 404

    def test_download_clip_not_found(self, client):
        """Test downloading non-existent clip."""
        response = client.get("/api/clips/999/download")
        assert response.status_code == 404


class TestCORS:
    """Test CORS configuration."""

    def test_cors_headers(self, client):
        """Test CORS headers are present."""
        response = client.options(
            "/api/videos/upload", headers={"Origin": "http://localhost:3000"}
        )
        assert response.status_code == 200
        assert "access-control-allow-origin" in response.headers


class TestErrorHandling:
    """Test error handling."""

    def test_404_error(self, client):
        """Test 404 error for non-existent route."""
        response = client.get("/nonexistent/route")
        assert response.status_code == 404

    def test_method_not_allowed(self, client):
        """Test method not allowed."""
        response = client.post("/health")
        assert response.status_code == 405
