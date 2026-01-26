import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from datetime import datetime


class TestGenerateManifestAtomic(unittest.TestCase):
    """Tests for generate_manifest_atomic() function - Phase 3: User Story 1"""

    def _setup_manifest_mocks(self):
        """Helper to setup common mocks for manifest tests"""
        patcher_frappe = patch('memora.services.cdn_export.json_generator.frappe')
        patcher_now = patch('memora.services.cdn_export.json_generator.now_datetime')
        patcher_overrides = patch('memora.services.cdn_export.json_generator.apply_plan_overrides')
        patcher_calc = patch('memora.services.cdn_export.json_generator.calculate_access_level')
        patcher_url = patch('memora.services.cdn_export.json_generator.get_content_url')

        mock_frappe = patcher_frappe.start()
        mock_now = patcher_now.start()
        mock_overrides = patcher_overrides.start()
        mock_calc = patcher_calc.start()
        mock_url = patcher_url.start()

        # Setup datetime - create a mock with timestamp and isoformat methods
        mock_dt = MagicMock()
        mock_dt.timestamp = Mock(return_value=1706270400)
        mock_dt.isoformat = Mock(return_value="2026-01-26T10:00:00")
        mock_now.return_value = mock_dt

        # Setup URL resolver
        mock_url.side_effect = lambda x: x

        # Setup overrides
        mock_overrides.return_value = {}

        return {
            'frappe': (patcher_frappe, mock_frappe),
            'now': (patcher_now, mock_now),
            'overrides': (patcher_overrides, mock_overrides),
            'calc': (patcher_calc, mock_calc),
            'url': (patcher_url, mock_url)
        }

    def test_generate_manifest_atomic_subjects_array_structure(self):
        """T014: Validate subjects array structure in manifest"""
        from memora.services.cdn_export.json_generator import generate_manifest_atomic

        mocks = self._setup_manifest_mocks()
        try:
            mock_frappe = mocks['frappe'][1]
            mock_calc = mocks['calc'][1]

            # Setup mock plan
            plan_doc = Mock()
            plan_doc.name = "PLAN-001"
            plan_doc.title = "Test Plan"
            plan_doc.season = None
            plan_doc.grade = None
            plan_doc.stream = None

            # Setup mock subjects
            subject1 = Mock()
            subject1.name = "SUBJ-001"
            subject1.title = "Mathematics"
            subject1.description = "Math subject"
            subject1.image = None
            subject1.color_code = None
            subject1.is_published = True
            subject1.is_linear = False

            subject2 = Mock()
            subject2.name = "SUBJ-002"
            subject2.title = "Science"
            subject2.description = None
            subject2.image = "/files/science.png"
            subject2.color_code = "#3B82F6"
            subject2.is_published = True
            subject2.is_linear = True

            # Setup plan subjects
            plan_subject1 = Mock()
            plan_subject1.subject = "SUBJ-001"

            plan_subject2 = Mock()
            plan_subject2.subject = "SUBJ-002"

            mock_frappe.get_all.side_effect = [
                [plan_subject1, plan_subject2],  # Plan subjects
                [subject1, subject2]  # Subjects
            ]

            # Mock calculate_access_level
            mock_calc.side_effect = ["public", "paid"]

            manifest = generate_manifest_atomic(plan_doc)

            # Assertions
            self.assertIsNotNone(manifest)
            self.assertEqual(manifest["plan_id"], "PLAN-001")
            self.assertEqual(manifest["title"], "Test Plan")
            self.assertIn("subjects", manifest)
            self.assertEqual(len(manifest["subjects"]), 2)

            # Validate subjects array structure
            for subject in manifest["subjects"]:
                self.assertIn("id", subject)
                self.assertIn("title", subject)
                self.assertIn("is_linear", subject)
                self.assertIn("hierarchy_url", subject)
                self.assertIn("bitmap_url", subject)
                self.assertIn("access", subject)
                self.assertIn("access_level", subject["access"])
                self.assertIn("is_published", subject["access"])
        finally:
            for patcher, _ in mocks.values():
                patcher.stop()

    def test_generate_manifest_atomic_includes_hierarchy_and_bitmap_urls(self):
        """T015: Manifest includes hierarchy_url and bitmap_url per subject"""
        from memora.services.cdn_export.json_generator import generate_manifest_atomic

        mocks = self._setup_manifest_mocks()
        try:
            mock_frappe = mocks['frappe'][1]
            mock_calc = mocks['calc'][1]

            # Setup mocks
            plan_doc = Mock()
            plan_doc.name = "PLAN-GRADE12-2024"
            plan_doc.title = "Grade 12"
            plan_doc.season = "2024"
            plan_doc.grade = "Grade 12"
            plan_doc.stream = "Scientific"

            # Setup subjects
            subject1 = Mock()
            subject1.name = "SUBJ-MATH"
            subject1.title = "Mathematics"
            subject1.description = None
            subject1.image = None
            subject1.color_code = None
            subject1.is_published = True
            subject1.is_linear = False

            plan_subject1 = Mock()
            plan_subject1.subject = "SUBJ-MATH"

            mock_frappe.get_all.side_effect = [
                [plan_subject1],
                [subject1]
            ]

            mock_calc.return_value = "paid"

            manifest = generate_manifest_atomic(plan_doc)

            # Verify hierarchy and bitmap URLs are present
            self.assertEqual(len(manifest["subjects"]), 1)
            subject = manifest["subjects"][0]

            # Should include hierarchy URL
            self.assertIn("hierarchy_url", subject)
            self.assertIn("PLAN-GRADE12-2024", subject["hierarchy_url"])
            self.assertIn("SUBJ-MATH_h.json", subject["hierarchy_url"])

            # Should include bitmap URL
            self.assertIn("bitmap_url", subject)
            self.assertIn("PLAN-GRADE12-2024", subject["bitmap_url"])
            self.assertIn("SUBJ-MATH_b.json", subject["bitmap_url"])
        finally:
            for patcher, _ in mocks.values():
                patcher.stop()

    def test_generate_manifest_atomic_empty_subjects_array(self):
        """T016: Empty subjects array when plan has no subjects"""
        from memora.services.cdn_export.json_generator import generate_manifest_atomic

        mocks = self._setup_manifest_mocks()
        try:
            mock_frappe = mocks['frappe'][1]

            # Setup mocks
            plan_doc = Mock()
            plan_doc.name = "PLAN-EMPTY"
            plan_doc.title = "Empty Plan"
            plan_doc.season = None
            plan_doc.grade = None
            plan_doc.stream = None

            # No plan subjects
            mock_frappe.get_all.side_effect = [
                [],  # Plan subjects empty
                []   # Subjects empty
            ]

            manifest = generate_manifest_atomic(plan_doc)

            # Verify empty subjects array
            self.assertIsNotNone(manifest)
            self.assertIn("subjects", manifest)
            self.assertEqual(len(manifest["subjects"]), 0)
            self.assertIsInstance(manifest["subjects"], list)
        finally:
            for patcher, _ in mocks.values():
                patcher.stop()


    def test_manifest_has_required_fields(self):
        """T020: Manifest has all required fields per schema"""
        mocks = self._setup_manifest_mocks()
        try:
            from memora.services.cdn_export.json_generator import generate_manifest_atomic

            mock_frappe = mocks['frappe'][1]

            # Setup plan
            plan_doc = Mock()
            plan_doc.name = "PLAN-001"
            plan_doc.title = "Test Plan"
            plan_doc.season = "2026"
            plan_doc.grade = "12"
            plan_doc.stream = "Science"

            # No subjects for simplicity
            mock_frappe.get_all.side_effect = [
                [],  # Plan subjects
                []   # Subjects
            ]

            manifest = generate_manifest_atomic(plan_doc)

            # Verify all required fields present
            required_fields = ["plan_id", "title", "version", "generated_at", "subjects"]
            for field in required_fields:
                self.assertIn(field, manifest, f"Missing required field: {field}")

            # Verify version is integer
            self.assertIsInstance(manifest["version"], int)

            # Verify generated_at is string
            self.assertIsInstance(manifest["generated_at"], str)

            # Verify subjects is array
            self.assertIsInstance(manifest["subjects"], list)

            # Verify optional season, grade, stream if provided
            self.assertIn("season", manifest)
            self.assertIn("grade", manifest)
            self.assertIn("stream", manifest)

        finally:
            for patcher, _ in mocks.values():
                patcher.stop()


def validate_subject_hierarchy_against_schema(hierarchy):
    """
    Validate generated hierarchy against subject_hierarchy.schema.json.

    Args:
        hierarchy (dict): Hierarchy data to validate

    Returns:
        tuple: (is_valid: bool, errors: list of error messages)
    """
    import jsonschema
    import os

    schema_path = os.path.join(
        os.path.dirname(__file__),
        "../../services/cdn_export/schemas",
        "subject_hierarchy.schema.json"
    )

    try:
        with open(schema_path, "r") as f:
            schema = json.load(f)
    except Exception as e:
        return False, [f"Failed to load subject_hierarchy schema: {str(e)}"]

    try:
        jsonschema.validate(instance=hierarchy, schema=schema)
        return True, []
    except jsonschema.ValidationError as e:
        return False, [str(e)]
    except Exception as e:
        return False, [f"Schema validation error: {str(e)}"]


class TestGenerateSubjectHierarchy(unittest.TestCase):
    """Tests for generate_subject_hierarchy() function - Phase 4: User Story 2"""

    def _setup_hierarchy_mocks(self):
        """Helper to setup common mocks for hierarchy tests"""
        patcher_frappe = patch('memora.services.cdn_export.json_generator.frappe')
        patcher_now = patch('memora.services.cdn_export.json_generator.now_datetime')
        patcher_overrides = patch('memora.services.cdn_export.json_generator.apply_plan_overrides')
        patcher_calc = patch('memora.services.cdn_export.json_generator.calculate_access_level')
        patcher_url = patch('memora.services.cdn_export.json_generator.get_content_url')

        mock_frappe = patcher_frappe.start()
        mock_now = patcher_now.start()
        mock_overrides = patcher_overrides.start()
        mock_calc = patcher_calc.start()
        mock_url = patcher_url.start()

        # Setup datetime - create a mock with timestamp and isoformat methods
        mock_dt = MagicMock()
        mock_dt.timestamp = Mock(return_value=1706270400)
        mock_dt.isoformat = Mock(return_value="2026-01-26T10:00:00")
        mock_now.return_value = mock_dt

        # Setup URL resolver
        mock_url.side_effect = lambda x: x

        # Setup overrides
        mock_overrides.return_value = {}

        return {
            'frappe': (patcher_frappe, mock_frappe),
            'now': (patcher_now, mock_now),
            'overrides': (patcher_overrides, mock_overrides),
            'calc': (patcher_calc, mock_calc),
            'url': (patcher_url, mock_url)
        }

    def test_generate_subject_hierarchy_excludes_lessons(self):
        """T021: generate_subject_hierarchy() excludes lessons from output"""
        from memora.services.cdn_export.json_generator import generate_subject_hierarchy

        mocks = self._setup_hierarchy_mocks()
        try:
            mock_frappe = mocks['frappe'][1]
            mock_calc = mocks['calc'][1]

            # Setup mock subject
            subject_doc = Mock()
            subject_doc.name = "SUBJ-MATH"
            subject_doc.title = "Mathematics"
            subject_doc.description = "Math subject"
            subject_doc.image = None
            subject_doc.color_code = None
            subject_doc.is_published = True
            subject_doc.is_linear = False

            # Setup mock track
            track = Mock()
            track.name = "TRACK-001"
            track.title = "Track 1"
            track.is_linear = True

            # Setup mock unit
            unit = Mock()
            unit.name = "UNIT-001"
            unit.title = "Unit 1"
            unit.is_linear = False
            unit.parent_track = "TRACK-001"

            # Setup mock topic
            topic = Mock()
            topic.name = "TOPIC-001"
            topic.title = "Topic 1"
            topic.is_linear = True
            topic.parent_unit = "UNIT-001"

            # Setup mock lesson
            lesson = Mock()
            lesson.name = "LESSON-001"
            lesson.title = "Lesson 1"
            lesson.parent_topic = "TOPIC-001"

            # Mock the retrieval calls in order:
            # 1. Tracks for subject
            # 2. Units for those tracks
            # 3. Topics for those units
            # 4. Lessons for those topics
            mock_frappe.get_all.side_effect = [
                [track],  # Memora Track for subject
                [unit],   # Memora Unit for tracks
                [topic],  # Memora Topic for units
                [lesson]  # Memora Lesson for topics
            ]

            # Mock access level calculations: subject, track, unit, topic
            mock_calc.side_effect = ["paid", "paid", "paid", "paid"]

            hierarchy = generate_subject_hierarchy(subject_doc, plan_id="PLAN-001")

            # Verify lessons are NOT in topics
            self.assertIsNotNone(hierarchy)
            self.assertIn("tracks", hierarchy)
            self.assertEqual(len(hierarchy["tracks"]), 1)

            # Traverse the hierarchy
            track_data = hierarchy["tracks"][0]
            self.assertIn("units", track_data)
            self.assertEqual(len(track_data["units"]), 1)

            unit_data = track_data["units"][0]
            self.assertIn("topics", unit_data)
            self.assertEqual(len(unit_data["topics"]), 1)

            topic_data = unit_data["topics"][0]
            # Should NOT have lessons in hierarchy
            self.assertNotIn("lessons", topic_data)
            # Should have topic_url instead
            self.assertIn("topic_url", topic_data)

        finally:
            for patcher, _ in mocks.values():
                patcher.stop()

    def test_hierarchy_is_linear_at_every_level(self):
        """T022: is_linear flag present at every hierarchy level"""
        from memora.services.cdn_export.json_generator import generate_subject_hierarchy

        mocks = self._setup_hierarchy_mocks()
        try:
            mock_frappe = mocks['frappe'][1]
            mock_calc = mocks['calc'][1]

            # Setup subject with is_linear
            subject_doc = Mock()
            subject_doc.name = "SUBJ-MATH"
            subject_doc.title = "Mathematics"
            subject_doc.description = None
            subject_doc.image = None
            subject_doc.color_code = None
            subject_doc.is_published = True
            subject_doc.is_linear = True  # Subject is linear

            track = Mock()
            track.name = "TRACK-001"
            track.title = "Track 1"
            track.is_linear = False  # Track is not linear

            unit = Mock()
            unit.name = "UNIT-001"
            unit.title = "Unit 1"
            unit.is_linear = True  # Unit is linear
            unit.parent_track = "TRACK-001"

            topic = Mock()
            topic.name = "TOPIC-001"
            topic.title = "Topic 1"
            topic.is_linear = False  # Topic is not linear
            topic.parent_unit = "UNIT-001"

            mock_frappe.get_all.side_effect = [
                [track],
                [unit],
                [topic],
                []  # No lessons
            ]

            mock_calc.side_effect = ["paid", "paid", "paid", "paid"]

            hierarchy = generate_subject_hierarchy(subject_doc, plan_id="PLAN-001")

            # Verify is_linear at every level
            self.assertEqual(hierarchy["is_linear"], True)
            self.assertEqual(hierarchy["tracks"][0]["is_linear"], False)
            self.assertEqual(hierarchy["tracks"][0]["units"][0]["is_linear"], True)
            self.assertEqual(hierarchy["tracks"][0]["units"][0]["topics"][0]["is_linear"], False)

        finally:
            for patcher, _ in mocks.values():
                patcher.stop()

    def test_hierarchy_topic_url_generation(self):
        """T023: topic_url generation pointing to topic JSON files"""
        from memora.services.cdn_export.json_generator import generate_subject_hierarchy

        mocks = self._setup_hierarchy_mocks()
        try:
            mock_frappe = mocks['frappe'][1]
            mock_calc = mocks['calc'][1]
            mock_url = mocks['url'][1]

            subject_doc = Mock()
            subject_doc.name = "SUBJ-MATH"
            subject_doc.title = "Mathematics"
            subject_doc.description = None
            subject_doc.image = None
            subject_doc.color_code = None
            subject_doc.is_published = True
            subject_doc.is_linear = False

            track = Mock()
            track.name = "TRACK-001"
            track.title = "Track 1"
            track.is_linear = False

            unit = Mock()
            unit.name = "UNIT-001"
            unit.title = "Unit 1"
            unit.is_linear = False
            unit.parent_track = "TRACK-001"

            topic = Mock()
            topic.name = "TOPIC-001"
            topic.title = "Topic 1"
            topic.is_linear = False
            topic.parent_unit = "UNIT-001"

            mock_frappe.get_all.side_effect = [
                [track],
                [unit],
                [topic],
                []
            ]

            mock_calc.side_effect = ["paid", "paid", "paid", "paid"]

            # URL resolver should format topic paths correctly
            mock_url.side_effect = lambda x: x

            hierarchy = generate_subject_hierarchy(subject_doc, plan_id="PLAN-001")

            topic_data = hierarchy["tracks"][0]["units"][0]["topics"][0]

            # Verify topic_url is present and formatted correctly
            self.assertIn("topic_url", topic_data)
            self.assertIn("plans", topic_data["topic_url"])
            self.assertIn("PLAN-001", topic_data["topic_url"])
            self.assertIn("TOPIC-001.json", topic_data["topic_url"])

        finally:
            for patcher, _ in mocks.values():
                patcher.stop()

    def test_hidden_nodes_excluded_from_hierarchy(self):
        """T024: Hidden nodes (topics) excluded from hierarchy"""
        from memora.services.cdn_export.json_generator import generate_subject_hierarchy

        mocks = self._setup_hierarchy_mocks()
        try:
            mock_frappe = mocks['frappe'][1]
            mock_calc = mocks['calc'][1]

            subject_doc = Mock()
            subject_doc.name = "SUBJ-MATH"
            subject_doc.title = "Mathematics"
            subject_doc.description = None
            subject_doc.image = None
            subject_doc.color_code = None
            subject_doc.is_published = True
            subject_doc.is_linear = False

            track = Mock()
            track.name = "TRACK-001"
            track.title = "Track 1"
            track.is_linear = False

            unit = Mock()
            unit.name = "UNIT-001"
            unit.title = "Unit 1"
            unit.is_linear = False
            unit.parent_track = "TRACK-001"

            # Two topics: one visible, one hidden
            topic1 = Mock()
            topic1.name = "TOPIC-001"
            topic1.title = "Topic 1"
            topic1.is_linear = False
            topic1.parent_unit = "UNIT-001"

            topic2 = Mock()
            topic2.name = "TOPIC-HIDDEN"
            topic2.title = "Hidden Topic"
            topic2.is_linear = False
            topic2.parent_unit = "UNIT-001"

            mock_frappe.get_all.side_effect = [
                [track],
                [unit],
                [topic1, topic2],
                []  # No lessons
            ]

            # Calls to calculate_access_level in order:
            # 1. Subject → "paid"
            # 2. Track → "paid"
            # 3. Unit → "paid"
            # 4. Topic1 → "paid" (visible)
            # 5. Topic2 → None (hidden, will be skipped)
            mock_calc.side_effect = ["paid", "paid", "paid", "paid", None]

            hierarchy = generate_subject_hierarchy(subject_doc, plan_id="PLAN-001")

            # Only topic1 should be included in the unit
            self.assertEqual(len(hierarchy["tracks"]), 1)
            self.assertEqual(len(hierarchy["tracks"][0]["units"]), 1)
            self.assertEqual(len(hierarchy["tracks"][0]["units"][0]["topics"]), 1)
            self.assertEqual(hierarchy["tracks"][0]["units"][0]["topics"][0]["id"], "TOPIC-001")

        finally:
            for patcher, _ in mocks.values():
                patcher.stop()

    def test_access_level_inheritance(self):
        """T025: Access level inheritance (paid subject → paid children)"""
        from memora.services.cdn_export.json_generator import generate_subject_hierarchy

        mocks = self._setup_hierarchy_mocks()
        try:
            mock_frappe = mocks['frappe'][1]
            mock_calc = mocks['calc'][1]

            subject_doc = Mock()
            subject_doc.name = "SUBJ-MATH"
            subject_doc.title = "Mathematics"
            subject_doc.description = None
            subject_doc.image = None
            subject_doc.color_code = None
            subject_doc.is_published = True
            subject_doc.is_linear = False

            track = Mock()
            track.name = "TRACK-001"
            track.title = "Track 1"
            track.is_linear = False

            unit = Mock()
            unit.name = "UNIT-001"
            unit.title = "Unit 1"
            unit.is_linear = False
            unit.parent_track = "TRACK-001"

            topic = Mock()
            topic.name = "TOPIC-001"
            topic.title = "Topic 1"
            topic.is_linear = False
            topic.parent_unit = "UNIT-001"

            mock_frappe.get_all.side_effect = [
                [track],
                [unit],
                [topic],
                []
            ]

            # All should inherit "paid" from subject
            mock_calc.side_effect = ["paid", "paid", "paid", "paid"]

            hierarchy = generate_subject_hierarchy(subject_doc, plan_id="PLAN-001")

            # Verify access_level inheritance
            self.assertEqual(hierarchy["access"]["access_level"], "paid")
            self.assertEqual(hierarchy["tracks"][0]["access"]["access_level"], "paid")
            self.assertEqual(hierarchy["tracks"][0]["units"][0]["access"]["access_level"], "paid")
            self.assertEqual(hierarchy["tracks"][0]["units"][0]["topics"][0]["access"]["access_level"], "paid")

        finally:
            for patcher, _ in mocks.values():
                patcher.stop()


class TestGenerateTopicJson(unittest.TestCase):
	"""Tests for generate_topic_json() function - Phase 5: User Story 3"""

	def _setup_topic_mocks(self):
		"""Helper to setup common mocks for topic tests"""
		patcher_frappe = patch('memora.services.cdn_export.json_generator.frappe')
		patcher_now = patch('memora.services.cdn_export.json_generator.now_datetime')
		patcher_overrides = patch('memora.services.cdn_export.json_generator.apply_plan_overrides')
		patcher_calc = patch('memora.services.cdn_export.json_generator.calculate_access_level')
		patcher_url = patch('memora.services.cdn_export.json_generator.get_content_url')

		mock_frappe = patcher_frappe.start()
		mock_now = patcher_now.start()
		mock_overrides = patcher_overrides.start()
		mock_calc = patcher_calc.start()
		mock_url = patcher_url.start()

		# Setup datetime - create a mock with timestamp and isoformat methods
		mock_dt = MagicMock()
		mock_dt.timestamp = Mock(return_value=1706270400)
		mock_dt.isoformat = Mock(return_value="2026-01-26T10:00:00")
		mock_now.return_value = mock_dt

		# Setup URL resolver
		mock_url.side_effect = lambda x: x

		# Setup overrides
		mock_overrides.return_value = {}

		return {
			'frappe': (patcher_frappe, mock_frappe),
			'now': (patcher_now, mock_now),
			'overrides': (patcher_overrides, mock_overrides),
			'calc': (patcher_calc, mock_calc),
			'url': (patcher_url, mock_url)
		}

	def test_generate_topic_json_with_lessons_array(self):
		"""T033: generate_topic_json() includes lessons array"""
		from memora.services.cdn_export.json_generator import generate_topic_json

		mocks = self._setup_topic_mocks()
		try:
			mock_frappe = mocks['frappe'][1]
			mock_calc = mocks['calc'][1]

			# Setup mock topic
			topic_doc = Mock()
			topic_doc.name = "TOPIC-001"
			topic_doc.title = "Introduction to Algebra"
			topic_doc.description = "Fundamentals of algebraic expressions"
			topic_doc.image = None
			topic_doc.is_linear = True
			topic_doc.is_published = True
			topic_doc.parent_unit = "UNIT-001"

			# Setup mock lessons
			lesson1 = Mock()
			lesson1.name = "LESSON-001"
			lesson1.title = "Variables"
			lesson1.description = "Learn variables"
			lesson1.is_published = True
			lesson1.bit_index = 0

			lesson2 = Mock()
			lesson2.name = "LESSON-002"
			lesson2.title = "Expressions"
			lesson2.description = "Learn expressions"
			lesson2.is_published = True
			lesson2.bit_index = 1

			# Mock frappe calls for get_doc (parent hierarchy)
			mock_frappe.get_doc.side_effect = [
				Mock(name="UNIT-001", parent_track="TRACK-001"),  # Unit
				Mock(name="TRACK-001", parent_subject="SUBJ-001"),  # Track
				Mock(name="SUBJ-001")  # Subject
			]

			# Mock frappe calls for get_all (lessons and stages)
			mock_frappe.get_all.side_effect = [
				[lesson1, lesson2],  # Lessons
				[Mock(parent="LESSON-001")] * 5,  # 5 stages for lesson 1
				[Mock(parent="LESSON-002")] * 2,  # 2 stages for lesson 2
			]

			# Mock access level calculations (topic, unit, track, subject, lesson1, lesson2)
			mock_calc.side_effect = ["paid", "paid", "paid", "paid", "paid", "paid"]

			topic = generate_topic_json(topic_doc, plan_id="PLAN-001")

			# Verify lessons array structure
			self.assertIsNotNone(topic)
			self.assertIn("lessons", topic)
			self.assertEqual(len(topic["lessons"]), 2)

			# Verify each lesson has required fields
			for lesson in topic["lessons"]:
				self.assertIn("id", lesson)
				self.assertIn("title", lesson)
				self.assertIn("bit_index", lesson)
				self.assertIn("lesson_url", lesson)
				self.assertIn("access", lesson)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_bit_index_included_per_lesson(self):
		"""T034: bit_index included per lesson in topic JSON"""
		from memora.services.cdn_export.json_generator import generate_topic_json

		mocks = self._setup_topic_mocks()
		try:
			mock_frappe = mocks['frappe'][1]
			mock_calc = mocks['calc'][1]

			topic_doc = Mock()
			topic_doc.name = "TOPIC-ALGEBRA-1"
			topic_doc.title = "Intro to Algebra"
			topic_doc.description = None
			topic_doc.image = None
			topic_doc.is_linear = True
			topic_doc.is_published = True
			topic_doc.parent_unit = "UNIT-ALGEBRA"

			lesson1 = Mock()
			lesson1.name = "LESSON-MATH-001"
			lesson1.title = "Lesson 1"
			lesson1.description = None
			lesson1.is_published = True
			lesson1.bit_index = 0

			lesson2 = Mock()
			lesson2.name = "LESSON-MATH-002"
			lesson2.title = "Lesson 2"
			lesson2.description = None
			lesson2.is_published = True
			lesson2.bit_index = 1

			# Mock frappe calls - need to set up unit/track/subject hierarchy
			mock_frappe.get_doc.side_effect = [
				Mock(parent_unit="UNIT-ALGEBRA"),  # For topic's parent lookup
				Mock(name="UNIT-ALGEBRA", parent_track="TRACK-MATH-CORE"),  # For unit's parent lookup
				Mock(name="TRACK-MATH-CORE", parent_subject="SUBJ-MATH"),  # For track's parent lookup
				Mock(name="SUBJ-MATH")  # For subject
			]

			mock_frappe.get_all.side_effect = [
				[lesson1, lesson2],  # Lessons
				[Mock(parent="LESSON-MATH-001")] * 3,  # 3 stages for lesson1
				[Mock(parent="LESSON-MATH-002")] * 2,  # 2 stages for lesson2
			]

			mock_calc.side_effect = ["paid", "paid", "paid", "paid", "paid", "paid"]

			topic = generate_topic_json(topic_doc, plan_id="PLAN-001", subject_id="SUBJ-MATH")

			self.assertIsNotNone(topic)
			self.assertIn("lessons", topic)
			lessons = topic["lessons"]
			self.assertEqual(len(lessons), 2)

			# Verify bit_index values from lesson documents
			self.assertEqual(lessons[0]["bit_index"], 0)
			self.assertEqual(lessons[1]["bit_index"], 1)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_lesson_url_pointing_to_shared_lessons(self):
		"""T035: lesson_url pointing to shared lessons/{lesson_id}.json"""
		from memora.services.cdn_export.json_generator import generate_topic_json

		mocks = self._setup_topic_mocks()
		try:
			mock_frappe = mocks['frappe'][1]
			mock_calc = mocks['calc'][1]
			mock_url = mocks['url'][1]

			topic_doc = Mock()
			topic_doc.name = "TOPIC-ALGEBRA-1"
			topic_doc.title = "Intro to Algebra"
			topic_doc.description = None
			topic_doc.image = None
			topic_doc.is_linear = True
			topic_doc.is_published = True
			topic_doc.parent_unit = "UNIT-ALGEBRA"

			lesson1 = Mock()
			lesson1.name = "LESSON-MATH-001"
			lesson1.title = "Lesson 1"
			lesson1.description = None
			lesson1.is_published = True
			lesson1.bit_index = 0

			mock_frappe.get_doc.side_effect = [
				Mock(parent_unit="UNIT-ALGEBRA"),
				Mock(name="UNIT-ALGEBRA", parent_track="TRACK-MATH-CORE"),
				Mock(name="TRACK-MATH-CORE", parent_subject="SUBJ-MATH"),
				Mock(name="SUBJ-MATH")
			]

			mock_frappe.get_all.side_effect = [
				[lesson1],  # Lessons
				[Mock(parent="LESSON-MATH-001")],  # Stages
			]

			mock_calc.side_effect = ["paid", "paid", "paid", "paid", "paid"]

			# URL resolver formats the lesson path
			mock_url.side_effect = lambda x: x

			topic = generate_topic_json(topic_doc, plan_id="PLAN-001", subject_id="SUBJ-MATH")

			self.assertIsNotNone(topic)
			self.assertIn("lessons", topic)
			lesson = topic["lessons"][0]
			self.assertIn("lesson_url", lesson)
			self.assertIn("lessons", lesson["lesson_url"])
			self.assertIn("LESSON-MATH-001.json", lesson["lesson_url"])

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_parent_breadcrumb_in_topic_json(self):
		"""T036: parent breadcrumb (unit_id, track_id, subject_id) in topic JSON"""
		from memora.services.cdn_export.json_generator import generate_topic_json

		mocks = self._setup_topic_mocks()
		try:
			mock_frappe = mocks['frappe'][1]
			mock_calc = mocks['calc'][1]

			topic_doc = Mock()
			topic_doc.name = "TOPIC-ALGEBRA-1"
			topic_doc.title = "Intro to Algebra"
			topic_doc.description = None
			topic_doc.image = None
			topic_doc.is_linear = True
			topic_doc.is_published = True
			topic_doc.parent_unit = "UNIT-ALGEBRA"

			# Setup parent documents
			unit_doc = Mock()
			unit_doc.name = "UNIT-ALGEBRA"
			unit_doc.title = "Algebra Fundamentals"
			unit_doc.parent_track = "TRACK-MATH-CORE"

			track_doc = Mock()
			track_doc.name = "TRACK-MATH-CORE"
			track_doc.title = "Core Mathematics"
			track_doc.parent_subject = "SUBJ-MATH"

			subject_doc = Mock()
			subject_doc.name = "SUBJ-MATH"
			subject_doc.title = "Mathematics"

			mock_frappe.get_doc.side_effect = [unit_doc, track_doc, subject_doc, subject_doc]

			lesson1 = Mock()
			lesson1.name = "LESSON-MATH-001"
			lesson1.title = "Lesson 1"
			lesson1.description = None
			lesson1.is_published = True
			lesson1.bit_index = 0

			mock_frappe.get_all.side_effect = [
				[lesson1],  # Lessons
				[Mock(parent="LESSON-MATH-001")],  # Stages
			]

			mock_calc.side_effect = ["paid", "paid", "paid", "paid", "paid"]

			topic = generate_topic_json(topic_doc, plan_id="PLAN-001", subject_id="SUBJ-MATH")

			self.assertIsNotNone(topic)
			self.assertIn("parent", topic)
			self.assertEqual(topic["parent"]["unit_id"], "UNIT-ALGEBRA")
			self.assertEqual(topic["parent"]["unit_title"], "Algebra Fundamentals")
			self.assertEqual(topic["parent"]["track_id"], "TRACK-MATH-CORE")
			self.assertEqual(topic["parent"]["track_title"], "Core Mathematics")
			self.assertEqual(topic["parent"]["subject_id"], "SUBJ-MATH")
			self.assertEqual(topic["parent"]["subject_title"], "Mathematics")

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_hidden_lessons_excluded_from_topic(self):
		"""T037: hidden lessons excluded from topic"""
		from memora.services.cdn_export.json_generator import generate_topic_json

		mocks = self._setup_topic_mocks()
		try:
			mock_frappe = mocks['frappe'][1]
			mock_calc = mocks['calc'][1]

			topic_doc = Mock()
			topic_doc.name = "TOPIC-ALGEBRA-1"
			topic_doc.title = "Intro to Algebra"
			topic_doc.description = None
			topic_doc.image = None
			topic_doc.is_linear = True
			topic_doc.is_published = True
			topic_doc.parent_unit = "UNIT-ALGEBRA"

			# Visible lesson
			lesson1 = Mock()
			lesson1.name = "LESSON-MATH-001"
			lesson1.title = "Lesson 1"
			lesson1.description = None
			lesson1.is_published = True
			lesson1.bit_index = 0

			# Hidden lesson (will return None access_level)
			lesson2 = Mock()
			lesson2.name = "LESSON-MATH-002"
			lesson2.title = "Lesson 2"
			lesson2.description = None
			lesson2.is_published = False
			lesson2.bit_index = 1

			mock_frappe.get_doc.side_effect = [
				Mock(parent_unit="UNIT-ALGEBRA"),
				Mock(name="UNIT-ALGEBRA", parent_track="TRACK-MATH-CORE"),
				Mock(name="TRACK-MATH-CORE", parent_subject="SUBJ-MATH"),
				Mock(name="SUBJ-MATH")
			]

			mock_frappe.get_all.side_effect = [
				[lesson1, lesson2],  # Lessons
				[Mock(parent="LESSON-MATH-001")],  # Stages for lesson1
				[Mock(parent="LESSON-MATH-002")],  # Stages for lesson2
			]

			# Lesson2 is hidden (access_level=None)
			mock_calc.side_effect = ["paid", "paid", "paid", "paid", "paid", None]

			topic = generate_topic_json(topic_doc, plan_id="PLAN-001", subject_id="SUBJ-MATH")

			self.assertIsNotNone(topic)
			self.assertIn("lessons", topic)
			# Only visible lesson should be in output
			lessons = topic["lessons"]
			self.assertEqual(len(lessons), 1)
			self.assertEqual(lessons[0]["id"], "LESSON-MATH-001")

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()


class TestGenerateLessonJsonShared(unittest.TestCase):
	"""Tests for generate_lesson_json_shared() function - Phase 6: User Story 4"""

	def _setup_lesson_mocks(self):
		"""Helper to setup common mocks for shared lesson tests"""
		patcher_frappe = patch('memora.services.cdn_export.json_generator.frappe')
		patcher_now = patch('memora.services.cdn_export.json_generator.now_datetime')
		patcher_schema = patch('memora.services.cdn_export.json_generator.validate_lesson_json_against_schema')

		mock_frappe = patcher_frappe.start()
		mock_now = patcher_now.start()
		mock_schema = patcher_schema.start()

		# Setup datetime - create a mock with timestamp and isoformat methods
		mock_dt = MagicMock()
		mock_dt.timestamp = Mock(return_value=1706270400)
		mock_dt.isoformat = Mock(return_value="2026-01-26T10:00:00")
		mock_now.return_value = mock_dt

		# Setup schema validation - default to valid
		mock_schema.return_value = (True, [])

		return {
			'frappe': (patcher_frappe, mock_frappe),
			'now': (patcher_now, mock_now),
			'schema': (patcher_schema, mock_schema)
		}

	def test_generate_lesson_json_shared_with_stages_array(self):
		"""T045: generate_lesson_json_shared() includes stages array"""
		from memora.services.cdn_export.json_generator import generate_lesson_json_shared

		mocks = self._setup_lesson_mocks()
		try:
			mock_frappe = mocks['frappe'][1]

			# Setup mock lesson
			lesson_doc = Mock()
			lesson_doc.name = "LESSON-MATH-001"
			lesson_doc.title = "Variables and Expressions"
			lesson_doc.description = "Learn about variables"

			# Setup mock stages
			stage1 = Mock()
			stage1.idx = 1
			stage1.title = "Introduction Video"
			stage1.type = "Video"
			stage1.weight = 1.0
			stage1.target_time = 180
			stage1.is_skippable = False
			stage1.config = '{"video_url": "https://cdn.example.com/videos/intro.mp4"}'

			stage2 = Mock()
			stage2.idx = 2
			stage2.title = "Practice Question"
			stage2.type = "Question"
			stage2.weight = 2.0
			stage2.target_time = 60
			stage2.is_skippable = False
			stage2.config = '{"question": "What is 2x when x=3?", "options": ["4", "5", "6", "7"]}'

			# Mock frappe.get_all for stages
			mock_frappe.get_all.return_value = [stage1, stage2]

			lesson = generate_lesson_json_shared(lesson_doc)

			# Verify lesson structure
			self.assertIsNotNone(lesson)
			self.assertIn("stages", lesson)
			self.assertEqual(len(lesson["stages"]), 2)

			# Verify each stage has required fields
			for stage in lesson["stages"]:
				self.assertIn("idx", stage)
				self.assertIn("title", stage)
				self.assertIn("type", stage)
				self.assertIn("config", stage)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_no_access_block_in_shared_lesson_json(self):
		"""T046: Shared lesson JSON has NO access block"""
		from memora.services.cdn_export.json_generator import generate_lesson_json_shared

		mocks = self._setup_lesson_mocks()
		try:
			mock_frappe = mocks['frappe'][1]

			lesson_doc = Mock()
			lesson_doc.name = "LESSON-001"
			lesson_doc.title = "Lesson 1"
			lesson_doc.description = None

			stage1 = Mock()
			stage1.idx = 1
			stage1.title = "Stage 1"
			stage1.type = "Video"
			stage1.weight = 1.0
			stage1.target_time = 100
			stage1.is_skippable = False
			stage1.config = '{}'

			mock_frappe.get_all.return_value = [stage1]

			lesson = generate_lesson_json_shared(lesson_doc)

			# Verify NO access block in output
			self.assertIsNotNone(lesson)
			self.assertNotIn("access", lesson)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_no_parent_block_in_shared_lesson_json(self):
		"""T047: Shared lesson JSON has NO parent block"""
		from memora.services.cdn_export.json_generator import generate_lesson_json_shared

		mocks = self._setup_lesson_mocks()
		try:
			mock_frappe = mocks['frappe'][1]

			lesson_doc = Mock()
			lesson_doc.name = "LESSON-001"
			lesson_doc.title = "Lesson 1"
			lesson_doc.description = None

			stage1 = Mock()
			stage1.idx = 1
			stage1.title = "Stage 1"
			stage1.type = "Text"
			stage1.weight = 1.0
			stage1.target_time = None
			stage1.is_skippable = True
			stage1.config = '{"content": "Some text"}'

			mock_frappe.get_all.return_value = [stage1]

			lesson = generate_lesson_json_shared(lesson_doc)

			# Verify NO parent block in output
			self.assertIsNotNone(lesson)
			self.assertNotIn("parent", lesson)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_navigation_is_standalone_true(self):
		"""T048: Shared lesson JSON has navigation.is_standalone=true"""
		from memora.services.cdn_export.json_generator import generate_lesson_json_shared

		mocks = self._setup_lesson_mocks()
		try:
			mock_frappe = mocks['frappe'][1]

			lesson_doc = Mock()
			lesson_doc.name = "LESSON-001"
			lesson_doc.title = "Test Lesson"
			lesson_doc.description = None

			stage1 = Mock()
			stage1.idx = 1
			stage1.title = "Stage"
			stage1.type = "Interactive"
			stage1.weight = 1.5
			stage1.target_time = 120
			stage1.is_skippable = True
			stage1.config = '{"interactive_id": "123"}'

			mock_frappe.get_all.return_value = [stage1]

			lesson = generate_lesson_json_shared(lesson_doc)

			# Verify navigation block with is_standalone=true
			self.assertIsNotNone(lesson)
			self.assertIn("navigation", lesson)
			self.assertIn("is_standalone", lesson["navigation"])
			self.assertTrue(lesson["navigation"]["is_standalone"])

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()

	def test_stage_fields_complete(self):
		"""T049: Stage fields (idx, title, type, weight, target_time, is_skippable, config) present"""
		from memora.services.cdn_export.json_generator import generate_lesson_json_shared

		mocks = self._setup_lesson_mocks()
		try:
			mock_frappe = mocks['frappe'][1]

			lesson_doc = Mock()
			lesson_doc.name = "LESSON-001"
			lesson_doc.title = "Complete Stage Test"
			lesson_doc.description = "Test all stage fields"

			stage1 = Mock()
			stage1.idx = 1
			stage1.title = "Full Stage"
			stage1.type = "Question"
			stage1.weight = 2.5
			stage1.target_time = 300
			stage1.is_skippable = True
			stage1.config = '{"complex": "config"}'

			mock_frappe.get_all.return_value = [stage1]

			lesson = generate_lesson_json_shared(lesson_doc)

			# Verify stage has all required fields
			self.assertIsNotNone(lesson)
			self.assertIn("stages", lesson)
			stage = lesson["stages"][0]
			self.assertIn("idx", stage)
			self.assertEqual(stage["idx"], 1)
			self.assertIn("title", stage)
			self.assertEqual(stage["title"], "Full Stage")
			self.assertIn("type", stage)
			self.assertEqual(stage["type"], "Question")
			self.assertIn("weight", stage)
			self.assertEqual(stage["weight"], 2.5)
			self.assertIn("target_time", stage)
			self.assertEqual(stage["target_time"], 300)
			self.assertIn("is_skippable", stage)
			self.assertTrue(stage["is_skippable"])
			self.assertIn("config", stage)

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()


class TestGenerateBitmapJson(unittest.TestCase):
	"""Tests for generate_bitmap_json() function - Phase 7: User Story 5"""

	def _setup_bitmap_mocks(self):
		"""Helper to setup common mocks for bitmap tests"""
		patcher_frappe = patch('memora.services.cdn_export.json_generator.frappe')
		patcher_now = patch('memora.services.cdn_export.json_generator.now_datetime')

		mock_frappe = patcher_frappe.start()
		mock_now = patcher_now.start()

		# Setup datetime
		mock_dt = MagicMock()
		mock_dt.timestamp = Mock(return_value=1706270400)
		mock_dt.isoformat = Mock(return_value="2026-01-26T10:00:00")
		mock_now.return_value = mock_dt

		return {
			'frappe': (patcher_frappe, mock_frappe),
			'now': (patcher_now, mock_now),
		}

	def test_generate_bitmap_json_structure(self):
		"""T057: Validate bitmap JSON structure (subject_id, mappings)"""
		from memora.services.cdn_export.json_generator import generate_bitmap_json

		mocks = self._setup_bitmap_mocks()
		try:
			mock_frappe = mocks['frappe'][1]

			# Setup mock subject
			subject_doc = Mock()
			subject_doc.name = "SUBJ-001"

			# Setup mock lessons with topics
			lesson1 = Mock()
			lesson1.name = "LESSON-001"
			lesson1.parent_topic = "TOPIC-001"

			lesson2 = Mock()
			lesson2.name = "LESSON-002"
			lesson2.parent_topic = "TOPIC-001"

			lesson3 = Mock()
			lesson3.name = "LESSON-003"
			lesson3.parent_topic = "TOPIC-002"

			# Mock get_all to return lessons with docstatus=1 (submitted)
			def mock_get_all(doctype, filters=None, fields=None, order_by=None):
				if doctype == "Memora Lesson" and filters:
					return [lesson1, lesson2, lesson3]
				return []

			mock_frappe.get_all.side_effect = mock_get_all

			bitmap = generate_bitmap_json(subject_doc)

			# Assertions
			self.assertIsNotNone(bitmap)
			self.assertEqual(bitmap["subject_id"], "SUBJ-001")
			self.assertEqual(bitmap["total_lessons"], 3)
			self.assertIn("mappings", bitmap)
			self.assertEqual(len(bitmap["mappings"]), 3)

			# Verify each lesson has bit_index and topic_id
			self.assertIn("LESSON-001", bitmap["mappings"])
			self.assertIn("bit_index", bitmap["mappings"]["LESSON-001"])
			self.assertIn("topic_id", bitmap["mappings"]["LESSON-001"])
			self.assertEqual(bitmap["mappings"]["LESSON-001"]["topic_id"], "TOPIC-001")

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()


class TestAtomicConsistency(unittest.TestCase):
	"""Tests for atomic file consistency - Phase 7: User Story 5"""

	def test_atomic_consistency_staging_and_swap(self):
		"""T058: Verify two-phase commit with staging then swap"""
		# This test would require mocking file operations
		# For now, we document the test structure
		pass

	def test_rollback_on_generation_failure(self):
		"""T059: Verify rollback deletes staging files on failure"""
		# This test would require mocking file operations and failure scenarios
		# For now, we document the test structure
		pass


class TestGetAtomicContentPaths(unittest.TestCase):
	"""Tests for get_atomic_content_paths_for_plan() function - Phase 7: User Story 5"""

	def _setup_mocks(self):
		"""Helper to setup common mocks"""
		patcher_frappe = patch('memora.services.cdn_export.json_generator.frappe')
		mock_frappe = patcher_frappe.start()
		return {
			'frappe': (patcher_frappe, mock_frappe),
		}

	def test_get_atomic_content_paths_returns_correct_file_paths(self):
		"""T060: Verify get_atomic_content_paths_for_plan() returns correct paths"""
		from memora.services.cdn_export.json_generator import get_atomic_content_paths_for_plan

		mocks = self._setup_mocks()
		try:
			mock_frappe = mocks['frappe'][1]

			# Setup mock plan with subjects and topics
			plan_subject1 = Mock()
			plan_subject1.subject = "SUBJ-001"

			plan_subject2 = Mock()
			plan_subject2.subject = "SUBJ-002"

			topic1 = Mock()
			topic1.name = "TOPIC-001"

			topic2 = Mock()
			topic2.name = "TOPIC-002"

			lesson1 = Mock()
			lesson1.name = "LESSON-001"

			lesson2 = Mock()
			lesson2.name = "LESSON-002"

			def mock_get_all(doctype, filters=None, fields=None):
				if doctype == "Memora Academic Plan Subject" and filters:
					return [plan_subject1, plan_subject2]
				elif doctype == "Memora Topic" and filters:
					return [topic1, topic2]
				elif doctype == "Memora Lesson" and filters:
					return [lesson1, lesson2]
				return []

			mock_frappe.get_all.side_effect = mock_get_all

			paths = get_atomic_content_paths_for_plan("PLAN-001")

			# Assertions
			self.assertIsNotNone(paths)
			self.assertIn("manifest", paths)
			self.assertIn("hierarchies", paths)
			self.assertIn("bitmaps", paths)
			self.assertIn("topics", paths)
			self.assertIn("lessons", paths)

			# Verify structure
			self.assertEqual(paths["manifest"], "plans/PLAN-001/manifest.json")
			self.assertIn("plans/PLAN-001/SUBJ-001_h.json", paths["hierarchies"])
			self.assertIn("plans/PLAN-001/SUBJ-001_b.json", paths["bitmaps"])

		finally:
			for patcher, _ in mocks.values():
				patcher.stop()


if __name__ == '__main__':
    unittest.main()
