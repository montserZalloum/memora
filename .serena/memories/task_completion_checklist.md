# Task Completion Checklist for Memora

## Pre-Completion Checklist

### Code Quality
- [ ] Code follows project style and conventions
- [ ] All docstrings are present and complete
- [ ] No TODO or FIXME comments left in code
- [ ] Error handling is implemented with clear messages
- [ ] Code is self-documenting (good variable names, clear logic)

### Testing
- [ ] Unit tests written (if required by TDD)
- [ ] All tests pass locally
- [ ] Test coverage meets requirements (100% for complex logic)
- [ ] Edge cases are tested
- [ ] Integration tests updated if needed

### Validation
- [ ] DocType JSON schema is valid (run `pre-commit run check-json`)
- [ ] All required fields are marked with `reqd: 1`
- [ ] Link fields have `search_index: 1` if used in filters
- [ ] Field order is correct in `field_order` array
- [ ] Default values are set where appropriate

### Constitution Compliance
- [ ] Principle I: Read/Write Segregation followed
- [ ] Principle II: High-Velocity Data Segregation followed
- [ ] Principle III: Content-Commerce Decoupling followed
- [ ] Principle IV: Logic Verification (TDD) followed
- [ ] Principle V: Performance-First Schema followed

## Post-Completion Actions

### 1. Run Pre-commit Checks
```bash
cd apps/memora
pre-commit run --all-files
```

**Expected Output**: All checks pass with no errors or warnings

**If Failing**:
- Fix ruff issues: `ruff check --fix memora/`
- Fix formatting: `ruff format memora/`
- Fix JSON issues: Validate JSON structure
- Re-run pre-commit until all pass

### 2. Run Database Migration (if schema changed)
```bash
cd $PATH_TO_YOUR_BENCH
bench migrate
```

**When Required**:
- Added new fields to DocType JSON
- Added new DocTypes
- Modified field properties (type, options, etc.)

**Expected Output**: Migration completes successfully with no errors

**If Failing**:
- Check JSON syntax
- Verify field definitions
- Check for duplicate field names
- Review Frappe error logs

### 3. Run Tests
```bash
# Run unit tests
pytest memora/tests/unit/

# Run integration tests (if applicable)
pytest memora/tests/integration/

# Run specific test file
pytest memora/tests/unit/cdn_export/test_access_calculator.py
```

**Expected Output**: All tests pass

**If Failing**:
- Review test output for specific failures
- Debug failing tests
- Fix code or tests as needed
- Re-run until all pass

### 4. Manual Verification (if applicable)

#### For DocType Changes
- [ ] Open DocType in Frappe UI
- [ ] Verify all fields appear correctly
- [ ] Test field validation
- [ ] Create a test document
- [ ] Save and verify no errors

#### For Service Changes
- [ ] Test service functions manually
- [ ] Verify Redis operations
- [ ] Check error handling
- [ ] Verify background job execution

#### For API Changes
- [ ] Test API endpoints
- [ ] Verify response format
- [ ] Check error responses
- [ ] Test authentication/authorization

### 5. Update Documentation
```bash
# Update tasks.md to mark task as complete
# Add [x] before task ID
```

**Example**:
```markdown
- [x] T009 Add is_public field (Check) to Memora Subject DocType
```

**Additional Updates**:
- Update data-model.md if schema changed
- Update plan.md if architecture changed
- Add comments to hooks.py if events added

### 6. Commit Changes
```bash
# Stage all changes
git add .

# Commit with descriptive message
git commit -m "feat: add is_public field to Memora Subject

- Add is_public Check field to distinguish public vs authenticated content
- Update field_order in JSON schema
- Add default value of 0 (unchecked)
- Complies with Constitution Principle III (Content-Commerce Decoupling)

Task: T009
Spec: 002-cdn-content-export"
```

**Commit Message Format**:
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `refactor`: Code refactoring
- `test`: Test changes
- `docs`: Documentation changes
- `chore`: Maintenance tasks

**Footer**:
- Task ID: `Task: T009`
- Spec ID: `Spec: 002-cdn-content-export`
- Constitution principles touched

### 7. Push to Remote (if ready)
```bash
git push origin <branch-name>
```

**When to Push**:
- Task is complete and tested
- All pre-commit checks pass
- All tests pass
- Manual verification complete
- Documentation updated

## Task-Specific Checklists

### T009: Add is_public field to Memora Subject
- [ ] Add `is_public` field to JSON schema
- [ ] Add to `field_order` array (after `is_free_preview`)
- [ ] Set fieldtype to `Check`
- [ ] Set default to `0`
- [ ] Run `pre-commit run check-json`
- [ ] Run `bench migrate`
- [ ] Verify field appears in Frappe UI
- [ ] Test creating Subject with is_public checked
- [ ] Mark T009 as complete in tasks.md
- [ ] Commit changes

### T010: Add required_item field to Memora Subject
- [ ] Add `required_item` field to JSON schema
- [ ] Add to `field_order` array (after `is_public`)
- [ ] Set fieldtype to `Link`
- [ ] Set options to `Item`
- [ ] Set `search_index: 1`
- [ ] Run `pre-commit run check-json`
- [ ] Run `bench migrate`
- [ ] Verify field appears in Frappe UI
- [ ] Test linking to ERPNext Item
- [ ] Mark T010 as complete in tasks.md
- [ ] Commit changes

### T011: Add required_item field to Memora Track
- [ ] Add `required_item` field to JSON schema
- [ ] Add to `field_order` array (after `is_sold_separately`)
- [ ] Set fieldtype to `Link`
- [ ] Set options to `Item`
- [ ] Set `search_index: 1`
- [ ] Run `pre-commit run check-json`
- [ ] Run `bench migrate`
- [ ] Verify field appears in Frappe UI
- [ ] Test linking to ERPNext Item
- [ ] Mark T011 as complete in tasks.md
- [ ] Commit changes

### T012: Add parent_item_required field to Memora Track
- [ ] Add `parent_item_required` field to JSON schema
- [ ] Add to `field_order` array (after `required_item`)
- [ ] Set fieldtype to `Check`
- [ ] Set default to `0`
- [ ] Run `pre-commit run check-json`
- [ ] Run `bench migrate`
- [ ] Verify field appears in Frappe UI
- [ ] Test checking/unchecking the field
- [ ] Mark T012 as complete in tasks.md
- [ ] Commit changes

## Common Issues and Solutions

### Pre-commit Fails
**Issue**: Ruff formatting issues
```bash
# Fix automatically
ruff format memora/
ruff check --fix memora/
```

**Issue**: JSON validation fails
- Check for trailing commas
- Verify field names are quoted
- Check for duplicate field names
- Validate JSON syntax

### Migration Fails
**Issue**: Field already exists
```sql
-- Check if field exists in database
DESCRIBE `tabMemora Subject`;
```

**Issue**: Duplicate field name
- Check `field_order` array
- Check `fields` array
- Ensure no duplicates

### Tests Fail
**Issue**: Test database state
```bash
# Reset test database
bench --site [site-name] reinstall
```

**Issue**: Missing fixtures
- Create test data in test setup
- Use `frappe.get_doc()` to create test documents

### Manual Verification Fails
**Issue**: Field not visible in UI
- Clear browser cache
- Restart Frappe server: `bench restart`
- Clear Frappe cache: `bench clear-cache`

**Issue**: Validation not working
- Check controller `validate()` method
- Verify field names match JSON schema
- Check for typos in field names

## Final Verification

Before marking a task as complete, ask yourself:

1. **Code Quality**: Is the code clean, readable, and follows conventions?
2. **Functionality**: Does it work as specified in the task description?
3. **Testing**: Are all tests passing with good coverage?
4. **Documentation**: Is the code documented and tasks.md updated?
5. **Constitution**: Does it comply with all relevant principles?
6. **Integration**: Does it work with existing code without breaking changes?

If all answers are **YES**, the task is complete!

## After All Tasks in Phase Complete

### Phase 2 Foundational Completion
- [ ] All tasks T009-T012 are complete
- [ ] All pre-commit checks pass
- [ ] All migrations successful
- [ ] All tests pass
- [ ] Manual verification complete
- [ ] Documentation updated
- [ ] All changes committed

### Ready for User Stories
When Phase 2 is complete, you can proceed to:
- Phase 3: User Story 1 (Automatic Content Sync)
- Phase 4: User Story 2 (Plan-Specific Content Generation)

**Checkpoint**: Foundation ready - user story implementation can now begin

## Quick Reference Commands

```bash
# Pre-commit
pre-commit run --all-files

# Migration
bench migrate

# Tests
pytest memora/tests/unit/

# Restart
bench restart

# Clear cache
bench clear-cache

# Commit
git add .
git commit -m "feat: description"

# Push
git push origin <branch>
```
