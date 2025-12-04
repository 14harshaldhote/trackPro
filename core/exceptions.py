"""
Custom Exception Classes

Provides specific exception types for better error handling and user feedback.
"""


class TrackerException(Exception):
    """Base exception for all tracker-related errors"""
    pass


class TrackerNotFoundError(TrackerException):
    """Raised when a tracker does not exist"""
    def __init__(self, tracker_id: str):
        self.tracker_id = tracker_id
        super().__init__(f"Tracker '{tracker_id}' not found")


class TaskNotFoundError(TrackerException):
    """Raised when a task instance does not exist"""
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task '{task_id}' not found")


class TemplateNotFoundError(TrackerException):
    """Raised when a task template does not exist"""
    def __init__(self, template_id: str):
        self.template_id = template_id
        super().__init__(f"Template '{template_id}' not found")


class InvalidDateRangeError(TrackerException):
    """Raised when date range is invalid (e.g., start > end)"""
    def __init__(self, start_date, end_date):
        self.start_date = start_date
        self.end_date = end_date
        super().__init__(f"Invalid date range: {start_date} to {end_date}")


class InvalidStatusError(TrackerException):
    """Raised when an invalid task status is provided"""
    def __init__(self, status: str, valid_statuses: list):
        self.status = status
        self.valid_statuses = valid_statuses
        super().__init__(
            f"Invalid status '{status}'. Valid options: {', '.join(valid_statuses)}"
        )


class ValidationError(TrackerException):
    """Raised when data validation fails"""
    def __init__(self, field: str, message: str):
        self.field = field
        self.message = message
        super().__init__(f"Validation error for '{field}': {message}")


class PermissionDeniedError(TrackerException):
    """Raised when user doesn't have permission for an action"""
    def __init__(self, action: str, resource: str):
        self.action = action
        self.resource = resource
        super().__init__(f"Permission denied: cannot {action} {resource}")


class DuplicateError(TrackerException):
    """Raised when trying to create a duplicate record"""
    def __init__(self, resource_type: str, identifier: str):
        self.resource_type = resource_type
        self.identifier = identifier
        super().__init__(f"Duplicate {resource_type}: '{identifier}' already exists")


class DataIntegrityError(TrackerException):
    """Raised when data integrity constraints are violated"""
    def __init__(self, message: str, details: dict = None):
        self.details = details or {}
        super().__init__(message)


class CacheError(TrackerException):
    """Raised when cache operations fail"""
    pass


class AnalyticsError(TrackerException):
    """Raised when analytics computation fails"""
    def __init__(self, metric: str, reason: str):
        self.metric = metric
        self.reason = reason
        super().__init__(f"Analytics error for '{metric}': {reason}")


class ExportError(TrackerException):
    """Raised when data export fails"""
    def __init__(self, export_type: str, reason: str):
        self.export_type = export_type
        self.reason = reason
        super().__init__(f"Export failed ({export_type}): {reason}")
