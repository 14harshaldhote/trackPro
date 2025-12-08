"""
Metric helper functions for behavior analytics.
Implements efficient algorithms for streak detection, consistency scoring, and balance metrics.

Uses Polars for high-performance dataframe operations when available (10x faster than Pandas).
All statistical methods use pure numpy - NO heavy dependencies (scipy/statsmodels/sklearn).
"""
import numpy as np
import pandas as pd
from typing import List, Dict, Tuple, Union
from datetime import date, timedelta

# Optional Polars import with fallback to Pandas
try:
    import polars as pl
    POLARS_AVAILABLE = True
except ImportError:
    POLARS_AVAILABLE = False

def detect_streaks_numpy(completion_series: pd.Series) -> Dict[str, int]:
    """
    Detects current and longest streaks using NumPy run-length encoding.
    
    Args:
        completion_series: Boolean pandas Series indexed by date, True = completed
    
    Returns:
        {
            'current_streak': int,
            'longest_streak': int,
            'total_days': int
        }
    """
    if completion_series.empty:
        return {'current_streak': 0, 'longest_streak': 0, 'total_days': 0}
    
    # Ensure sorted by date
    completion_series = completion_series.sort_index()
    
    # Convert to numpy boolean array
    completed = completion_series.values.astype(bool)
    
    # Run-length encoding using diff and cumsum
    # Find where value changes
    changes = np.diff(np.concatenate(([False], completed, [False])).astype(int))
    run_starts = np.where(changes == 1)[0]
    run_ends = np.where(changes == -1)[0]
    
    # Calculate run lengths
    run_lengths = run_ends - run_starts
    
    # Find longest streak
    longest_streak = int(run_lengths.max()) if len(run_lengths) > 0 else 0
    
    # Current streak is the last run if it ends at the last element
    current_streak = 0
    if len(run_lengths) > 0 and run_ends[-1] == len(completed):
        current_streak = int(run_lengths[-1])
    
    return {
        'current_streak': current_streak,
        'longest_streak': longest_streak,
        'total_days': len(completed)
    }

def compute_rolling_consistency(completion_series: pd.Series, window_days: int = 7) -> pd.Series:
    """
    Computes rolling window consistency score (0-100).
    
    Args:
        completion_series: Boolean pandas Series indexed by date
        window_days: Rolling window size
    
    Returns:
        Series of consistency scores (0-100)
    """
    if completion_series.empty:
        return pd.Series(dtype=float)
    
    # Ensure sorted
    completion_series = completion_series.sort_index()
    
    # Rolling mean (proportion completed in window) * 100
    rolling_mean = completion_series.astype(float).rolling(window=window_days, min_periods=1).mean()
    
    return rolling_mean * 100

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
    
    interval_std = float(np.std(intervals))
    interval_mean = float(np.mean(intervals))
    
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
    entropy = -sum(p * np.log2(p) if p > 0 else 0 for p in proportions.values())
    
    # Maximum entropy occurs when all categories are equal
    n_categories = len(category_counts)
    max_entropy = np.log2(n_categories) if n_categories > 1 else 0
    
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

def compute_trend_line(x_values: np.ndarray, y_values: np.ndarray) -> Dict[str, float]:
    """
    Computes linear regression trend line.
    
    Returns:
        {
            'slope': float,
            'intercept': float,
            'r_squared': float
        }
    """
    if len(x_values) < 2:
        return {'slope': 0.0, 'intercept': 0.0, 'r_squared': 0.0}
    
    # Use numpy polyfit for linear regression
    coeffs = np.polyfit(x_values, y_values, 1)
    slope, intercept = coeffs
    
    # Calculate R-squared
    y_pred = slope * x_values + intercept
    ss_res = np.sum((y_values - y_pred) ** 2)
    ss_tot = np.sum((y_values - np.mean(y_values)) ** 2)
    r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
    
    return {
        'slope': float(slope),
        'intercept': float(intercept),
        'r_squared': float(r_squared)
    }

def compute_correlation_matrix(data_dict: Dict[str, np.ndarray], method: str = 'pearson') -> Dict:
    """
    Computes correlation matrix between multiple series.
    
    Args:
        data_dict: {metric_name: array_of_values}
        method: 'pearson' or 'spearman'
    
    Returns:
        {
            'correlation_matrix': dict,
            'p_values': dict,
            'significant': dict  # True if p < 0.05
        }
    """
    if not SCIPY_AVAILABLE:
        return {
            'correlation_matrix': {},
            'p_values': {},
            'significant': {},
            'error': 'scipy not available'
        }
    
    stats = scipy_stats
    
    metric_names = list(data_dict.keys())
    n_metrics = len(metric_names)
    
    if n_metrics < 2:
        return {
            'correlation_matrix': {},
            'p_values': {},
            'significant': {}
        }
    
    corr_matrix = {}
    p_values = {}
    significant = {}
    
    for i, metric1 in enumerate(metric_names):
        corr_matrix[metric1] = {}
        p_values[metric1] = {}
        significant[metric1] = {}
        
        for j, metric2 in enumerate(metric_names):
            if i == j:
                corr_matrix[metric1][metric2] = 1.0
                p_values[metric1][metric2] = 0.0
                significant[metric1][metric2] = True
            else:
                # Align arrays (take minimum length)
                arr1 = data_dict[metric1]
                arr2 = data_dict[metric2]
                min_len = min(len(arr1), len(arr2))
                arr1 = arr1[:min_len]
                arr2 = arr2[:min_len]
                
                if len(arr1) < 3:
                    corr_matrix[metric1][metric2] = 0.0
                    p_values[metric1][metric2] = 1.0
                    significant[metric1][metric2] = False
                else:
                    # Check for constant arrays (no variance) - correlation undefined
                    if np.std(arr1) == 0 or np.std(arr2) == 0:
                        corr_matrix[metric1][metric2] = 0.0
                        p_values[metric1][metric2] = 1.0
                        significant[metric1][metric2] = False
                    else:
                        if method == 'pearson':
                            corr, p_val = stats.pearsonr(arr1, arr2)
                        else:  # spearman
                            corr, p_val = stats.spearmanr(arr1, arr2)
                        
                        corr_matrix[metric1][metric2] = float(corr)
                        p_values[metric1][metric2] = float(p_val)
                        significant[metric1][metric2] = p_val < 0.05
    
    return {
        'correlation_matrix': corr_matrix,
        'p_values': p_values,
        'significant': significant
    }

def smooth_series(series: pd.Series, method: str = 'savgol', window: int = 7) -> pd.Series:
    """
    Smooths a time series using various methods.
    
    Args:
        series: Time series to smooth
        method: 'savgol', 'moving_avg', or 'exponential'
        window: Window size for smoothing
    
    Returns:
        Smoothed series
    """
    if not SCIPY_AVAILABLE:
        # Fallback to simple moving average
        return series.rolling(window=window, center=True).mean().fillna(series)
    
    if len(series) < window:
        return series
    
    if method == 'savgol':
        # Savitzky-Golay filter
        # Polynomial order should be less than window
        polyorder = min(3, window - 1)
        smoothed = savgol_filter(series.values, window, polyorder)
        return pd.Series(smoothed, index=series.index)
    
    elif method == 'moving_avg':
        # Simple moving average
        return series.rolling(window=window, center=True).mean().fillna(series)
    
    elif method == 'exponential':
        # Exponential moving average
        return series.ewm(span=window, adjust=False).mean()
    
    else:
        return series

def detect_change_points(series: pd.Series, threshold: float = 0.2) -> List[Dict]:
    """
    Detects significant change points in a time series.
    
    Args:
        series: Time series to analyze
        threshold: Minimum change (as fraction of std) to count as change point
    
    Returns:
        List of {'date': date, 'change': float, 'direction': 'up'|'down'}
    """
    if len(series) < 3:
        return []
    
    # Compute first differences
    diffs = series.diff()
    
    # Threshold based on std of differences
    std = diffs.std()
    threshold_value = threshold * std
    
    change_points = []
    for i in range(1, len(diffs)):
        if abs(diffs.iloc[i]) > threshold_value:
            change_points.append({
                'date': str(series.index[i]),
                'change': float(diffs.iloc[i]),
                'direction': 'up' if diffs.iloc[i] > 0 else 'down',
                'magnitude': float(abs(diffs.iloc[i]) / std)  # In units of std
            })
    
    return change_points

def forecast_arima(series: pd.Series, steps: int = 7) -> Dict:
    """
    Forecasts future values using ARIMA model.
    
    Args:
        series: Historical time series
        steps: Number of steps to forecast
    
    Returns:
        {
            'forecast': list of values,
            'confidence_lower': list,
            'confidence_upper': list,
            'model_params': dict
        }
    """
    try:
        from statsmodels.tsa.arima.model import ARIMA
    except ImportError:
        # Fallback to simple method if statsmodels not available
        return _simple_forecast(series, steps)
    
    if len(series) < 10:
        # Not enough data for ARIMA, use simple method
        return _simple_forecast(series, steps)
    
    try:
        # Auto ARIMA-like: try simple (1,1,1) model
        model = ARIMA(series.values, order=(1, 1, 1))
        fitted = model.fit()
        
        # Forecast
        forecast_result = fitted.forecast(steps=steps)
        
        # Confidence intervals (approximate)
        std_err = fitted.resid.std()
        forecast_values = forecast_result
        
        confidence_lower = forecast_values - 1.96 * std_err
        confidence_upper = forecast_values + 1.96 * std_err
        
        return {
            'forecast': forecast_values.tolist(),
            'confidence_lower': confidence_lower.tolist(),
            'confidence_upper': confidence_upper.tolist(),
            'model_params': {
                'order': '(1,1,1)',
                'aic': float(fitted.aic),
                'std_err': float(std_err)
            }
        }
    except Exception as e:
        # If ARIMA fails, use simple forecast
        return _simple_forecast(series, steps)

def _simple_forecast(series: pd.Series, steps: int) -> Dict:
    """Simple forecast using exponential smoothing fallback."""
    if len(series) == 0:
        return {
            'forecast': [0.0] * steps,
            'confidence_lower': [0.0] * steps,
            'confidence_upper': [0.0] * steps,
            'model_params': {'method': 'constant', 'value': 0.0}
        }
    
    # Use exponential weighted mean for forecast
    alpha = 0.3
    last_value = float(series.iloc[-1])
    ema = float(series.ewm(alpha=alpha, adjust=False).mean().iloc[-1])
    
    # Simple forecast: use EMA
    forecast = [ema] * steps
    
    # Confidence based on recent volatility
    std = float(series.tail(10).std()) if len(series) >= 10 else float(series.std())
    confidence_lower = [ema - 1.96 * std] * steps
    confidence_upper = [ema + 1.96 * std] * steps
    
    return {
        'forecast': forecast,
        'confidence_lower': confidence_lower,
        'confidence_upper': confidence_upper,
        'model_params': {
            'method': 'exponential_smoothing',
            'alpha': alpha,
            'ema': ema,
            'std': std
        }
    }

def analyze_seasonality(series: pd.Series, period: int = 7) -> Dict:
    """
    Detects seasonality in time series.
    
    Args:
        series: Time series to analyze
        period: Expected period (e.g., 7 for weekly)
    
    Returns:
        {
            'has_seasonality': bool,
            'seasonal_strength': float (0-1),
            'seasonal_pattern': list
        }
    """
    if len(series) < period * 2:
        return {
            'has_seasonality': False,
            'seasonal_strength': 0.0,
            'seasonal_pattern': []
        }
    
    # Compute seasonal averages
    seasonal_pattern = []
    for i in range(period):
        # Values at positions: i, i+period, i+2*period, ...
        seasonal_values = series.iloc[i::period]
        if len(seasonal_values) > 0:
            seasonal_pattern.append(float(seasonal_values.mean()))
        else:
            seasonal_pattern.append(0.0)
    
    # Measure strength: variance of seasonal pattern vs overall variance
    if len(seasonal_pattern) > 1:
        seasonal_var = np.var(seasonal_pattern)
        total_var = np.var(series.values)
        seasonal_strength = seasonal_var / total_var if total_var > 0 else 0.0
        seasonal_strength = min(1.0, seasonal_strength)
    else:
        seasonal_strength = 0.0
    
    has_seasonality = seasonal_strength > 0.3
    
    return {
        'has_seasonality': has_seasonality,
        'seasonal_strength': float(seasonal_strength),
        'seasonal_pattern': seasonal_pattern
    }


# ============================================================================
# POLARS-OPTIMIZED FUNCTIONS (10x faster than Pandas)
# ============================================================================

def aggregate_daily_metrics_polars(data_dict: List[Dict]) -> pl.DataFrame:
    """
    Fast aggregation using Polars (Rust-based, zero-copy operations)
    
    Args:
        data_dict: List of dicts with task completion data
    
    Returns:
        Polars DataFrame with aggregated metrics
    """
    if not POLARS_AVAILABLE:
        # Fallback to pandas
        return pl.from_pandas(pd.DataFrame(data_dict))
    
    df = pl.DataFrame(data_dict)
    
    # Fast group-by aggregations (10x faster than pandas)
    daily_agg = df.group_by('date').agg([
        pl.count('task_id').alias('total_tasks'),
        pl.col('status').filter(pl.col('status') == 'DONE').count().alias('completed'),
        pl.col('weight').sum().alias('total_weight'),
        pl.col('weight').filter(pl.col('status') == 'DONE').sum().alias('completed_weight')
    ])
    
    # Calculate completion rate
    daily_agg = daily_agg.with_columns([
        ((pl.col('completed') / pl.col('total_tasks')) * 100).alias('completion_rate'),
        ((pl.col('completed_weight') / pl.col('total_weight')) * 100).alias('weighted_rate')
    ])
    
    return daily_agg


def detect_seasonality_acf(series: Union[pd.Series, np.ndarray], period: int = 7) -> Dict:
    """
    Advanced seasonality detection using AutoCorrelation Function (ACF)
    Pure numpy implementation - no statsmodels required
    
    Args:
        series: Time series data
        period: Expected seasonal period (7 for weekly)
    
    Returns:
        {
            'has_seasonality': bool,
            'seasonal_strength': float,
            'significant_lags': List[int],
            'acf_values': List[float]
        }
    """
    if len(series) < period * 3:
        return {
            'has_seasonality': False,
            'seasonal_strength': 0.0,
            'significant_lags': [],
            'acf_values': []
        }
    
    # Convert to numpy array if needed
    if isinstance(series, pd.Series):
        series = series.values
    
    # Calculate ACF using numpy (FFT-based for speed)
    max_lag = min(period * 2, len(series) // 2)
    acf_values = _calculate_acf_numpy(series, max_lag)
    
    # Check significance at seasonal lag
    # Threshold: 1.96 / sqrt(n) for 95% confidence
    threshold = 1.96 / np.sqrt(len(series))
    
    significant_lags = []
    for lag in range(1, max_lag + 1):
        if abs(acf_values[lag]) > threshold:
            significant_lags.append(lag)
    
    # Seasonal strength: ACF at seasonal lag
    if period < len(acf_values):
        seasonal_strength = abs(acf_values[period])
    else:
        seasonal_strength = 0.0
    
    has_seasonality = seasonal_strength > threshold and period in significant_lags
    
    return {
        'has_seasonality': has_seasonality,
        'seasonal_strength': float(seasonal_strength),
        'significant_lags': significant_lags[:10],  # Top 10
        'acf_values': acf_values[:period * 2].tolist(),
        'method': 'acf_numpy'
    }


def _calculate_acf_numpy(series: np.ndarray, max_lag: int) -> np.ndarray:
    """
    Calculate AutoCorrelation Function using pure numpy (FFT-based)
    Fast and serverless-safe
    
    Args:
        series: 1D numpy array
        max_lag: Maximum lag to calculate
    
    Returns:
        ACF values from lag 0 to max_lag
    """
    # Demean the series
    series_mean = np.mean(series)
    series_demeaned = series - series_mean
    
    # Use FFT for fast correlation calculation
    n = len(series)
    
    # Pad to next power of 2 for FFT efficiency
    nfft = 2 ** int(np.ceil(np.log2(2 * n - 1)))
    
    # Compute autocorrelation via FFT
    fft_series = np.fft.fft(series_demeaned, n=nfft)
    auto_corr = np.fft.ifft(fft_series * np.conj(fft_series)).real[:n]
    
    # Normalize by variance and sample size
    variance = auto_corr[0]
    if variance == 0:
        return np.zeros(max_lag + 1)
    
    acf = auto_corr / variance
    
    # Return only up to max_lag
    return acf[:max_lag + 1]


def compute_pearson_correlation(x: np.ndarray, y: np.ndarray) -> Dict:
    """
    Compute Pearson correlation without scipy (pure numpy)
    
    Returns:
        {
            'correlation': float,
            'p_value': float (approximate),
            'significant': bool
        }
    """
    if len(x) != len(y) or len(x) < 3:
        return {'correlation': 0.0, 'p_value': 1.0, 'significant': False}
    
    # Remove NaN values
    mask = ~(np.isnan(x) | np.isnan(y))
    x = x[mask]
    y = y[mask]
    
    if len(x) < 3:
        return {'correlation': 0.0, 'p_value': 1.0, 'significant': False}
    
    # Pearson correlation
    x_mean = np.mean(x)
    y_mean = np.mean(y)
    
    numerator = np.sum((x - x_mean) * (y - y_mean))
    denominator = np.sqrt(np.sum((x - x_mean)**2) * np.sum((y - y_mean)**2))
    
    if denominator == 0:
        return {'correlation': 0.0, 'p_value': 1.0, 'significant': False}
    
    r = numerator / denominator
    
    # Approximate p-value using t-distribution
    n = len(x)
    t_stat = r * np.sqrt(n - 2) / np.sqrt(1 - r**2) if abs(r) < 1 else np.inf
    
    # Very rough p-value approximation (conservative)
    # For proper p-value, would need scipy.stats.t.sf
    if abs(t_stat) > 2.0:  # Roughly p < 0.05 for n > 30
        p_value = 0.01
        significant = True
    elif abs(t_stat) > 1.0:
        p_value = 0.1
        significant = False
    else:
        p_value = 0.5
        significant = False
    
    return {
        'correlation': float(r),
        'p_value': float(p_value),
        'significant': significant,
        't_statistic': float(t_stat)
    }


def rolling_statistics_polars(df: pl.DataFrame, value_col: str, window: int = 7) -> pl.DataFrame:
    """
    Fast rolling statistics using Polars
    
    Args:
        df: Polars DataFrame with date and value columns
        value_col: Name of value column
        window: Rolling window size
    
    Returns:
        DataFrame with added rolling statistics
    """
    if not POLARS_AVAILABLE:
        # Convert to pandas for fallback
        pd_df = df.to_pandas() if hasattr(df, 'to_pandas') else df
        pd_df[f'{value_col}_rolling_mean'] = pd_df[value_col].rolling(window).mean()
        pd_df[f'{value_col}_rolling_std'] = pd_df[value_col].rolling(window).std()
        return pl.from_pandas(pd_df)
    
    # Polars rolling operations (much faster)
    result = df.with_columns([
        pl.col(value_col).rolling_mean(window).alias(f'{value_col}_rolling_mean'),
        pl.col(value_col).rolling_std(window).alias(f'{value_col}_rolling_std'),
        pl.col(value_col).rolling_min(window).alias(f'{value_col}_rolling_min'),
        pl.col(value_col).rolling_max(window).alias(f'{value_col}_rolling_max')
    ])
    
    return result


def compute_z_score_anomalies(values: np.ndarray, threshold: float = 2.5) -> Dict:
    """
    Detect anomalies using Z-score method (lightweight, no sklearn)
    
    Args:
        values: Array of values
        threshold: Z-score threshold (default: 2.5 = ~1.2% outliers)
    
    Returns:
        {
            'anomaly_indices': List[int],
            'anomaly_values': List[float],
            'z_scores': np.ndarray
        }
    """
    if len(values) < 3:
        return {
            'anomaly_indices': [],
            'anomaly_values': [],
            'z_scores': []
        }
    
    mean = np.mean(values)
    std = np.std(values)
    
    if std == 0:
        return {
            'anomaly_indices': [],
            'anomaly_values': [],
            'z_scores': np.zeros(len(values))
        }
    
    z_scores = (values - mean) / std
    anomaly_mask = np.abs(z_scores) > threshold
    anomaly_indices = np.where(anomaly_mask)[0].tolist()
    anomaly_values = values[anomaly_mask].tolist()
    
    return {
        'anomaly_indices': anomaly_indices,
        'anomaly_values': anomaly_values,
        'z_scores': z_scores,
        'threshold': threshold
    }


def exponential_moving_average(values: np.ndarray, alpha: float = 0.3) -> np.ndarray:
    """
    Calculate EMA without pandas (pure numpy, faster)
    
    Args:
        values: Input array
        alpha: Smoothing factor (0-1)
    
    Returns:
        EMA array
    """
    if len(values) == 0:
        return np.array([])
    
    ema = np.zeros(len(values))
    ema[0] = values[0]
    
    for i in range(1, len(values)):
        ema[i] = alpha * values[i] + (1 - alpha) * ema[i-1]
    
    return ema
