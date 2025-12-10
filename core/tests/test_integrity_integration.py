"""
Integration tests for core/integrations/integrity.py

Tests data integrity checking:
- Orphan detection
- Logical consistency validation
- Dry-run mode
- Repair functionality
"""
import pytest
from datetime import date
from unittest.mock import Mock, patch, MagicMock

from core.integrations.integrity import IntegrityService


@pytest.fixture
def user(db):
    """Create a test user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='integrity_test_user',
        email='integrity@test.com',
        password='testpass123'
    )


@pytest.fixture
def integrity_service():
    """Create IntegrityService in dry-run mode."""
    return IntegrityService(dry_run=True)


@pytest.fixture
def integrity_service_repair():
    """Create IntegrityService that can repair."""
    return IntegrityService(dry_run=False)


# ============================================================================
# Tests for IntegrityService initialization
# ============================================================================

class TestIntegrityServiceInit:
    """Tests for IntegrityService initialization."""
    
    def test_default_dry_run_false(self):
        """Default should be dry_run=False."""
        service = IntegrityService()
        
        assert service.dry_run is False
    
    def test_dry_run_mode(self):
        """Should respect dry_run parameter."""
        service = IntegrityService(dry_run=True)
        
        assert service.dry_run is True
    
    def test_has_db_reference(self):
        """Should have database reference."""
        service = IntegrityService()
        
        assert service.db is not None


# ============================================================================
# Tests for run_integrity_check
# ============================================================================

class TestRunIntegrityCheck:
    """Tests for IntegrityService.run_integrity_check."""
    
    def test_returns_report_structure(self, integrity_service):
        """Should return expected report structure."""
        with patch.object(integrity_service, '_check_orphans'):
            with patch.object(integrity_service, '_check_logical_consistency'):
                report = integrity_service.run_integrity_check()
        
        assert 'scanned' in report
        assert 'issues_found' in report
        assert 'repaired' in report
        assert 'quarantined' in report
        assert 'dry_run' in report
        assert 'details' in report
    
    def test_respects_dry_run_parameter(self, integrity_service):
        """Should use dry_run from parameter."""
        with patch.object(integrity_service, '_check_orphans'):
            with patch.object(integrity_service, '_check_logical_consistency'):
                report = integrity_service.run_integrity_check(dry_run=False)
        
        assert integrity_service.dry_run is False
    
    def test_override_dry_run_at_call_time(self, integrity_service):
        """Should allow dry_run override at call time."""
        assert integrity_service.dry_run is True
        
        with patch.object(integrity_service, '_check_orphans'):
            with patch.object(integrity_service, '_check_logical_consistency'):
                report = integrity_service.run_integrity_check(dry_run=False)
        
        assert integrity_service.dry_run is False
    
    def test_clean_database_no_issues(self, integrity_service):
        """Clean database should have no issues."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = []
            
            report = integrity_service.run_integrity_check()
        
        assert report['issues_found'] == 0


# ============================================================================
# Tests for _check_orphans
# ============================================================================

class TestCheckOrphans:
    """Tests for IntegrityService._check_orphans."""
    
    def test_detects_orphan_task_instance(self, integrity_service):
        """Should detect task pointing to non-existent instance."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            def fetch_side_effect(sheet):
                if sheet == 'TaskInstances':
                    return [{'task_instance_id': 'task1', 'tracker_instance_id': 'orphan-instance'}]
                elif sheet == 'TrackerInstances':
                    return []  # No valid instances
                elif sheet == 'TaskTemplates':
                    return []
                elif sheet == 'TrackerDefinitions':
                    return []
                return []
            
            mock_fetch.side_effect = fetch_side_effect
            
            report = {'scanned': 0, 'issues_found': 0, 'details': []}
            integrity_service._check_orphans(report)
        
        assert report['issues_found'] == 1
        assert report['details'][0]['type'] == 'orphan'
    
    def test_detects_orphan_template(self, integrity_service):
        """Should detect template pointing to non-existent tracker."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            def fetch_side_effect(sheet):
                if sheet == 'TaskInstances':
                    return []
                elif sheet == 'TrackerInstances':
                    return []
                elif sheet == 'TaskTemplates':
                    return [{'template_id': 'tmpl1', 'tracker_id': 'orphan-tracker'}]
                elif sheet == 'TrackerDefinitions':
                    return []  # No valid tracker
                return []
            
            mock_fetch.side_effect = fetch_side_effect
            
            report = {'scanned': 0, 'issues_found': 0, 'details': []}
            integrity_service._check_orphans(report)
        
        assert report['issues_found'] == 1
    
    def test_no_orphans_in_valid_data(self, integrity_service):
        """Should find no orphans in valid data."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            def fetch_side_effect(sheet):
                if sheet == 'TaskInstances':
                    return [{'task_instance_id': 'task1', 'tracker_instance_id': 'inst1'}]
                elif sheet == 'TrackerInstances':
                    return [{'instance_id': 'inst1'}]
                elif sheet == 'TaskTemplates':
                    return [{'template_id': 'tmpl1', 'tracker_id': 'tracker1'}]
                elif sheet == 'TrackerDefinitions':
                    return [{'tracker_id': 'tracker1'}]
                return []
            
            mock_fetch.side_effect = fetch_side_effect
            
            report = {'scanned': 0, 'issues_found': 0, 'details': []}
            integrity_service._check_orphans(report)
        
        assert report['issues_found'] == 0


# ============================================================================
# Tests for _check_logical_consistency
# ============================================================================

class TestCheckLogicalConsistency:
    """Tests for IntegrityService._check_logical_consistency."""
    
    def test_detects_invalid_date_range(self, integrity_service):
        """Should detect end date before start date."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'instance_id': 'inst1',
                    'period_start': '2025-12-15',
                    'period_end': '2025-12-10'  # End before start!
                }
            ]
            
            report = {'scanned': 0, 'issues_found': 0, 'repaired': 0, 'details': []}
            integrity_service._check_logical_consistency(report)
        
        assert report['issues_found'] == 1
        assert report['details'][0]['type'] == 'invalid_date_range'
    
    def test_valid_date_range_passes(self, integrity_service):
        """Should not flag valid date ranges."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'instance_id': 'inst1',
                    'period_start': '2025-12-10',
                    'period_end': '2025-12-15'  # Valid range
                }
            ]
            
            report = {'scanned': 0, 'issues_found': 0, 'repaired': 0, 'details': []}
            integrity_service._check_logical_consistency(report)
        
        assert report['issues_found'] == 0
    
    def test_same_start_end_is_valid(self, integrity_service):
        """Same start and end date should be valid."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'instance_id': 'inst1',
                    'period_start': '2025-12-10',
                    'period_end': '2025-12-10'  # Same date (daily tracker)
                }
            ]
            
            report = {'scanned': 0, 'issues_found': 0, 'repaired': 0, 'details': []}
            integrity_service._check_logical_consistency(report)
        
        assert report['issues_found'] == 0
    
    def test_handles_date_objects(self, integrity_service):
        """Should handle date objects (not just strings)."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'instance_id': 'inst1',
                    'period_start': date(2025, 12, 10),
                    'period_end': date(2025, 12, 15)
                }
            ]
            
            report = {'scanned': 0, 'issues_found': 0, 'repaired': 0, 'details': []}
            integrity_service._check_logical_consistency(report)
        
        assert report['issues_found'] == 0
    
    def test_handles_missing_dates(self, integrity_service):
        """Should handle records with missing dates."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'instance_id': 'inst1',
                    'period_start': None,
                    'period_end': None
                }
            ]
            
            report = {'scanned': 0, 'issues_found': 0, 'repaired': 0, 'details': []}
            integrity_service._check_logical_consistency(report)
        
        # Should not crash and not flag as issue
        assert report['issues_found'] == 0


# ============================================================================
# Tests for repair functionality
# ============================================================================

class TestRepairFunctionality:
    """Tests for repair functionality."""
    
    def test_repairs_date_range_when_not_dry_run(self, integrity_service_repair):
        """Should repair invalid date range when not in dry-run mode."""
        with patch.object(integrity_service_repair.db, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'instance_id': 'inst1',
                    'period_start': '2025-12-15',
                    'period_end': '2025-12-10'  # Invalid
                }
            ]
            
            with patch.object(integrity_service_repair.db, 'update') as mock_update:
                report = {'scanned': 0, 'issues_found': 0, 'repaired': 0, 'details': []}
                integrity_service_repair._check_logical_consistency(report)
                
                mock_update.assert_called_once()
                assert report['repaired'] == 1
    
    def test_no_repair_in_dry_run(self, integrity_service):
        """Should not repair in dry-run mode."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = [
                {
                    'instance_id': 'inst1',
                    'period_start': '2025-12-15',
                    'period_end': '2025-12-10'
                }
            ]
            
            with patch.object(integrity_service.db, 'update') as mock_update:
                report = {'scanned': 0, 'issues_found': 0, 'repaired': 0, 'details': []}
                integrity_service._check_logical_consistency(report)
                
                mock_update.assert_not_called()
                assert report['repaired'] == 0


# ============================================================================
# Tests for _get_id_field
# ============================================================================

class TestGetIdField:
    """Tests for IntegrityService._get_id_field."""
    
    def test_tracker_definitions(self, integrity_service):
        """Should return tracker_id for TrackerDefinitions."""
        field = integrity_service._get_id_field('TrackerDefinitions')
        
        assert field == 'tracker_id'
    
    def test_task_templates(self, integrity_service):
        """Should return template_id for TaskTemplates."""
        field = integrity_service._get_id_field('TaskTemplates')
        
        assert field == 'template_id'
    
    def test_tracker_instances(self, integrity_service):
        """Should return instance_id for TrackerInstances."""
        field = integrity_service._get_id_field('TrackerInstances')
        
        assert field == 'instance_id'
    
    def test_task_instances(self, integrity_service):
        """Should return task_instance_id for TaskInstances."""
        field = integrity_service._get_id_field('TaskInstances')
        
        assert field == 'task_instance_id'
    
    def test_unknown_sheet(self, integrity_service):
        """Should return None for unknown sheet."""
        field = integrity_service._get_id_field('UnknownSheet')
        
        assert field is None


# ============================================================================
# Full Integration Tests
# ============================================================================

class TestIntegrityFullIntegration:
    """Full integration tests for IntegrityService."""
    
    def test_full_check_empty_database(self, integrity_service):
        """Should handle empty database."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            mock_fetch.return_value = []
            
            report = integrity_service.run_integrity_check()
        
        assert report['issues_found'] == 0
        assert report['scanned'] == 0
    
    def test_full_check_with_multiple_issues(self, integrity_service):
        """Should detect multiple types of issues."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            def fetch_side_effect(sheet):
                if sheet == 'TaskInstances':
                    return [{'task_instance_id': 'task1', 'tracker_instance_id': 'orphan'}]
                elif sheet == 'TrackerInstances':
                    return [
                        {
                            'instance_id': 'inst1',
                            'period_start': '2025-12-15',
                            'period_end': '2025-12-10'  # Invalid
                        }
                    ]
                elif sheet == 'TaskTemplates':
                    return [{'template_id': 'tmpl1', 'tracker_id': 'orphan-tracker'}]
                elif sheet == 'TrackerDefinitions':
                    return []
                return []
            
            mock_fetch.side_effect = fetch_side_effect
            
            report = integrity_service.run_integrity_check()
        
        assert report['issues_found'] >= 2
    
    def test_report_contains_issue_details(self, integrity_service):
        """Should include details for each issue."""
        with patch.object(integrity_service.db, 'fetch_all') as mock_fetch:
            def fetch_side_effect(sheet):
                if sheet == 'TaskInstances':
                    return [{'task_instance_id': 'task1', 'tracker_instance_id': 'orphan'}]
                elif sheet == 'TrackerInstances':
                    return []
                elif sheet == 'TaskTemplates':
                    return []
                elif sheet == 'TrackerDefinitions':
                    return []
                return []
            
            mock_fetch.side_effect = fetch_side_effect
            
            report = integrity_service.run_integrity_check()
        
        assert len(report['details']) >= 1
        detail = report['details'][0]
        assert 'type' in detail
        assert 'table' in detail
        assert 'id' in detail
        assert 'message' in detail
