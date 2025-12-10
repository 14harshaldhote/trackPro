
import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import date
from core.behavioral.insights_engine import (
    InsightsEngine, Insight, InsightType, Severity, get_insights, get_top_insight
)

@pytest.fixture
def mock_analytics():
    with patch('core.behavioral.insights_engine.analytics') as mock:
        yield mock

@pytest.fixture
def mock_db():
    with patch('core.behavioral.insights_engine.crud.db') as mock:
        yield mock

@pytest.fixture
def engine(mock_analytics):
    # Setup default mock returns
    mock_analytics.compute_completion_rate.return_value = {'daily_rates': []}
    mock_analytics.detect_streaks.return_value = {'value': {'current_streak': 0, 'longest_streak': 0}}
    mock_analytics.compute_consistency_score.return_value = {'value': 80}
    mock_analytics.compute_balance_score.return_value = {'value': 80}
    mock_analytics.compute_effort_index.return_value = {'value': 10}
    mock_analytics.analyze_notes_sentiment.return_value = {}
    mock_analytics.analyze_trends.return_value = {'trend_direction': 'stable'}
    
    return InsightsEngine("tracker-123")

class TestInsightsEngine:
    
    def test_initialization(self, mock_analytics):
        """Test that engine initializes and loads metrics."""
        engine = InsightsEngine("tracker-123")
        assert engine.tracker_id == "tracker-123"
        mock_analytics.compute_completion_rate.assert_called_with("tracker-123")

    def test_check_consistency_low(self, engine, mock_analytics):
        """Test detection of low consistency."""
        mock_analytics.compute_consistency_score.return_value = {
            'value': 30, # Low score
            'rolling_scores': [30, 30, 30],
            'raw_inputs': {'total_days': 20}
        }
        engine._load_metrics() # Reload with new mock values
        
        engine._check_consistency()
        
        assert len(engine.insights) == 1
        insight = engine.insights[0]
        assert insight.insight_type == InsightType.LOW_CONSISTENCY
        assert insight.severity == Severity.HIGH
        assert insight.confidence == 0.8

    def test_check_weekend_dip(self, engine, mock_analytics):
        """Test detection of weekend performance dip."""
        # 2 weeks of data
        # Mon-Fri: 100%, Sat-Sun: 50%
        daily_rates = []
        start_date = date(2023, 1, 1) # Sunday
        for i in range(14):
            day = start_date + \
                (timedelta(days=i) if 'timedelta' in globals() else __import__('datetime').timedelta(days=i))
            # If weekend (Sat=5, Sun=6)
            rate = 50 if day.weekday() >= 5 else 100
            daily_rates.append({'date': day.isoformat(), 'rate': rate})
            
        mock_analytics.compute_completion_rate.return_value = {'daily_rates': daily_rates}
        engine._load_metrics()
        
        engine._check_weekend_pattern()
        
        assert len(engine.insights) == 1
        insight = engine.insights[0]
        assert insight.insight_type == InsightType.WEEKEND_DIP
        assert "significant" in insight.description

    def test_check_streak_risk(self, engine, mock_analytics):
        """Test detection of streak risk."""
        mock_analytics.detect_streaks.return_value = {
            'value': {'current_streak': 5, 'longest_streak': 10}
        }
        mock_analytics.compute_completion_rate.return_value = {
            'daily_rates': [
                {'rate': 85}, # Prev
                {'rate': 50}  # Recent drop
            ]
        }
        engine._load_metrics()
        
        engine._check_streak_risk()
        
        assert len(engine.insights) == 1
        assert engine.insights[0].insight_type == InsightType.STREAK_RISK
        assert engine.insights[0].severity == Severity.HIGH

    def test_check_mood_correlation(self, engine, mock_analytics):
        """Test detection of mood correlation."""
        mock_analytics.compute_correlations.return_value = {
            'correlation_matrix': {
                'mood': {'completion_rate': 0.8}
            },
            'significant': {
                'mood': {'completion_rate': True}
            }
        }
        
        engine._check_mood_correlation()
        
        assert len(engine.insights) == 1
        assert engine.insights[0].insight_type == InsightType.MOOD_CORRELATION
        assert "positive correlation" in engine.insights[0].description

    def test_check_sleep_impact(self, engine, mock_db):
        """Test detection of sleep impact from notes."""
        # Mock notes
        mock_notes = []
        for i in range(6):
            mock_notes.append({
                'content': f"Slept {4 if i < 3 else 8} hours",
                'date': f"2023-01-{i+1}"
            })
        mock_db.fetch_filter.return_value = mock_notes
        
        engine._check_sleep_impact()
        
        assert len(engine.insights) == 1
        assert engine.insights[0].insight_type == InsightType.SLEEP_IMPACT
        assert "less than 6 hours" in engine.insights[0].description

    def test_check_category_balance(self, engine, mock_analytics):
        """Test detection of category imbalance."""
        mock_analytics.compute_balance_score.return_value = {
            'value': 30,
            'category_distribution': {
                'Work': 80,
                'Health': 5,
                'Social': 15
            }
        }
        engine._load_metrics()
        
        engine._check_category_balance()
        
        assert len(engine.insights) == 1
        assert engine.insights[0].insight_type == InsightType.CATEGORY_IMBALANCE
        assert "Work" in engine.insights[0].description

    def test_check_effort_recovery(self, engine, mock_analytics):
        """Test suggestion for recovery."""
        mock_analytics.compute_effort_index.return_value = {
            'value': 80,
            'raw_inputs': {'completed_tasks': 25}
        }
        mock_analytics.compute_completion_rate.return_value = {
            'daily_rates': [{'rate': 90} for _ in range(5)]
        }
        engine._load_metrics()
        
        engine._check_effort_recovery()
        
        assert len(engine.insights) == 1
        assert engine.insights[0].insight_type == InsightType.HIGH_EFFORT_RECOVERY

    def test_check_trends_improving(self, engine, mock_analytics):
        """Test detection of improving trend."""
        mock_analytics.analyze_trends.return_value = {
            'trend_direction': 'improving',
            'improving_periods': 8,
            'total_periods': 10
        }
        engine._load_metrics()
        
        engine._check_trends()
        
        assert len(engine.insights) == 1
        assert engine.insights[0].insight_type == InsightType.IMPROVEMENT_TREND

    def test_to_dict(self, engine, mock_analytics):
        """Test serialization of insights."""
        mock_analytics.compute_consistency_score.return_value = {'value': 20}
        engine._load_metrics()
        engine._check_consistency()
        
        result = engine.to_dict()
        assert len(result) == 1
        assert result[0]['type'] == 'low_consistency'
        assert result[0]['severity'] == 'high'

def test_get_insights_wrapper(mock_analytics):
    """Test the convenience function."""
    with patch('core.behavioral.insights_engine.InsightsEngine') as MockEngine:
        instance = MockEngine.return_value
        instance.to_dict.return_value = [{'title': 'Test Insight'}]
        
        result = get_insights("tracker-1")
        
        assert result == [{'title': 'Test Insight'}]
        MockEngine.assert_called_with("tracker-1")
        instance.generate_insights.assert_called()

def test_get_top_insight_wrapper(mock_analytics):
    """Test get_top_insight."""
    with patch('core.behavioral.insights_engine.get_insights') as mock_get:
        mock_get.return_value = [{'title': 'Top'}, {'title': 'Second'}]
        
        result = get_top_insight("tracker-1")
        assert result['title'] == 'Top'
        
        mock_get.return_value = []
        assert get_top_insight("tracker-1") is None
