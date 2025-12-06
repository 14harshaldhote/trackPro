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


# ============================================
# HAPTIC FEEDBACK (iOS UIImpactFeedbackGenerator)
# ============================================

HAPTIC_SUCCESS = 'success'        # UINotificationFeedbackGenerator.success
HAPTIC_WARNING = 'warning'        # UINotificationFeedbackGenerator.warning
HAPTIC_ERROR = 'error'            # UINotificationFeedbackGenerator.error
HAPTIC_LIGHT = 'light'            # UIImpactFeedbackGenerator.light
HAPTIC_MEDIUM = 'medium'          # UIImpactFeedbackGenerator.medium
HAPTIC_HEAVY = 'heavy'            # UIImpactFeedbackGenerator.heavy
HAPTIC_RIGID = 'rigid'            # UIImpactFeedbackGenerator.rigid
HAPTIC_SELECTION = 'selection'    # UISelectionFeedbackGenerator

# Action to haptic mapping
HAPTIC_FEEDBACK = {
    'task_complete': HAPTIC_SUCCESS,
    'task_skip': HAPTIC_WARNING,
    'task_delete': HAPTIC_ERROR,
    'task_toggle': HAPTIC_MEDIUM,
    'button_tap': HAPTIC_LIGHT,
    'drag_drop': HAPTIC_RIGID,
    'selection_change': HAPTIC_SELECTION,
    'streak_milestone': HAPTIC_HEAVY,
    'celebration': HAPTIC_HEAVY,
    'error': HAPTIC_ERROR,
}

# Actions that trigger haptic feedback
HAPTIC_ACTIONS = [
    'task_toggle',
    'task_delete',
    'tracker_create',
    'goal_achieved',
    'streak_continued',
]


# ============================================
# UI COLORS (iOS/Web design system)
# ============================================

UI_COLORS = {
    'success': '#22c55e',       # Green - task complete
    'warning': '#f59e0b',       # Amber - skip/caution
    'error': '#ef4444',         # Red - delete/destructive
    'info': '#3b82f6',          # Blue - informational
    'primary': '#6366f1',       # Indigo - primary actions
    'secondary': '#64748b',     # Slate - secondary
}


# ============================================
# SWIPE ACTION CONFIGURATION
# ============================================

# Minimum touch target size per Apple HIG (44pt)
TOUCH_TARGET_MIN_SIZE = 44

# Default swipe action button widths
SWIPE_ACTION_WIDTHS = {
    'complete': 44,
    'skip': 60,
    'delete': 70,
    'archive': 70,
}


def get_haptic_for_action(action: str) -> str:
    """Get haptic feedback type for an action."""
    return HAPTIC_FEEDBACK.get(action, HAPTIC_LIGHT)