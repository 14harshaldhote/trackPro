"""
Data Integrity Service for Tracker Pro.

Performs integrity checks on the database:
- Orphan detection (records pointing to non-existent parents)
- Logical consistency checks (business rules validation)

Note: Schema validation is handled automatically by Django ORM,
so we focus on business logic integrity checks.
"""
import logging
import uuid
import json
from datetime import datetime, date
from core.repositories import base_repository as crud
from core.utils import constants

logger = logging.getLogger(__name__)

class IntegrityService:
    def __init__(self):
        self.db = crud.db

    def run_integrity_check(self):
        """Main entry point for integrity checks."""
        logger.info("Starting integrity check...")
        report = {
            "scanned": 0,
            "issues_found": 0,
            "repaired": 0,
            "quarantined": 0
        }

        # Django ORM handles schema validation automatically
        # We focus on business logic integrity checks

        # 1. Orphan Detection
        self._check_orphans(report)

        # 2. Logical Consistency
        self._check_logical_consistency(report)

        logger.info(f"Integrity check complete. Report: {report}")
        return report

    def _check_orphans(self, report):
        """Checks for records pointing to non-existent parents using set operations."""
        
        # TaskInstance -> TrackerInstance
        tasks = self.db.fetch_all('TaskInstances')
        tracker_instances_ids = {t['instance_id'] for t in self.db.fetch_all('TrackerInstances')}
        
        for task in tasks:
            if task.get('tracker_instance_id') not in tracker_instances_ids:
                report['issues_found'] += 1
                logger.warning(f"Orphaned TaskInstance: {task.get('task_instance_id')}")
                # With Django ORM, orphans are prevented by CASCADE, but we check anyway

        # TaskTemplate -> TrackerDefinition
        templates = self.db.fetch_all('TaskTemplates')
        tracker_defs_ids = {t['tracker_id'] for t in self.db.fetch_all('TrackerDefinitions')}
        
        for tmpl in templates:
            if tmpl.get('tracker_id') not in tracker_defs_ids:
                report['issues_found'] += 1
                logger.warning(f"Orphaned TaskTemplate: {tmpl.get('template_id')}")

    def _check_logical_consistency(self, report):
        """Checks business logic rules."""
        # Example: End date before start date
        instances = self.db.fetch_all('TrackerInstances')
        for inst in instances:
            try:
                start = inst.get('period_start')
                end = inst.get('period_end')
                
                # Convert if strings
                if isinstance(start, str):
                    start = date.fromisoformat(start)
                if isinstance(end, str):
                    end = date.fromisoformat(end)
                
                if start and end and end < start:
                    report['issues_found'] += 1
                    # Repair: Set end = start
                    self.db.update('TrackerInstances', 'instance_id', inst['instance_id'], 
                                 {'period_end': start.isoformat()})
                    logger.info(f"Fixed invalid date range for instance {inst['instance_id']}")
                    report['repaired'] += 1
            except Exception as e:
                logger.error(f"Error checking consistency for instance {inst.get('instance_id')}: {e}")

    def _get_id_field(self, sheet):
        """Get the ID field name for a given sheet."""
        mapping = {
            'TrackerDefinitions': 'tracker_id',
            'TaskTemplates': 'template_id',
            'TrackerInstances': 'instance_id',
            'TaskInstances': 'task_instance_id'
        }
        return mapping.get(sheet)
