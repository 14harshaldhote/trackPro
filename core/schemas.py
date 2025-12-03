from marshmallow import Schema, fields, validate, post_load
import uuid
from datetime import date, datetime

class TrackerDefinitionSchema(Schema):
    tracker_id = fields.Str(required=True)
    name = fields.Str(required=True)
    time_mode = fields.Str(required=True, validate=validate.OneOf(["daily", "weekly", "monthly", "custom"]))
    description = fields.Str(load_default="")
    created_at = fields.DateTime(load_default=lambda: datetime.now())

class TaskTemplateSchema(Schema):
    template_id = fields.Str(required=True)
    tracker_id = fields.Str(required=True)
    description = fields.Str(required=True)
    is_recurring = fields.Bool(load_default=True)
    category = fields.Str(load_default="general")
    weight = fields.Int(load_default=1) # For effort/score calculation

class TrackerInstanceSchema(Schema):
    instance_id = fields.Str(required=True)
    tracker_id = fields.Str(required=True)
    period_start = fields.Date(required=True)
    period_end = fields.Date(required=True)
    status = fields.Str(validate=validate.OneOf(["active", "completed", "archived"]), load_default="active")

class TaskInstanceSchema(Schema):
    task_instance_id = fields.Str(required=True)
    tracker_instance_id = fields.Str(required=True)
    template_id = fields.Str(allow_none=True) # None if extra task
    description = fields.Str(required=True)
    status = fields.Str(validate=validate.OneOf(["TODO", "DONE", "SKIPPED"]), load_default="TODO")
    date = fields.Date(required=True)
    notes = fields.Str(load_default="", allow_none=True)
    metadata = fields.Dict(load_default={}, allow_none=True)

class AuditEntrySchema(Schema):
    timestamp = fields.DateTime(required=True)
    action_type = fields.Str(required=True)
    entity_type = fields.Str(required=True)
    entity_id = fields.Str(required=True)
    details = fields.Str(load_default="")
    origin = fields.Str(load_default="system")

class DayNoteSchema(Schema):
    note_id = fields.Str(required=True)
    tracker_id = fields.Str(required=True)
    date = fields.Date(required=True)
    content = fields.Str(required=True)
    sentiment_score = fields.Float(allow_none=True)
    keywords = fields.List(fields.Str(), load_default=[])
