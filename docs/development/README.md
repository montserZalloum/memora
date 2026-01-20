# Memora Development Guide

Complete guide for setting up and developing the Memora application.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Development Setup](#development-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Code Style Guidelines](#code-style-guidelines)
- [Testing](#testing)
- [Debugging](#debugging)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Prerequisites

### System Requirements

- **Operating System**: Linux, macOS, or Windows with WSL
- **Python**: 3.11 or higher
- **Node.js**: 16.x or higher (for frontend tools)
- **PostgreSQL**: 14.x or higher
- **Redis**: 6.x or higher
- **Git**: Latest version

### Software Requirements

- **Bench**: Frappe bench CLI tool
- **Frappe Framework**: v15 or higher
- **Python Packages**: See `pyproject.toml`
- **Node Packages**: See `package.json` (if applicable)

### Hardware Requirements

- **RAM**: Minimum 4GB, Recommended 8GB+
- **Disk Space**: Minimum 20GB free space
- **CPU**: 2+ cores recommended

## Installation

### Step 1: Install Bench

```bash
# Clone bench repository
git clone https://github.com/frappe/bench ~/bench-repo

# Install bench
cd ~/bench-repo
sudo python3 install.py --user

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH=$PATH:~/.local/bin
```

### Step 2: Create New Bench

```bash
# Create a new bench
bench init my-bench --frappe-branch version-15

cd my-bench
```

### Step 3: Install Memora

```bash
# Get the app
bench get-app https://github.com/your-org/memora --branch develop

# Install the app
bench install-app memora
```

### Step 4: Configure Redis

Edit `sites/common_site_config.json`:

```json
{
  "redis_cache": "redis://localhost:13000",
  "srs_redis_cache": "redis://localhost:13000"
}
```

### Step 5: Start Services

```bash
# Start Redis
redis-server --port 13000

# Start Frappe development server
bench start
```

## Development Setup

### Initial Setup

```bash
# Navigate to bench directory
cd ~/my-bench

# Switch to development site
bench use site1.local

# Enable developer mode
bench set-config developer_mode 1

# Clear cache
bench clear-cache
```

### Pre-commit Hooks

Install pre-commit hooks for code quality:

```bash
cd apps/memora
pre-commit install
```

Pre-commit tools configured:
- **ruff**: Python linting and formatting
- **eslint**: JavaScript linting
- **prettier**: Code formatting
- **pyupgrade**: Python syntax modernization

### Database Setup

```bash
# Create database (if not exists)
bench new-site site1.local --db-root-user root --db-root-password yourpassword

# Install memora on site
bench --site site1.local install-app memora

# Run migrations
bench --site site1.local migrate
```

### Running Benchmarks

```bash
# Run performance tests
cd apps/memora
pytest memora/tests/performance_test.py
```

## Project Structure

```
memora/
├── api/                    # API endpoints (modular)
│   ├── __init__.py        # Public API gateway
│   ├── utils.py           # Shared utilities
│   ├── subjects.py        # Subjects & tracks
│   ├── map_engine.py      # Learning map
│   ├── sessions.py        # Gameplay sessions
│   ├── reviews.py         # Review sessions (SRS)
│   ├── srs.py            # SRS admin endpoints
│   ├── profile.py         # Player profiles
│   ├── quests.py          # Daily quests
│   ├── leaderboard.py     # Leaderboards
│   ├── onboarding.py      # User onboarding
│   └── store.py         # In-app store
├── services/              # Business logic services
│   ├── srs_redis_manager.py      # Redis operations
│   ├── srs_persistence.py        # Async DB writes
│   ├── srs_archiver.py           # Season archival
│   ├── srs_reconciliation.py     # Cache consistency
│   └── partition_manager.py      # DB partitioning
├── memora/doctype/         # Frappe DocTypes
│   ├── player_profile/
│   ├── player_memory_tracker/
│   ├── gameplay_session/
│   ├── game_subject/
│   ├── game_topic/
│   ├── game_lesson/
│   └── ...
├── patches/                # Database migrations
│   └── v1_0/
│       ├── setup_partitioning.py
│       └── fix_null_seasons.py
├── tests/                  # Test suite
│   ├── test_srs_archiver.py
│   ├── test_srs_redis.py
│   ├── test_srs_reconciliation.py
│   └── performance_test.py
├── public/                 # Static assets
│   ├── js/
│   ├── css/
│   └── images/
├── templates/              # Jinja templates
├── config/                # Configuration files
├── setup_folder/          # Setup scripts
│   └── infrastructure.py
├── hooks.py              # Frappe hooks
├── setup.py              # Python package setup
├── pyproject.toml       # Python dependencies
└── README.md            # App documentation
```

## Development Workflow

### Creating a New Feature

1. **Create Feature Branch**
   ```bash
   bench switch-to-branch feature/my-new-feature
   ```

2. **Make Changes**
   - Edit files in appropriate modules
   - Follow code style guidelines
   - Write tests for new functionality

3. **Run Tests**
   ```bash
   # Run all tests
   bench --site site1.local run-tests --app memora

   # Run specific test file
   cd apps/memora
   pytest memora/tests/test_srs_archiver.py
   ```

4. **Run Pre-commit**
   ```bash
   cd apps/memora
   pre-commit run --all-files
   ```

5. **Commit Changes**
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```

6. **Push and Create PR**
   ```bash
   git push origin feature/my-new-feature
   ```

### Adding New API Endpoint

1. **Choose Module**: Select appropriate API module (e.g., `subjects.py`)

2. **Add Function**:
   ```python
   @frappe.whitelist()
   def my_new_endpoint(param1, param2):
       """My new endpoint documentation"""
       try:
           # Your logic here
           return {"status": "success", "data": result}
       except Exception as e:
           frappe.log_error(str(e), "my_new_endpoint")
           frappe.throw(str(e))
   ```

3. **Export in `__init__.py`**:
   ```python
   from .my_module import my_new_endpoint
   ```

4. **Write Tests**: Create test file in `tests/`

5. **Update Documentation**: Update API documentation

### Adding New DocType

1. **Create DocType Directory**:
   ```bash
   bench --site site1.local make-doctype "My New DocType" memora
   ```

2. **Define Fields**: Edit JSON file

3. **Add Controller Logic**: Edit Python file

4. **Create Tests**: Create test file

5. **Run Migration**:
   ```bash
   bench --site site1.local migrate
   ```

### Adding New Service

1. **Create Service File**:
   ```python
   # memora/services/my_service.py
   class MyService:
       def __init__(self):
           pass
       
       def my_method(self, param):
           # Logic here
           pass
   ```

2. **Use Service**:
   ```python
   from memora.services.my_service import MyService
   
   service = MyService()
   result = service.my_method(param)
   ```

3. **Write Tests**: Create test file

## Code Style Guidelines

### Python Code Style

Follow PEP 8 conventions:

```python
# Good
def calculate_xp(score: int, difficulty: float) -> int:
    """Calculate XP based on score and difficulty."""
    return int(score * difficulty)

# Bad
def CalculateXP(s,d):
    return s*d
```

### Type Hints

Use type hints for function signatures:

```python
from typing import List, Dict, Optional

def get_user_data(user_id: str) -> Optional[Dict]:
    """Get user data by ID."""
    pass

def process_items(items: List[str]) -> Dict[str, int]:
    """Process list of items."""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def get_review_session(user: str, season: str) -> Dict:
    """Get review session for a user.
    
    Args:
        user: User email or ID
        season: Season name
        
    Returns:
        Dictionary with review session data
        
    Raises:
        ValidationError: If user not found
    """
    pass
```

### Error Handling

Always handle errors gracefully:

```python
try:
    result = operation()
except SpecificError as e:
    frappe.log_error(str(e), "function_name")
    frappe.throw(_("Operation failed"))
except Exception as e:
    frappe.log_error(frappe.get_traceback(), "function_name")
    frappe.throw(_("An unexpected error occurred"))
```

### Database Queries

Use Frappe's database API:

```python
# Good: Use Frappe API
records = frappe.get_all(
    "Player Memory Tracker",
    filters={"player": user, "season": season},
    fields=["question_id", "stability"],
    limit=20
)

# Acceptable: Raw SQL for complex queries
records = frappe.db.sql("""
    SELECT question_id, stability
    FROM `tabPlayer Memory Tracker`
    WHERE player = %s AND season = %s
    LIMIT 20
""", (user, season), as_dict=True)
```

### API Endpoints

Always use `@frappe.whitelist()` decorator:

```python
@frappe.whitelist()
def my_endpoint(param: str) -> Dict:
    """My endpoint."""
    pass
```

## Testing

### Running Tests

```bash
# Run all tests
bench --site site1.local run-tests --app memora

# Run specific test file
cd apps/memora
pytest memora/tests/test_srs_archiver.py -v

# Run with coverage
pytest --cov=memora memora/tests/ --cov-report=html
```

### Writing Tests

```python
import frappe
from frappe.tests.utils import FrappeTestCase
import pytest

class TestMyService(FrappeTestCase):
    def setUp(self):
        """Setup before each test."""
        frappe.set_user("Administrator")
    
    def tearDown(self):
        """Cleanup after each test."""
        frappe.db.rollback()
    
    def test_my_function(self):
        """Test my function."""
        result = my_function(param="test")
        self.assertEqual(result, expected_value)
```

### Test Coverage

Aim for 80%+ test coverage:

```bash
# Generate coverage report
pytest --cov=memora memora/tests/ --cov-report=term-missing
```

## Debugging

### Enable Debug Mode

```bash
bench set-config developer_mode 1
bench set-config logging_level DEBUG
```

### View Logs

```bash
# View Frappe logs
bench --site site1.local tail-logs

# View Redis logs
tail -f /var/log/redis/redis.log
```

### Use Python Debugger

```python
import pdb; pdb.set_trace()

# Or use ipdb if installed
import ipdb; ipdb.set_trace()
```

### Debug API Endpoints

```python
@frappe.whitelist()
def my_endpoint():
    """Debug endpoint."""
    import frappe
    frappe.logger().debug("Debug message")
    # Your logic
    pass
```

## Deployment

### Production Setup

1. **Disable Developer Mode**
   ```bash
   bench set-config developer_mode 0
   ```

2. **Set Production Configuration**
   ```json
   {
     "redis_cache": "redis://redis-server:6379",
     "srs_redis_cache": "redis://redis-server:6379",
     "maintenance_mode": 0
   }
   ```

3. **Run Migrations**
   ```bash
   bench --site site1.local migrate
   ```

4. **Build Assets**
   ```bash
   bench build --app memora
   ```

5. **Restart Services**
   ```bash
   bench restart
   ```

### Monitoring

Monitor key metrics:
- **Redis**: Memory usage, connection count
- **PostgreSQL**: Query performance, connection pool
- **Application**: Response times, error rates

## Troubleshooting

### Common Issues

#### Redis Connection Failed

**Problem**: Cannot connect to Redis

**Solution**:
```bash
# Check if Redis is running
redis-cli -p 13000 ping

# Start Redis
redis-server --port 13000

# Check configuration
cat sites/common_site_config.json
```

#### Database Migration Failed

**Problem**: Migration fails with error

**Solution**:
```bash
# Check migration status
bench --site site1.local migrate --skip-failing

# Manually fix migration
# Edit migration file and re-run
bench --site site1.local migrate
```

#### Tests Failing

**Problem**: Tests fail intermittently

**Solution**:
```bash
# Clear cache
bench clear-cache

# Rebuild database
bench --site site1.local reinstall-app memora

# Run tests with verbose output
pytest -v memora/tests/
```

#### Performance Issues

**Problem**: Slow API responses

**Solution**:
```bash
# Check Redis cache status
frappe.get_doc("Memora Settings").get_cache_status()

# Rebuild cache if needed
from memora.services.srs_redis_manager import rebuild_season_cache
rebuild_season_cache("2024-2025")

# Check database indexes
# Use EXPLAIN ANALYZE on slow queries
```

### Getting Help

- **Documentation**: Check `/docs` folder
- **Logs**: Review error logs
- **Community**: Ask in Frappe community
- **Support**: Email dev@corex.com

---

## Additional Resources

- [Frappe Framework Docs](https://frappeframework.com/docs)
- [Python Documentation](https://docs.python.org/3/)
- [Redis Documentation](https://redis.io/documentation)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)

---

**Last Updated**: 2026-01-20
**Version**: 1.0
