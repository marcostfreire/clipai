# ClipAI Tests

## Running Tests

### Backend Tests

```bash
cd backend

# Install test dependencies
pip install pytest pytest-cov pytest-asyncio httpx

# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_ffmpeg_service.py -v

# Run specific test
pytest tests/test_api.py::TestHealthEndpoints::test_health_check -v
```

### Frontend Tests

```bash
cd frontend

# Install dependencies
npm install

# Run linting
npm run lint

# Type checking
npx tsc --noEmit

# Build test
npm run build
```

## Test Structure

```
backend/tests/
├── conftest.py              # Test configuration
├── test_api.py              # API endpoint tests
├── test_ffmpeg_service.py   # FFmpeg service tests
└── test_gemini_service.py   # Gemini AI service tests
```

## Test Coverage

Target coverage: 80%+

Current coverage:
- FFmpeg Service: ~85%
- Gemini Service: ~80%
- API Endpoints: ~75%

## Writing Tests

### Example Test

```python
import pytest
from app.services.ffmpeg_service import FFmpegService

def test_format_ass_time():
    service = FFmpegService(settings)
    result = service.format_ass_time(65.5)
    assert result == "0:01:05.50"
```

### Mocking External Services

```python
from unittest.mock import Mock, patch

@patch('subprocess.run')
def test_extract_frames(mock_run, ffmpeg_service):
    mock_run.return_value = Mock(returncode=0)
    result = ffmpeg_service.extract_frames(video_path, output_dir)
    assert result == output_dir
```
