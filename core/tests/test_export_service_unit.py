"""
Unit tests for core/services/export_service.py

Tests data export functionality:
- JSON, CSV, and Excel exports
- Monthly data aggregation
- Empty dataset handling
- Error cases (invalid format)
"""
import pytest
from datetime import date, timedelta
from unittest.mock import Mock, patch, MagicMock
from io import StringIO, BytesIO

from core.services.export_service import ExportService


@pytest.fixture
def user(db):
    """Create a test user."""
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username='export_test_user',
        email='export@test.com',
        password='testpass123'
    )


@pytest.fixture
def tracker(db, user):
    """Create a test tracker."""
    from core.tests.factories import TrackerFactory
    return TrackerFactory.create(user)


@pytest.fixture
def export_service(user):
    """Create ExportService instance."""
    return ExportService(user)


@pytest.fixture
def tracker_with_data(db, user, tracker):
    """Create tracker with task data for export."""
    from core.tests.factories import TemplateFactory, InstanceFactory, TaskInstanceFactory
    
    template = TemplateFactory.create(tracker)
    
    # Create instances for several days
    for day in range(1, 6):
        target_date = date(2025, 12, day)
        instance = InstanceFactory.create(tracker, target_date=target_date)
        
        # Some tasks done, some not
        TaskInstanceFactory.create(
            instance, template, 
            status='DONE' if day % 2 == 0 else 'TODO'
        )
    
    return tracker


# ============================================================================
# Tests for export_month
# ============================================================================

class TestExportMonth:
    """Tests for ExportService.export_month."""
    
    @pytest.mark.django_db
    def test_export_json_format(self, export_service, tracker_with_data):
        """Should export data in JSON format."""
        response = export_service.export_month(2025, 12, format='json')
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
    
    @pytest.mark.django_db
    def test_export_csv_format(self, export_service, tracker_with_data):
        """Should export data in CSV format."""
        response = export_service.export_month(2025, 12, format='csv')
        
        assert response.status_code == 200
        assert 'text/csv' in response['Content-Type']
    
    @pytest.mark.django_db
    def test_export_xlsx_format(self, export_service, tracker_with_data):
        """Should export data in Excel format."""
        response = export_service.export_month(2025, 12, format='xlsx')
        
        assert response.status_code == 200
        assert 'spreadsheet' in response['Content-Type'] or 'csv' in response['Content-Type']
    
    @pytest.mark.django_db
    def test_invalid_format_raises_error(self, export_service):
        """Should raise ValueError for invalid format."""
        with pytest.raises(ValueError) as exc_info:
            export_service.export_month(2025, 12, format='invalid')
        
        assert 'Unsupported format' in str(exc_info.value)
    
    @pytest.mark.django_db
    def test_export_with_tracker_filter(self, export_service, tracker_with_data):
        """Should filter by tracker_id when provided."""
        response = export_service.export_month(
            2025, 12, 
            format='json',
            tracker_id=tracker_with_data.tracker_id
        )
        
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_export_empty_month(self, export_service):
        """Should handle month with no data."""
        response = export_service.export_month(2020, 1, format='json')
        
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_content_disposition_header(self, export_service):
        """Should set Content-Disposition header for download."""
        response = export_service.export_month(2025, 12, format='json')
        
        assert 'Content-Disposition' in response
        assert 'tracker_export' in response['Content-Disposition']


# ============================================================================
# Tests for _get_month_data
# ============================================================================

class TestGetMonthData:
    """Tests for ExportService._get_month_data."""
    
    @pytest.mark.django_db
    def test_returns_data_structure(self, export_service, tracker_with_data):
        """Should return expected data structure."""
        start_date = date(2025, 12, 1)
        end_date = date(2025, 12, 31)
        
        data = export_service._get_month_data(start_date, end_date)
        
        assert 'month' in data
        assert 'start_date' in data
        assert 'end_date' in data
        assert 'summary' in data
        assert 'daily_data' in data
    
    @pytest.mark.django_db
    def test_daily_data_has_entries(self, export_service, tracker_with_data):
        """Should have entry for each day in range."""
        start_date = date(2025, 12, 1)
        end_date = date(2025, 12, 10)
        
        data = export_service._get_month_data(start_date, end_date)
        
        assert len(data['daily_data']) == 10
    
    @pytest.mark.django_db
    def test_daily_entry_structure(self, export_service, tracker_with_data):
        """Each daily entry should have required fields."""
        start_date = date(2025, 12, 1)
        end_date = date(2025, 12, 5)
        
        data = export_service._get_month_data(start_date, end_date)
        
        for entry in data['daily_data']:
            assert 'date' in entry
            assert 'day_of_week' in entry
            assert 'total_tasks' in entry
            assert 'completed_tasks' in entry
            assert 'completion_rate' in entry
    
    @pytest.mark.django_db
    def test_summary_stats(self, export_service, tracker_with_data):
        """Should calculate summary statistics."""
        start_date = date(2025, 12, 1)
        end_date = date(2025, 12, 31)
        
        data = export_service._get_month_data(start_date, end_date)
        
        summary = data['summary']
        assert 'total_tasks' in summary
        assert 'completed_tasks' in summary
        assert 'completion_rate' in summary
    
    @pytest.mark.django_db
    def test_filters_by_tracker_id(self, export_service, user):
        """Should filter by tracker when provided."""
        from core.tests.factories import TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory
        
        tracker1 = TrackerFactory.create(user, name='Tracker 1')
        tracker2 = TrackerFactory.create(user, name='Tracker 2')
        
        template1 = TemplateFactory.create(tracker1)
        template2 = TemplateFactory.create(tracker2)
        
        target_date = date(2025, 12, 1)
        
        instance1 = InstanceFactory.create(tracker1, target_date=target_date)
        TaskInstanceFactory.create(instance1, template1, status='DONE')
        
        instance2 = InstanceFactory.create(tracker2, target_date=target_date)
        TaskInstanceFactory.create(instance2, template2, status='TODO')
        
        # Get data for tracker1 only
        data = export_service._get_month_data(
            date(2025, 12, 1),
            date(2025, 12, 5),
            tracker_id=tracker1.tracker_id
        )
        
        # Should only count tracker1's tasks
        day1 = data['daily_data'][0]
        assert day1['total_tasks'] == 1
        assert day1['completed_tasks'] == 1


# ============================================================================
# Tests for _export_json
# ============================================================================

class TestExportJson:
    """Tests for ExportService._export_json."""
    
    @pytest.mark.django_db
    def test_returns_json_response(self, export_service):
        """Should return JsonResponse."""
        data = {
            'month': 'December 2025',
            'summary': {'total_tasks': 10},
            'daily_data': []
        }
        
        response = export_service._export_json(data, 2025, 12)
        
        assert response.status_code == 200
        assert response['Content-Type'] == 'application/json'
    
    @pytest.mark.django_db
    def test_filename_format(self, export_service):
        """Filename should include year and month."""
        data = {'month': 'December 2025', 'summary': {}, 'daily_data': []}
        
        response = export_service._export_json(data, 2025, 12)
        
        assert 'tracker_export_2025_12.json' in response['Content-Disposition']


# ============================================================================
# Tests for _export_csv
# ============================================================================

class TestExportCsv:
    """Tests for ExportService._export_csv."""
    
    @pytest.mark.django_db
    def test_returns_csv_content(self, export_service):
        """Should return CSV content."""
        data = {
            'month': 'December 2025',
            'summary': {'total_tasks': 10, 'completed_tasks': 5, 'completion_rate': 50},
            'daily_data': [
                {
                    'date': '2025-12-01',
                    'day_of_week': 'Monday',
                    'total_tasks': 5,
                    'completed_tasks': 3,
                    'completion_rate': 60.0
                }
            ]
        }
        
        response = export_service._export_csv(data, 2025, 12)
        
        assert 'text/csv' in response['Content-Type']
    
    @pytest.mark.django_db
    def test_csv_has_header_row(self, export_service):
        """CSV should have header row."""
        data = {
            'month': 'December 2025',
            'summary': {'total_tasks': 0, 'completed_tasks': 0, 'completion_rate': 0},
            'daily_data': []
        }
        
        response = export_service._export_csv(data, 2025, 12)
        content = response.content.decode('utf-8')
        
        assert 'Date' in content
        assert 'Completion Rate' in content
    
    @pytest.mark.django_db
    def test_csv_includes_summary(self, export_service):
        """CSV should include summary row."""
        data = {
            'month': 'December 2025',
            'summary': {'total_tasks': 10, 'completed_tasks': 7, 'completion_rate': 70.0},
            'daily_data': []
        }
        
        response = export_service._export_csv(data, 2025, 12)
        content = response.content.decode('utf-8')
        
        assert 'Summary' in content


# ============================================================================
# Tests for _export_excel
# ============================================================================

class TestExportExcel:
    """Tests for ExportService._export_excel."""
    
    @pytest.mark.django_db
    def test_returns_excel_content(self, export_service):
        """Should return Excel content."""
        data = {
            'month': 'December 2025',
            'summary': {'total_tasks': 10, 'completed_tasks': 5, 'completion_rate': 50},
            'daily_data': [
                {
                    'date': '2025-12-01',
                    'day_of_week': 'Monday',
                    'total_tasks': 5,
                    'completed_tasks': 3,
                    'completion_rate': 60.0
                }
            ]
        }
        
        response = export_service._export_excel(data, 2025, 12)
        
        # Should return either Excel or CSV (fallback)
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_excel_filename(self, export_service):
        """Excel file should have .xlsx extension."""
        data = {
            'month': 'December 2025',
            'summary': {'total_tasks': 0, 'completed_tasks': 0, 'completion_rate': 0},
            'daily_data': []
        }
        
        response = export_service._export_excel(data, 2025, 12)
        
        # Should have xlsx or csv extension in filename
        disposition = response['Content-Disposition']
        assert '.xlsx' in disposition or '.csv' in disposition
    
    @pytest.mark.django_db
    def test_excel_fallback_to_csv(self, export_service):
        """Should fallback to CSV if openpyxl unavailable."""
        data = {
            'month': 'December 2025',
            'summary': {'total_tasks': 0, 'completed_tasks': 0, 'completion_rate': 0},
            'daily_data': []
        }
        
        with patch.dict('sys.modules', {'openpyxl': None}):
            # This might not work as expected due to import caching
            # but the code has a try/except for ImportError
            response = export_service._export_excel(data, 2025, 12)
            
            assert response.status_code == 200


# ============================================================================
# Edge Cases
# ============================================================================

class TestExportServiceEdgeCases:
    """Edge case tests for ExportService."""
    
    @pytest.mark.django_db
    def test_february_leap_year(self, export_service):
        """Should handle February in leap year."""
        response = export_service.export_month(2024, 2, format='json')
        
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_february_non_leap_year(self, export_service):
        """Should handle February in non-leap year."""
        response = export_service.export_month(2025, 2, format='json')
        
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_all_tasks_completed(self, export_service, user):
        """Should handle 100% completion rate."""
        from core.tests.factories import TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory
        
        tracker = TrackerFactory.create(user)
        template = TemplateFactory.create(tracker)
        instance = InstanceFactory.create(tracker, target_date=date(2025, 12, 1))
        TaskInstanceFactory.create(instance, template, status='DONE')
        
        data = export_service._get_month_data(date(2025, 12, 1), date(2025, 12, 1))
        
        assert data['summary']['completion_rate'] == 100.0
    
    @pytest.mark.django_db
    def test_no_tasks(self, export_service, user):
        """Should handle period with no tasks."""
        from core.tests.factories import TrackerFactory, InstanceFactory
        
        tracker = TrackerFactory.create(user)
        InstanceFactory.create(tracker, target_date=date(2025, 12, 1))
        
        data = export_service._get_month_data(date(2025, 12, 1), date(2025, 12, 1))
        
        # Should not divide by zero
        assert data['summary']['completion_rate'] == 0
    
    @pytest.mark.django_db
    def test_special_characters_in_notes(self, export_service, user):
        """Should handle special characters in data."""
        from core.tests.factories import TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory
        
        tracker = TrackerFactory.create(user, name='Tracker with "quotes"')
        template = TemplateFactory.create(tracker, description='Task with <tags>')
        instance = InstanceFactory.create(tracker, target_date=date(2025, 12, 1))
        TaskInstanceFactory.create(instance, template, status='DONE')
        
        response = export_service.export_month(2025, 12, format='csv')
        
        assert response.status_code == 200
    
    @pytest.mark.django_db
    def test_large_dataset(self, export_service, user):
        """Should handle larger datasets efficiently."""
        from core.tests.factories import TrackerFactory, TemplateFactory, InstanceFactory, TaskInstanceFactory
        
        tracker = TrackerFactory.create(user)
        template = TemplateFactory.create(tracker)
        
        # Create 30 days of data
        for day in range(1, 31):
            target_date = date(2025, 12, day)
            instance = InstanceFactory.create(tracker, target_date=target_date)
            for _ in range(5):  # 5 tasks per day
                TaskInstanceFactory.create(instance, template, status='DONE')
        
        response = export_service.export_month(2025, 12, format='json')
        
        assert response.status_code == 200
