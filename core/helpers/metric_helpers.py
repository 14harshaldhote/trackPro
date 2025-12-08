"""
Metric helper functions for behavior analytics.
Implements efficient algorithms for streak detection, consistency scoring, and balance metrics.

Pure Python implementation to be serverless-friendly.
No heavy dependencies (pandas, numpy, scipy, statsmodels, sklearn).
"""
import math
import statistics
from typing import List, Dict, Tuple, Union
from datetime import date, timedelta

def detect_streaks(completion_list: List[bool]) -> Dict[str, int]:
    """
    Detect current and longest streaks using pure Python.
    
    Args:
        completion_list: List of booleans, True = completed
    
    Returns:
        {
            'current': int,
            'best': int
        }
    """
    if not completion_list:
        return {'current': 0, 'best': 0}
        
    current = 0
    best = 0
    temp = 0
    
    # Calculate best streak
    for status in completion_list:
        if status:
            temp += 1
            if temp > best:
                best = temp
        else:
            temp = 0
            
    # Calculate current streak (scan from end)
    for status in reversed(completion_list):
        if status:
            current += 1
        else:
            break
            
    return {'current': current, 'best': best}

def compute_rolling_consistency(completion_series: List[float], window_days: int = 7) -> List[float]:
    """
    Computes rolling window consistency score (0-100).
    
    Args:
        completion_series: List of floats (0 or 1)
        window_days: Rolling window size
    
    Returns:
        List of consistency scores (0-100)
    """
    if not completion_series:
        return []
        
    result = []
    series_len = len(completion_series)
    
    for i in range(series_len):
        start_idx = max(0, i - window_days + 1)
        # Use simple slice
        window = completion_series[start_idx : i + 1]
        
        avg = sum(window) / len(window)
        result.append(avg * 100) # Convert to 0-100 score
        
    return result

def compute_interval_consistency(dates: List[date]) -> Dict[str, float]:
    """
    Computes consistency based on intervals between completion dates.
    Lower standard deviation = higher consistency.
    
    Args:
        dates: List of completion dates
    
    Returns:
        {
            'interval_std': float (days),
            'interval_mean': float (days),
            'consistency_score': float (0-100, normalized)
        }
    """
    if len(dates) < 2:
        return {
            'interval_std': 0.0,
            'interval_mean': 0.0,
            'consistency_score': 0.0
        }
    
    # Sort dates
    sorted_dates = sorted(dates)
    
    # Calculate intervals in days
    intervals = [(sorted_dates[i+1] - sorted_dates[i]).days for i in range(len(sorted_dates) - 1)]
    
    interval_std = float(statistics.stdev(intervals)) if len(intervals) > 1 else 0.0
    interval_mean = float(statistics.mean(intervals))
    
    # Normalize to 0-100: lower std = higher score
    # Use inverse relationship with cap
    if interval_mean > 0:
        coefficient_of_variation = interval_std / interval_mean
        # Map CV to 0-100 (CV of 0 = 100, CV of 1+ = 0)
        consistency_score = max(0, min(100, 100 * (1 - coefficient_of_variation)))
    else:
        consistency_score = 0.0
    
    return {
        'interval_std': interval_std,
        'interval_mean': interval_mean,
        'consistency_score': consistency_score
    }

def compute_category_balance(category_counts: Dict[str, int]) -> Dict[str, float]:
    """
    Computes balance score based on category distribution.
    Uses normalized entropy: higher = more balanced.
    
    Args:
        category_counts: {category: count}
    
    Returns:
        {
            'entropy': float,
            'max_entropy': float,
            'balance_score': float (0-100),
            'normalized_distribution': {category: percentage}
        }
    """
    if not category_counts or sum(category_counts.values()) == 0:
        return {
            'entropy': 0.0,
            'max_entropy': 0.0,
            'balance_score': 0.0,
            'normalized_distribution': {}
        }
    
    total = sum(category_counts.values())
    proportions = {cat: count / total for cat, count in category_counts.items()}
    
    # Calculate Shannon entropy
    entropy = -sum(p * math.log2(p) if p > 0 else 0 for p in proportions.values())
    
    # Maximum entropy occurs when all categories are equal
    n_categories = len(category_counts)
    max_entropy = math.log2(n_categories) if n_categories > 1 else 0
    
    # Normalize to 0-100
    balance_score = (entropy / max_entropy * 100) if max_entropy > 0 else 100.0
    
    # Percentages
    normalized_distribution = {cat: p * 100 for cat, p in proportions.items()}
    
    return {
        'entropy': float(entropy),
        'max_entropy': float(max_entropy),
        'balance_score': float(balance_score),
        'normalized_distribution': normalized_distribution
    }

def compute_effort_index(tasks: List[Dict], duration_field: str = 'duration', difficulty_field: str = 'difficulty') -> Dict[str, float]:
    """
    Computes effort index combining duration and difficulty.
    
    Args:
        tasks: List of task dicts
        duration_field: Field name for duration (hours)
        difficulty_field: Field name for difficulty ('low', 'medium', 'high')
    
    Returns:
        {
            'total_duration': float,
            'difficulty_score': float,
            'effort_index': float
        }
    """
    difficulty_weights = {
        'low': 1,
        'medium': 2,
        'high': 3
    }
    
    total_duration = 0.0
    difficulty_score = 0.0
    
    for task in tasks:
        # Duration
        duration = task.get(duration_field, 0)
        if isinstance(duration, (int, float)):
            total_duration += duration
        
        # Difficulty
        difficulty = task.get(difficulty_field, 'medium')
        if isinstance(difficulty, str):
            difficulty_score += difficulty_weights.get(difficulty.lower(), 2)
    
    # Effort = duration + weighted difficulty
    effort_index = total_duration + difficulty_score
    
    return {
        'total_duration': float(total_duration),
        'difficulty_score': float(difficulty_score),
        'effort_index': float(effort_index)
    }

def compute_trend_line_pure_python(x_values: List[float], y_values: List[float]) -> Dict[str, float]:
    """
    Computes linear regression trend line using pure Python.
    
    Returns:
        {
            'slope': float,
            'intercept': float,
            'r_squared': float
        }
    """
    if len(x_values) < 2 or len(x_values) != len(y_values):
        return {'slope': 0.0, 'intercept': 0.0, 'r_squared': 0.0}
    
    n = len(x_values)
    
    sum_x = sum(x_values)
    sum_y = sum(y_values)
    sum_xy = sum(x * y for x, y in zip(x_values, y_values))
    sum_x2 = sum(x**2 for x in x_values)
    
    try:
        # Calculate slope (m)
        numerator = n * sum_xy - sum_x * sum_y
        denominator = n * sum_x2 - sum_x**2
        
        if denominator == 0: # Vertical line or all x values are the same
            slope = float('inf') if numerator > 0 else float('-inf')
            intercept = 0.0 # Intercept is undefined for vertical line, set to 0
        else:
            slope = numerator / denominator
        
        # Calculate intercept (b)
        intercept = (sum_y - slope * sum_x) / n
        
        # Calculate R-squared
        y_pred = [slope * x + intercept for x in x_values]
        mean_y = sum_y / n
        
        ss_res = sum((y - y_p)**2 for y, y_p in zip(y_values, y_pred))
        ss_tot = sum((y - mean_y)**2 for y in y_values)
        
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        
    except ZeroDivisionError:
        return {'slope': 0.0, 'intercept': 0.0, 'r_squared': 0.0}
    
    return {
        'slope': float(slope),
        'intercept': float(intercept),
        'r_squared': float(r_squared)
    }

def compute_correlation_matrix(data_dict: Dict[str, List[float]]) -> Dict:
    """
    Computes correlation matrix between multiple series using pure Python (Pearson).
    
    Args:
        data_dict: {metric_name: list_of_values}
    
    Returns:
        {
            'correlation_matrix': dict,
            'warning': str (if p-values are not available)
        }
    """
    corr_matrix = {}
    
    metric_names = list(data_dict.keys())
    n_metrics = len(metric_names)
    
    if n_metrics < 2:
        return {
            'correlation_matrix': {},
            'warning': 'Not enough metrics to compute correlation matrix.'
        }
        
    for i, metric1 in enumerate(metric_names):
        corr_matrix[metric1] = {}
        for j, metric2 in enumerate(metric_names):
            if i == j:
                corr_matrix[metric1][metric2] = 1.0
            else:
                list1 = data_dict[metric1]
                list2 = data_dict[metric2]
                min_len = min(len(list1), len(list2))
                list1_aligned = list1[:min_len]
                list2_aligned = list2[:min_len]
                
                if len(list1_aligned) < 2:
                    corr_matrix[metric1][metric2] = 0.0
                else:
                    corr = calculate_correlation(list1_aligned, list2_aligned)
                    corr_matrix[metric1][metric2] = float(corr)
    
    return {
        'correlation_matrix': corr_matrix,
        'warning': 'P-values are not computed as scipy is not available.'
    }

def smooth_series(series: List[float], method: str = 'moving_avg', window: int = 7) -> List[float]:
    """
    Smooths a time series using various methods.
    
    Args:
        series: Time series to smooth
        method: 'moving_avg' or 'exponential'
        window: Window size for smoothing
    
    Returns:
        Smoothed series
    """
    if not series:
        return []
    
    if len(series) < window:
        return list(series) # Return a copy if window is larger than series
    
    if method == 'moving_avg':
        # Simple moving average
        smoothed_series = []
        for i in range(len(series)):
            start_idx = max(0, i - window // 2)
            end_idx = min(len(series), i + window // 2 + 1)
            window_slice = series[start_idx:end_idx]
            if window_slice:
                smoothed_series.append(statistics.mean(window_slice))
            else:
                smoothed_series.append(series[i]) # Should not happen if series is not empty
        return smoothed_series
    
    elif method == 'exponential':
        # Exponential moving average
        return _calculate_ema_pure_python(series, window)
    
    else:
        return list(series)

def detect_change_points(series: List[float], threshold: float = 0.2) -> List[Dict]:
    """Simple change point detection based on significant shifts in mean"""
    if not series: 
        return []
    
    change_points = []
    window = 3
    if len(series) < 2 * window:
        return []
        
    for i in range(window, len(series) - window):
        prev_mean = sum(series[i-window:i]) / window
        next_mean = sum(series[i:i+window]) / window
        
        diff = abs(next_mean - prev_mean)
        if diff > threshold:
            change_points.append({
                'index': i,
                'diff': diff,
                'type': 'jump' if next_mean > prev_mean else 'drop'
            })
            
    return change_points

def _calculate_ema_pure_python(values: List[float], span: int) -> List[float]:
    """
    Calculates Exponential Moving Average (EMA) for a list of values.
    """
    if not values:
        return []
    if span <= 0:
        return list(values) # No smoothing
        
    alpha = 2 / (span + 1)
    ema_values = [values[0]]
    
    for i in range(1, len(values)):
        new_val = alpha * values[i] + (1 - alpha) * ema_values[-1]
        ema_values.append(new_val)
        
    return ema_values
    
def calculate_correlation(series_a: List[float], series_b: List[float]) -> float:
    """Calculate Pearson Correlation Coefficient"""
    if len(series_a) != len(series_b) or len(series_a) < 2:
        return 0.0
        
    mean_a = sum(series_a) / len(series_a)
    mean_b = sum(series_b) / len(series_b)
    
    numerator = sum((a - mean_a) * (b - mean_b) for a, b in zip(series_a, series_b))
    
    denom_a = sum((a - mean_a) ** 2 for a in series_a)
    denom_b = sum((b - mean_b) ** 2 for b in series_b)
    
    denominator = math.sqrt(denom_a * denom_b)
    
    if denominator == 0:
        return 0.0
        
    return numerator / denominator

# Removed compute_pearson_correlation with numpy
# Use calculate_correlation instead.
# Removed z-score, fft, and other heavy math functions
# Pure implementation of necessary stats functions

def calculate_mean(values: List[float]) -> float:
    return sum(values) / len(values) if values else 0.0

def calculate_std(values: List[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0

def exponential_moving_average(values: List[float], alpha: float = 0.3) -> List[float]:
    """Pure Python EMA"""
    if not values:
        return []
    
    ema = [values[0]]
    for i in range(1, len(values)):
        new_val = alpha * values[i] + (1 - alpha) * ema[-1]
        ema.append(new_val)
    return ema
