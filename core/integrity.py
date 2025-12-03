import logging
import uuid
import json
from datetime import datetime, date
from core import crud, schemas, constants
from core.db_engine import ExcelDB
from marshmallow import ValidationError

logger = logging.getLogger(__name__)

class IntegrityService:
    def __init__(self):
        self.db = crud.db
        self.repair_log_file = "integrity_repairs.xlsx" # We might log to main DB or separate file. 
                                                        # Plan said separate file, but for simplicity let's use main DB AuditLogs or Quarantine.
                                                        # Actually, let's stick to the plan of using a separate log if needed, 
                                                        # but since we added Quarantine to main DB, let's use that for bad data.
                                                        # For "repairs", we can log to AuditLogs with action_type=ACTION_AUTO_FIX.

    def run_integrity_check(self):
        """Main entry point for integrity checks."""
        logger.info("Starting integrity check...")
        report = {
            "scanned": 0,
            "issues_found": 0,
            "repaired": 0,
            "quarantined": 0
        }

        # 1. Schema Validation
        self._check_schemas(report)

        # 2. Orphan Detection
        self._check_orphans(report)

        # 3. Logical Consistency
        self._check_logical_consistency(report)

        logger.info(f"Integrity check complete. Report: {report}")
        return report

    def _check_schemas(self, report):
        """Validates all records against marshmallow schemas."""
        
        # Map sheets to schemas
        sheet_schema_map = {
            'TrackerDefinitions': schemas.TrackerDefinitionSchema(),
            'TaskTemplates': schemas.TaskTemplateSchema(),
            'TrackerInstances': schemas.TrackerInstanceSchema(),
            'TaskInstances': schemas.TaskInstanceSchema()
        }

        for sheet, schema in sheet_schema_map.items():
            records = self.db.fetch_all(sheet)
            batch_updates = [] # List of (id, update_dict)
            
            for record in records:
                report['scanned'] += 1
                try:
                    # Validate
                    schema.load(record)
                except ValidationError as err:
                    report['issues_found'] += 1
                    repair = self._handle_schema_error(sheet, record, err, report)
                    if repair:
                        batch_updates.append(repair)

            # Apply batch updates
            if batch_updates:
                id_field = self._get_id_field(sheet)
                self.db.update_many(sheet, id_field, batch_updates)
                logger.info(f"Applied {len(batch_updates)} repairs to {sheet}")

    def _handle_schema_error(self, sheet, record, error, report):
        """Decides whether to repair or quarantine based on error. Returns (id, update_dict) or None."""
        # logger.warning(f"Schema error in {sheet}: {error.messages}") # Too noisy for batch
        
        # Attempt Auto-Repair
        repaired_record = record.copy()
        repaired = False
        updates = {}

        # Track handled errors
        handled_fields = set()

        # Example Repair: Missing status -> Set default
        if 'status' in error.messages:
            if sheet == 'TrackerInstances':
                updates['status'] = constants.TRACKER_STATUS_ACTIVE
                handled_fields.add('status')
            elif sheet == 'TaskInstances':
                updates['status'] = constants.TASK_STATUS_TODO
                handled_fields.add('status')

        # Repair: Notes is None -> ""
        if 'notes' in error.messages:
            updates['notes'] = ""
            handled_fields.add('notes')

        # Repair: Metadata is None or invalid -> {}
        if 'metadata' in error.messages:
            updates['metadata'] = {}
            handled_fields.add('metadata')
        
        # Check if we handled all errors
        all_handled = set(error.messages.keys()).issubset(handled_fields)

        if all_handled and updates:
            report['repaired'] += 1
            id_field = self._get_id_field(sheet)
            if id_field and id_field in record:
                return (record[id_field], updates)
            else:
                # Can't update without ID, quarantine
                self._quarantine(sheet, record, "Missing ID during repair", report)
                return None
        else:
            # Unfixable (or partial fix not sufficient)
            self._quarantine(sheet, record, f"Schema Validation Failed: {error.messages}", report)
            return None

    def _check_orphans(self, report):
        """Checks for records pointing to non-existent parents using set operations."""
        
        # TaskInstance -> TrackerInstance
        tasks = self.db.fetch_all('TaskInstances')
        tracker_instances_ids = {t['instance_id'] for t in self.db.fetch_all('TrackerInstances')}
        
        # Use set subtraction to find orphans efficiently? 
        # We need the full record to quarantine it, so we can't just find IDs.
        # But we can filter efficiently.
        
        for task in tasks:
            if task.get('tracker_instance_id') not in tracker_instances_ids:
                report['issues_found'] += 1
                self._quarantine('TaskInstances', task, "Orphaned TaskInstance (Parent TrackerInstance not found)", report)

        # TaskTemplate -> TrackerDefinition
        templates = self.db.fetch_all('TaskTemplates')
        tracker_defs_ids = {t['tracker_id'] for t in self.db.fetch_all('TrackerDefinitions')}
        
        for tmpl in templates:
            if tmpl.get('tracker_id') not in tracker_defs_ids:
                 report['issues_found'] += 1
                 self._quarantine('TaskTemplates', tmpl, "Orphaned TaskTemplate (Parent TrackerDefinition not found)", report)

    def _check_logical_consistency(self, report):
        """Checks business logic rules."""
        # Example: End date before start date
        instances = self.db.fetch_all('TrackerInstances')
        for inst in instances:
            try:
                start = inst.get('period_start')
                end = inst.get('period_end')
                
                # Convert if strings
                if isinstance(start, str): start = date.fromisoformat(start)
                if isinstance(end, str): end = date.fromisoformat(end)
                
                if start and end and end < start:
                    report['issues_found'] += 1
                    # Repair: Swap? Or set end = start?
                    # Let's set end = start
                    self.db.update('TrackerInstances', 'instance_id', inst['instance_id'], {'period_end': start.isoformat()})
                    self.db.log_audit(constants.ACTION_AUTO_FIX, 'TrackerInstance', inst['instance_id'], "Fixed invalid date range (end < start)")
                    report['repaired'] += 1
            except Exception as e:
                logger.error(f"Error checking consistency for instance {inst.get('instance_id')}: {e}")

    def _quarantine(self, sheet, record, reason, report):
        """Moves a record to Quarantine sheet and deletes from original."""
        try:
            # 1. Add to Quarantine
            quarantine_data = {
                'quarantine_id': str(uuid.uuid4()),
                'timestamp': datetime.now().isoformat(),
                'original_sheet': sheet,
                'original_data': json.dumps(record, default=str),
                'issue_type': 'Validation Failure',
                'details': reason
            }
            self.db.insert('Quarantine', quarantine_data)
            
            # 2. Delete from Original (if ID exists)
            id_field = self._get_id_field(sheet)
            if id_field and id_field in record:
                self.db.delete(sheet, id_field, record[id_field]) 
                
            report['quarantined'] += 1
            logger.info(f"Quarantined record from {sheet}: {reason}")
            
        except Exception as e:
            logger.error(f"Failed to quarantine record: {e}")

    def _get_id_field(self, sheet):
        mapping = {
            'TrackerDefinitions': 'tracker_id',
            'TaskTemplates': 'template_id',
            'TrackerInstances': 'instance_id',
            'TaskInstances': 'task_instance_id'
        }
        return mapping.get(sheet)
