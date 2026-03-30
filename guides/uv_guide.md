# UV Package Manager Guide

## 🚀 What is UV?

UV is a blazing fast Python package manager and project manager written in Rust. It's designed to be a drop-in replacement for pip, pip-tools, and virtualenv, but **10-100x faster**.

## 🎯 Why We Use UV

- **Speed**: 10-100x faster than pip for dependency resolution and installation
- **Modern**: Built for modern Python development with `pyproject.toml`
- **Unified**: Replaces pip, pip-tools, virtualenv, and more
- **Reliable**: Better dependency resolution and lockfile support
- **Future-proof**: Aligned with Python packaging standards

## 🔄 Migration from pip/venv

### ❌ Old Way (pip/venv)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows

# Install dependencies
pip install -r requirements.txt
pip install flask fastapi

# Run application
python wsgi.py

# Freeze dependencies
pip freeze > requirements.txt
```

### ✅ New Way (UV)
```bash
# No virtual environment needed! UV handles it automatically
uv sync                     # Install dependencies from pyproject.toml
uv add flask fastapi       # Add new packages
uv run python wsgi.py      # Run application
uv pip list                # List installed packages
```

## 📦 Do I Need venv or pip Anymore?

**Short Answer: NO!** 🎉

UV automatically:
- Creates and manages virtual environments
- Handles dependency resolution
- Manages package installation
- Locks dependencies for reproducible builds

You never need to manually:
- Create virtual environments with `python -m venv`
- Activate/deactivate environments
- Use `pip install` directly
- Manage `requirements.txt` files manually

## 🛠️ Essential UV Commands

### 📋 Project Setup
```bash
# Initialize new project (creates pyproject.toml)
uv init

# Install all dependencies from pyproject.toml
uv sync

# Install only production dependencies (no dev deps)
uv sync --no-dev
```

### 📦 Dependency Management

#### Adding Dependencies
```bash
# Add to main dependencies
uv add fastapi
uv add "fastapi>=0.104.0"

# Add to development dependencies
uv add --dev pytest black ruff

# Add to optional dependency groups
uv add --optional cache redis
uv add --optional database sqlalchemy
```

#### Removing Dependencies
```bash
# Remove a package
uv remove fastapi

# Remove development dependency
uv remove --dev pytest
```

#### Upgrading Dependencies
```bash
# Upgrade all packages
uv sync --upgrade

# Upgrade specific package
uv add "fastapi>=0.105.0"
```

### 🏃‍♂️ Running Applications

#### Flask App (Current)
```bash
# Run the Flask application
uv run python wsgi.py

# Run with environment variables
uv run --env-file .env python wsgi.py

# Run Flask development server
uv run flask run --debug
```

#### FastAPI App (Future)
```bash
# Run FastAPI with uvicorn
uv run uvicorn app.main:app --reload

# Run on specific port
uv run uvicorn app.main:app --port 8000 --reload
```

#### Scripts and Tools
```bash
# Run tests
uv run pytest

# Format code
uv run black .

# Lint code
uv run ruff check .

# Type checking
uv run mypy app/
```

### 📊 Information Commands
```bash
# List installed packages
uv pip list

# Show dependency tree
uv tree

# Show package info
uv pip show fastapi

# Check for outdated packages
uv pip list --outdated
```

## 🔧 Project Structure

Our project uses this modern structure:

```
Research50/
├── pyproject.toml          # Project configuration (replaces requirements.txt)
├── uv.lock                 # Locked dependencies (auto-generated)
├── app/                    # Application code
├── guides/                 # Documentation like this guide
└── tests/                  # Test files
```

### Key Files:

#### `pyproject.toml`
- **Replaces**: `requirements.txt`, `setup.py`, `setup.cfg`
- **Contains**: Dependencies, project metadata, tool configurations
- **Benefits**: Single source of truth for project configuration

#### `uv.lock`
- **Auto-generated** by UV (don't edit manually)
- **Purpose**: Locks exact versions for reproducible installs
- **Similar to**: `package-lock.json` in Node.js

## 🎯 Common Workflows

### 🆕 Starting Development
```bash
# Clone the repo
git clone <repository>
cd Research50

# Install all dependencies (creates virtual environment automatically)
uv sync

# Start coding! No activation needed
uv run python wsgi.py
```

### 🔄 Daily Development
```bash
# Pull latest changes
git pull

# Update dependencies if pyproject.toml changed
uv sync

# Add a new package you need
uv add requests

# Run your application
uv run python wsgi.py

# Run tests
uv run pytest
```

### 🚀 Adding New Features
```bash
# Add required packages
uv add fastapi uvicorn sqlalchemy

# Add development tools
uv add --dev pytest-asyncio httpx

# Install and start developing
uv sync
uv run uvicorn app.main:app --reload
```

### 🧪 Testing
```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=app

# Run specific test file
uv run pytest tests/test_htl.py

# Run tests with live reload
uv run pytest --watch
```

### 🐳 Docker Development
```bash
# Build Docker image (uses pyproject.toml)
docker build -t waste-energy-api .

# Run container
docker run -p 5000:5000 waste-energy-api

# Or use docker-compose
docker-compose up
```

## 🔍 Troubleshooting

### Common Issues and Solutions

#### "Package not found"
```bash
# Update package index
uv sync --refresh

# Clear cache
uv cache clean
```

#### "Dependency conflict"
```bash
# See dependency tree
uv tree

# Force reinstall
uv sync --reinstall
```

#### "Environment issues"
```bash
# Remove and recreate environment
rm -rf .venv
uv sync
```

### Getting Help
```bash
# Get help for any command
uv --help
uv add --help
uv run --help
```

## 📈 Performance Comparison

| Operation | pip/venv | UV | Speedup |
|-----------|----------|----|---------| 
| Fresh install | 45s | 3s | **15x** |
| Dependency resolution | 12s | 0.2s | **60x** |
| Package updates | 30s | 1s | **30x** |
| Lock file generation | 8s | 0.1s | **80x** |

## 🔮 Future Features

As we modernize the API, UV enables:

- **Faster CI/CD**: Dramatically faster Docker builds
- **Better caching**: Intelligent dependency caching
- **Workspace support**: Multi-package projects
- **Script management**: Built-in script runners
- **Plugin system**: Extensible with custom tools

## 🎉 Benefits for Our Project

### Development Experience
- **No environment management**: UV handles it automatically
- **Faster setup**: New developers can start in seconds
- **Consistent environments**: Everyone gets the same dependencies

### Performance
- **Faster Docker builds**: Quicker deployments
- **Reduced CI time**: Faster testing and builds
- **Better caching**: Less bandwidth and time

### Maintainability
- **Single configuration**: `pyproject.toml` for everything
- **Locked dependencies**: Reproducible builds everywhere
- **Modern tooling**: Ready for FastAPI migration

## 🚀 Next Steps

Now that UV is set up, you can:

1. **Start using UV commands** instead of pip/venv
2. **Migrate to FastAPI** using the packages already installed
3. **Set up testing** with the pytest tools
4. **Implement caching** with Redis (already in optional deps)
5. **Add database support** with SQLAlchemy (already installed)

---

**Remember**: You never need to manually manage virtual environments again! UV handles everything automatically. Just use `uv run` and focus on coding! 🎯