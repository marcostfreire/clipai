# Contributing to ClipAI

Thank you for considering contributing to ClipAI! This document provides guidelines and instructions for contributing.

## Code of Conduct

Be respectful, inclusive, and constructive in all interactions.

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in [Issues](../../issues)
2. If not, create a new issue with:
   - Clear title and description
   - Steps to reproduce
   - Expected vs actual behavior
   - Environment details (OS, Python/Node version)
   - Logs/screenshots if applicable

### Suggesting Features

1. Check if the feature has been suggested in [Issues](../../issues)
2. Create a new issue with:
   - Clear description of the feature
   - Use cases and benefits
   - Possible implementation approach
   - Examples from similar tools

### Submitting Pull Requests

1. **Fork the repository**

```bash
git clone https://github.com/yourusername/clipai.git
cd clipai
```

2. **Create a branch**

```bash
git checkout -b feature/amazing-feature
# or
git checkout -b fix/bug-description
```

3. **Make your changes**

Follow the coding standards below.

4. **Test your changes**

```bash
# Backend tests
cd backend
pytest

# Frontend build test
cd frontend
npm run build
```

5. **Commit your changes**

```bash
git commit -m "Add: Brief description of changes"
```

Use conventional commit messages:
- `Add:` - New feature
- `Fix:` - Bug fix
- `Update:` - Update existing feature
- `Refactor:` - Code refactoring
- `Docs:` - Documentation changes
- `Test:` - Adding tests
- `Style:` - Formatting changes

6. **Push to your fork**

```bash
git push origin feature/amazing-feature
```

7. **Create Pull Request**

- Go to the original repository
- Click "New Pull Request"
- Select your branch
- Fill in the PR template
- Link related issues

## Development Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or .\venv\Scripts\Activate.ps1 on Windows
pip install -r requirements.txt
pip install -r requirements-dev.txt  # Development dependencies
```

### Frontend

```bash
cd frontend
npm install
```

## Coding Standards

### Python (Backend)

- Follow PEP 8
- Use type hints
- Maximum line length: 100 characters
- Use docstrings for functions/classes
- Use meaningful variable names

```python
def process_video(video_id: int, options: dict) -> ProcessingResult:
    """
    Process a video to generate viral clips.
    
    Args:
        video_id: ID of the video to process
        options: Processing options
        
    Returns:
        ProcessingResult with clips and metadata
        
    Raises:
        ProcessingError: If processing fails
    """
    pass
```

Use **ruff** for linting:

```bash
pip install ruff
ruff check app/
```

### TypeScript (Frontend)

- Use TypeScript strict mode
- Use functional components with hooks
- Use meaningful component names
- Follow Airbnb style guide
- Maximum line length: 100 characters

```typescript
interface VideoCardProps {
  video: Video;
  onSelect: (id: number) => void;
}

export function VideoCard({ video, onSelect }: VideoCardProps) {
  // Component implementation
}
```

Use **ESLint**:

```bash
npm run lint
```

### Commit Messages

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
Add: Support for MP3 audio files
Fix: Video processing timeout issue
Update: Gemma integration
Docs: Add deployment guide
Test: Add FFmpeg service tests
```

### Branch Naming

- `feature/feature-name` - New features
- `fix/bug-description` - Bug fixes
- `refactor/what-changed` - Refactoring
- `docs/what-documented` - Documentation
- `test/what-tested` - Tests

## Testing

### Backend Tests

```bash
cd backend

# Run all tests
pytest

# Run specific test file
pytest tests/test_ffmpeg_service.py -v

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test
pytest tests/test_api.py::TestHealthEndpoints::test_health_check -v
```

Write tests for:
- New features
- Bug fixes
- Edge cases

Example test:

```python
def test_extract_frames(ffmpeg_service, test_video_path):
    """Test frame extraction from video."""
    output_dir = "/tmp/frames"
    result = ffmpeg_service.extract_frames(test_video_path, output_dir)
    
    assert result == output_dir
    assert os.path.exists(output_dir)
    assert len(os.listdir(output_dir)) > 0
```

### Frontend Tests

```bash
cd frontend

# Type checking
npx tsc --noEmit

# Linting
npm run lint

# Build test
npm run build
```

## Documentation

- Update README.md if adding features
- Add JSDoc/docstrings to new functions
- Update API documentation if changing endpoints
- Add comments for complex logic
- Update DEPLOYMENT.md for infrastructure changes

## Review Process

1. Code will be reviewed by maintainers
2. Address any feedback or requested changes
3. Once approved, PR will be merged
4. Your contribution will be credited

## Project Structure

```
clipai/
├── backend/
│   ├── app/
│   │   ├── api/          # API endpoints
│   │   ├── services/     # Business logic
│   │   ├── tasks/        # Celery tasks
│   │   ├── models.py     # Database models
│   │   └── schemas.py    # Pydantic schemas
│   ├── tests/            # Backend tests
│   └── requirements.txt  # Dependencies
├── frontend/
│   ├── app/              # Next.js app
│   ├── components/       # React components
│   ├── lib/              # Utilities
│   └── package.json      # Dependencies
└── docs/                 # Documentation
```

## Getting Help

- Open a [Discussion](../../discussions) for questions
- Join our Discord server: [link]
- Read the [Documentation](../../wiki)
- Check [existing issues](../../issues)

## Areas Needing Help

- [ ] Unit tests for video processor
- [ ] E2E tests with Playwright
- [ ] Performance optimization for large videos
- [ ] Support for more video formats
- [ ] Better error messages
- [ ] Internationalization (i18n)
- [ ] Dark mode for frontend
- [ ] Mobile app (React Native)

## Recognition

Contributors will be:
- Listed in CONTRIBUTORS.md
- Credited in release notes
- Given GitHub badges
- Mentioned on social media (with permission)

Thank you for contributing! 🎉
