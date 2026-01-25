"""
Unit tests for health_checker module.
"""
import unittest
from unittest.mock import patch, MagicMock, Mock
import frappe
from memora.services.cdn_export.health_checker import (
    is_business_hours,
    hourly_health_check,
    daily_full_scan,
    send_disk_alert,
    send_sync_failure_alert
)
from datetime import datetime, timezone


class TestBusinessHours(unittest.TestCase):
    """Test business hours detection logic."""

    @patch('memora.services.cdn_export.health_checker.datetime')
    def test_hourly_check_skips_outside_business_hours(self, mock_datetime):
        """Test that hourly health check skips execution outside business hours."""
        # Simulate 7:59 AM (before business hours start)
        mock_datetime.now.return_value = datetime(2026, 1, 25, 7, 59, 0)
        
        with patch('memora.services.cdn_export.health_checker.check_disk_space') as mock_disk_check:
            hourly_health_check()
            # Disk check should not be called
            mock_disk_check.assert_not_called()

    @patch('memora.services.cdn_export.health_checker.is_business_hours')
    @patch('memora.services.cdn_export.health_checker.datetime')
    def test_hourly_check_runs_during_business_hours(self, mock_datetime, mock_is_business):
        """Test that hourly health check runs during business hours."""
        mock_is_business.return_value = True
        # Simulate 10:00 AM (during business hours)
        mock_datetime.now.return_value = datetime(2026, 1, 25, 10, 0, 0)
        
        with patch('memora.services.cdn_export.health_checker.check_disk_space') as mock_disk_check:
            with patch('memora.services.cdn_export.health_checker._sample_random_files') as mock_sample:
                mock_disk_check.return_value = (True, 45.0)
                mock_sample.return_value = {'sampled': 100, 'missing': []}
                
                report = hourly_health_check()
                
                # Disk check should be called
                self.assertEqual(mock_disk_check.call_count, 1)
                self.assertEqual(report['status'], 'healthy')

    @patch('memora.services.cdn_export.health_checker.datetime')
    def test_hourly_check_skips_on_weekend(self, mock_datetime):
        """Test that hourly health check skips on weekends."""
        # Simulate Saturday at 10:00 AM
        mock_now = Mock()
        mock_now.hour = 10
        mock_now.weekday.return_value = 5  # Saturday
        mock_datetime.now.return_value = mock_now
        
        with patch('memora.services.cdn_export.health_checker.check_disk_space') as mock_disk_check:
            hourly_health_check()
            # Disk check should not be called
            mock_disk_check.assert_not_called()

    @patch('memora.services.cdn_export.health_checker.datetime')
    def test_hourly_check_skips_after_business_hours(self, mock_datetime):
        """Test that hourly health check skips after 6 PM."""
        # Simulate 6:01 PM (after business hours)
        mock_datetime.now.return_value = datetime(2026, 1, 25, 18, 1, 0)
        
        with patch('memora.services.cdn_export.health_checker.check_disk_space') as mock_disk_check:
            hourly_health_check()
            # Disk check should not be called
            mock_disk_check.assert_not_called()


class TestHourlyHealthCheck(unittest.TestCase):
    """Test hourly health check functionality."""

    @patch('memora.services.cdn_export.health_checker.is_business_hours')
    @patch('memora.services.cdn_export.health_checker.check_disk_space')
    @patch('memora.services.cdn_export.health_checker._sample_random_files')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_hourly_check_samples_files(self, mock_frappe, mock_sample, mock_disk_check, mock_is_business):
        """Test that hourly check samples random files."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_is_business.return_value = True
        mock_disk_check.return_value = (True, 45.0)
        mock_sample.return_value = {'sampled': 100, 'missing': []}
        
        report = hourly_health_check()
        
        # Should sample files
        self.assertEqual(mock_sample.call_count, 1)
        self.assertEqual(mock_sample.call_args[0][0], 100)
        self.assertEqual(report['sample_files_checked'], 100)
        self.assertEqual(report['missing_files'], [])
        self.assertEqual(report['status'], 'healthy')

    @patch('memora.services.cdn_export.health_checker.is_business_hours')
    @patch('memora.services.cdn_export.health_checker.check_disk_space')
    @patch('memora.services.cdn_export.health_checker._sample_random_files')
    @patch('memora.services.cdn_export.health_checker.send_disk_alert')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_hourly_check_detects_disk_low(self, mock_frappe, mock_alert, mock_sample, mock_disk_check, mock_is_business):
        """Test that hourly check detects low disk space."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_is_business.return_value = True
        mock_disk_check.return_value = (False, 5.0)  # 5% free, below 10% threshold
        mock_sample.return_value = {'sampled': 100, 'missing': []}
        
        report = hourly_health_check()
        
        self.assertEqual(report['disk_free_percent'], 5.0)
        self.assertEqual(report['disk_ok'], False)
        self.assertEqual(report['status'], 'critical')

    @patch('memora.services.cdn_export.health_checker.is_business_hours')
    @patch('memora.services.cdn_export.health_checker.check_disk_space')
    @patch('memora.services.cdn_export.health_checker._sample_random_files')
    @patch('memora.services.cdn_export.health_checker.send_disk_alert')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_disk_alert_sent_below_threshold(self, mock_frappe, mock_alert, mock_sample, mock_disk_check, mock_is_business):
        """Test that disk alert is sent when space is below threshold."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_is_business.return_value = True
        mock_disk_check.return_value = (False, 5.0)  # Below 10% threshold
        mock_sample.return_value = {'sampled': 100, 'missing': []}
        
        hourly_health_check()
        
        # Alert should be sent
        mock_alert.assert_called_once_with(5.0)


class TestDailyFullScan(unittest.TestCase):
    """Test daily full scan functionality."""

    @patch('memora.services.cdn_export.health_checker.check_disk_space')
    @patch('memora.services.cdn_export.health_checker._get_expected_files_from_db')
    @patch('memora.services.cdn_export.health_checker._verify_files_exist')
    @patch('memora.services.cdn_export.health_checker._find_orphan_files')
    @patch('memora.services.cdn_export.health_checker._queue_regeneration_for_missing_files')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_daily_scan_finds_missing_files(self, mock_frappe, mock_queue, mock_orphans, mock_verify, mock_expected, mock_disk):
        """Test that daily scan identifies missing files."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_disk.return_value = (True, 45.0)
        mock_expected.return_value = [
            'plans/PLAN-001/manifest.json',
            'units/UNIT-001.json',
            'lessons/LESSON-001.json'
        ]
        mock_verify.return_value = ['units/UNIT-001.json']  # This file is missing
        mock_orphans.return_value = []
        
        report = daily_full_scan()
        
        self.assertEqual(report['total_files_expected'], 3)
        self.assertEqual(report['total_files_found'], 2)
        self.assertEqual(report['missing_files'], ['units/UNIT-001.json'])
        self.assertEqual(report['status'], 'warning')

    @patch('memora.services.cdn_export.health_checker.check_disk_space')
    @patch('memora.services.cdn_export.health_checker._get_expected_files_from_db')
    @patch('memora.services.cdn_export.health_checker._verify_files_exist')
    @patch('memora.services.cdn_export.health_checker._find_orphan_files')
    @patch('memora.services.cdn_export.health_checker._queue_regeneration_for_missing_files')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_daily_scan_finds_orphan_files(self, mock_frappe, mock_queue, mock_orphans, mock_verify, mock_expected, mock_disk):
        """Test that daily scan identifies orphan files."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_disk.return_value = (True, 45.0)
        mock_expected.return_value = [
            'plans/PLAN-001/manifest.json',
            'units/UNIT-001.json'
        ]
        mock_verify.return_value = []  # All expected files exist
        mock_orphans.return_value = ['lessons/LESSON-DELETED.json']  # Orphan file
        
        report = daily_full_scan()
        
        self.assertEqual(report['orphan_files'], ['lessons/LESSON-DELETED.json'])
        self.assertEqual(report['status'], 'warning')

    @patch('memora.services.cdn_export.health_checker.check_disk_space')
    @patch('memora.services.cdn_export.health_checker._get_expected_files_from_db')
    @patch('memora.services.cdn_export.health_checker._verify_files_exist')
    @patch('memora.services.cdn_export.health_checker._find_orphan_files')
    @patch('memora.services.cdn_export.health_checker._queue_regeneration_for_missing_files')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_daily_scan_queues_regeneration_for_missing(self, mock_frappe, mock_queue, mock_orphans, mock_verify, mock_expected, mock_disk):
        """Test that daily scan queues regeneration for missing files."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_disk.return_value = (True, 45.0)
        mock_expected.return_value = ['units/UNIT-001.json']
        mock_verify.return_value = ['units/UNIT-001.json']  # Missing file
        mock_orphans.return_value = []
        
        report = daily_full_scan()
        
        # Should queue regeneration
        mock_queue.assert_called_once_with(['units/UNIT-001.json'])
        self.assertEqual(report['action_taken'], 'Queued regeneration for 1 missing files')

    @patch('memora.services.cdn_export.health_checker.check_disk_space')
    @patch('memora.services.cdn_export.health_checker._get_expected_files_from_db')
    @patch('memora.services.cdn_export.health_checker._verify_files_exist')
    @patch('memora.services.cdn_export.health_checker._find_orphan_files')
    @patch('memora.services.cdn_export.health_checker._queue_regeneration_for_missing_files')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_daily_scan_reports_healthy_when_all_ok(self, mock_frappe, mock_queue, mock_orphans, mock_verify, mock_expected, mock_disk):
        """Test that daily scan reports healthy when all checks pass."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_disk.return_value = (True, 45.0)
        mock_expected.return_value = ['plans/PLAN-001/manifest.json']
        mock_verify.return_value = []  # No missing files
        mock_orphans.return_value = []  # No orphan files
        
        report = daily_full_scan()
        
        self.assertEqual(report['total_files_expected'], 1)
        self.assertEqual(report['total_files_found'], 1)
        self.assertEqual(report['missing_files'], [])
        self.assertEqual(report['orphan_files'], [])
        self.assertEqual(report['status'], 'healthy')


class TestSendDiskAlert(unittest.TestCase):
    """Test disk alert functionality."""

    @patch('memora.services.cdn_export.health_checker.frappe.sendmail')
    @patch('memora.services.cdn_export.health_checker.frappe.publish_realtime')
    @patch('memora.services.cdn_export.health_checker.frappe.get_all')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_send_disk_alert_sends_email(self, mock_frappe, mock_get_all, mock_publish, mock_sendmail):
        """Test that disk alert sends email to system managers."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_get_all.return_value = ['admin@example.com', 'sysadmin@example.com']
        
        send_disk_alert(5.0)
        
        # Check that sendmail was called
        self.assertEqual(mock_sendmail.call_count, 2)
        call_args = mock_sendmail.call_args
        
        self.assertIn('5.0%', call_args.kwargs['subject'])
        self.assertIn('admin@example.com', call_args.kwargs['recipients'])
        self.assertIn('sysadmin@example.com', call_args.kwargs['recipients'])

    @patch('memora.services.cdn_export.health_checker.frappe.sendmail')
    @patch('memora.services.cdn_export.health_checker.frappe.publish_realtime')
    @patch('memora.services.cdn_export.health_checker.frappe.get_all')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_send_disk_alert_sends_in_app_notification(self, mock_frappe, mock_get_all, mock_publish, mock_sendmail):
        """Test that disk alert sends in-app notification."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_get_all.return_value = ['admin@example.com']
        
        send_disk_alert(5.0)
        
        # Check that publish_realtime was called for each user
        self.assertEqual(mock_publish.call_count, 1)
        call_args = mock_publish.call_args
        
        self.assertEqual(call_args.kwargs['event'], 'msgprint')
        self.assertIn('5.0%', call_args.kwargs['message'])
        self.assertEqual(call_args.kwargs['user'], 'admin@example.com')


class TestSendSyncFailureAlert(unittest.TestCase):
    """Test sync failure alert functionality."""

    @patch('memora.services.cdn_export.health_checker.frappe.sendmail')
    @patch('memora.services.cdn_export.health_checker.frappe.publish_realtime')
    @patch('memora.services.cdn_export.health_checker.frappe.get_all')
    @patch('memora.services.cdn_export.health_checker.frappe.get_doc')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_send_sync_failure_alert_sends_email(self, mock_frappe, mock_get_doc, mock_get_all, mock_publish, mock_sendmail):
        """Test that sync failure alert sends email to system managers."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_get_all.return_value = ['admin@example.com']
        
        # Mock sync log document
        mock_log = MagicMock()
        mock_log.plan_id = 'PLAN-001'
        mock_log.name = 'SYNC-001'
        mock_log.retry_count = 5
        mock_log.error_message = 'Connection timeout'
        mock_get_doc.return_value = mock_log
        
        send_sync_failure_alert('SYNC-001')
        
        # Check that sendmail was called
        self.assertEqual(mock_sendmail.call_count, 1)
        call_args = mock_sendmail.call_args
        
        self.assertIn('PLAN-001', call_args.kwargs['subject'])
        self.assertIn('Dead Letter', call_args.kwargs['message'])

    @patch('memora.services.cdn_export.health_checker.frappe.sendmail')
    @patch('memora.services.cdn_export.health_checker.frappe.publish_realtime')
    @patch('memora.services.cdn_export.health_checker.frappe.get_all')
    @patch('memora.services.cdn_export.health_checker.frappe.get_doc')
    @patch('memora.services.cdn_export.health_checker.frappe')
    def test_send_sync_failure_alert_sends_in_app_notification(self, mock_frappe, mock_get_doc, mock_get_all, mock_publish, mock_sendmail):
        """Test that sync failure alert sends in-app notification."""
        mock_logger = MagicMock()
        mock_frappe.logger = mock_logger
        mock_get_all.return_value = ['admin@example.com']
        
        # Mock sync log document
        mock_log = MagicMock()
        mock_log.plan_id = 'PLAN-001'
        mock_log.name = 'SYNC-001'
        mock_get_doc.return_value = mock_log
        
        send_sync_failure_alert('SYNC-001')
        
        # Check that publish_realtime was called
        self.assertEqual(mock_publish.call_count, 1)
        call_args = mock_publish.call_args
        
        self.assertEqual(call_args.kwargs['event'], 'msgprint')
        self.assertIn('PLAN-001', call_args.kwargs['message'])
        self.assertEqual(call_args.kwargs['user'], 'admin@example.com')
