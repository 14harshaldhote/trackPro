from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core import crud, services
from datetime import datetime
import json
import uuid

def get_day_view(request, date_str):
    try:
        # Validate date
        date_obj = datetime.strptime(date_str, '%Y-%m-%d').date()
        
        # Ensure tracker instances exist for this date
        services.check_all_trackers(date_obj)
        
        # Fetch all tasks for this date across all trackers
        # This is a bit complex with the current structure, so let's simplify:
        # Get all active tracker instances that cover this date.
        
        # For now, let's just return a success message or specific data if needed.
        # The frontend might expect a list of tasks.
        
        # Let's fetch all tasks for today from all trackers
        all_tasks = []
        trackers = crud.get_all_tracker_definitions()
        for tracker in trackers:
            instances = crud.get_tracker_instances(tracker['tracker_id'])
            # Filter for relevant instance (simplified)
            for inst in instances:
                # Assuming daily for now or check date match
                # If we want to be precise, we need start/end date in instance
                # But we only have period_start/end in logic, let's assume instance has it or we infer.
                # Actually TrackerInstance has period_start/end.
                
                # Let's just get all tasks for the instance that matches the date
                # For daily, period_start == date_obj
                if inst.get('period_start') == date_str:
                     tasks = crud.get_task_instances_for_tracker_instance(inst['instance_id'])
                     all_tasks.extend(tasks)
        
        return JsonResponse({'status': 'success', 'tasks': all_tasks})
    except ValueError:
        return JsonResponse({'error': 'Invalid date format. Use YYYY-MM-DD'}, status=400)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@csrf_exempt
def update_task_view(request, task_id):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            updates = {}
            if 'status' in body:
                updates['status'] = body['status']
            if 'notes' in body:
                updates['notes'] = body['notes']
            
            if not updates:
                return JsonResponse({'error': 'No fields to update'}, status=400)
                
            success = crud.update_task_instance(task_id, updates)
            if success:
                return JsonResponse({'status': 'success'})
            else:
                return JsonResponse({'error': 'Task not found'}, status=404)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Method not allowed'}, status=405)

@csrf_exempt
def add_task_view(request, date_str):
    # This is tricky because we need to know WHICH tracker instance to add to.
    # For now, let's assume we add to a "General" tracker or require tracker_id.
    # Or we just fail if not specified.
    
    # Let's deprecate this simple view in favor of a more robust one that takes tracker_id.
    return JsonResponse({'error': 'Not implemented. Use specific tracker endpoints.'}, status=501)
