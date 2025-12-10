
import pytest
from unittest.mock import Mock, patch, MagicMock
from core.exports.exporter import (
    StreamingCSVExporter, stream_tracker_export, generate_behavior_summary, 
    export_data, generate_journey_report, export_all_notes
)
from django.http import HttpResponse

class TestExporter:

    def test_streaming_csv_exporter(self):
        """Test streaming CSV generation."""
        exporter = StreamingCSVExporter(['Header1', 'Header2'])
        
        data = [
            ['Row1Col1', 'Row1Col2'],
            ['Row2Col1', 'Row2Col2']
        ]
        
        generator = exporter.stream(iter(data))
        
        # First chunk is header
        header = next(generator)
        assert 'Header1,Header2' in header
        
        # Next chunks are rows
        row1 = next(generator)
        assert 'Row1Col1,Row1Col2' in row1
        
        row2 = next(generator)
        assert 'Row2Col1,Row2Col2' in row2

    def test_stream_tracker_export(self):
        """Test tracker data generator."""
        with patch('core.models.TaskInstance') as MockTaskInstance:
            # Mock query set
            qs = MockTaskInstance.objects.filter.return_value.select_related.return_value.order_by.return_value
            
            # Create mock tasks
            t1 = Mock()
            t1.tracker_instance.period_start = "2023-01-01"
            t1.template.description = "Task 1"
            t1.status = "DONE"
            t1.template.category = "Work"
            
            qs.iterator.return_value = iter([t1])
            
            generator = stream_tracker_export("t-1")
            
            row = next(generator)
            assert row == ('2023-01-01', 'Task 1', 'DONE', 'Work')

    def test_generate_behavior_summary(self):
        """Test Excel generation logic."""
        with patch('xlsxwriter.Workbook') as MockWorkbook, \
             patch('core.repositories.base_repository.db') as mock_db, \
             patch('core.analytics.compute_completion_rate') as mock_completion, \
             patch('core.analytics.detect_streaks') as mock_streaks, \
             patch('core.analytics.compute_consistency_score') as mock_consistency, \
             patch('core.analytics.compute_balance_score') as mock_balance, \
             patch('core.analytics.compute_effort_index') as mock_effort:
             
            # Setup data
            mock_db.fetch_by_id.return_value = {'name': 'Test Tracker'}
            mock_completion.return_value = {'value': 80, 'daily_rates': []}
            mock_streaks.return_value = {'value': {'current_streak': 5, 'longest_streak': 5}}
            mock_consistency.return_value = {'value': 90}
            mock_balance.return_value = {'value': 70, 'category_distribution': {'A': 50}}
            mock_effort.return_value = {'value': 10}
            
            # Run
            generate_behavior_summary("t-1", "output.xlsx")
            
            # verify
            MockWorkbook.assert_called_with("output.xlsx")
            wb = MockWorkbook.return_value
            assert wb.add_worksheet.call_count >= 3 # Overview, Daily, Balance
            wb.close.assert_called()

    def test_export_data_csv(self):
        """Test export to CSV using tablib."""
        with patch('core.analytics.compute_completion_rate') as mock_completion, \
             patch('tablib.Dataset') as MockDataset:
             
            mock_completion.return_value = {
                'daily_rates': [{'date': '2023-01-01', 'total': 1, 'completed': 1, 'rate': 100}]
            }
            
            ds = MockDataset.return_value
            ds.export.return_value = "csv_data"
            
            response = export_data("t-1", format='csv')
            assert isinstance(response, HttpResponse)
            assert response.content == b"csv_data"
            assert response['Content-Type'] == 'text/csv'

    def test_export_data_json(self):
        """Test export to JSON (which is implemented inline)."""
        with patch('core.analytics.compute_completion_rate') as mock_completion:
            mock_completion.return_value = {
                'daily_rates': [{'date': '2023-01-01', 'total': 1, 'completed': 1, 'rate': 100}]
            }
            
            response = export_data("t-1", format='json')
            assert isinstance(response, HttpResponse)
            assert b"2023-01-01" in response.content

    def test_generate_journey_report(self):
        """Test journey report generation."""
        with patch('core.repositories.base_repository.db') as mock_db, \
             patch('xlsxwriter.Workbook'):
             
            mock_db.fetch_all.return_value = [
                {
                    'timestamp': '2023-01-01',
                    'action_type': 'CREATE',
                    'entity_type': 'Tracker',
                    'entity_id': 't-1',
                    'details': 'Created tracker'
                }
            ]
            
            result = generate_journey_report("t-1")
            
            assert result['total_events'] == 1
            assert "CREATE: 1 times" in result['summary']

    def test_export_all_notes(self):
        """Test notes export."""
        with patch('core.repositories.base_repository.db') as mock_db, \
             patch('tablib.Dataset') as MockDataset:
             
            mock_db.fetch_filter.return_value = [{'date': '2023-01-01', 'content': 'Note'}]
            
            ds = MockDataset.return_value
            ds.export.return_value = "csv_content"
            
            result = export_all_notes("t-1", format='csv')
            assert result == "csv_content"
            ds.append.assert_called()
