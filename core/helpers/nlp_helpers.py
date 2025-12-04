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
    """
    _ensure_nltk()
    from nltk.sentiment.vader import SentimentIntensityAnalyzer
    
    if not text:
        return {'compound': 0.0, 'pos': 0.0, 'neu': 1.0, 'neg': 0.0}
    
    sia = SentimentIntensityAnalyzer()
    scores = sia.polarity_scores(text)
    return scores

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
