
import pytest
from unittest.mock import Mock, patch
from core.helpers import nlp_helpers

class TestNLPHelpersUnit:

    @pytest.fixture
    def mock_nltk(self):
        with patch.dict('sys.modules', {'nltk': Mock(), 'nltk.corpus': Mock(), 'nltk.sentiment.vader': Mock()}) as mocked_modules:
            yield mocked_modules

    def test_preprocess_text(self):
        assert nlp_helpers.preprocess_text("  HeLLo  ") == "hello"
        assert nlp_helpers.preprocess_text("") == ""

    def test_tokenize(self, mock_nltk):
        # We need to patch nlp_helpers._ensure_nltk to avoid real download
        with patch('core.helpers.nlp_helpers._ensure_nltk') as mock_ensure:
            with patch('nltk.word_tokenize') as mock_tokenize:
                mock_tokenize.return_value = ['hello', 'world']
                tokens = nlp_helpers.tokenize("hello world")
                assert tokens == ['hello', 'world']
                mock_ensure.assert_called()

    def test_remove_stopwords(self, mock_nltk):
        with patch('core.helpers.nlp_helpers._ensure_nltk'):
            # Stopwords is NLTK corpus
            mock_stopwords = Mock()
            mock_stopwords.words.return_value = ['a', 'the', 'is']
            
            with patch('nltk.corpus.stopwords', mock_stopwords):
                tokens = ['this', 'is', 'a', 'test', 'of', 'text']
                # remove_stopwords checks if t.lower() not in words AND len(t) > 2
                # 'this' > 2, not in [a, the, is] -> Keep
                # 'is' -> Remove
                # 'a' -> Remove
                # 'test' -> Keep
                # 'of' -> Length 2. len > 2 needs to strictly be > 2?
                # Code: len(t) > 2
                
                filtered = nlp_helpers.remove_stopwords(tokens)
                assert 'test' in filtered
                assert 'this' in filtered
                assert 'of' not in filtered # Length 2
                assert 'is' not in filtered

    def test_compute_sentiment(self):
        with patch('django.core.cache.cache') as mock_cache:
            mock_cache.get.return_value = None
            
            with patch('core.helpers.nlp_helpers._ensure_nltk'):
                with patch('nltk.sentiment.vader.SentimentIntensityAnalyzer') as MockSIA:
                    sia_instance = MockSIA.return_value
                    sia_instance.polarity_scores.return_value = {
                        'compound': 0.8, 'pos': 0.9, 'neu': 0.1, 'neg': 0.0
                    }
                    
                    res = nlp_helpers.compute_sentiment("Great job")
                    assert res['compound'] == 0.8
                    mock_cache.set.assert_called()

    def test_compute_sentiment_cached(self):
        with patch('django.core.cache.cache') as mock_cache:
            mock_cache.get.return_value = {'compound': 0.5}
            res = nlp_helpers.compute_sentiment("Cached")
            assert res['compound'] == 0.5

    def test_compute_sentiment_fallback(self):
        # Force exception
        with patch('django.core.cache.cache') as mock_cache:
            mock_cache.get.return_value = None
            with patch('core.helpers.nlp_helpers._ensure_nltk', side_effect=Exception("NLTK error")):
                res = nlp_helpers.compute_sentiment("Fail")
                assert res['neu'] == 1.0

    def test_extract_keywords(self):
        with patch('core.helpers.nlp_helpers.tokenize') as mock_tok:
            mock_tok.return_value = ['apple', 'banana', 'apple', 'the']
            with patch('core.helpers.nlp_helpers.remove_stopwords') as mock_rem:
                # filter 'the' out, keep 'apple', 'banana'
                mock_rem.return_value = ['apple', 'banana', 'apple']
                
                res = nlp_helpers.extract_keywords("text", top_n=2)
                # Counter: apple:2, banana:1
                assert res == [('apple', 2), ('banana', 1)]

    def test_extract_sleep_pattern(self):
        assert nlp_helpers.extract_sleep_pattern("I slept 8 hours")['hours'] == 8.0
        assert nlp_helpers.extract_sleep_pattern("Sleep: 7.5")['hours'] == 7.5
        assert nlp_helpers.extract_sleep_pattern("6 hours of sleep")['hours'] == 6.0
        assert nlp_helpers.extract_sleep_pattern("No sleep info")['hours'] is None

    def test_extract_feeling_statements(self):
        text = "I feel happy today. Also I feel a bit tired."
        res = nlp_helpers.extract_feeling_statements(text)
        assert "happy" in res[0]
        assert "a bit tired" in res[1]

    def test_extract_numeric_patterns(self):
        text = "I ran 5 km in 2 hours. 100% effort."
        res = nlp_helpers.extract_numeric_patterns(text)
        assert 5.0 in res['all_numbers']
        assert 2.0 in res['hours']
        assert 100.0 in res['percentages']

    def test_analyze_text_comprehensive(self):
        with patch('core.helpers.nlp_helpers.compute_sentiment') as mock_sent:
            mock_sent.return_value = {}
            with patch('core.helpers.nlp_helpers.extract_keywords') as mock_kw:
                mock_kw.return_value = []
                res = nlp_helpers.analyze_text_comprehensive("test")
                assert 'sentiment' in res
                assert 'sleep' in res

    def test_parse_recurrence_pattern(self):
        # Daily
        assert nlp_helpers.parse_recurrence_pattern("every day")['pattern_type'] == 'daily'
        
        # Interval
        res = nlp_helpers.parse_recurrence_pattern("every 3 days")
        assert res['pattern_type'] == 'interval'
        assert res['interval'] == 3
        
        res = nlp_helpers.parse_recurrence_pattern("every 2 weeks")
        assert res['pattern_type'] == 'interval'
        assert res['interval'] == 14
        
        # Weekly
        assert nlp_helpers.parse_recurrence_pattern("weekly")['pattern_type'] == 'weekly'
        
        # Specific days
        res = nlp_helpers.parse_recurrence_pattern("On Monday and Friday")
        assert res['pattern_type'] == 'custom'
        assert res['days_of_week'] == [0, 4] # 0=Mon, 4=Fri
        
        # Weekdays
        res = nlp_helpers.parse_recurrence_pattern("weekdays")
        assert res['days_of_week'] == [0, 1, 2, 3, 4]
        
        # Monthly
        assert nlp_helpers.parse_recurrence_pattern("monthly")['pattern_type'] == 'monthly'
        
        # None
        assert nlp_helpers.parse_recurrence_pattern("random text")['pattern_type'] is None

    def test_extract_goal_keywords(self):
        text = "I want to lose 5 kg by next week. It is critical."
        res = nlp_helpers.extract_goal_keywords(text)
        assert 'lose' in res['goal_verbs']
        assert res['targets'][0]['unit'] == 'kg'
        assert res['targets'][0]['value'] == 5.0
        assert 'next week' in res['time_references'][0]
        assert res['priority_level'] == 'high' # critical
        assert res['is_goal_statement'] is True
        
        text2 = "Just hanging out"
        res2 = nlp_helpers.extract_goal_keywords(text2)
        assert res2['is_goal_statement'] is False
        assert res2['priority_level'] == 'low'

    def test_ensure_nltk_logic(self):
        # Reset initialized
        nlp_helpers._nltk_initialized = False
        with patch('nltk.data.find') as mock_find:
            mock_find.side_effect = LookupError("Not found") # Force download
            with patch('nltk.download') as mock_dl:
                nlp_helpers._ensure_nltk()
                assert mock_dl.call_count >= 1
        
        # Subsequent call returns early
        with patch('nltk.download') as mock_dl:
            nlp_helpers._ensure_nltk()
            mock_dl.assert_not_called()
