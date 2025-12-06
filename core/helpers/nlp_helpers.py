"""
NLP utilities for text analysis on tracker notes.
Uses classical NLP techniques (NLTK) for sentiment, keywords, and pattern extraction.
"""
import re
import logging
from collections import Counter
from typing import List, Dict, Tuple

logger = logging.getLogger(__name__)

# Lazy import NLTK to avoid startup overhead
_nltk_initialized = False

def _ensure_nltk():
    """Ensures NLTK is initialized and required data is downloaded."""
    global _nltk_initialized
    if _nltk_initialized:
        return
    
    try:
        import nltk
        # Download required data
        for resource in ['vader_lexicon', 'stopwords', 'punkt']:
            try:
                nltk.data.find(f'sentiment/{resource}' if resource == 'vader_lexicon' else f'tokenizers/{resource}' if resource == 'punkt' else f'corpora/{resource}')
            except LookupError:
                logger.info(f"Downloading NLTK {resource}...")
                nltk.download(resource, quiet=True)
        
        _nltk_initialized = True
    except Exception as e:
        logger.error(f"Failed to initialize NLTK: {e}")
        raise

def preprocess_text(text: str) -> str:
    """
    Normalizes text: lowercase, strip whitespace.
    """
    if not text:
        return ""
    return text.strip().lower()

def tokenize(text: str) -> List[str]:
    """
    Tokenizes text into words using NLTK.
    """
    _ensure_nltk()
    import nltk
    
    text = preprocess_text(text)
    tokens = nltk.word_tokenize(text)
    return tokens

def remove_stopwords(tokens: List[str]) -> List[str]:
    """
    Removes common stopwords from token list.
    """
    _ensure_nltk()
    from nltk.corpus import stopwords
    
    stop_words = set(stopwords.words('english'))
    return [t for t in tokens if t.lower() not in stop_words and len(t) > 2]

def compute_sentiment(text: str) -> Dict[str, float]:
    """
    Computes sentiment using VADER (Valence Aware Dictionary and sEntiment Reasoner).
    
    Returns:
        {
            'compound': float (-1 to 1, overall sentiment),
            'pos': float (0 to 1, positive),
            'neu': float (0 to 1, neutral),
            'neg': float (0 to 1, negative)
        }
    
    Falls back to neutral sentiment if NLTK unavailable.
    Results are cached for 1 hour.
    """
    if not text or not text.strip():
        return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0}
    
    # Check cache first
    from django.core.cache import cache
    import hashlib
    
    text_hash = hashlib.md5(text.encode()).hexdigest()[:16]
    cache_key = f"sentiment:{text_hash}"
    
    cached = cache.get(cache_key)
    if cached is not None:
        return cached
    
    # Try NLTK VADER
    try:
        _ensure_nltk()
        from nltk.sentiment.vader import SentimentIntensityAnalyzer
        
        sia = SentimentIntensityAnalyzer()
        scores = sia.polarity_scores(text)
        
        # Cache for 1 hour
        cache.set(cache_key, scores, 3600)
        return scores
        
    except Exception as e:
        # Fallback: return neutral sentiment
        logger.warning(f"NLTK sentiment analysis failed: {e}, returning neutral")
        neutral = {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0}
        return neutral


# Alias for backwards compatibility
def analyze_sentiment(text: str) -> Dict[str, float]:
    """Alias for compute_sentiment for backwards compatibility."""
    return compute_sentiment(text)

def extract_keywords(text: str, top_n: int = 10) -> List[Tuple[str, int]]:
    """
    Extracts top keywords using frequency analysis (after stopword removal).
    
    Returns:
        List of (word, count) tuples, sorted by frequency.
    """
    tokens = tokenize(text)
    tokens = remove_stopwords(tokens)
    
    # Filter out punctuation and very short words
    tokens = [t for t in tokens if t.isalpha() and len(t) > 2]
    
    if not tokens:
        return []
    
    counter = Counter(tokens)
    return counter.most_common(top_n)

def extract_sleep_pattern(text: str) -> Dict[str, any]:
    """
    Extracts sleep-related information using regex.
    
    Patterns:
        - "slept X hours"
        - "sleep: X"
        - "X hours of sleep"
    
    Returns:
        {'hours': float | None, 'matched_text': str | None}
    """
    patterns = [
        r'slept?\s+(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)',
        r'sleep:?\s*(\d+(?:\.\d+)?)',
        r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)\s+(?:of\s+)?sleep',
    ]
    
    text_lower = text.lower()
    for pattern in patterns:
        match = re.search(pattern, text_lower)
        if match:
            return {
                'hours': float(match.group(1)),
                'matched_text': match.group(0)
            }
    
    return {'hours': None, 'matched_text': None}

def extract_feeling_statements(text: str) -> List[str]:
    """
    Extracts "I feel..." statements using regex.
    
    Returns:
        List of feeling statements found.
    """
    pattern = r'I feel (\w+(?:\s+\w+){0,3})'
    matches = re.findall(pattern, text, re.IGNORECASE)
    return matches

def extract_numeric_patterns(text: str) -> Dict[str, List[float]]:
    """
    Extracts numeric values with context.
    
    Returns:
        {'all_numbers': [...], 'hours': [...], 'percentages': [...]}
    """
    numbers = re.findall(r'\d+(?:\.\d+)?', text)
    hours = re.findall(r'(\d+(?:\.\d+)?)\s*(?:hours?|hrs?)', text.lower())
    percentages = re.findall(r'(\d+(?:\.\d+)?)\s*%', text)
    
    return {
        'all_numbers': [float(n) for n in numbers],
        'hours': [float(h) for h in hours],
        'percentages': [float(p) for p in percentages]
    }

def analyze_text_comprehensive(text: str) -> Dict:
    """
    Performs comprehensive NLP analysis on text.
    
    Returns:
        {
            'sentiment': {...},
            'keywords': [...],
            'sleep': {...},
            'feelings': [...],
            'numeric_patterns': {...}
        }
    """
    return {
        'sentiment': compute_sentiment(text),
        'keywords': extract_keywords(text),
        'sleep': extract_sleep_pattern(text),
        'feelings': extract_feeling_statements(text),
        'numeric_patterns': extract_numeric_patterns(text)
    }


def parse_recurrence_pattern(text: str) -> Dict:
    """
    Parse natural language recurrence patterns.
    
    Supports patterns like:
        - "every day", "daily"
        - "every 3 days"
        - "weekly", "every week"
        - "on monday and friday"
        - "weekdays", "weekends"
        - "monthly", "every month"
    
    Returns:
        {
            'pattern_type': 'daily' | 'interval' | 'weekly' | 'monthly' | 'custom' | None,
            'interval': int | None,
            'days_of_week': List[int] | None,  # 0=Monday, 6=Sunday
            'raw_match': str | None
        }
    """
    text_lower = text.lower().strip()
    
    # Daily patterns
    if re.match(r'(every\s*day|daily|each\s*day)', text_lower):
        return {
            'pattern_type': 'daily',
            'interval': 1,
            'days_of_week': None,
            'raw_match': text_lower
        }
    
    # Interval patterns: "every N days/weeks"
    interval_match = re.match(r'every\s+(\d+)\s+(day|week|month)s?', text_lower)
    if interval_match:
        num = int(interval_match.group(1))
        unit = interval_match.group(2)
        return {
            'pattern_type': 'interval',
            'interval': num if unit == 'day' else num * 7 if unit == 'week' else num * 30,
            'days_of_week': None,
            'raw_match': interval_match.group(0)
        }
    
    # Weekly patterns
    if re.match(r'(weekly|every\s*week)', text_lower):
        return {
            'pattern_type': 'weekly',
            'interval': 7,
            'days_of_week': None,
            'raw_match': text_lower
        }
    
    # Specific days of week
    day_map = {
        'monday': 0, 'mon': 0,
        'tuesday': 1, 'tue': 1,
        'wednesday': 2, 'wed': 2,
        'thursday': 3, 'thu': 3,
        'friday': 4, 'fri': 4,
        'saturday': 5, 'sat': 5,
        'sunday': 6, 'sun': 6
    }
    
    days_pattern = r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday|mon|tue|wed|thu|fri|sat|sun)\b'
    found_days = re.findall(days_pattern, text_lower)
    
    if found_days:
        days_of_week = sorted(set(day_map[d] for d in found_days))
        return {
            'pattern_type': 'custom',
            'interval': None,
            'days_of_week': days_of_week,
            'raw_match': ', '.join(found_days)
        }
    
    # Weekdays/Weekends
    if 'weekday' in text_lower:
        return {
            'pattern_type': 'custom',
            'interval': None,
            'days_of_week': [0, 1, 2, 3, 4],  # Mon-Fri
            'raw_match': 'weekdays'
        }
    
    if 'weekend' in text_lower:
        return {
            'pattern_type': 'custom',
            'interval': None,
            'days_of_week': [5, 6],  # Sat-Sun
            'raw_match': 'weekends'
        }
    
    # Monthly patterns
    if re.match(r'(monthly|every\s*month)', text_lower):
        return {
            'pattern_type': 'monthly',
            'interval': 30,
            'days_of_week': None,
            'raw_match': text_lower
        }
    
    # No pattern found
    return {
        'pattern_type': None,
        'interval': None,
        'days_of_week': None,
        'raw_match': None
    }


def extract_goal_keywords(text: str) -> Dict:
    """
    Extract goal-related keywords and sentiment from text.
    
    Identifies:
        - Goal verbs (achieve, complete, reach, etc.)
        - Time references (by next week, in 30 days)
        - Quantitative targets (lose 5 kg, save $1000)
        - Priority indicators (must, important, critical)
    
    Returns:
        {
            'goal_verbs': List[str],
            'time_references': List[str],
            'targets': List[Dict],
            'priority_level': 'high' | 'medium' | 'low',
            'is_goal_statement': bool
        }
    """
    text_lower = text.lower()
    
    # Goal action verbs
    goal_verbs_pattern = r'\b(achieve|complete|finish|accomplish|reach|attain|gain|lose|improve|increase|decrease|start|stop|learn|master|build|create|develop|establish)\b'
    goal_verbs = re.findall(goal_verbs_pattern, text_lower)
    
    # Time references
    time_pattern = r'\b(by\s+(next\s+)?(week|month|year|monday|tuesday|wednesday|thursday|friday|saturday|sunday)|in\s+\d+\s+(days?|weeks?|months?)|before\s+\w+|until\s+\w+)\b'
    time_refs = re.findall(time_pattern, text_lower)
    time_references = [t[0] if isinstance(t, tuple) else t for t in time_refs]
    
    # Quantitative targets (number + unit)
    targets = []
    target_pattern = r'(\d+(?:\.\d+)?)\s*(kg|lbs?|pounds?|km|miles?|hours?|minutes?|\$|dollars?|times?|reps?|pages?|books?|%|percent)'
    target_matches = re.findall(target_pattern, text_lower)
    for value, unit in target_matches:
        targets.append({'value': float(value), 'unit': unit})
    
    # Priority indicators
    high_priority = ['must', 'critical', 'essential', 'urgent', 'important', 'priority']
    medium_priority = ['should', 'want to', 'would like', 'plan to']
    
    priority = 'low'
    for word in high_priority:
        if word in text_lower:
            priority = 'high'
            break
    if priority == 'low':
        for word in medium_priority:
            if word in text_lower:
                priority = 'medium'
                break
    
    # Determine if this looks like a goal statement
    is_goal = bool(goal_verbs) or bool(targets) or bool(time_references)
    
    return {
        'goal_verbs': list(set(goal_verbs)),
        'time_references': time_references,
        'targets': targets,
        'priority_level': priority,
        'is_goal_statement': is_goal
    }

