"""
Behavior Analytics Engine
Provides comprehensive metrics, NLP analysis, and visualizations for tracker data.
All metrics return structured metadata for explainability.

NOTE: Matplotlib/Seaborn visualizations are disabled for Vercel serverless deployment.
Only core metrics and analytics functions are available.
"""
import io
import base64
import statistics
import math
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from collections import Counter
from core.repositories import base_repository as crud
from core.helpers import nlp_helpers as nlp_utils
from core.helpers import metric_helpers
from core.helpers.cache_helpers import cache_result, CACHE_TIMEOUTS

# Dependencies removed: pandas, numpy, matplotlib, seaborn
# Serverless-friendly pure Python implementation
_matplotlib_available = False

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
    
    # Build structured data (previously Dataframe)
    data = []
    total_completed = 0
    total_scheduled = 0

    for inst in instances:
        inst_date = inst.period_start or inst.tracking_date
        if isinstance(inst_date, str):
            inst_date = date.fromisoformat(inst_date)
        
        tasks = inst.tasks.all()
        if not tasks:
            continue
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t.status == 'DONE')
        rate = (completed / total) * 100 if total > 0 else 0.0
        
        # Accumulate totals
        total_scheduled += total
        total_completed += completed

        data.append({
            'date': inst_date,
            'total': total,
            'completed': completed,
            'rate': rate
        })
    
    overall_rate = (total_completed / total_scheduled) * 100 if total_scheduled > 0 else 0.0
    
    return {
        'metric_name': 'completion_rate',
        'value': float(overall_rate),
        'daily_rates': data, # Already list of dicts
        'raw_inputs': {
            'total_instances': len(data),
            'total_tasks': total_scheduled,
            'completed_tasks': total_completed
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
    
    # Convert to simple list of booleans ordered by date
    # Sort by date
    sorted_items = sorted(completion_data.items())
    completion_list = [status for _, status in sorted_items]
    
    # Use metric_helpers for streak detection (pure python now)
    streak_data = metric_helpers.detect_streaks(completion_list)
    
    return {
        'metric_name': 'streaks',
        'value': {
            'current_streak': streak_data['current'],
            'longest_streak': streak_data['best']
        },
        'raw_inputs': {'total_days': len(completion_list)},
        'formula': 'Run-length encoding of consecutive completion days',
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
    
    # Sort by date
    sorted_dates = sorted(completion_data.keys())
    # Convert bools to 1.0/0.0
    values = [100.0 if completion_data[d] else 0.0 for d in sorted_dates]
    
    # Calculate rolling average manually
    rolling_scores = []
    if not values:
        rolling_scores = []
    else:
        # Simple moving average
        current_window = []
        for i, val in enumerate(values):
            current_window.append(val)
            if len(current_window) > window_days:
                current_window.pop(0)
            
            avg_score = sum(current_window) / len(current_window)
            rolling_scores.append({
                'date': str(sorted_dates[i]),
                'score': avg_score
            })
            
    current_score = rolling_scores[-1]['score'] if rolling_scores else 0.0
    
    return {
        'metric_name': 'consistency_score',
        'value': current_score,
        'rolling_scores': rolling_scores,
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
    
    # Calculate entropy manually
    total_count = sum(category_counts.values())
    entropy = 0.0
    normalized_distribution = {}
    
    if total_count > 0:
        for count in category_counts.values():
            p = count / total_count
            if p > 0:
                entropy -= p * math.log2(p)
                
        # Calculate max possible entropy (log2 of number of categories)
        num_categories = len(category_counts)
        max_entropy = math.log2(num_categories) if num_categories > 1 else 1.0
        
        # Normalize to 0-100
        balance_score = (entropy / max_entropy) * 100 if max_entropy > 0 else 100.0 # Single category is technically perfectly balanced with itself? Or 0? Usually 0 diversity. 
        # Actually for "balance" usually means diversity. Let's stick to entropy.
        # If only 1 category exists, entropy is 0.
        if num_categories <= 1:
            balance_score = 0.0 if num_categories == 1 else 0.0
        else:
            balance_score = (entropy / max_entropy) * 100
            
        for cat, count in category_counts.items():
            normalized_distribution[cat] = (count / total_count) * 100
    else:
        balance_score = 0.0
        entropy = 0.0
        max_entropy = 0.0
        
    balance_data = {
        'balance_score': balance_score,
        'entropy': entropy,
        'max_entropy': max_entropy,
        'normalized_distribution': normalized_distribution
    }
    
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
    
    avg_mood = statistics.mean([s['compound'] for s in daily_sentiments]) if daily_sentiments else 0.0
    
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
    
    # Manual rolling mean
    rolling_data = []
    
    # Sort by date
    daily_mood_sorted = sorted(daily_mood, key=lambda x: x['date'])
    
    compounds = [x['compound'] for x in daily_mood_sorted]
    
    for i in range(len(compounds)):
        # Determine window start
        start_idx = max(0, i - window_days + 1)
        window = compounds[start_idx : i+1]
        
        avg_val = sum(window) / len(window)
        rolling_data.append({
            'date': daily_mood_sorted[i]['date'],
            'mood': float(avg_val)
        })
    
    current_trend = rolling_data[-1]['mood'] if rolling_data else 0.0
    
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
    Computes correlation matrix between multiple metrics (pure Python).
    
    Args:
        tracker_id: Tracker ID
        metrics: List of metrics to correlate (default: ['completion_rate', 'mood', 'effort'])
    
    Returns:
        {
            'metric_name': 'correlations',
            'correlation_matrix': dict,
            'raw_inputs': {...},
            'formula': str,
            'computed_at': datetime
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
        # Create map date_str -> rate
        if daily_rates:
            for r in daily_rates:
                d_str = str(r['date'])
                if d_str not in data_dict: data_dict[d_str] = {}
                data_dict[d_str]['completion_rate'] = r['rate']
    
    # Mood (sentiment)
    if 'mood' in metrics:
        sentiment_data = analyze_notes_sentiment(tracker_id)
        daily_mood = sentiment_data.get('daily_mood', [])
        if daily_mood:
            for m in daily_mood:
                d_str = str(m['date'])
                if d_str not in data_dict: data_dict[d_str] = {}
                data_dict[d_str]['mood'] = m['compound']
    
    # Effort
    if 'effort' in metrics:
        # Need per-day effort - compute from instances
        instances = crud.get_tracker_instances(tracker_id)
        templates = crud.get_task_templates_for_tracker(tracker_id)
        # Fix: templates is a QuerySet of objects, not dicts
        template_map = {str(t.template_id): getattr(t, 'weight', 1) for t in templates}
        
        for inst in instances:
            tasks = crud.get_task_instances_for_tracker_instance(inst.instance_id)
            day_effort = sum(template_map.get(str(t.template_id), 1) for t in tasks if t.status == 'DONE')
            
            d_str = str(inst.period_start or inst.tracking_date)
            if d_str not in data_dict: data_dict[d_str] = {}
            data_dict[d_str]['effort'] = day_effort

    # Prepare aligned lists
    aligned_data = {m: [] for m in metrics}
    
    # Only include dates where we have data for at least 2 metrics?
    # Or just pairwise? Correlation matrix pairwise is best.
    
    # Strategy: For each pair of metrics, extract common dates
    correlation_matrix = {}
    
    for i, m1 in enumerate(metrics):
        correlation_matrix[m1] = {}
        for m2 in metrics:
            if m1 == m2:
                correlation_matrix[m1][m2] = 1.0
                continue
            
            vals1 = []
            vals2 = []
            
            for d_str, day_data in data_dict.items():
                if m1 in day_data and m2 in day_data:
                    vals1.append(day_data[m1])
                    vals2.append(day_data[m2])
            
            if len(vals1) < 2:
                correlation_matrix[m1][m2] = 0.0
            else:
                correlation_matrix[m1][m2] = metric_helpers.calculate_correlation(vals1, vals2)

    return {
        'metric_name': 'correlations',
        'correlation_matrix': correlation_matrix,
        'p_values': {}, # Not supported in lightweight mode
        'significant': {}, # Not supported in lightweight mode
        'raw_inputs': {'metrics': metrics, 'data_points': len(data_dict)},
        'formula': 'Pearson correlation coefficient (aligned by date)',
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
    # Lightweight Time Series Analysis
    
    # 1. Fetch Data
    series = []
    if metric == 'completion_rate':
        c_data = compute_completion_rate(tracker_id)
        series = [r['rate'] for r in c_data.get('daily_rates', [])]
    
    if not series:
         return _empty_timeseries_result(metric)
         
    # 2. Compute Trend (Linear Regression)
    # x values are just indices 0..n-1
    x_vals = list(range(len(series)))
    trend_result = metric_helpers.compute_trend_line_pure_python(x_vals, series)
    
    # 3. Forecast (Simple EMA projection)
    # Use standard EMA with alpha=0.3
    forecast_values = metric_helpers.exponential_moving_average(series, alpha=0.3)
    # Simple projection
    last_val = forecast_values[-1] if forecast_values else 0
    forecast_projection = [last_val] * forecast_days 
    
    return {
        'metric_name': 'time_series_analysis',
        'metric': metric,
        'trend': {
            'slope': trend_result['slope'],
            'direction': 'improving' if trend_result['direction'] > 0 else 'declining',
            'r_squared': 0.0 # Not computed in simplified version
        },
        'forecast': {
            'forecast': forecast_projection,
            'confidence_lower': [],
            'confidence_upper': []
        },
        'change_points': [],
        'seasonality': {'has_seasonality': False},
        'raw_inputs': {'data_points': len(series)},
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
    # Lightweight Trend Analysis
    completion_data = compute_completion_rate(tracker_id)
    daily_rates = completion_data.get('daily_rates', [])
    
    if not daily_rates:
        return {
            'metric_name': 'trend_analysis',
            'smoothed_data': [],
            'trend_direction': 'stable',
            'improving_periods': 0
        }
        
    rates = [r['rate'] for r in daily_rates]
    # metric_helpers.exponential_moving_average takes 'alpha', not 'span' in the lightweight version
    # calculate_ema was renamed/removed, using exponential_moving_average
    # Standard alpha for span=14 is 2/(14+1) ~= 0.133
    alpha = 2 / (window + 1)
    smoothed = metric_helpers.exponential_moving_average(rates, alpha=alpha)
    
    improving_periods = sum(1 for i in range(1, len(smoothed)) if smoothed[i] > smoothed[i-1])
    
    start_v = smoothed[0] if smoothed else 0
    end_v = smoothed[-1] if smoothed else 0
    
    if end_v > start_v: direction = 'improving'
    elif end_v < start_v: direction = 'declining'
    else: direction = 'stable'
    
    smoothed_data = [
        {'date': daily_rates[i]['date'], 'value': v}
        for i, v in enumerate(smoothed)
    ]
    
    return {
        'metric_name': 'trend_analysis',
        'smoothed_data': smoothed_data,
        'trend_direction': direction,
        'improving_periods': improving_periods,
        'total_periods': len(smoothed),
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
        
        # Sort by date
        sorted_rates = sorted(daily_rates, key=lambda x: x['date'])
        
        historical_values = [r['rate'] for r in sorted_rates]
        historical_dates = [r['date'] for r in sorted_rates]
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
    # last_date is already a date object or string from above
    if isinstance(last_date, str):
        last_date = date.fromisoformat(last_date)
    elif isinstance(last_date, datetime):
        last_date = last_date.date()
    
    if last_date is None:
        last_date = date.today()
    
    try:
        forecast_dates = [last_date + timedelta(days=i+1) for i in range(days)]
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
        
        # Sort by date
        sorted_rates = sorted(daily_rates, key=lambda x: x['date'])
        
        if len(sorted_rates) == 0:
            return None
            
        historical_values = [r['rate'] for r in sorted_rates]
        historical_dates = [r['date'] for r in sorted_rates]
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
    if isinstance(last_date, str):
        last_date = date.fromisoformat(last_date)
    
    if last_date is None:
        last_date = date.today()
    
    try:
        forecast_dates = [last_date + timedelta(days=i+1) for i in range(days)]
    except Exception:
        return None
    
    # Return data for frontend Chart.js rendering instead of matplotlib image
    return {
        'chart_type': 'forecast',
        'metric': metric,
        'historical': {
            'labels': [d.strftime('%b %d') if isinstance(d, (date, datetime)) else str(d) for d in historical_dates],
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
    
    # Sort by date
    sorted_rates = sorted(daily_rates, key=lambda x: x['date'])
    
    if not sorted_rates:
        return None
        
    dates = [r['date'] for r in sorted_rates]
    rates = [r['rate'] for r in sorted_rates]
    
    # Compute trend line
    x_vals = list(range(len(rates)))
    trend_info = metric_helpers.compute_trend_line_pure_python(x_vals, rates)
    
    trend_line = [trend_info['slope'] * x + trend_info['intercept'] for x in x_vals]
    
    # Return data for frontend Chart.js rendering
    return {
        'chart_type': 'progress_with_trend',
        'labels': [d.strftime('%b %d') if isinstance(d, (date, datetime)) else str(d) for d in dates],
        'actual': [float(r) for r in rates],
        'trend': [float(t) for t in trend_line],
        'trend_info': {
            'slope': trend_info['slope'],
            'r_squared': trend_info['r_squared'],
            'direction': 'improving' if trend_info['slope'] > 0 else 'declining' if trend_info['slope'] < 0 else 'stable'
        }
    }

