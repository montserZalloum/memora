import os
import sys
import unittest

# Add app to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    import frappe
    from frappe.test_runner import make_test_records
    from memora.services.cdn_export.json_generator import (
        generate_manifest,
        generate_subject_json,
        generate_unit_json,
        generate_lesson_json
    )
    from memora.services.cdn_export.search_indexer import (
        generate_search_index,
        generate_subject_shard
    )
    FRAPPE_AVAILABLE = True
except ImportError:
    FRAPPE_AVAILABLE = False


class TestJSONSchemas(unittest.TestCase):
    """
    Contract tests validating that generated JSON matches schema specifications.

    These tests validate the output contracts against the JSON schemas defined in
    specs/002-cdn-content-export/contracts/
    """

    @classmethod
    def setUpClass(cls):
        if not FRAPPE_AVAILABLE:
            cls.skipTest(cls, "Frappe not available")
            return

        frappe.init(site="test_site", db_name="test_db")
        frappe.connect()
        frappe.set_user("Administrator")

    @classmethod
    def tearDownClass(cls):
        if FRAPPE_AVAILABLE:
            frappe.destroy()

    def setUp(self):
        if not FRAPPE_AVAILABLE:
            self.skipTest("Frappe not available")

    def test_manifest_schema_compliance(self):
        """
        Test that generated manifest JSON complies with manifest.schema.json

        Validates:
        - All required fields present
        - Field types match schema
        - Nested structure correct
        """
        schema_path = os.path.join(
            os.path.dirname(__file__),
            '../../memora/services/cdn_export/schemas/manifest.schema.json'
        )

        if not os.path.exists(schema_path):
            self.skipTest(f"Schema file not found: {schema_path}")

        import json
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema library not installed")

        with open(schema_path, 'r') as f:
            schema = json.load(f)

        # Generate a test manifest
        plan_doc = self._create_test_plan()
        manifest = generate_manifest(plan_doc)

        # Validate against schema
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(manifest))

        if errors:
            error_msg = "\n".join([f"{' -> '.join(str(p) for p in e.path)}: {e.message}" for e in errors])
            self.fail(f"Manifest schema validation failed:\n{error_msg}")

    def test_lesson_schema_compliance(self):
        """
        Test that generated lesson JSON complies with lesson.schema.json

        Validates:
        - All required fields present including signed_url_expiry
        - Access control fields present and correct types
        - Stages structure matches schema
        """
        schema_path = os.path.join(
            os.path.dirname(__file__),
            '../../memora/services/cdn_export/schemas/lesson.schema.json'
        )

        if not os.path.exists(schema_path):
            self.skipTest(f"Schema file not found: {schema_path}")

        import json
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema library not installed")

        with open(schema_path, 'r') as f:
            schema = json.load(f)

        # Generate a test lesson
        lesson_doc = self._create_test_lesson()
        lesson_json = generate_lesson_json(lesson_doc, plan_id="TEST-PLAN-001")

        self.assertIsNotNone(lesson_json, "Lesson should not be None")

        # Validate against schema
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(lesson_json))

        if errors:
            error_msg = "\n".join([f"{' -> '.join(str(p) for p in e.path)}: {e.message}" for e in errors])
            self.fail(f"Lesson schema validation failed:\n{error_msg}")

        # Additional checks for US4 requirements
        self.assertIn("signed_url_expiry", lesson_json, "Lesson should have signed_url_expiry field")
        self.assertIn("access", lesson_json, "Lesson should have access object")
        self.assertIn("access_level", lesson_json["access"], "Access should have access_level")
        self.assertIn("is_published", lesson_json["access"], "Access should have is_published")

    def test_subject_schema_compliance(self):
        """
        Test that generated subject JSON complies with subject.schema.json

        Validates:
        - All required fields present
        - Tracks structure matches schema
        - Access control fields present
        """
        schema_path = os.path.join(
            os.path.dirname(__file__),
            '../../memora/services/cdn_export/schemas/subject.schema.json'
        )

        if not os.path.exists(schema_path):
            self.skipTest(f"Schema file not found: {schema_path}")

        import json
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema library not installed")

        with open(schema_path, 'r') as f:
            schema = json.load(f)

        # Generate a test subject
        subject_doc = self._create_test_subject()
        subject_json = generate_subject_json(subject_doc, plan_id="TEST-PLAN-001")

        self.assertIsNotNone(subject_json, "Subject should not be None")

        # Validate against schema
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(subject_json))

        if errors:
            error_msg = "\n".join([f"{' -> '.join(str(p) for p in e.path)}: {e.message}" for e in errors])
            self.fail(f"Subject schema validation failed:\n{error_msg}")

        # Additional checks for access control
        self.assertIn("access", subject_json, "Subject should have access object")
        self.assertIn("access_level", subject_json["access"], "Access should have access_level")
        self.assertIn("is_published", subject_json["access"], "Access should have is_published")

    def test_unit_schema_compliance(self):
        """
        Test that generated unit JSON complies with unit.schema.json

        Validates:
        - All required fields present
        - Topics structure matches schema
        - Access control fields present
        """
        schema_path = os.path.join(
            os.path.dirname(__file__),
            '../../memora/services/cdn_export/schemas/unit.schema.json'
        )

        if not os.path.exists(schema_path):
            self.skipTest(f"Schema file not found: {schema_path}")

        import json
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema library not installed")

        with open(schema_path, 'r') as f:
            schema = json.load(f)

        # Generate a test unit
        unit_doc = self._create_test_unit()
        unit_json = generate_unit_json(unit_doc, plan_id="TEST-PLAN-001")

        self.assertIsNotNone(unit_json, "Unit should not be None")

        # Validate against schema
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(unit_json))

        if errors:
            error_msg = "\n".join([f"{' -> '.join(str(p) for p in e.path)}: {e.message}" for e in errors])
            self.fail(f"Unit schema validation failed:\n{error_msg}")

        # Additional checks for access control
        self.assertIn("access", unit_data, "Unit should have access object")
        self.assertIn("access_level", unit_data["access"], "Access should have access_level")
        self.assertIn("is_published", unit_data["access"], "Access should have is_published")

    def test_search_index_schema_compliance(self):
        """
        Test that generated search index complies with search_index.schema.json

        Validates:
        - All required fields present (plan_id, version, generated_at, total_lessons)
        - Either 'entries' (non-sharded) or 'shards' (sharded) is present
        - is_sharded flag matches structure
        """
        schema_path = os.path.join(
            os.path.dirname(__file__),
            '../../memora/services/cdn_export/schemas/search_index.schema.json'
        )

        if not os.path.exists(schema_path):
            self.skipTest(f"Schema file not found: {schema_path}")

        import json
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema library not installed")

        with open(schema_path, 'r') as f:
            schema = json.load(f)

        # Generate a test search index
        plan_doc = self._create_test_plan()
        search_index = generate_search_index(plan_doc.name)

        # Validate against schema
        validator = jsonschema.Draft7Validator(schema)
        errors = list(validator.iter_errors(search_index))

        if errors:
            error_msg = "\n".join([f"{' -> '.join(str(p) for p in e.path)}: {e.message}" for e in errors])
            self.fail(f"Search index schema validation failed:\n{error_msg}")

        # Check required fields
        self.assertIn("plan_id", search_index, "Search index should have plan_id")
        self.assertIn("version", search_index, "Search index should have version")
        self.assertIn("generated_at", search_index, "Search index should have generated_at")
        self.assertIn("total_lessons", search_index, "Search index should have total_lessons")
        self.assertIn("is_sharded", search_index, "Search index should have is_sharded")

        # Check structure consistency
        if search_index["is_sharded"]:
            self.assertIn("shards", search_index, "Sharded index should have shards array")
            self.assertNotIn("entries", search_index, "Sharded index should not have entries")
        else:
            self.assertIn("entries", search_index, "Non-sharded index should have entries array")
            self.assertNotIn("shards", search_index, "Non-sharded index should not have shards")

    def test_subject_shard_schema_compliance(self):
        """
        Test that generated subject shard complies with schema structure

        Validates:
        - Subject shard has correct fields (plan_id, subject_id, subject_name, lessons)
        - Lessons in shard have correct structure
        """
        plan_doc = self._create_test_plan()
        subject_doc = self._create_test_subject()

        shard = generate_subject_shard(plan_doc.name, subject_doc.name)

        # Check required fields
        self.assertIn("plan_id", shard, "Subject shard should have plan_id")
        self.assertIn("subject_id", shard, "Subject shard should have subject_id")
        self.assertIn("subject_name", shard, "Subject shard should have subject_name")
        self.assertIn("generated_at", shard, "Subject shard should have generated_at")
        self.assertIn("lessons", shard, "Subject shard should have lessons array")

        # Check lesson structure in shard
        for lesson in shard["lessons"]:
            self.assertIn("lesson_id", lesson, "Lesson should have lesson_id")
            self.assertIn("lesson_name", lesson, "Lesson should have lesson_name")
            self.assertIn("subject_id", lesson, "Lesson should have subject_id")
            self.assertIn("subject_name", lesson, "Lesson should have subject_name")
            self.assertIn("unit_id", lesson, "Lesson should have unit_id")
            self.assertIn("unit_name", lesson, "Lesson should have unit_name")
            self.assertIn("topic_id", lesson, "Lesson should have topic_id")
            self.assertIn("topic_name", lesson, "Lesson should have topic_name")

    def test_access_control_fields_in_lesson(self):
        """
        Test that lesson JSON contains all required access control metadata

        Validates US4 requirement: "JSON files contain all access control fields"
        """
        lesson_doc = self._create_test_lesson()
        lesson_json = generate_lesson_json(lesson_doc, plan_id="TEST-PLAN-001")

        self.assertIsNotNone(lesson_json, "Lesson should not be None")

        access = lesson_json["access"]
        self.assertIn("is_published", access, "Missing is_published in access")
        self.assertIn("access_level", access, "Missing access_level in access")

        # Check that access_level is one of the allowed values
        valid_levels = ["public", "authenticated", "paid", "free_preview"]
        self.assertIn(access["access_level"], valid_levels,
                      f"Invalid access_level: {access['access_level']}")

    def test_video_url_replacement_with_signed_url(self):
        """
        Test that video URLs are replaced with signed URLs in lesson stages

        Validates US4 requirement: "Replace video URLs in stage config with signed URLs"
        """
        lesson_doc = self._create_test_lesson_with_video()
        lesson_json = generate_lesson_json(lesson_doc, plan_id="TEST-PLAN-001")

        self.assertIsNotNone(lesson_json, "Lesson should not be None")
        self.assertTrue(len(lesson_json["stages"]) > 0, "Lesson should have at least one stage")

        video_stage = lesson_json["stages"][0]
        self.assertEqual(video_stage["type"], "Video", "First stage should be Video type")

        # Check that video_url is present (it should be a signed URL)
        self.assertIn("video_url", video_stage["config"], "Video stage should have video_url in config")

        # Verify it's a signed URL (contains query parameters)
        video_url = video_stage["config"]["video_url"]
        self.assertIn("?", video_url, "Video URL should be a signed URL with query parameters")

    def test_signed_url_expiry_field_present(self):
        """
        Test that lesson JSON contains signed_url_expiry field

        Validates US4 requirement: "Signed URLs with 4-hour expiry"
        """
        lesson_doc = self._create_test_lesson()
        lesson_json = generate_lesson_json(lesson_doc, plan_id="TEST-PLAN-001")

        self.assertIsNotNone(lesson_json, "Lesson should not be None")

        self.assertIn("signed_url_expiry", lesson_json,
                      "Lesson should have signed_url_expiry field")

        # Verify it's a valid ISO 8601 date-time string
        from datetime import datetime
        try:
            expiry_time = datetime.fromisoformat(lesson_json["signed_url_expiry"])
            # Check that expiry is in the future
            import time
            self.assertGreater(expiry_time.timestamp(), time.time(),
                           "Signed URL expiry should be in the future")
        except ValueError:
            self.fail(f"signed_url_expiry should be ISO 8601 format: {lesson_json['signed_url_expiry']}")

    # Helper methods for creating test data

    def _create_test_plan(self):
        """Create a test plan document"""
        try:
            return frappe.get_doc("Memora Academic Plan", "TEST-PLAN-001")
        except frappe.DoesNotExistError:
            return frappe.get_doc({
                "doctype": "Memora Academic Plan",
                "name": "TEST-PLAN-001",
                "title": "Test Plan",
                "season": "2025-2026",
                "grade": "Grade 10",
                "stream": "Scientific"
            }).insert(ignore_permissions=True)

    def _create_test_subject(self):
        """Create a test subject document"""
        try:
            return frappe.get_doc("Memora Subject", "TEST-SUBJECT-001")
        except frappe.DoesNotExistError:
            return frappe.get_doc({
                "doctype": "Memora Subject",
                "name": "TEST-SUBJECT-001",
                "title": "Test Subject",
                "description": "Test subject description",
                "is_published": 1,
                "is_public": 0
            }).insert(ignore_permissions=True)

    def _create_test_unit(self):
        """Create a test unit document"""
        subject = self._create_test_subject()

        try:
            return frappe.get_doc("Memora Unit", "TEST-UNIT-001")
        except frappe.DoesNotExistError:
            # Create track first
            track = frappe.get_doc({
                "doctype": "Memora Track",
                "name": "TEST-TRACK-001",
                "title": "Test Track",
                "parent_subject": subject.name,
                "sort_order": 1
            }).insert(ignore_permissions=True)

            return frappe.get_doc({
                "doctype": "Memora Unit",
                "name": "TEST-UNIT-001",
                "title": "Test Unit",
                "description": "Test unit description",
                "parent_track": track.name,
                "sort_order": 1
            }).insert(ignore_permissions=True)

    def _create_test_lesson(self):
        """Create a test lesson document"""
        unit = self._create_test_unit()

        try:
            return frappe.get_doc("Memora Topic", "TEST-TOPIC-001")
        except frappe.DoesNotExistError:
            topic = frappe.get_doc({
                "doctype": "Memora Topic",
                "name": "TEST-TOPIC-001",
                "title": "Test Topic",
                "parent_unit": unit.name,
                "sort_order": 1
            }).insert(ignore_permissions=True)

            return frappe.get_doc({
                "doctype": "Memora Lesson",
                "name": "TEST-LESSON-001",
                "title": "Test Lesson",
                "description": "Test lesson description",
                "parent_topic": topic.name,
                "sort_order": 1,
                "is_published": 1,
                "is_free_preview": 0
            }).insert(ignore_permissions=True)

    def _create_test_lesson_with_video(self):
        """Create a test lesson with a video stage"""
        lesson = self._create_test_lesson()

        # Add a video stage
        import json
        stage_config = json.dumps({
            "type": "Video",
            "video_url": "https://test-bucket.r2.cloudflarestorage.com/videos/test-video.mp4",
            "thumbnail": "https://test-bucket.r2.cloudflarestorage.com/thumbnails/test-video.jpg"
        })

        return frappe.get_doc({
            "doctype": "Memora Lesson Stage",
            "name": "TEST-STAGE-001",
            "title": "Video Stage",
            "parent": lesson.name,
            "sort_order": 1,
            "stage_config": stage_config
        }).insert(ignore_permissions=True)


if __name__ == '__main__':
    unittest.main()
