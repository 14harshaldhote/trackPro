# core/constants.py
"""
Central constants file for consistent status values across the application.
Use these constants instead of hardcoded strings to prevent validation errors.
"""

# Status choices
STATUS_TODO = 'TODO'
STATUS_IN_PROGRESS = 'IN_PROGRESS'
STATUS_DONE = 'DONE'
STATUS_MISSED = 'MISSED'
STATUS_BLOCKED = 'BLOCKED'

STATUS_CHOICES = [
    STATUS_TODO,
    STATUS_IN_PROGRESS,
    STATUS_DONE,
    STATUS_MISSED,
    STATUS_BLOCKED,
]

# Status display info
STATUS_INFO = {
    STATUS_TODO: {'label': 'To Do', 'color': 'grey', 'icon': '○'},
    STATUS_IN_PROGRESS: {'label': 'In Progress', 'color': 'blue', 'icon': '◐'},
    STATUS_DONE: {'label': 'Done', 'color': 'green', 'icon': '✓'},
    STATUS_MISSED: {'label': 'Missed', 'color': 'red', 'icon': '✗'},
    STATUS_BLOCKED: {'label': 'Blocked', 'color': 'orange', 'icon': '⚠'},
}

# ============================================
# TRACKER STATUS VALUES
# ============================================
TRACKER_STATUS_ACTIVE = "active"
TRACKER_STATUS_COMPLETED = "completed"
TRACKER_STATUS_ARCHIVED = "archived"

TRACKER_STATUS_CHOICES = [
    TRACKER_STATUS_ACTIVE,
    TRACKER_STATUS_COMPLETED,
    TRACKER_STATUS_ARCHIVED
]

# ============================================
# TASK STATUS VALUES
# ============================================
TASK_STATUS_TODO = "TODO"
TASK_STATUS_IN_PROGRESS = "IN_PROGRESS"
TASK_STATUS_DONE = "DONE"
TASK_STATUS_CANCELLED = "CANCELLED"

TASK_STATUS_CHOICES = [
    TASK_STATUS_TODO,
    TASK_STATUS_IN_PROGRESS,
    TASK_STATUS_DONE,
    TASK_STATUS_CANCELLED
]

# ============================================
# TIME MODE VALUES
# ============================================
TIME_MODE_DAILY = "daily"
TIME_MODE_WEEKLY = "weekly"
TIME_MODE_MONTHLY = "monthly"
TIME_MODE_CUSTOM = "custom"

TIME_MODE_CHOICES = [
    TIME_MODE_DAILY,
    TIME_MODE_WEEKLY,
    TIME_MODE_MONTHLY,
    TIME_MODE_CUSTOM
]

# ============================================
# AUDIT LOG ACTION TYPES
# ============================================
ACTION_CREATE = "create"
ACTION_UPDATE = "update"
ACTION_DELETE = "delete"
ACTION_AUTO_FIX = "auto_fix"
ACTION_MIGRATION = "migration"

ACTION_CHOICES = [
    ACTION_CREATE,
    ACTION_UPDATE,
    ACTION_DELETE,
    ACTION_AUTO_FIX,
    ACTION_MIGRATION
]

# ============================================
# ENTITY TYPES FOR AUDIT LOGGING
# ============================================
ENTITY_TRACKER_DEF = "TrackerDefinition"
ENTITY_TRACKER_INST = "TrackerInstance"
ENTITY_TASK_TEMPLATE = "TaskTemplate"
ENTITY_TASK_INST = "TaskInstance"
ENTITY_DAY_NOTE = "DayNote"

ENTITY_TYPE_CHOICES = [
    ENTITY_TRACKER_DEF,
    ENTITY_TRACKER_INST,
    ENTITY_TASK_TEMPLATE,
    ENTITY_TASK_INST,
    ENTITY_DAY_NOTE
]

# ============================================
# ORIGIN/PLATFORM VALUES
# ============================================
ORIGIN_WEB = "web"
ORIGIN_IOS = "ios"
ORIGIN_SYSTEM = "system"

ORIGIN_CHOICES = [
    ORIGIN_WEB,
    ORIGIN_IOS,
    ORIGIN_SYSTEM
]

# ============================================
# PRIORITY VALUES
# ============================================
PRIORITY_LOW = "low"
PRIORITY_MEDIUM = "medium"
PRIORITY_HIGH = "high"
PRIORITY_CRITICAL = "critical"

PRIORITY_CHOICES = [
    PRIORITY_LOW,
    PRIORITY_MEDIUM,
    PRIORITY_HIGH,
    PRIORITY_CRITICAL
]


# ============================================
# HELPER FUNCTIONS
# ============================================

def is_valid_tracker_status(status: str) -> bool:
    """Check if tracker status is valid."""
    return status in TRACKER_STATUS_CHOICES


def is_valid_task_status(status: str) -> bool:
    """Check if task status is valid."""
    return status in TASK_STATUS_CHOICES


def is_valid_time_mode(mode: str) -> bool:
    """Check if time mode is valid."""
    return mode in TIME_MODE_CHOICES


def normalize_tracker_status(status: str) -> str:
    """
    Normalize tracker status to lowercase.
    Handles common input variations.
    """
    status_map = {
        'ACTIVE': TRACKER_STATUS_ACTIVE,
        'active': TRACKER_STATUS_ACTIVE,
        'Active': TRACKER_STATUS_ACTIVE,
        'COMPLETED': TRACKER_STATUS_COMPLETED,
        'completed': TRACKER_STATUS_COMPLETED,
        'Completed': TRACKER_STATUS_COMPLETED,
        'ARCHIVED': TRACKER_STATUS_ARCHIVED,
        'archived': TRACKER_STATUS_ARCHIVED,
        'Archived': TRACKER_STATUS_ARCHIVED,
    }
    return status_map.get(status, status.lower())


def normalize_task_status(status: str) -> str:
    """
    Normalize task status to uppercase with underscores.
    Handles common input variations.
    """
    status_map = {
        'todo': TASK_STATUS_TODO,
        'TODO': TASK_STATUS_TODO,
        'Todo': TASK_STATUS_TODO,
        'in_progress': TASK_STATUS_IN_PROGRESS,
        'IN_PROGRESS': TASK_STATUS_IN_PROGRESS,
        'in-progress': TASK_STATUS_IN_PROGRESS,
        'InProgress': TASK_STATUS_IN_PROGRESS,
        'done': TASK_STATUS_DONE,
        'DONE': TASK_STATUS_DONE,
        'Done': TASK_STATUS_DONE,
        'completed': TASK_STATUS_DONE,  # Alias
        'cancelled': TASK_STATUS_CANCELLED,
        'CANCELLED': TASK_STATUS_CANCELLED,
        'canceled': TASK_STATUS_CANCELLED,  # US spelling
        'CANCELED': TASK_STATUS_CANCELLED,
    }
    return status_map.get(status, status.upper())


# ============================================
# DISPLAY HELPERS
# ============================================

TRACKER_STATUS_DISPLAY = {
    TRACKER_STATUS_ACTIVE: "Active",
    TRACKER_STATUS_COMPLETED: "Completed",
    TRACKER_STATUS_ARCHIVED: "Archived"
}

TASK_STATUS_DISPLAY = {
    TASK_STATUS_TODO: "To Do",
    TASK_STATUS_IN_PROGRESS: "In Progress",
    TASK_STATUS_DONE: "Done",
    TASK_STATUS_CANCELLED: "Cancelled"
}

TASK_STATUS_EMOJI = {
    TASK_STATUS_TODO: "⏳",
    TASK_STATUS_IN_PROGRESS: "🔄",
    TASK_STATUS_DONE: "✅",
    TASK_STATUS_CANCELLED: "❌"
}

TIME_MODE_DISPLAY = {
    TIME_MODE_DAILY: "Daily",
    TIME_MODE_WEEKLY: "Weekly",
    TIME_MODE_MONTHLY: "Monthly",
    TIME_MODE_CUSTOM: "Custom"
}


def get_status_display(status: str, entity_type: str = "task") -> str:
    """Get human-readable status display."""
    if entity_type == "task":
        return TASK_STATUS_DISPLAY.get(status, status)
    elif entity_type == "tracker":
        return TRACKER_STATUS_DISPLAY.get(status, status)
    return status


def get_status_emoji(status: str) -> str:
    """Get emoji representation of task status."""
    return TASK_STATUS_EMOJI.get(status, "")


# ============================================================================
# UX CONSTANTS (Following OpusSuggestion.md)
# ============================================================================

# Haptic Feedback Types (iOS UIImpactFeedbackGenerator)
HAPTIC_FEEDBACK = {
    # UINotificationFeedbackGenerator types
    'task_complete': 'success',          # UINotificationFeedbackGenerator.success
    'task_skip': 'warning',              # UINotificationFeedbackGenerator.warning
    'task_delete': 'error',              # UINotificationFeedbackGenerator.error
    
    # UIImpactFeedbackGenerator types
    'button_tap': 'light',               # UIImpactFeedbackGenerator.light
    'toggle': 'medium',                  # UIImpactFeedbackGenerator.medium
    'drag_drop': 'rigid',                # UIImpactFeedbackGenerator.rigid
    'streak_milestone': 'heavy',         # UIImpactFeedbackGenerator.heavy
    
    # UISelectionFeedbackGenerator
    'selection_change': 'selection',     # UISelectionFeedbackGenerator
}

# Action types that trigger haptics
HAPTIC_ACTIONS = [
    'task_toggle',
    'task_delete',
    'tracker_create',
    'goal_achieved',
    'streak_continued',
    'quick_add',
    'bulk_complete',
]

# Sound Effects
SOUND_EFFECTS = {
    'task_complete': 'complete.aiff',
    'celebration': 'celebration.aiff',
    'reminder': 'reminder.aiff',
    'alert': 'alert.aiff',
    'error': 'error.aiff',
    'button_tap': 'tap.aiff',
}

# Animation Types
ANIMATIONS = {
    'confetti': {
        'duration': 2000,  # ms
        'particles': 50,
        'colors': ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']
    },
    'fireworks': {
        'duration': 3000,
        'bursts': 5
    },
    'checkmark': {
        'duration': 500,
        'scale': 1.2
    },
    'pulse': {
        'duration': 300,
        'iterations': 1
    }
}

# iOS Swipe Action Colors
SWIPE_ACTION_COLORS = {
    'complete': '#22c55e',    # Green
    'skip': '#f59e0b',        # Amber
    'delete': '#ef4444',      # Red
    'edit': '#3b82f6',        # Blue
    'archive': '#6b7280',     # Gray
}

# iOS Bottom Sheet Detents
MODAL_DETENTS = {
    'small': ['medium'],
    'medium': ['medium', 'large'],
    'large': ['large'],
    'fullscreen': []  # No detents = full screen
}

MODAL_PRESENTATIONS = {
    'sheet': 'sheet',              # iOS .sheet()
    'fullscreen': 'fullscreen',    # iOS .fullScreenCover()
    'popover': 'popover',          # iOS .popover()
}

# Touch Target Sizes (Apple HIG)
TOUCH_TARGETS = {
    'minimum': 44,        # Apple HIG minimum
    'comfortable': 48,    # Recommended for primary actions
    'large': 60,         # For frequently used actions
}

# Loading & Performance
CACHE_TIMEOUTS = {
    'user_dashboard': 30,          # 30 seconds (frequently changes)
    'user_overview': 120,          # 2 minutes
    'prefetch_data': 60,           # 1 minute
    'modal_content': 300,          # 5 minutes (static-ish)
    'analytics': 600,              # 10 minutes
    'insights': 1800,              # 30 minutes
}

SKELETON_DEFAULTS = {
    'dashboard': 8,        # Number of skeleton items
    'today': 6,
    'week': 7,
    'trackers': 6,
    'list': 10,
}

# Pagination
PAGINATION = {
    'default_page_size': 20,
    'max_page_size': 100,
    'mobile_page_size': 15,       # Smaller for mobile bandwidth
}

# Notification Settings
NOTIFICATION_TYPES = {
    'info': {
        'icon': 'ℹ️',
        'color': '#3b82f6',
        'duration': 3000
    },
    'success': {
        'icon': '✅',
        'color': '#22c55e',
        'duration': 3000
    },
    'warning': {
        'icon': '⚠️',
        'color': '#f59e0b',
        'duration': 5000
    },
    'error': {
        'icon': '❌',
        'color': '#ef4444',
        'duration': 5000
    },
    'achievement': {
        'icon': '🎉',
        'color': '#8b5cf6',
        'duration': 4000
    },
    'reminder': {
        'icon': '🔔',
        'color': '#06b6d4',
        'duration': 4000
    }
}