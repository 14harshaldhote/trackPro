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
    def __init__(self, dry_run: bool = False):
        """
        Initialize IntegrityService.
        
        Args:
            dry_run: If True, report issues without making repairs
        """
        self.db = crud.db
        self.dry_run = dry_run

    def run_integrity_check(self, dry_run: bool = None):
        """
        Main entry point for integrity checks.
        
        Args:
            dry_run: Override instance dry_run setting
            
        Returns:
            Report dict with scan results
        """
        # Allow override at call time
        if dry_run is not None:
            self.dry_run = dry_run
            
        mode = "[DRY-RUN]" if self.dry_run else ""
        logger.info(f"{mode} Starting integrity check...")
        
        report = {
            "scanned": 0,
            "issues_found": 0,
            "repaired": 0,
            "quarantined": 0,
            "dry_run": self.dry_run,
            "details": []
        }

        # Django ORM handles schema validation automatically
        # We focus on business logic integrity checks

        # 1. Orphan Detection
        self._check_orphans(report)

        # 2. Logical Consistency
        self._check_logical_consistency(report)

        logger.info(f"{mode} Integrity check complete. Report: {report}")
        return report

    def _check_orphans(self, report):
        """Checks for records pointing to non-existent parents using set operations."""
        
        # TaskInstance -> TrackerInstance
        tasks = self.db.fetch_all('TaskInstances')
        tracker_instances_ids = {t['instance_id'] for t in self.db.fetch_all('TrackerInstances')}
        
        for task in tasks:
            report['scanned'] += 1
            if task.get('tracker_instance_id') not in tracker_instances_ids:
                report['issues_found'] += 1
                issue = {
                    'type': 'orphan',
                    'table': 'TaskInstances',
                    'id': task.get('task_instance_id'),
                    'message': f"Orphaned TaskInstance: {task.get('task_instance_id')}"
                }
                report['details'].append(issue)
                logger.warning(issue['message'])
                # With Django ORM, orphans are prevented by CASCADE, but we check anyway

        # TaskTemplate -> TrackerDefinition
        templates = self.db.fetch_all('TaskTemplates')
        tracker_defs_ids = {t['tracker_id'] for t in self.db.fetch_all('TrackerDefinitions')}
        
        for tmpl in templates:
            report['scanned'] += 1
            if tmpl.get('tracker_id') not in tracker_defs_ids:
                report['issues_found'] += 1
                issue = {
                    'type': 'orphan',
                    'table': 'TaskTemplates',
                    'id': tmpl.get('template_id'),
                    'message': f"Orphaned TaskTemplate: {tmpl.get('template_id')}"
                }
                report['details'].append(issue)
                logger.warning(issue['message'])

    def _check_logical_consistency(self, report):
        """Checks business logic rules."""
        # Example: End date before start date
        instances = self.db.fetch_all('TrackerInstances')
        for inst in instances:
            report['scanned'] += 1
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
                    issue = {
                        'type': 'invalid_date_range',
                        'table': 'TrackerInstances',
                        'id': inst['instance_id'],
                        'message': f"Invalid date range: end ({end}) < start ({start})"
                    }
                    report['details'].append(issue)
                    
                    if not self.dry_run:
                        # Repair: Set end = start
                        self.db.update('TrackerInstances', 'instance_id', inst['instance_id'], 
                                     {'period_end': start.isoformat()})
                        logger.info(f"Fixed invalid date range for instance {inst['instance_id']}")
                        report['repaired'] += 1
                    else:
                        logger.info(f"[DRY-RUN] Would fix date range for instance {inst['instance_id']}")
                        
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
