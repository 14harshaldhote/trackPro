"""
Services package for Tracker Pro.

Business logic layer containing domain services:

V1.0 Core Services:
- tracker_service: Tracker creation, update, delete, clone, restore
- task_service: Task operations and status management
- instance_service: Instance generation for daily/weekly/monthly modes
- streak_service: Streak calculation with threshold support
- goal_service: Goal progress calculation and insights
- notification_service: Push/in-app notification handling
- analytics_service: Stats, heatmaps, and insights
- dashboard_service: Dashboard data aggregation
- share_service: Share link validation and security

V1.5 Enhanced Services:
- tag_service: Tag management and filtering
- search_service: Enhanced search with history and suggestions
- entity_relation_service: Task dependencies and relations
- sync_service: Device sync and conflict resolution

V2.0 Power Services:
- knowledge_graph_service: Entity relationship visualization
- habit_intelligence_service: Pattern detection and insights
- activity_replay_service: Historical state viewing
- collaboration_service: Shared tracker editing

Utility Services:
- export_service: Data export (CSV, JSON, PDF)
- forecast_service: Trend analysis and predictions
- grid_builder_service: Calendar grid generation
- points_service: Points and gamification
- view_service: View data preparation
"""

# Explicit imports for convenience
from .tracker_service import TrackerService
from .task_service import TaskService
from .instance_service import InstanceService
from .streak_service import StreakService
from .goal_service import GoalService
from .notification_service import NotificationService
from .analytics_service import AnalyticsService
from .dashboard_service import DashboardService
from .share_service import ShareService
from .tag_service import TagService
from .search_service import SearchService
from .entity_relation_service import EntityRelationService
from .sync_service import SyncService
from .export_service import ExportService
from .forecast_service import ForecastService

# V2.0 Services
from .knowledge_graph_service import KnowledgeGraphService
from .habit_intelligence_service import HabitIntelligenceService
from .activity_replay_service import ActivityReplayService
from .collaboration_service import CollaborationService

__all__ = [
    # V1.0 Core
    'TrackerService',
    'TaskService',
    'InstanceService',
    'StreakService',
    'GoalService',
    'NotificationService',
    'AnalyticsService',
    'DashboardService',
    'ShareService',
    
    # V1.5 Enhanced
    'TagService',
    'SearchService',
    'EntityRelationService',
    'SyncService',
    
    # V2.0 Power Features
    'KnowledgeGraphService',
    'HabitIntelligenceService',
    'ActivityReplayService',
    'CollaborationService',
    
    # Utilities
    'ExportService',
    'ForecastService',
]
