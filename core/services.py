import uuid
from datetime import date
from core import crud, time_utils
from core.models import TrackerInstance, TaskInstance

def ensure_tracker_instance(tracker_id, reference_date=None):
    """
    Ensures a TrackerInstance exists for the given tracker and date.
    If not, creates it and its tasks.
    """
    if reference_date is None:
        reference_date = date.today()
        
    # 1. Get Tracker Definition
    trackers = crud.get_all_tracker_definitions()
    tracker_def = next((t for t in trackers if t['tracker_id'] == tracker_id), None)
    
    if not tracker_def:
        print(f"Tracker {tracker_id} not found.")
        return None
        
    # 2. Calculate Period
    start_date, end_date = time_utils.get_period_dates(tracker_def['time_mode'], reference_date)
    
    # 3. Check if Instance Exists
    # We need a way to query by date/tracker. 
    # Current CRUD `get_tracker_instances` returns all for a tracker.
    # We can filter in memory for now (Phase 1 scale).
    existing_instances = crud.get_tracker_instances(tracker_id)
    
    # Check for overlap or exact match. 
    # For simplicity, we check if an instance covers the reference_date.
    # Actually, we should check if an instance exists for this specific calculated period.
    
    current_instance = None
    for inst in existing_instances:
        # Parse dates if they are strings (ExcelDB might return strings)
        p_start = inst['period_start']
        p_end = inst['period_end']
        if isinstance(p_start, str): p_start = date.fromisoformat(p_start)
        if isinstance(p_end, str): p_end = date.fromisoformat(p_end)
            
        if p_start == start_date and p_end == end_date:
            current_instance = inst
            break
            
    if current_instance:
        return current_instance
        
    # 4. Create New Instance
    print(f"Creating new instance for {tracker_def['name']} ({start_date} to {end_date})")
    new_instance_data = {
        "instance_id": str(uuid.uuid4()),
        "tracker_id": tracker_id,
        "tracking_date": reference_date,  # Primary date for the instance
        "period_start": start_date,
        "period_end": end_date,
       "status": "active"
    }
    current_instance = crud.create_tracker_instance(new_instance_data)
    
    # 5. Create Tasks from Templates
    templates = crud.get_task_templates_for_tracker(tracker_id)
    for tmpl in templates:
        # Skip deleted templates
        if tmpl.get('description', '').startswith("[DELETED]"):
            continue
            
        # For daily trackers, task date is the period date.
        # For weekly/monthly, we might want to set it to start_date or leave it generic.
        # Let's set it to start_date for now.
        crud.create_task_instance({
            "task_instance_id": str(uuid.uuid4()),
            "tracker_instance_id": current_instance['instance_id'],
            "template_id": tmpl['template_id'],
            "description": tmpl['description'],
            "status": "TODO",
            "date": start_date, # Default to start of period
            "notes": "",
            "metadata": {}
        })
        
    # 6. Carry-over Logic (Optional - Basic Implementation)
    # Find previous instance
    # This requires sorting instances. 
    # Let's skip complex carry-over for this exact step, as per plan "Implement carry-over rules" is a task.
    # We will add it in a refinement step.
    
    return current_instance

def check_all_trackers(reference_date=None):
    """Checks all trackers and ensures instances exist for the reference date."""
    if reference_date is None:
        reference_date = date.today()
        
    trackers = crud.get_all_tracker_definitions()
    for tracker in trackers:
        ensure_tracker_instance(tracker['tracker_id'], reference_date)
