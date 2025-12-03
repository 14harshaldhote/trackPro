"""
Behavior Analytics Engine
Provides comprehensive metrics, NLP analysis, and visualizations for tracker data.
All metrics return structured metadata for explainability.
"""
import matplotlib
matplotlib.use('Agg') # Non-interactive backend
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from core import crud, nlp_utils, metric_helpers

def get_plot_as_base64(fig):
    """Converts a matplotlib figure to base64 string."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', bbox_inches='tight', transparent=True, dpi=100)
    buf.seek(0)
    image_base64 = base64.b64encode(buf.getvalue()).decode('utf-8')
    plt.close(fig)
    return image_base64

# ====================================================================
# CORE METRICS
# ====================================================================

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
    instances = crud.get_tracker_instances(tracker_id)
    
    if not instances:
        return {
            'metric_name': 'completion_rate',
            'value': 0.0,
            'daily_rates': [],
            'raw_inputs': {'total_instances': 0, 'total_tasks': 0},
            'formula': 'completion_rate = (completed_tasks / scheduled_tasks) * 100',
            'computed_at': datetime.now()
        }
    
    # Build DataFrame
    data = []
    for inst in instances:
        inst_date = inst['period_start']
        if isinstance(inst_date, str):
            inst_date = date.fromisoformat(inst_date)
        
        # Filter by date range
        if start_date and inst_date < start_date:
            continue
        if end_date and inst_date > end_date:
            continue
        
        tasks = crud.get_task_instances_for_tracker_instance(inst['instance_id'])
        if not tasks:
            continue
        
        total = len(tasks)
        completed = sum(1 for t in tasks if t.get('status') == 'DONE')
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
    instances = crud.get_tracker_instances(tracker_id)
    
    # Build date-indexed completion series
    completion_data = {}
    
    for inst in instances:
        inst_date = inst['period_start']
        if isinstance(inst_date, str):
            inst_date = date.fromisoformat(inst_date)
        
        tasks = crud.get_task_instances_for_tracker_instance(inst['instance_id'])
        
        # Filter by template if specified
        if task_template_id:
            tasks = [t for t in tasks if t.get('template_id') == task_template_id]
        
        if tasks:
            # Day is completed if any task is DONE
            completed = any(t.get('status') == 'DONE' for t in tasks)
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
    instances = crud.get_tracker_instances(tracker_id)
    
    # Build completion series
    completion_data = {}
    for inst in instances:
        inst_date = inst['period_start']
        if isinstance(inst_date, str):
            inst_date = date.fromisoformat(inst_date)
        
        tasks = crud.get_task_instances_for_tracker_instance(inst['instance_id'])
        completed = any(t.get('status') == 'DONE' for t in tasks) if tasks else False
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
    template_map = {t['template_id']: t.get('category', 'Uncategorized') for t in templates}
    
    instances = crud.get_tracker_instances(tracker_id)
    category_counts = {}
    
    for inst in instances:
        tasks = crud.get_task_instances_for_tracker_instance(inst['instance_id'])
        for t in tasks:
            cat = template_map.get(t.get('template_id'), 'Uncategorized')
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
    template_map = {t['template_id']: t.get('weight', 1) for t in templates}
    
    instances = crud.get_tracker_instances(tracker_id)
    total_effort = 0.0
    task_count = 0
    
    for inst in instances:
        inst_date = inst['period_start']
        if isinstance(inst_date, str):
            inst_date = date.fromisoformat(inst_date)
        
        if start_date and inst_date < start_date:
            continue
        if end_date and inst_date > end_date:
            continue
        
        tasks = crud.get_task_instances_for_tracker_instance(inst['instance_id'])
        for t in tasks:
            if t.get('status') == 'DONE':
                weight = template_map.get(t.get('template_id'), 1)
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
    """Generates a line chart of task completion over time."""
    completion_data = compute_completion_rate(tracker_id)
    daily_rates = completion_data['daily_rates']
    
    if not daily_rates:
        return None
    
    df = pd.DataFrame(daily_rates)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Plot
    sns.set_theme(style="darkgrid", rc={
        "axes.facecolor": "#00000000",
        "figure.facecolor": "#00000000",
        "text.color": "white",
        "axes.labelcolor": "white",
        "xtick.color": "white",
        "ytick.color": "white"
    })
    fig, ax = plt.subplots(figsize=(10, 4))
    
    sns.lineplot(data=df, x='date', y='rate', marker='o', linewidth=2.5, color='#00E676', ax=ax)
    ax.fill_between(df['date'], df['rate'], alpha=0.2, color='#00E676')
    
    ax.set_title('Completion Rate Trend', color='white', fontsize=14)
    ax.set_ylabel('Completion %')
    ax.set_xlabel('Date')
    ax.set_ylim(0, 105)
    
    return get_plot_as_base64(fig)

def generate_category_pie_chart(tracker_id):
    """Generates a donut chart of task distribution by category."""
    balance_data = compute_balance_score(tracker_id)
    category_dist = balance_data['category_distribution']
    
    if not category_dist:
        return None
    
    # Plot
    labels = list(category_dist.keys())
    sizes = list(category_dist.values())
    colors = sns.color_palette('pastel')[0:len(labels)]
    
    fig, ax = plt.subplots(figsize=(6, 6))
    wedges, texts, autotexts = ax.pie(
        sizes, labels=labels, autopct='%1.1f%%',
        startangle=90, colors=colors, pctdistance=0.85,
        textprops={'color':"white"}
    )
    
    # Draw circle for donut
    centre_circle = plt.Circle((0,0),0.70,fc='none')
    fig.gca().add_artist(centre_circle)
    
    ax.axis('equal')
    plt.title('Task Distribution by Category', color='white')
    
    return get_plot_as_base64(fig)

def generate_completion_heatmap(tracker_id, days=30):
    """Generates a calendar-style heatmap of completions."""
    completion_data = compute_completion_rate(tracker_id)
    daily_rates = completion_data['daily_rates']
    
    if not daily_rates:
        return None
    
    df = pd.DataFrame(daily_rates)
    df['date'] = pd.to_datetime(df['date'])
    
    # Take last N days
    df = df.sort_values('date').tail(days)
    
    if df.empty:
        return None
    
    # Create calendar grid (week rows, day columns)
    df['day_of_week'] = df['date'].dt.dayofweek
    df['week'] = ((df['date'] - df['date'].min()).dt.days // 7)
    
    pivot = df.pivot(index='week', columns='day_of_week', values='rate')
    
    # Plot
    sns.set_theme()
    fig, ax = plt.subplots(figsize=(10, 4))
    
    sns.heatmap(pivot, cmap='Greens', annot=False, cbar_kws={'label': 'Completion %'}, ax=ax)
    ax.set_xlabel('Day of Week (Mon-Sun)')
    ax.set_ylabel('Week')
    ax.set_title('Completion Heatmap', fontsize=14)
    
    return get_plot_as_base64(fig)

def generate_streak_timeline(tracker_id):
    """Generates an annotated timeline showing streaks."""
    streak_data = detect_streaks(tracker_id)
    
    # For visualization, we need the full completion series
    instances = crud.get_tracker_instances(tracker_id)
    completion_data = {}
    
    for inst in instances:
        inst_date = inst['period_start']
        if isinstance(inst_date, str):
            inst_date = date.fromisoformat(inst_date)
        
        tasks = crud.get_task_instances_for_tracker_instance(inst['instance_id'])
        completed = any(t.get('status') == 'DONE' for t in tasks) if tasks else False
        completion_data[inst_date] = 1 if completed else 0
    
    if not completion_data:
        return None
    
    df = pd.DataFrame(list(completion_data.items()), columns=['date', 'completed'])
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date')
    
    # Plot
    sns.set_theme()
    fig, ax = plt.subplots(figsize=(12, 3))
    
    ax.fill_between(df['date'], 0, df['completed'], alpha=0.7, color='#00E676', step='mid')
    ax.plot(df['date'], df['completed'], marker='o', color='#00E676', linewidth=2)
    
    # Annotate current streak
    ax.text(0.95, 0.95, f"Current Streak: {streak_data['value']['current_streak']} days",
            transform=ax.transAxes, ha='right', va='top',
            bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
    
    ax.set_ylabel('Completed')
    ax.set_xlabel('Date')
    ax.set_title('Streak Timeline', fontsize=14)
    ax.set_ylim(-0.1, 1.1)
    
    return get_plot_as_base64(fig)

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
        template_map = {t['template_id']: t.get('weight', 1) for t in templates}
        
        daily_effort = []
        for inst in instances:
            tasks = crud.get_task_instances_for_tracker_instance(inst['instance_id'])
            day_effort = sum(template_map.get(t.get('template_id'), 1) for t in tasks if t.get('status') == 'DONE')
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
# ADVANCED VISUALIZATIONS
# ====================================================================

def generate_correlation_heatmap(tracker_id: str):
    """Generates correlation heatmap."""
    corr_data = compute_correlations(tracker_id)
    corr_matrix = corr_data.get('correlation_matrix', {})
    
    if not corr_matrix:
        return None
    
    # Convert to DataFrame for seaborn
    metrics = list(corr_matrix.keys())
    matrix_values = []
    for m1 in metrics:
        row = [corr_matrix[m1].get(m2, 0) for m2 in metrics]
        matrix_values.append(row)
    
    df = pd.DataFrame(matrix_values, index=metrics, columns=metrics)
    
    # Plot
    sns.set_theme()
    fig, ax = plt.subplots(figsize=(8, 6))
    
    sns.heatmap(df, annot=True, cmap='coolwarm', center=0, vmin=-1, vmax=1, 
                square=True, linewidths=1, cbar_kws={"shrink": 0.8}, ax=ax)
    
    ax.set_title('Metric Correlations', fontsize=14)
    
    return get_plot_as_base64(fig)

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
    
    forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days)
    
    # Plot
    sns.set_theme()
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Historical
    ax.plot(historical_dates, historical_values, marker='o', label='Historical', color='#2196F3', linewidth=2)
    
    # Forecast
    ax.plot(forecast_dates, forecast_values, marker='s', label='Forecast', color='#FF9800', linewidth=2, linestyle='--')
    
    # Confidence interval
    ax.fill_between(forecast_dates, conf_lower, conf_upper, alpha=0.3, color='#FF9800', label='95% Confidence')
    
    ax.set_title(f'{metric.replace("_", " ").title()} Forecast ({days} days)', fontsize=14)
    ax.set_ylabel('Value')
    ax.set_xlabel('Date')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    return get_plot_as_base64(fig)

def generate_forecast_chart(tracker_id: str, metric: str = 'completion_rate', days: int = 7):
    """Generates forecast chart with confidence intervals."""
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
        
        # Validate we have data
        if len(df) == 0:
            return None
        
        historical_values = df['rate'].values
        historical_dates = df['date'].values
    else:
        return None
    
    # Validate historical dates
    if len(historical_dates) == 0:
        return None
    
    forecast_result = ts_data['forecast']
    forecast_values = forecast_result.get('forecast', [])
    conf_lower = forecast_result.get('confidence_lower', [])
    conf_upper = forecast_result.get('confidence_upper', [])
    
    # Validate forecast data
    if not forecast_values or len(forecast_values) == 0:
        return None
    
    # Create forecast dates - validate last_date is not NaT
    last_date = historical_dates[-1]
    if pd.isna(last_date):
        # Use today as fallback
        last_date = pd.Timestamp.now().normalize()
    
    try:
        forecast_dates = pd.date_range(start=last_date + pd.Timedelta(days=1), periods=days)
    except Exception as e:
        logger.error(f"Error creating forecast dates: {e}")
        return None
    
    # Plot
    sns.set_theme()
    fig, ax = plt.subplots(figsize=(12, 5))
    
    # Historical
    ax.plot(historical_dates, historical_values, marker='o', label='Historical', color='#2196F3', linewidth=2)
    
    # Forecast
    ax.plot(forecast_dates, forecast_values, marker='s', label='Forecast', color='#FF9800', linewidth=2, linestyle='--')
    
    # Confidence interval
    ax.fill_between(forecast_dates, conf_lower, conf_upper, alpha=0.3, color='#FF9800', label='95% Confidence')
    
    ax.set_title(f'{metric.replace("_", " ").title()} Forecast ({days} days)', fontsize=14)
    ax.set_ylabel('Value')
    ax.set_xlabel('Date')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    return get_plot_as_base64(fig)

def generate_progress_chart_with_trend(tracker_id: str):
    """Generates progress chart with trend line."""
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
    
    # Plot
    sns.set_theme()
    fig, ax = plt.subplots(figsize=(12, 5))
    
    ax.scatter(df['date'], df['rate'], alpha=0.6, s=50, color='#4CAF50', label='Actual')
    ax.plot(df['date'], trend_line, color='#F44336', linewidth=2, linestyle='--', label=f'Trend (R²={trend_info["r_squared"]:.2f})')
    
    ax.set_title('Progress with Trend Line', fontsize=14)
    ax.set_ylabel('Completion Rate %')
    ax.set_xlabel('Date')
    ax.legend()
    ax.grid(True, alpha=0.3)
    
    return get_plot_as_base64(fig)

