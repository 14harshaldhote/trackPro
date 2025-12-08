"""
Behavior Analytics Engine
Provides comprehensive metrics, NLP analysis, and visualizations for tracker data.
All metrics return structured metadata for explainability.

NOTE: Matplotlib/Seaborn visualizations are disabled for Vercel serverless deployment.
Only core metrics and analytics functions are available.
"""
import io
import base64
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from core.repositories import base_repository as crud
from core.helpers import nlp_helpers as nlp_utils
from core.helpers import metric_helpers
from core.helpers.cache_helpers import cache_result, CACHE_TIMEOUTS

# Matplotlib/Seaborn disabled for serverless deployment
# Visualization functions will return None
_matplotlib_available = False

# ====================================================================
# CORE METRICS
# ====================================================================

@cache_result(timeout=CACHE_TIMEOUTS['completion_rate'], key_prefix='completion_rate')
def compute_completion_rate(tracker_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict:
    """
    Computes completion rate using pandas aggregations.
    
    Formula: completion_rate = (completed_tasks / scheduled_tasks) * 100
    
    Returns:
        {
            'metric_name': 'completion_rate',
            'value': float (0-100),
            'raw_inputs': {...},
            'formula': str,
            'computed_at': datetime
        }
    """
    # Use optimized query that prefetches tasks
    instances = crud.get_tracker_instances_with_tasks(tracker_id, start_date, end_date)
    
    if not instances:
        return {
            'metric_name': 'completion_rate',
            'value': 0.0,
            'daily_rates': [],
            'raw_inputs': {'total_instances': 0, 'total_tasks': 0},
            'formula': 'completion_rate = (completed_tasks / scheduled_tasks) * 100',
            'computed_at': datetime.now()
        }
    
    # Build DataFrame - tasks are already prefetched
    data = []
    for inst in instances:
        inst_date = inst.period_start or inst.tracking_date
        if isinstance(inst_date, str):
            inst_date = date.fromisoformat(inst_date)
        
        # Tasks are nested in the instance dict from prefetch
        # With ORM objects and prefetch_related, utilize .all() which hits cache
        tasks = inst.tasks.all()
        if not tasks:
            continue
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == 'DONE')
        rate = (completed / total) * 100 if total > 0 else 0.0
        
        data.append({
            'date': inst_date,
            'total': total,
            'completed': completed,
            'rate': rate
        })
    
    df = pd.DataFrame(data)
    
    if df.empty:
        overall_rate = 0.0
    else:
        overall_rate = (df['completed'].sum() / df['total'].sum()) * 100 if df['total'].sum() > 0 else 0.0
    
    return {
        'metric_name': 'completion_rate',
        'value': float(overall_rate),
        'daily_rates': df.to_dict('records') if not df.empty else [],
        'raw_inputs': {
            'total_instances': len(data),
            'total_tasks': int(df['total'].sum()) if not df.empty else 0,
            'completed_tasks': int(df['completed'].sum()) if not df.empty else 0
        },
        'formula': 'completion_rate = (completed_tasks / scheduled_tasks) * 100',
        'computed_at': datetime.now()
    }

@cache_result(timeout=CACHE_TIMEOUTS['streaks'], key_prefix='streaks')
def detect_streaks(tracker_id: str, task_template_id: Optional[str] = None) -> Dict:
    """
    Detects current and longest streaks using NumPy run-length encoding.
    
    Returns:
        {
            'metric_name': 'streaks',
            'value': {'current': int, 'longest': int},
            'raw_inputs': {...},
            'formula': str,
            'computed_at': datetime
        }
    """
    # Use optimized prefetch query
    instances = crud.get_tracker_instances_with_tasks(tracker_id)
    
    # Build date-indexed completion series
    completion_data = {}
    
    for inst in instances:
        inst_date = inst.period_start or inst.tracking_date
        if isinstance(inst_date, str):
            inst_date = date.fromisoformat(inst_date)
        
        # Tasks already prefetched
        tasks = inst.tasks.all()
        
        # Filter by template if specified
        if task_template_id:
            tasks = [t for t in tasks if str(t.template_id) == str(task_template_id)]
        
        if tasks:
            # Day is completed if any task is DONE
            completed = any(t.status == 'DONE' for t in tasks)
            completion_data[inst_date] = completed
    
    if not completion_data:
        return {
            'metric_name': 'streaks',
            'value': {'current_streak': 0, 'longest_streak': 0},
            'raw_inputs': {'total_days': 0},
            'formula': 'Run-length encoding of consecutive completion days using NumPy diff + cumsum',
            'computed_at': datetime.now()
        }
    
    # Convert to pandas Series
    completion_series = pd.Series(completion_data).sort_index()
    
    # Use metric_helpers for streak detection
    streak_data = metric_helpers.detect_streaks_numpy(completion_series)
    
    return {
        'metric_name': 'streaks',
        'value': {
            'current_streak': streak_data['current_streak'],
            'longest_streak': streak_data['longest_streak']
        },
        'raw_inputs': {'total_days': streak_data['total_days']},
        'formula': 'Run-length encoding of consecutive completion days using NumPy diff + cumsum',
        'computed_at': datetime.now()
    }

@cache_result(timeout=CACHE_TIMEOUTS['consistency'], key_prefix='consistency')
def compute_consistency_score(tracker_id: str, window_days: int = 7) -> Dict:
    """
    Computes consistency score using rolling window analysis.
    
    Returns:
        {
            'metric_name': 'consistency_score',
            'value': float (0-100),
            'rolling_scores': [...],
            'raw_inputs': {...},
            'formula': str,
            'computed_at': datetime
        }
    """
    # Use optimized prefetch query
    instances = crud.get_tracker_instances_with_tasks(tracker_id)
    
    # Build completion series
    completion_data = {}
    for inst in instances:
        inst_date = inst.period_start or inst.tracking_date
        if isinstance(inst_date, str):
            inst_date = date.fromisoformat(inst_date)
        
        # Tasks already prefetched
        tasks = inst.tasks.all()
        completed = any(t.status == 'DONE' for t in tasks) if tasks else False
        completion_data[inst_date] = completed
    
    if not completion_data:
        return {
            'metric_name': 'consistency_score',
            'value': 0.0,
            'rolling_scores': [],
            'raw_inputs': {'window_days': window_days, 'total_days': 0},
            'formula': f'{window_days}-day rolling window mean of completion rate * 100',
            'computed_at': datetime.now()
        }
    
    completion_series = pd.Series(completion_data).sort_index()
    rolling_scores = metric_helpers.compute_rolling_consistency(completion_series, window_days)
    
    # Current consistency is the most recent rolling score
    current_score = float(rolling_scores.iloc[-1]) if not rolling_scores.empty else 0.0
    
    return {
        'metric_name': 'consistency_score',
        'value': current_score,
        'rolling_scores': [{'date': str(d), 'score': float(s)} for d, s in rolling_scores.items()],
        'raw_inputs': {'window_days': window_days, 'total_days': len(completion_data)},
        'formula': f'{window_days}-day rolling window mean of completion rate * 100',
        'computed_at': datetime.now()
    }

@cache_result(timeout=CACHE_TIMEOUTS['tracker_stats'], key_prefix='balance')
def compute_balance_score(tracker_id: str) -> Dict:
    """
    Computes balance score using category distribution entropy.
    
    Formula: Normalized Shannon entropy (0-100, higher = more balanced)
    
    Returns:
        {
            'metric_name': 'balance_score',
            'value': float (0-100),
            'category_distribution': {...},
            'raw_inputs': {...},
            'formula': str,
            'computed_at': datetime
        }
    """
    templates = crud.get_task_templates_for_tracker(tracker_id)
    # Fix: templates is a QuerySet of objects, not dicts
    template_map = {str(t.template_id): getattr(t, 'category', 'Uncategorized') for t in templates}
    
    # Use optimized prefetch query
    instances = crud.get_tracker_instances_with_tasks(tracker_id)
    category_counts = {}
    
    for inst in instances:
        # Tasks already prefetched
        tasks = inst.tasks.all()
        for t in tasks:
            cat = template_map.get(str(t.template_id), 'Uncategorized')
            category_counts[cat] = category_counts.get(cat, 0) + 1
    
    balance_data = metric_helpers.compute_category_balance(category_counts)
    
    return {
        'metric_name': 'balance_score',
        'value': balance_data['balance_score'],
        'category_distribution': balance_data['normalized_distribution'],
        'raw_inputs': {
            'category_counts': category_counts,
            'entropy': balance_data['entropy'],
            'max_entropy': balance_data['max_entropy']
        },
        'formula': 'Normalized Shannon entropy: -Σ(p_i * log2(p_i)) / log2(n_categories) * 100',
        'computed_at': datetime.now()
    }

@cache_result(timeout=CACHE_TIMEOUTS['analytics'], key_prefix='effort')
def compute_effort_index(tracker_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict:
    """
    Computes effort index combining task difficulty and duration.
    
    Note: Currently uses task weight as a proxy for difficulty.
    
    Returns:
        {
            'metric_name': 'effort_index',
            'value': float,
            'raw_inputs': {...},
            'formula': str,
            'computed_at': datetime
        }
    """
    templates = crud.get_task_templates_for_tracker(tracker_id)
    # Fix: templates is a QuerySet of objects, not dicts
    template_map = {str(t.template_id): getattr(t, 'weight', 1) for t in templates}
    
    # Use optimized prefetch query with date filtering
    instances = crud.get_tracker_instances_with_tasks(tracker_id, start_date, end_date)
    total_effort = 0.0
    task_count = 0
    
    for inst in instances:
        # Tasks already prefetched
        tasks = inst.tasks.all()
        for t in tasks:
            if t.status == 'DONE':
                weight = template_map.get(str(t.template_id), 1)
                total_effort += weight
                task_count += 1
    
    return {
        'metric_name': 'effort_index',
        'value': float(total_effort),
        'raw_inputs': {
            'completed_tasks': task_count,
            'total_weight': total_effort
        },
        'formula': 'Sum of task weights for completed tasks',
        'computed_at': datetime.now()
    }

# ====================================================================
# NLP & TEXT ANALYSIS
# ====================================================================

def analyze_notes_sentiment(tracker_id: str, start_date: Optional[date] = None, end_date: Optional[date] = None) -> Dict:
    """
    Analyzes sentiment of notes using VADER.
    
    Returns:
        {
            'metric_name': 'sentiment_analysis',
            'daily_mood': [...],
            'average_mood': float,
            'raw_inputs': {...},
            'formula': str,
            'computed_at': datetime
        }
    """
    # Fetch notes from DayNotes sheet
    all_notes = crud.db.fetch_filter('DayNotes', tracker_id=tracker_id)
    
    if not all_notes:
        return {
            'metric_name': 'sentiment_analysis',
            'daily_mood': [],
            'average_mood': 0.0,
            'raw_inputs': {'note_count': 0},
            'formula': 'VADER sentiment analysis (compound score -1 to +1)',
            'computed_at': datetime.now()
        }
    
    daily_sentiments = []
    for note in all_notes:
        note_date = note['date']
        if isinstance(note_date, str):
            note_date = date.fromisoformat(note_date)
        
        if start_date and note_date < start_date:
            continue
        if end_date and note_date > end_date:
            continue
        
        sentiment = nlp_utils.compute_sentiment(note.get('content', ''))
        daily_sentiments.append({
            'date': str(note_date),
            'compound': sentiment['compound'],
            'pos': sentiment['pos'],
            'neu': sentiment['neu'],
            'neg': sentiment['neg']
        })
    
    avg_mood = np.mean([s['compound'] for s in daily_sentiments]) if daily_sentiments else 0.0
    
    return {
        'metric_name': 'sentiment_analysis',
        'daily_mood': daily_sentiments,
        'average_mood': float(avg_mood),
        'raw_inputs': {'note_count': len(daily_sentiments)},
        'formula': 'VADER sentiment analysis (compound score -1 to +1)',
        'computed_at': datetime.now()
    }

def extract_keywords_from_notes(tracker_id: str, top_n: int = 10) -> Dict:
    """
    Extracts top keywords from all notes using frequency analysis.
    
    Returns:
        {
            'metric_name': 'keyword_extraction',
            'keywords': [(word, count), ...],
            'raw_inputs': {...},
            'formula': str,
            'computed_at': datetime
        }
    """
    all_notes = crud.db.fetch_filter('DayNotes', tracker_id=tracker_id)
    
    if not all_notes:
        return {
            'metric_name': 'keyword_extraction',
            'keywords': [],
            'raw_inputs': {'note_count': 0},
            'formula': 'Token frequency analysis after stopword removal',
            'computed_at': datetime.now()
        }
    
    # Concatenate all note content
    combined_text = ' '.join(note.get('content', '') for note in all_notes)
    
    keywords = nlp_utils.extract_keywords(combined_text, top_n)
    
    return {
        'metric_name': 'keyword_extraction',
        'keywords': keywords,
        'raw_inputs': {'note_count': len(all_notes), 'total_chars': len(combined_text)},
        'formula': 'Token frequency analysis after stopword removal',
        'computed_at': datetime.now()
    }

def compute_mood_trends(tracker_id: str, window_days: int = 7) -> Dict:
    """
    Computes rolling mood trends from sentiment scores.
    
    Returns:
        {
            'metric_name': 'mood_trends',
            'rolling_mood': [...],
            'current_trend': float,
            'raw_inputs': {...},
            'formula': str,
            'computed_at': datetime
        }
    """
    sentiment_data = analyze_notes_sentiment(tracker_id)
    daily_mood = sentiment_data['daily_mood']
    
    if not daily_mood:
        return {
            'metric_name': 'mood_trends',
            'rolling_mood': [],
            'current_trend': 0.0,
            'raw_inputs': {'window_days': window_days, 'data_points': 0},
            'formula': f'{window_days}-day rolling mean of sentiment scores',
            'computed_at': datetime.now()
        }
    
    # Convert to DataFrame
    df = pd.DataFrame(daily_mood)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').set_index('date')
    
    # Rolling mean
    rolling_mean = df['compound'].rolling(window=window_days, min_periods=1).mean()
    
    rolling_data = [
        {'date': str(d.date()), 'mood': float(m)}
        for d, m in rolling_mean.items()
    ]
    
    current_trend = float(rolling_mean.iloc[-1]) if not rolling_mean.empty else 0.0
    
    return {
        'metric_name': 'mood_trends',
        'rolling_mood': rolling_data,
        'current_trend': current_trend,
        'raw_inputs': {'window_days': window_days, 'data_points': len(daily_mood)},
        'formula': f'{window_days}-day rolling mean of sentiment scores',
        'computed_at': datetime.now()
    }

# ====================================================================
# VISUALIZATIONS
# ====================================================================

def generate_completion_chart(tracker_id):
    """Generates a line chart of task completion over time.
    
    NOTE: Visualization disabled for Vercel deployment.
    """
    # Matplotlib not available on serverless
    return None

def generate_category_pie_chart(tracker_id):
    """Generates a donut chart of task distribution by category.
    
    NOTE: Visualization disabled for Vercel deployment.
    """
    # Matplotlib not available on serverless
    return None

def generate_completion_heatmap(tracker_id, days=30):
    """Generates a calendar-style heatmap of completions.
    
    NOTE: Visualization disabled for Vercel deployment.
    """
    # Matplotlib not available on serverless
    return None

def generate_streak_timeline(tracker_id):
    """Generates an annotated timeline showing streaks.
    
    NOTE: Visualization disabled for Vercel deployment.
    """
    # Matplotlib not available on serverless
    return None

@cache_result(timeout=CACHE_TIMEOUTS['tracker_stats'], key_prefix='tracker_stats')
def compute_tracker_stats(tracker_id):
    """
    Computes comprehensive statistics for a tracker.
    Legacy function for compatibility.
    """
    completion = compute_completion_rate(tracker_id)
    streaks = detect_streaks(tracker_id)
    
    return {
        'total_tasks': completion['raw_inputs']['total_tasks'],
        'completed_tasks': completion['raw_inputs']['completed_tasks'],
        'completion_rate': completion['value'],
        'current_streak': streaks['value']['current_streak']
    }

# ====================================================================
# ADVANCED ANALYTICS
# ====================================================================

def compute_correlations(tracker_id: str, metrics: Optional[List[str]] = None) -> Dict:
    """
    Computes correlation matrix between multiple metrics.
    
    Args:
        tracker_id: Tracker ID
        metrics: List of metrics to correlate (default: ['completion_rate', 'mood', 'effort'])
    
    Returns:
        {
            'metric_name': 'correlations',
            'correlation_matrix': dict,
            'p_values': dict,
            'significant': dict,
            'raw_inputs': {...},
            'formula': str
        }
    """
    if metrics is None:
        metrics = ['completion_rate', 'mood', 'effort']
    
    # Collect data for each metric
    data_dict = {}
    
    # Completion rate by day
    if 'completion_rate' in metrics:
        completion_data = compute_completion_rate(tracker_id)
        daily_rates = completion_data.get('daily_rates', [])
        if daily_rates:
            data_dict['completion_rate'] = np.array([r['rate'] for r in daily_rates])
    
    # Mood (sentiment)
    if 'mood' in metrics:
        sentiment_data = analyze_notes_sentiment(tracker_id)
        daily_mood = sentiment_data.get('daily_mood', [])
        if daily_mood:
            data_dict['mood'] = np.array([m['compound'] for m in daily_mood])
    
    # Effort
    if 'effort' in metrics:
        # Need per-day effort - compute from instances
        instances = crud.get_tracker_instances(tracker_id)
        templates = crud.get_task_templates_for_tracker(tracker_id)
        # Fix: templates is a QuerySet of objects, not dicts
        template_map = {str(t.template_id): getattr(t, 'weight', 1) for t in templates}
        
        daily_effort = []
        for inst in instances:
            tasks = crud.get_task_instances_for_tracker_instance(inst.instance_id)
            day_effort = sum(template_map.get(str(t.template_id), 1) for t in tasks if t.status == 'DONE')
            daily_effort.append(day_effort)
        
        if daily_effort:
            data_dict['effort'] = np.array(daily_effort)
    
    if len(data_dict) < 2:
        return {
            'metric_name': 'correlations',
            'correlation_matrix': {},
            'p_values': {},
            'significant': {},
            'raw_inputs': {'metrics': metrics, 'data_available': list(data_dict.keys())},
            'formula': 'Pearson correlation coefficient: r = cov(X,Y) / (σ_X * σ_Y)',
            'computed_at': datetime.now()
        }
    
    corr_result = metric_helpers.compute_correlation_matrix(data_dict, method='pearson')
    
    return {
        'metric_name': 'correlations',
        'correlation_matrix': corr_result['correlation_matrix'],
        'p_values': corr_result['p_values'],
        'significant': corr_result['significant'],
        'raw_inputs': {'metrics': list(data_dict.keys()), 'sample_sizes': {k: len(v) for k, v in data_dict.items()}},
        'formula': 'Pearson correlation coefficient: r = cov(X,Y) / (σ_X * σ_Y)',
        'computed_at': datetime.now()
    }

def analyze_time_series(tracker_id: str, metric: str = 'completion_rate', forecast_days: int = 7) -> Dict:
    """
    Analyzes time series and generates forecast using ARIMA.
    
    Args:
        tracker_id: Tracker ID
        metric: Which metric to analyze ('completion_rate', 'mood', 'effort')
        forecast_days: Number of days to forecast
    
    Returns:
        {
            'metric_name': 'time_series_analysis',
            'trend': dict,
            'forecast': {...},
            'change_points': list,
            'seasonality': dict
        }
    """
    # Get time series data
    if metric == 'completion_rate':
        completion_data = compute_completion_rate(tracker_id)
        daily_rates = completion_data.get('daily_rates', [])
        if not daily_rates:
            return _empty_timeseries_result(metric)
        
        df = pd.DataFrame(daily_rates)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        series = df['rate']
    
    elif metric == 'mood':
        sentiment_data = analyze_notes_sentiment(tracker_id)
        daily_mood = sentiment_data.get('daily_mood', [])
        if not daily_mood:
            return _empty_timeseries_result(metric)
        
        df = pd.DataFrame(daily_mood)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date').sort_index()
        series = df['compound']
    
    else:
        return _empty_timeseries_result(metric)
    
    # Smooth series for trend
    smoothed = metric_helpers.smooth_series(series, method='savgol', window=7)
    
    # Detect trend
    x_vals = np.arange(len(series))
    trend_info = metric_helpers.compute_trend_line(x_vals, series.values)
    
    # Detect change points
    change_points = metric_helpers.detect_change_points(series, threshold=0.3)
    
    # Forecast
    forecast_result = metric_helpers.forecast_arima(series, steps=forecast_days)
    
    # Seasonality analysis
    seasonality = metric_helpers.analyze_seasonality(series, period=7)
    
    return {
        'metric_name': 'time_series_analysis',
        'metric': metric,
        'trend': {
            'slope': trend_info['slope'],
            'direction': 'improving' if trend_info['slope'] > 0 else 'declining',
            'r_squared': trend_info['r_squared']
        },
        'forecast': forecast_result,
        'change_points': change_points,
        'seasonality': seasonality,
        'raw_inputs': {'data_points': len(series), 'date_range': [str(series.index[0]), str(series.index[-1])]},
        'computed_at': datetime.now()
    }

def _empty_timeseries_result(metric: str) -> Dict:
    """Returns empty time series result."""
    return {
        'metric_name': 'time_series_analysis',
        'metric': metric,
        'trend': {'slope': 0, 'direction': 'stable', 'r_squared': 0},
        'forecast': {'forecast': [], 'confidence_lower': [], 'confidence_upper': []},
        'change_points': [],
        'seasonality': {'has_seasonality': False, 'seasonal_strength': 0.0},
        'raw_inputs': {'data_points': 0},
        'computed_at': datetime.now()
    }

def analyze_trends(tracker_id: str, window: int = 14, smooth_method: str = 'savgol') -> Dict:
    """
    Analyzes trends using smoothing.
    
    Returns:
        {
            'metric_name': 'trend_analysis',
            'smoothed_data': [...],
            'trend_direction': str,
            'improving_periods': int
        }
    """
    completion_data = compute_completion_rate(tracker_id)
    daily_rates = completion_data.get('daily_rates', [])
    
    if not daily_rates:
        return {
            'metric_name': 'trend_analysis',
            'smoothed_data': [],
            'trend_direction': 'stable',
            'improving_periods': 0
        }
    
    df = pd.DataFrame(daily_rates)
    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date').sort_index()
    
    # Smooth
    smoothed = metric_helpers.smooth_series(df['rate'], method=smooth_method, window=window)
    
    # Count improving periods
    improving = sum(1 for i in range(1, len(smoothed)) if smoothed.iloc[i] > smoothed.iloc[i-1])
    
    # Overall direction
    if smoothed.iloc[-1] > smoothed.iloc[0]:
        direction = 'improving'
    elif smoothed.iloc[-1] < smoothed.iloc[0]:
        direction = 'declining'
    else:
        direction = 'stable'
    
    smoothed_data = [{'date': str(d), 'value': float(v)} for d, v in smoothed.items()]
    
    return {
        'metric_name': 'trend_analysis',
        'smoothed_data': smoothed_data,
        'trend_direction': direction,
        'improving_periods': improving,
        'total_periods': len(smoothed) - 1,
        'computed_at': datetime.now()
    }

# ====================================================================
# ADVANCED VISUALIZATIONS (Disabled for serverless deployment)
# ====================================================================

def generate_correlation_heatmap(tracker_id: str):
    """Generates correlation heatmap.
    
    NOTE: Visualization disabled for Vercel/serverless deployment.
    Returns correlation data as dict instead of image.
    """
    corr_data = compute_correlations(tracker_id)
    # Return data instead of image for frontend to render
    return corr_data

def simple_forecast(tracker_id: str, metric: str = 'completion_rate', days: int = 7) -> Dict:
    """
    Generate simple forecast using moving average.
    
    Args:
        tracker_id: Tracker ID
        metric: Metric to forecast
        days: Number of days to forecast
        
    Returns:
        Forecast dictionary
    """
    # Get time series
    ts_data = analyze_time_series(tracker_id, metric, days)
    
    # Check if we have valid data
    if not ts_data or 'forecast' not in ts_data:
        return {
            'metric_name': 'forecast',
            'forecast_dates': [],
            'forecast_values': [],
            'method': 'none',
            'error': 'Insufficient data for forecasting'
        }
    
    # Get historical data for the graph
    if metric == 'completion_rate':
        completion_data = compute_completion_rate(tracker_id)
        daily_rates = completion_data.get('daily_rates', [])
        if not daily_rates:
            return {
                'metric_name': 'forecast',
                'forecast_dates': [],
                'forecast_values': [],
                'method': 'none',
                'error': 'No historical data'
            }
        
        df = pd.DataFrame(daily_rates)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        historical_values = df['rate'].values
        historical_dates = df['date'].values
    else:
        return {
            'metric_name': 'forecast',
            'forecast_dates': [],
            'forecast_values': [],
            'method': 'none',
            'error': 'Unsupported metric'
        }
    
    # Validate historical dates
    if len(historical_dates) == 0:
        return {
            'metric_name': 'forecast',
            'forecast_dates': [],
            'forecast_values': [],
            'method': 'none',
            'error': 'No historical dates'
        }
    
    forecast_result = ts_data['forecast']
    forecast_values = forecast_result.get('forecast', [])
    conf_lower = forecast_result.get('confidence_lower', [])
    conf_upper = forecast_result.get('confidence_upper', [])
    
    # Create forecast dates - validate last_date is not NaT
    last_date = historical_dates[-1]
    if pd.isna(last_date):
        # Use today as fallback
        last_date = pd.Timestamp.now().normalize()
    
    try:
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days)
    except Exception:
        return {
            'metric_name': 'forecast',
            'forecast_dates': [],
            'forecast_values': [],
            'method': 'none',
            'error': 'Error creating forecast dates'
        }
    
    # Return data for frontend Chart.js rendering instead of matplotlib image
    return {
        'metric_name': 'forecast',
        'metric': metric,
        'historical': {
            'dates': [str(d) for d in historical_dates],
            'values': [float(v) for v in historical_values]
        },
        'forecast': {
            'dates': [str(d) for d in forecast_dates],
            'values': [float(v) for v in forecast_values],
            'confidence_lower': [float(v) for v in conf_lower],
            'confidence_upper': [float(v) for v in conf_upper]
        },
        'method': 'arima_or_exponential'
    }

def generate_forecast_chart(tracker_id: str, metric: str = 'completion_rate', days: int = 7):
    """Generates forecast chart data.
    
    NOTE: Visualization disabled for Vercel/serverless deployment.
    Returns data for frontend Chart.js rendering instead of matplotlib image.
    """
    ts_data = analyze_time_series(tracker_id, metric=metric, forecast_days=days)
    
    # Validate we have forecast data
    if not ts_data or 'forecast' not in ts_data:
        return None
    
    # Get historical data for the graph
    if metric == 'completion_rate':
        completion_data = compute_completion_rate(tracker_id)
        daily_rates = completion_data.get('daily_rates', [])
        if not daily_rates:
            return None
        
        df = pd.DataFrame(daily_rates)
        df['date'] = pd.to_datetime(df['date'])
        df = df.sort_values('date')
        
        if len(df) == 0:
            return None
        
        historical_values = df['rate'].values
        historical_dates = df['date'].values
    else:
        return None
    
    if len(historical_dates) == 0:
        return None
    
    forecast_result = ts_data['forecast']
    forecast_values = forecast_result.get('forecast', [])
    conf_lower = forecast_result.get('confidence_lower', [])
    conf_upper = forecast_result.get('confidence_upper', [])
    
    if not forecast_values:
        return None
    
    last_date = historical_dates[-1]
    if pd.isna(last_date):
        last_date = pd.Timestamp.now().normalize()
    
    try:
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days)
    except Exception:
        return None
    
    # Return data for frontend Chart.js rendering instead of matplotlib image
    return {
        'chart_type': 'forecast',
        'metric': metric,
        'historical': {
            'labels': [pd.Timestamp(d).strftime('%b %d') for d in historical_dates],
            'data': [float(v) for v in historical_values]
        },
        'forecast': {
            'labels': [d.strftime('%b %d') for d in forecast_dates],
            'data': [float(v) for v in forecast_values],
            'confidence_lower': [float(v) for v in conf_lower],
            'confidence_upper': [float(v) for v in conf_upper]
        }
    }

def generate_progress_chart_with_trend(tracker_id: str):
    """Generates progress chart data with trend line.
    
    NOTE: Visualization disabled for Vercel/serverless deployment.
    Returns data for frontend Chart.js rendering instead of matplotlib image.
    """
    completion_data = compute_completion_rate(tracker_id)
    daily_rates = completion_data.get('daily_rates', [])
    
    if not daily_rates:
        return None
    
    df = pd.DataFrame(daily_rates)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Compute trend line
    x_vals = np.arange(len(df))
    trend_info = metric_helpers.compute_trend_line(x_vals, df['rate'].values)
    
    trend_line = trend_info['slope'] * x_vals + trend_info['intercept']
    
    # Return data for frontend Chart.js rendering
    return {
        'chart_type': 'progress_with_trend',
        'labels': [d.strftime('%b %d') for d in df['date']],
        'actual': [float(r) for r in df['rate'].values],
        'trend': [float(t) for t in trend_line],
        'trend_info': {
            'slope': trend_info['slope'],
            'r_squared': trend_info['r_squared'],
            'direction': 'improving' if trend_info['slope'] > 0 else 'declining' if trend_info['slope'] < 0 else 'stable'
        }
    }

