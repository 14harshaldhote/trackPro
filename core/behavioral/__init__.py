"""
Behavioral Insights Engine Package

Rule-based insights tied to behavioral science research.
Generates actionable suggestions based on tracker metrics and NLP analysis.

No AI/ML - purely deterministic rules grounded in research.
"""
from core.behavioral.insights_engine import (
    InsightsEngine,
    InsightType,
    Severity,
    Insight,
    get_insights,
    get_top_insight,
    RESEARCH_NOTES
)

__all__ = [
    'InsightsEngine',
    'InsightType',
    'Severity',
    'Insight',
    'get_insights',
    'get_top_insight',
    'RESEARCH_NOTES'
]
