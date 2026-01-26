"""Fixtures for CDN export unit tests.

This module provides sample DocType data structures for testing the atomic JSON
generation pipeline without hitting the database.
"""

import json
from typing import Any, Dict


def get_sample_academic_plan() -> Dict[str, Any]:
	"""Get a sample Memora Academic Plan document.

	Returns a basic plan with a single subject and hierarchy for testing.
	"""
	return {
		"doctype": "Memora Academic Plan",
		"name": "PLAN-TEST-001",
		"plan_title": "Test Plan",
		"season": "2026",
		"grade": "Grade 10",
		"stream": "General",
		"published": 1,
		"subjects": [
			{
				"doctype": "Memora Plan Subject",
				"subject": "SUBJ-MATH",
				"idx": 1,
			},
			{
				"doctype": "Memora Plan Subject",
				"subject": "SUBJ-SCI",
				"idx": 2,
			},
		],
		"overrides": [],
	}


def get_sample_subject() -> Dict[str, Any]:
	"""Get a sample Memora Subject document with hierarchy."""
	return {
		"doctype": "Memora Subject",
		"name": "SUBJ-MATH",
		"subject_title": "Mathematics",
		"subject_description": "Core Mathematics",
		"is_public": 1,
		"is_linear": 0,
		"color_code": "#3B82F6",
		"image": "/files/math.png",
		"published": 1,
		"tracks": [
			{
				"doctype": "Memora Track",
				"name": "TRACK-ALG",
				"track_title": "Algebra",
				"is_linear": 1,
				"published": 1,
				"units": [
					{
						"doctype": "Memora Unit",
						"name": "UNIT-LINEAR-EQ",
						"unit_title": "Linear Equations",
						"published": 1,
						"topics": [
							{
								"doctype": "Memora Topic",
								"name": "TOPIC-EQ-SOLVING",
								"topic_title": "Solving Equations",
								"published": 1,
								"lessons": [
									{
										"doctype": "Memora Lesson",
										"name": "LESSON-EQ-001",
										"lesson_title": "Lesson 1",
										"published": 1,
										"idx": 1,
									},
									{
										"doctype": "Memora Lesson",
										"name": "LESSON-EQ-002",
										"lesson_title": "Lesson 2",
										"published": 1,
										"idx": 2,
									},
								],
								"idx": 1,
							},
						],
						"idx": 1,
					},
				],
				"idx": 1,
			},
		],
	}


def get_sample_lesson() -> Dict[str, Any]:
	"""Get a sample Memora Lesson document with stages."""
	return {
		"doctype": "Memora Lesson",
		"name": "LESSON-EQ-001",
		"lesson_title": "Introduction to Linear Equations",
		"lesson_description": "Learn the basics",
		"published": 1,
		"stages": [
			{
				"doctype": "Memora Lesson Stage",
				"title": "Stage 1: Introduction",
				"stage_type": "interactive_content",
				"weight": 1,
				"target_time": 300,
				"is_skippable": 0,
				"config": json.dumps(
					{
						"content_type": "html",
						"content_url": "/files/stage1.html",
					}
				),
				"idx": 1,
			},
			{
				"doctype": "Memora Lesson Stage",
				"title": "Stage 2: Practice",
				"stage_type": "quiz",
				"weight": 2,
				"target_time": 600,
				"is_skippable": 1,
				"config": json.dumps(
					{
						"quiz_id": "QUIZ-EQ-001",
						"passing_score": 80,
					}
				),
				"idx": 2,
			},
		],
	}


def get_sample_plan_override() -> Dict[str, Any]:
	"""Get a sample Memora Plan Override for testing override logic."""
	return {
		"doctype": "Memora Plan Override",
		"name": "OVERRIDE-001",
		"plan": "PLAN-TEST-001",
		"target_doctype": "Memora Subject",
		"target_name": "SUBJ-MATH",
		"action": "Set Access Level",
		"action_value": "free_preview",
	}


def get_manifest_fixture() -> Dict[str, Any]:
	"""Get a sample generated manifest.json for assertions."""
	return {
		"plan_id": "PLAN-TEST-001",
		"title": "Test Plan",
		"season": "2026",
		"grade": "Grade 10",
		"stream": "General",
		"version": 1706270400,
		"generated_at": "2026-01-26T10:00:00Z",
		"subjects": [
			{
				"id": "SUBJ-MATH",
				"title": "Mathematics",
				"description": "Core Mathematics",
				"image": "/files/math.png",
				"color_code": "#3B82F6",
				"is_linear": False,
				"hierarchy_url": "plans/PLAN-TEST-001/SUBJ-MATH_h.json",
				"bitmap_url": "plans/PLAN-TEST-001/SUBJ-MATH_b.json",
				"access": {
					"is_published": True,
					"access_level": "public",
					"required_item": None,
				},
			},
			{
				"id": "SUBJ-SCI",
				"title": "Science",
				"description": "Core Science",
				"image": "/files/science.png",
				"color_code": "#10B981",
				"is_linear": False,
				"hierarchy_url": "plans/PLAN-TEST-001/SUBJ-SCI_h.json",
				"bitmap_url": "plans/PLAN-TEST-001/SUBJ-SCI_b.json",
				"access": {
					"is_published": True,
					"access_level": "public",
					"required_item": None,
				},
			},
		],
		"search_index_url": "plans/PLAN-TEST-001/search_index.json",
	}


def get_hierarchy_fixture() -> Dict[str, Any]:
	"""Get a sample generated subject hierarchy JSON."""
	return {
		"subject_id": "SUBJ-MATH",
		"title": "Mathematics",
		"is_linear": False,
		"description": "Core Mathematics",
		"access": {
			"is_published": True,
			"access_level": "public",
		},
		"stats": {
			"total_tracks": 1,
			"total_units": 1,
			"total_topics": 1,
			"total_lessons": 2,
		},
		"tracks": [
			{
				"id": "TRACK-ALG",
				"title": "Algebra",
				"is_linear": True,
				"access": {
					"is_published": True,
					"access_level": "public",
				},
				"units": [
					{
						"id": "UNIT-LINEAR-EQ",
						"title": "Linear Equations",
						"is_linear": True,
						"access": {
							"is_published": True,
							"access_level": "public",
						},
						"topics": [
							{
								"id": "TOPIC-EQ-SOLVING",
								"title": "Solving Equations",
								"is_linear": True,
								"topic_url": "plans/PLAN-TEST-001/TOPIC-EQ-SOLVING.json",
								"lesson_count": 2,
								"access": {
									"is_published": True,
									"access_level": "public",
								},
							}
						],
					}
				],
			}
		],
	}


def get_topic_fixture() -> Dict[str, Any]:
	"""Get a sample generated topic JSON."""
	return {
		"topic_id": "TOPIC-EQ-SOLVING",
		"title": "Solving Equations",
		"is_linear": True,
		"parent": {
			"unit_id": "UNIT-LINEAR-EQ",
			"track_id": "TRACK-ALG",
			"subject_id": "SUBJ-MATH",
		},
		"lessons": [
			{
				"id": "LESSON-EQ-001",
				"title": "Lesson 1",
				"idx": 1,
				"bit_index": 0,
				"stage_count": 2,
				"lesson_url": "lessons/LESSON-EQ-001.json",
				"access": {
					"is_published": True,
					"access_level": "public",
				},
			},
			{
				"id": "LESSON-EQ-002",
				"title": "Lesson 2",
				"idx": 2,
				"bit_index": 1,
				"stage_count": 1,
				"lesson_url": "lessons/LESSON-EQ-002.json",
				"access": {
					"is_published": True,
					"access_level": "public",
				},
			},
		],
	}


def get_lesson_fixture() -> Dict[str, Any]:
	"""Get a sample generated shared lesson JSON."""
	return {
		"lesson_id": "LESSON-EQ-001",
		"title": "Introduction to Linear Equations",
		"description": "Learn the basics",
		"navigation": {
			"is_standalone": True,
		},
		"stages": [
			{
				"idx": 1,
				"title": "Stage 1: Introduction",
				"type": "interactive_content",
				"weight": 1,
				"target_time": 300,
				"is_skippable": False,
				"config": {
					"content_type": "html",
					"content_url": "/files/stage1.html",
				},
			},
			{
				"idx": 2,
				"title": "Stage 2: Practice",
				"type": "quiz",
				"weight": 2,
				"target_time": 600,
				"is_skippable": True,
				"config": {
					"quiz_id": "QUIZ-EQ-001",
					"passing_score": 80,
				},
			},
		],
	}


def get_bitmap_fixture() -> Dict[str, Any]:
	"""Get a sample generated subject bitmap JSON."""
	return {
		"subject_id": "SUBJ-MATH",
		"plan_id": "PLAN-TEST-001",
		"mappings": [
			{
				"bit_index": 0,
				"lesson_id": "LESSON-EQ-001",
				"topic_id": "TOPIC-EQ-SOLVING",
				"unit_id": "UNIT-LINEAR-EQ",
				"track_id": "TRACK-ALG",
			},
			{
				"bit_index": 1,
				"lesson_id": "LESSON-EQ-002",
				"topic_id": "TOPIC-EQ-SOLVING",
				"unit_id": "UNIT-LINEAR-EQ",
				"track_id": "TRACK-ALG",
			},
		],
	}
