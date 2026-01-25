# Code Style and Conventions for Memora

## Python Code Style

### File Structure
```python
# Copyright (c) 2026, corex and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _

class DocTypeName(Document):
    """DocType controller class."""
    
    def validate(self):
        """Validate document before save."""
        pass
    
    def before_save(self):
        """Set defaults before saving."""
        pass
```

### Indentation and Spacing
- **Indentation**: Use **TABS** (not spaces)
- **Line Length**: Maximum 110 characters
- **Blank Lines**: 
  - 2 blank lines between top-level definitions
  - 1 blank line between method definitions
  - No trailing whitespace

### Quotes
- **String Quotes**: Use **double quotes** for all strings
- **Docstrings**: Use triple double quotes `"""..."""`

### Naming Conventions

#### Classes
- **Style**: PascalCase
- **Examples**: `MemoraSubject`, `CDNSettings`, `AccessCalculator`

#### Methods and Functions
- **Style**: snake_case
- **Examples**: `validate_endpoint_url`, `calculate_access_level`, `get_pending_plans`

#### Variables
- **Style**: snake_case
- **Examples**: `plan_id`, `files_uploaded`, `error_message`

#### Constants
- **Style**: UPPER_SNAKE_CASE
- **Examples**: `MAX_RETRY_COUNT`, `DEFAULT_BATCH_INTERVAL`, `REDIS_QUEUE_KEY`

#### Private Methods
- **Style**: Prefix with underscore
- **Examples**: `_validate_internal_field`, `_process_child_nodes`

### Type Hints
- Use `frappe.types.DF` for typing when needed
- Type hints are optional but recommended for complex functions
- Example:
```python
from typing import Optional, List, Dict

def get_pending_plans() -> List[str]:
    """Get list of pending plan IDs from Redis queue."""
    pass

def calculate_access_level(
    plan_id: str,
    content_type: str,
    content_id: str
) -> Optional[str]:
    """Calculate access level for content."""
    pass
```

### Docstrings
- **Required**: All classes and methods must have docstrings
- **Style**: Google-style or reStructuredText
- **Format**: Triple double quotes
- **Content**: Brief description, parameters, return value (if applicable)

Examples:
```python
class CDNSettings(Document):
    """CDN Settings DocType controller.
    
    Manages configuration for CDN export system including
    storage provider credentials and batch processing settings.
    """
    
    def validate_endpoint_url(self):
        """Validate that endpoint_url is a valid URL.
        
        Uses regex pattern to validate URL format including
        http/https protocol, domain, and optional port.
        
        Raises:
            frappe.throw: If endpoint_url is not a valid URL
        """
        pass
    
    def mark_as_success(self, files_uploaded=0, files_deleted=0):
        """Mark the log as success.
        
        Args:
            files_uploaded: Number of files uploaded to CDN
            files_deleted: Number of files deleted from CDN
        """
        pass
```

### Method Organization
Order methods in DocType controllers:
1. `validate()` - Main validation entry point
2. `before_save()` - Set defaults before save
3. `on_update()` - Post-save hooks
4. `on_trash()` - Pre-delete hooks
5. `after_delete()` - Post-delete hooks
6. Custom validation methods (private)
7. Custom helper methods (private)
8. Static methods (public utilities)

### Error Handling
- Use `frappe.throw()` for validation errors
- Use `frappe.log_error()` for logging errors
- Use try-except for external API calls
- Provide clear error messages

Example:
```python
def validate_bucket_name(self):
    """Validate that bucket_name is not empty."""
    if not self.bucket_name or not self.bucket_name.strip():
        frappe.throw(_("Bucket Name is required"))

def upload_to_cdn(self, data, key):
    """Upload data to CDN.
    
    Args:
        data: JSON data to upload
        key: CDN key/path
        
    Returns:
        URL of uploaded file
        
    Raises:
        frappe.throw: If upload fails
    """
    try:
        # Upload logic
        pass
    except Exception as e:
        frappe.log_error(f"CDN upload failed: {str(e)}")
        frappe.throw(_("Failed to upload to CDN"))
```

### Database Queries
- Use `frappe.db.get_all()` for listing documents
- Use `frappe.get_doc()` for single document retrieval
- Use `frappe.db.exists()` to check existence
- Use `frappe.db.count()` for counting
- Always use indexes on filter fields

Examples:
```python
# Get all documents
subjects = frappe.get_all(
    "Memora Subject",
    filters={"is_published": 1},
    fields=["name", "title", "is_public"],
    order_by="sort_order"
)

# Get single document
subject = frappe.get_doc("Memora Subject", subject_id)

# Check existence
if frappe.db.exists("Memora Subject", subject_id):
    pass

# Count documents
count = frappe.db.count("Memora Subject", {"is_published": 1})
```

### Frappe DocType JSON Schema

#### Field Order
Fields must be listed in `field_order` array in display order:
```json
{
  "field_order": [
    "title",
    "color_code",
    "is_published",
    "is_free_preview",
    "sort_order",
    "image",
    "description"
  ],
  "fields": [...]
}
```

#### Field Types
Common field types:
- `Data` - Text input
- `Small Text` - Multi-line text
- `Int` - Integer number
- `Check` - Checkbox (default "0" for unchecked)
- `Link` - Link to another DocType
- `Select` - Dropdown selection
- `Password` - Password field (encrypted)
- `Attach Image` - Image upload
- `Datetime` - Date and time

#### Field Properties
- `fieldname`: Internal field name (snake_case)
- `label`: Display label (Title Case)
- `fieldtype`: Field type
- `reqd`: 1 if required
- `default`: Default value
- `search_index`: 1 for Link fields used in filters
- `options`: Options for Select/Link fields
- `in_list_view`: 1 to show in list view

Example:
```json
{
  "fieldname": "is_public",
  "fieldtype": "Check",
  "label": "Is Public",
  "default": "0"
},
{
  "fieldname": "required_item",
  "fieldtype": "Link",
  "label": "Required Item",
  "options": "Item",
  "search_index": 1
}
```

### Redis Usage
- Use `frappe.cache` for Redis operations
- Use meaningful key prefixes
- Set TTL for temporary data
- Use appropriate data structures

Examples:
```python
# Set value
frappe.cache.set_value("cdn_export:pending_plans", plan_ids)

# Get value
plan_ids = frappe.cache.get_value("cdn_export:pending_plans")

# Set with TTL (5 minutes)
frappe.cache.set_value("cdn_export:lock:plan123", timestamp, timeout=300)

# Add to set
frappe.cache.sadd("cdn_export:pending_plans", plan_id)

# Get set members
plan_ids = frappe.cache.smembers("cdn_export:pending_plans")

# Delete key
frappe.cache.delete_value("cdn_export:lock:plan123")
```

### Background Jobs
- Use `frappe.enqueue()` for async tasks
- Provide meaningful job names
- Set appropriate queue
- Handle errors gracefully

Example:
```python
def queue_plan_rebuild(plan_id):
    """Queue plan rebuild as background job."""
    frappe.enqueue(
        "memora.services.cdn_export.batch_processor.rebuild_plan",
        plan_id=plan_id,
        queue="long",
        timeout=600,
        job_name=f"rebuild_plan_{plan_id}"
    )
```

### Testing

#### Unit Tests
- Use pytest framework
- Test file name: `test_{module_name}.py`
- Test class: `Test{ClassName}`
- Test method: `test_{scenario}`

Example:
```python
import frappe
from frappe.tests.utils import FrappeTestCase

class TestAccessCalculator(FrappeTestCase):
    def test_calculate_access_level_public(self):
        """Test access level calculation for public content."""
        from memora.services.cdn_export.access_calculator import calculate_access_level
        
        result = calculate_access_level(
            plan_id="plan123",
            content_type="Subject",
            content_id="subject456"
        )
        
        self.assertEqual(result, "public")
    
    def test_calculate_access_level_paid(self):
        """Test access level calculation for paid content."""
        # Test implementation
        pass
```

#### Test Organization
- Arrange-Act-Assert pattern
- Clear test names
- Comments for complex scenarios
- Setup/teardown with fixtures

Example:
```python
def test_override_hiding_content(self):
    """Test that plan override hides content correctly.
    
    Given: Subject has is_free_preview = True
    And: Plan override sets action = "Hide"
    When: Calculate access level
    Then: Content should be hidden (access_level = None)
    """
    # Arrange
    subject = self.create_test_subject(is_free_preview=True)
    override = self.create_test_override(
        plan_id="plan123",
        target_doctype="Memora Subject",
        target_name=subject.name,
        action="Hide"
    )
    
    # Act
    result = calculate_access_level(
        plan_id="plan123",
        content_type="Subject",
        content_id=subject.name
    )
    
    # Assert
    self.assertIsNone(result)
```

### Comments
- Use comments to explain **why**, not **what**
- Keep comments concise
- Update comments when code changes
- Avoid obvious comments

Good:
```python
# Use Redis Set for automatic deduplication of pending plans
frappe.cache.sadd("cdn_export:pending_plans", plan_id)

# TTL prevents stale locks (5 minutes)
frappe.cache.set_value(f"cdn_export:lock:{plan_id}", timestamp, timeout=300)
```

Bad:
```python
# Add plan_id to set
frappe.cache.sadd("cdn_export:pending_plans", plan_id)

# Set value with timeout
frappe.cache.set_value(f"cdn_export:lock:{plan_id}", timestamp, timeout=300)
```

### Import Organization
- Standard library imports first
- Third-party imports second
- Local imports third
- Group related imports
- Sort alphabetically

Example:
```python
import re
from datetime import datetime
from typing import Optional, List, Dict

import frappe
from frappe.model.document import Document
from frappe import _

from memora.services.cdn_export import change_tracker
from memora.services.cdn_export import json_generator
```

## JavaScript Code Style

### File Structure
```javascript
// Copyright (c) 2026, corex and contributors
// For license information, please see license.txt

frappe.ui.form.on('DocTypeName', {
    refresh: function(frm) {
        // Refresh logic
    },
    
    validate: function(frm) {
        // Validation logic
    }
});
```

### Naming Conventions
- **Variables**: camelCase
- **Functions**: camelCase
- **Constants**: UPPER_SNAKE_CASE
- **Classes**: PascalCase

### Formatting
- **Indentation**: 2 spaces
- **Quotes**: Single quotes for strings
- **Semicolons**: Required
- **Line Length**: 100 characters

## JSON Schema Style

### Formatting
- **Indentation**: 2 spaces
- **Quotes**: Double quotes
- **Trailing commas**: No trailing commas
- **Keys**: Always quoted

Example:
```json
{
  "doctype": "DocType",
  "name": "Memora Subject",
  "module": "Memora",
  "field_order": [
    "title",
    "is_published"
  ],
  "fields": [
    {
      "fieldname": "title",
      "fieldtype": "Data",
      "label": "Title",
      "reqd": 1
    }
  ]
}
```

## Constitution Compliance

### Principle I: Read/Write Segregation
- Use background jobs for JSON generation
- Don't query hierarchical data in API responses
- Pre-calculate and cache complex structures

### Principle II: High-Velocity Data Segregation
- Use Redis for queues and locks
- Batch high-velocity writes
- Offload logs to specialized storage

### Principle III: Content-Commerce Decoupling
- Keep content DocTypes pure (no pricing)
- Use Link fields to Item for commerce
- Access control via Product Grant mapping

### Principle IV: Logic Verification (TDD)
- Write failing tests first for complex logic
- 100% coverage for access calculator
- 100% coverage for dependency resolver

### Principle V: Performance-First Schema
- Add indexes on all filter fields
- Use JSON fields for polymorphic content
- Pre-calculate fields over joins

## Common Patterns

### DocType Validation Pattern
```python
def validate(self):
    """Main validation entry point."""
    self.validate_field_a()
    self.validate_field_b()
    self.validate_relationships()

def validate_field_a(self):
    """Validate field A."""
    if not self.field_a:
        frappe.throw(_("Field A is required"))
```

### Default Values Pattern
```python
def before_save(self):
    """Set defaults before saving."""
    if not self.status:
        self.status = "Queued"
    if self.retry_count is None:
        self.retry_count = 0
```

### Status Transition Pattern
```python
def mark_as_success(self):
    """Mark document as success."""
    self.status = "Success"
    self.completed_at = datetime.now()
    self.save()

def mark_as_failed(self, error_message):
    """Mark document as failed."""
    self.status = "Failed"
    self.completed_at = datetime.now()
    self.error_message = error_message
    self.retry_count = (self.retry_count or 0) + 1
    self.save()
```

### Static Query Pattern
```python
@staticmethod
def get_recent_failures(limit=10):
    """Get recent failed sync logs."""
    return frappe.get_all(
        "CDN Sync Log",
        filters={
            "status": ["in", ["Failed", "Dead Letter"]]
        },
        fields=["name", "plan_id", "status", "error_message", "creation"],
        order_by="creation desc",
        limit=limit
    )
```
