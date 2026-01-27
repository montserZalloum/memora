# Suggested Commands for Memora Development

## Essential Commands

### Pre-commit (Code Quality)
```bash
# Install pre-commit hooks (first time setup)
cd apps/memora
pre-commit install

# Run all pre-commit checks
pre-commit run --all-files

# Run pre-commit on staged files only
pre-commit run

# Run specific hook
pre-commit run ruff --all-files
```

### Frappe/Bench Commands
```bash
# Navigate to bench directory
cd $PATH_TO_YOUR_BENCH

# Install app
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app memora

# Run database migrations (after schema changes)
bench migrate

# Start development server
bench start

# Restart services
bench restart

# Clear cache
bench clear-cache

# Run all tests
bench run-tests

# Run specific app tests
bench --site [site-name] run-tests --app memora

# Create new DocType
bench new-doctype "DocTypeName" --module "Memora"

# Create new API endpoint
bench new-api "api_endpoint_name" --module "Memora"
```

### Ruff (Python Linter/Formatter)
```bash
# Check code for issues
ruff check memora/

# Fix auto-fixable issues
ruff check --fix memora/

# Format code
ruff format memora/

# Check imports only
ruff check --select I memora/

# Sort imports
ruff check --select I --fix memora/
```

### Testing
```bash
# Run all unit tests
pytest memora/tests/unit/

# Run all integration tests
pytest memora/tests/integration/

# Run specific test file
pytest memora/tests/unit/cdn_export/test_access_calculator.py

# Run with verbose output
pytest -v memora/tests/unit/

# Run with coverage
pytest --cov=memora memora/tests/unit/

# Run specific test function
pytest memora/tests/unit/cdn_export/test_access_calculator.py::test_calculate_access_level
```

### Git Commands
```bash
# Check git status
git status

# Add all changes
git add .

# Commit changes
git commit -m "feat: add is_published field to Memora Subject"

# Push to remote
git push origin [branch-name]

# Create new branch
git checkout -b [branch-name]

# Pull latest changes
git pull origin [branch-name]
```

### System Commands (Linux)
```bash
# List files recursively
ls -laR memora/

# Find files by name
find memora/ -name "*.py"

# Search for pattern in files
grep -r "pattern" memora/

# Check file permissions
ls -l memora/

# Change directory
cd /path/to/directory

# Show current directory
pwd

# View file content
cat file.txt

# View file with line numbers
cat -n file.txt

# Edit file
nano file.txt
# or
vim file.txt
```

## Workflow Commands

### Typical Development Workflow
```bash
# 1. Create feature branch
git checkout -b feature/002-cdn-content-export

# 2. Make changes to code
# ... edit files ...

# 3. Run pre-commit checks
pre-commit run --all-files

# 4. Run tests
pytest memora/tests/unit/

# 5. Run migrations if schema changed
bench migrate

# 6. Commit changes
git add .
git commit -m "feat: add is_published field to Memora Subject"

# 7. Push to remote
git push origin feature/002-cdn-content-export
```

### After DocType Schema Changes
```bash
# 1. Update JSON schema
# ... edit memora/memora/doctype/{name}/{name}.json ...

# 2. Run pre-commit to validate JSON
pre-commit run check-json --all-files

# 3. Run migration
bench migrate

# 4. Verify DocType in Frappe
# Open browser: http://[site-url]/app/{doctype-name}
```

### After Adding New Fields
```bash
# 1. Add field to JSON schema
# ... edit memora/memora/doctype/{name}/{name}.json ...

# 2. Add field to field_order array
# ... ensure field is in correct position ...

# 3. Run migration
bench migrate

# 4. Test field in UI
# Open DocType form and verify field appears
```

## Speckit Methodology Commands

### Feature Development Workflow
```bash
# 1. Read spec and plan
cat specs/002-cdn-content-export/spec.md
cat specs/002-cdn-content-export/plan.md

# 2. Check tasks
cat specs/002-cdn-content-export/tasks.md

# 3. Implement task
# ... write code ...

# 4. Run tests
pytest memora/tests/unit/cdn_export/

# 5. Run pre-commit
pre-commit run --all-files

# 6. Update task status
# ... edit specs/002-cdn-content-export/tasks.md ...

# 7. Commit
git add .
git commit -m "feat: implement T009 - add is_published field to Memora Subject"
```

### Constitution Compliance Check
```bash
# Review constitution
cat .specify/memory/constitution.md

# Check if changes comply with principles
# - I. Read/Write Segregation
# - II. High-Velocity Data Segregation
# - III. Content-Commerce Decoupling
# - IV. Logic Verification (TDD)
# - V. Performance-First Schema Design
```

## Debugging Commands

### Check Frappe Logs
```bash
# View Frappe error logs
tail -f logs/error.log

# View Frappe worker logs
tail -f logs/worker.log

# View web server logs
tail -f logs/web.log
```

### Database Queries
```bash
# Access Frappe database
bench --site [site-name] mariadb

# Run query
SELECT * FROM `tabMemora Subject` LIMIT 10;

# Exit
exit;
```

### Redis Commands
```bash
# Access Redis
redis-cli

# Check keys
KEYS cdn_export:*

# Get queue size
SCARD cdn_export:pending_plans

# Check lock
GET cdn_export:lock:{plan_id}

# Exit
exit;
```

## Deployment Commands

### Before Deployment
```bash
# 1. Run all tests
bench run-tests --app memora

# 2. Run pre-commit
pre-commit run --all-files

# 3. Check migrations
bench migrate

# 4. Clear cache
bench clear-cache
```

### After Deployment
```bash
# 1. Restart services
bench restart

# 2. Check logs
tail -f logs/error.log

# 3. Verify DocTypes exist
# Open browser and check each DocType

# 4. Run smoke tests
# ... run critical user flows ...
```

## Quick Reference

### File Locations
- DocType JSON: `memora/memora/doctype/{name}/{name}.json`
- DocType Controller: `memora/memora/doctype/{name}/{name}.py`
- Services: `memora/services/cdn_export/`
- API Endpoints: `memora/api/`
- Tests: `memora/tests/`
- Hooks: `memora/hooks.py`

### Common Patterns
- DocType field: Link to "Item" for ERPNext integration
- Index field: `"search_index": 1` for filterable Link fields
- Required field: `"reqd": 1`
- Default value: `"default": "0"` for checkboxes

### Constitution Principles
- **Principle I**: Use background jobs for JSON generation
- **Principle II**: Use Redis for high-velocity data
- **Principle III**: Keep content DocTypes pure (no pricing)
- **Principle IV**: TDD for complex logic (access calculator, dependency resolver)
- **Principle V**: Use indexes on all filter fields
