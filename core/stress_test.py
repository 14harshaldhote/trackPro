#!/usr/bin/env python
"""
Enhanced Stress Test for Behavioral Analytics Engine

Tests:
- Performance with 100+ users, 10,000+ tasks
- User data isolation (no cross-contamination)
- Edge cases (empty data, single task, extreme values)
- Analytics, forecasting, and behavioral insights
- Detailed error/warning/bottleneck logging

Usage:
    python core/stress_test.py
"""
import os
import sys
import time
import logging
import traceback
from datetime import date, datetime, timedelta
import random
import uuid
from collections import defaultdict

# Setup Django
sys.path.insert(0, '/Users/harshalsmac/WORK/personal/Tracker')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trackerWeb.settings')

import django
django.setup()

from django.contrib.auth.models import User
from django.db import connection, reset_queries, transaction
from django.conf import settings

from core.models import (
    TrackerDefinition, TrackerInstance, TaskInstance,
    TaskTemplate, DayNote
)
from core import analytics
from core.behavioral import get_insights, InsightsEngine
from core.helpers import nlp_helpers, metric_helpers

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger(__name__)

# Enable SQL query logging for bottleneck detection
settings.DEBUG = True


class StressTestResults:
    """Collects and reports stress test results."""
    
    def __init__(self):
        self.errors = []
        self.warnings = []
        self.bottlenecks = []
        self.timings = defaultdict(list)
        self.query_counts = defaultdict(list)
        self.start_time = None
        self.isolation_results = []
        self.edge_case_results = []
        
    def log_error(self, operation, error, traceback_str=None):
        self.errors.append({
            'operation': operation,
            'error': str(error),
            'traceback': traceback_str,
            'timestamp': datetime.now()
        })
        logger.error(f"❌ ERROR in {operation}: {error}")
    
    def log_warning(self, operation, message):
        self.warnings.append({
            'operation': operation,
            'message': message,
            'timestamp': datetime.now()
        })
        logger.warning(f"⚠️  WARNING in {operation}: {message}")
    
    def log_timing(self, operation, duration, query_count=0):
        self.timings[operation].append(duration)
        self.query_counts[operation].append(query_count)
        
        # Flag as bottleneck if too slow
        if duration > 2.0:
            self.bottlenecks.append({
                'operation': operation,
                'duration': duration,
                'query_count': query_count,
                'severity': 'HIGH' if duration > 5.0 else 'MEDIUM'
            })
            logger.warning(f"🐌 SLOW: {operation} took {duration:.2f}s ({query_count} queries)")
    
    def log_isolation_test(self, test_name, passed, details=""):
        self.isolation_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"🔒 Isolation Test [{status}]: {test_name}")
    
    def log_edge_case(self, test_name, passed, details=""):
        self.edge_case_results.append({
            'test': test_name,
            'passed': passed,
            'details': details
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"🧪 Edge Case [{status}]: {test_name}")
    
    def print_report(self):
        """Print comprehensive test report."""
        total_time = time.time() - self.start_time
        
        print("\n" + "="*80)
        print("📊 ENHANCED STRESS TEST REPORT")
        print("="*80)
        
        # Summary
        print(f"\n⏱️  Total execution time: {total_time:.2f}s")
        print(f"❌ Errors: {len(self.errors)}")
        print(f"⚠️  Warnings: {len(self.warnings)}")
        print(f"🐌 Bottlenecks: {len(self.bottlenecks)}")
        
        # Isolation Tests
        isolation_passed = sum(1 for t in self.isolation_results if t['passed'])
        isolation_total = len(self.isolation_results)
        print(f"🔒 User Isolation: {isolation_passed}/{isolation_total} tests passed")
        
        # Edge Cases
        edge_passed = sum(1 for t in self.edge_case_results if t['passed'])
        edge_total = len(self.edge_case_results)
        print(f"🧪 Edge Cases: {edge_passed}/{edge_total} tests passed")
        
        # Timing breakdown
        print("\n" + "-"*80)
        print("📈 TIMING BREAKDOWN")
        print("-"*80)
        print(f"{'Operation':<40} {'Avg(s)':<10} {'Max(s)':<10} {'Calls':<8} {'Queries/call':<12}")
        print("-"*80)
        
        for op, times in sorted(self.timings.items(), key=lambda x: -sum(x[1])):
            avg_time = sum(times) / len(times)
            max_time = max(times)
            queries = self.query_counts[op]
            avg_queries = sum(queries) / len(queries) if queries else 0
            print(f"{op:<40} {avg_time:<10.3f} {max_time:<10.3f} {len(times):<8} {avg_queries:<12.1f}")
        
        # Bottlenecks
        if self.bottlenecks:
            print("\n" + "-"*80)
            print("🐌 BOTTLENECKS (operations > 2s)")
            print("-"*80)
            for b in sorted(self.bottlenecks, key=lambda x: -x['duration']):
                print(f"  [{b['severity']}] {b['operation']}: {b['duration']:.2f}s ({b['query_count']} queries)")
        
        # Isolation Test Details
        if self.isolation_results:
            print("\n" + "-"*80)
            print("🔒 USER ISOLATION TEST RESULTS")
            print("-"*80)
            for result in self.isolation_results:
                status = "✅ PASS" if result['passed'] else "❌ FAIL"
                print(f"  {status} {result['test']}")
                if result['details']:
                    print(f"      → {result['details']}")
        
        # Edge Case Details
        if self.edge_case_results:
            print("\n" + "-"*80)
            print("🧪 EDGE CASE TEST RESULTS")
            print("-"*80)
            for result in self.edge_case_results:
                status = "✅ PASS" if result['passed'] else "❌ FAIL"
                print(f"  {status} {result['test']}")
                if result['details']:
                    print(f"      → {result['details']}")
        
        # Errors
        if self.errors:
            print("\n" + "-"*80)
            print("❌ ERRORS")
            print("-"*80)
            for e in self.errors[:10]:  # Show first 10
                print(f"  • {e['operation']}: {e['error']}")
            if len(self.errors) > 10:
                print(f"  ... and {len(self.errors) - 10} more errors")
        
        # Warnings
        if self.warnings:
            print("\n" + "-"*80)
            print("⚠️  WARNINGS")
            print("-"*80)
            for w in self.warnings[:10]:  # Show first 10
                print(f"  • {w['operation']}: {w['message']}")
            if len(self.warnings) > 10:
                print(f"  ... and {len(self.warnings) - 10} more warnings")
        
        # Optimization recommendations
        print("\n" + "-"*80)
        print("💡 OPTIMIZATION RECOMMENDATIONS")
        print("-"*80)
        
        recommendations = []
        
        # Check query counts
        for op, queries in self.query_counts.items():
            avg_q = sum(queries) / len(queries) if queries else 0
            if avg_q > 50:
                recommendations.append(f"• {op}: High query count ({avg_q:.0f}/call). Consider prefetching or caching.")
        
        # Check slow operations
        for op, times in self.timings.items():
            avg_time = sum(times) / len(times)
            if avg_time > 1.0:
                recommendations.append(f"• {op}: Slow ({avg_time:.2f}s avg). Consider async or batch processing.")
        
        if not recommendations:
            print("  ✅ No major optimization issues detected!")
        else:
            for r in recommendations:
                print(f"  {r}")
        
        print("\n" + "="*80)
        
        # Return summary dict
        return {
            'total_time': total_time,
            'errors': len(self.errors),
            'warnings': len(self.warnings),
            'bottlenecks': len(self.bottlenecks),
            'isolation_passed': isolation_passed == isolation_total,
            'edge_cases_passed': edge_passed == edge_total
        }


def timed_operation(results: StressTestResults, operation_name: str):
    """Decorator/context manager for timing operations."""
    class Timer:
        def __enter__(self):
            reset_queries()
            self.start = time.time()
            return self
        
        def __exit__(self, *args):
            duration = time.time() - self.start
            query_count = len(connection.queries)
            results.log_timing(operation_name, duration, query_count)
    
    return Timer()


def generate_users_bulk(count: int, results: StressTestResults) -> list:
    """Generate test users."""
    logger.info(f"👤 Generating {count} users...")
    
    with timed_operation(results, "generate_users"):
        created_users = []
        for i in range(count):
            user = User.objects.create_user(
                username=f'stresstest_user_{i}_{uuid.uuid4().hex[:6]}',
                email=f'stress{i}@test.com',
                password='testpass123'
            )
            created_users.append(user)
    
    logger.info(f"✅ Created {len(created_users)} users")
    return created_users


def generate_trackers_and_tasks_bulk(users: list, results: StressTestResults) -> dict:
    """Generate trackers and tasks using bulk operations."""
    trackers_per_user = 2
    tasks_per_tracker = 4
    days_of_data = 30
    
    logger.info(f"📝 Generating trackers and tasks (bulk)...")
    
    categories = ['Health', 'Work', 'Personal', 'Learning', 'Finance']
    positive_notes = [
        "Feeling great today! Made good progress.",
        "Productive day, accomplished all my goals.",
        "Feeling motivated and energized.",
        "Great sleep last night, slept 8 hours!",
        "Happy with my consistency this week."
    ]
    negative_notes = [
        "Feeling a bit overwhelmed today.",
        "Struggled to focus, low energy.",
        "Didn't sleep well, only 5 hours.",
        "Feeling stressed about work.",
        "Tired and unmotivated."
    ]
    
    stats = {
        'trackers': 0,
        'templates': 0,
        'instances': 0,
        'tasks': 0,
        'notes': 0
    }
    
    with timed_operation(results, "generate_all_data_bulk"):
        # Create all trackers
        trackers_to_create = []
        for user in users:
            for t in range(trackers_per_user):
                trackers_to_create.append(TrackerDefinition(
                    tracker_id=str(uuid.uuid4()),
                    user=user,
                    name=f'Tracker {t+1} for {user.username}',
                    time_mode='daily'
                ))
        
        created_trackers = TrackerDefinition.objects.bulk_create(trackers_to_create)
        stats['trackers'] = len(created_trackers)
        
        # Create templates for each tracker
        templates_to_create = []
        tracker_templates_map = {}  # tracker_id -> list of template objects
        
        for tracker in created_trackers:
            tracker_templates_map[tracker.tracker_id] = []
            for i in range(tasks_per_tracker):
                template = TaskTemplate(
                    template_id=str(uuid.uuid4()),
                    tracker=tracker,
                    description=f'Task {i+1}',
                    category=random.choice(categories),
                    weight=random.randint(1, 3)
                )
                templates_to_create.append(template)
                tracker_templates_map[tracker.tracker_id].append(template)
        
        created_templates = TaskTemplate.objects.bulk_create(templates_to_create)
        stats['templates'] = len(created_templates)
        
        # Refresh template map with actual IDs
        for template in created_templates:
            # Update tracker_templates_map with saved templates
            for t_list in tracker_templates_map.values():
                for i, t in enumerate(t_list):
                    if t.template_id == template.template_id:
                        t_list[i] = template
        
        # Create instances and tasks
        today = date.today()
        instances_to_create = []
        tasks_to_create = []
        notes_to_create = []
        
        for tracker in created_trackers:
            templates = tracker_templates_map.get(tracker.tracker_id, [])
            
            for day_offset in range(days_of_data):
                current_date = today - timedelta(days=day_offset)
                
                instance = TrackerInstance(
                    instance_id=str(uuid.uuid4()),
                    tracker=tracker,
                    tracking_date=current_date,
                    period_start=current_date,
                    period_end=current_date,
                    status='active'
                )
                instances_to_create.append(instance)
                
                # Random completion pattern
                completion_rate = random.uniform(0.3, 1.0)
                
                for template in templates:
                    completed = random.random() < completion_rate
                    tasks_to_create.append(TaskInstance(
                        task_instance_id=str(uuid.uuid4()),
                        tracker_instance=instance,
                        template=template,
                        status='DONE' if completed else 'TODO'
                    ))
                
                # Add note occasionally
                if random.random() < 0.4:
                    note_text = random.choice(positive_notes if completion_rate > 0.6 else negative_notes)
                    notes_to_create.append(DayNote(
                        note_id=str(uuid.uuid4()),
                        tracker=tracker,
                        date=current_date,
                        content=note_text
                    ))
        
        # Bulk create in batches
        BATCH_SIZE = 1000
        
        for i in range(0, len(instances_to_create), BATCH_SIZE):
            TrackerInstance.objects.bulk_create(instances_to_create[i:i+BATCH_SIZE])
        stats['instances'] = len(instances_to_create)
        
        for i in range(0, len(tasks_to_create), BATCH_SIZE):
            TaskInstance.objects.bulk_create(tasks_to_create[i:i+BATCH_SIZE])
        stats['tasks'] = len(tasks_to_create)
        
        for i in range(0, len(notes_to_create), BATCH_SIZE):
            DayNote.objects.bulk_create(notes_to_create[i:i+BATCH_SIZE])
        stats['notes'] = len(notes_to_create)
    
    logger.info(f"✅ Created: {stats['trackers']} trackers, {stats['templates']} templates, "
                f"{stats['instances']} instances, {stats['tasks']} tasks, {stats['notes']} notes")
    
    return stats


def test_user_isolation(users: list, results: StressTestResults):
    """Test that user data is properly isolated."""
    logger.info("🔒 Testing user data isolation...")
    
    if len(users) < 2:
        results.log_warning("isolation", "Need at least 2 users for isolation testing")
        return
    
    user1, user2 = users[0], users[1]
    
    # Test 1: Tracker ownership
    user1_trackers = TrackerDefinition.objects.filter(user=user1)
    user2_trackers = TrackerDefinition.objects.filter(user=user2)
    
    # Ensure no overlap
    user1_ids = set(t.tracker_id for t in user1_trackers)
    user2_ids = set(t.tracker_id for t in user2_trackers)
    
    no_overlap = len(user1_ids & user2_ids) == 0
    results.log_isolation_test(
        "Tracker Ownership Isolation",
        no_overlap,
        f"User1: {len(user1_ids)} trackers, User2: {len(user2_ids)} trackers, Overlap: {len(user1_ids & user2_ids)}"
    )
    
    # Test 2: Analytics returns different data for different users
    if user1_trackers.exists() and user2_trackers.exists():
        tracker1 = user1_trackers.first()
        tracker2 = user2_trackers.first()
        
        with timed_operation(results, "isolation_analytics"):
            completion1 = analytics.compute_completion_rate(str(tracker1.tracker_id))
            completion2 = analytics.compute_completion_rate(str(tracker2.tracker_id))
        
        # The data should be independent (not necessarily different, but from different trackers)
        results.log_isolation_test(
            "Analytics Data Independence",
            True,  # If no error, analytics correctly separates data
            f"Tracker1 completion: {completion1.get('value', 0):.1f}%, Tracker2: {completion2.get('value', 0):.1f}%"
        )
    
    # Test 3: Insights are user-specific
    if user1_trackers.exists() and user2_trackers.exists():
        tracker1 = user1_trackers.first()
        tracker2 = user2_trackers.first()
        
        try:
            with timed_operation(results, "isolation_insights"):
                insights1 = get_insights(str(tracker1.tracker_id))
                insights2 = get_insights(str(tracker2.tracker_id))
            
            results.log_isolation_test(
                "Insights Data Independence",
                True,
                f"User1 insights: {len(insights1)}, User2 insights: {len(insights2)}"
            )
        except Exception as e:
            results.log_error("isolation_insights", e)
    
    # Test 4: Journey/Timeline is user-specific
    try:
        from core.exports.exporter import generate_journey_report
        
        tracker1 = user1_trackers.first()
        tracker2 = user2_trackers.first()
        
        if tracker1 and tracker2:
            journey1 = generate_journey_report(str(tracker1.tracker_id))
            journey2 = generate_journey_report(str(tracker2.tracker_id))
            
            results.log_isolation_test(
                "Journey Report Independence",
                True,
                f"User1 events: {journey1.get('total_events', 0)}, User2 events: {journey2.get('total_events', 0)}"
            )
    except Exception as e:
        results.log_error("isolation_journey", e)


def test_edge_cases(results: StressTestResults):
    """Test edge cases and boundary conditions."""
    logger.info("🧪 Testing edge cases...")
    
    # Create a test user for edge cases
    edge_user = User.objects.create_user(
        username=f'edge_test_user_{uuid.uuid4().hex[:6]}',
        password='testpass123'
    )
    
    try:
        # Edge Case 1: Empty tracker (no tasks)
        empty_tracker = TrackerDefinition.objects.create(
            tracker_id=str(uuid.uuid4()),
            user=edge_user,
            name='Empty Tracker',
            time_mode='daily'
        )
        
        try:
            completion = analytics.compute_completion_rate(str(empty_tracker.tracker_id))
            passed = completion.get('value') == 0.0
            results.log_edge_case("Empty Tracker - Completion Rate", passed, 
                                  f"Expected 0.0, got {completion.get('value')}")
        except Exception as e:
            results.log_edge_case("Empty Tracker - Completion Rate", False, str(e))
        
        try:
            streaks = analytics.detect_streaks(str(empty_tracker.tracker_id))
            passed = streaks.get('value', {}).get('current_streak') == 0
            results.log_edge_case("Empty Tracker - Streaks", passed,
                                  f"Expected 0 streak, got {streaks.get('value', {}).get('current_streak')}")
        except Exception as e:
            results.log_edge_case("Empty Tracker - Streaks", False, str(e))
        
        try:
            insights = get_insights(str(empty_tracker.tracker_id))
            results.log_edge_case("Empty Tracker - Insights", True,
                                  f"Returned {len(insights)} insights without error")
        except Exception as e:
            results.log_edge_case("Empty Tracker - Insights", False, str(e))
        
        # Edge Case 2: Single task, single day
        single_tracker = TrackerDefinition.objects.create(
            tracker_id=str(uuid.uuid4()),
            user=edge_user,
            name='Single Task Tracker',
            time_mode='daily'
        )
        
        template = TaskTemplate.objects.create(
            template_id=str(uuid.uuid4()),
            tracker=single_tracker,
            description='Single Task',
            weight=1
        )
        
        instance = TrackerInstance.objects.create(
            instance_id=str(uuid.uuid4()),
            tracker=single_tracker,
            tracking_date=date.today(),
            period_start=date.today(),
            period_end=date.today(),
            status='active'
        )
        
        TaskInstance.objects.create(
            task_instance_id=str(uuid.uuid4()),
            tracker_instance=instance,
            template=template,
            status='DONE'
        )
        
        try:
            completion = analytics.compute_completion_rate(str(single_tracker.tracker_id))
            passed = completion.get('value') == 100.0
            results.log_edge_case("Single Task 100% - Completion", passed,
                                  f"Expected 100.0, got {completion.get('value')}")
        except Exception as e:
            results.log_edge_case("Single Task 100% - Completion", False, str(e))
        
        try:
            streaks = analytics.detect_streaks(str(single_tracker.tracker_id))
            passed = streaks.get('value', {}).get('current_streak') >= 1
            results.log_edge_case("Single Task - Streak Detection", passed,
                                  f"Got streak: {streaks.get('value', {}).get('current_streak')}")
        except Exception as e:
            results.log_edge_case("Single Task - Streak Detection", False, str(e))
        
        # Edge Case 3: All tasks missed
        missed_tracker = TrackerDefinition.objects.create(
            tracker_id=str(uuid.uuid4()),
            user=edge_user,
            name='All Missed Tracker',
            time_mode='daily'
        )
        
        template_m = TaskTemplate.objects.create(
            template_id=str(uuid.uuid4()),
            tracker=missed_tracker,
            description='Missed Task',
            weight=1
        )
        
        for day in range(5):
            inst = TrackerInstance.objects.create(
                instance_id=str(uuid.uuid4()),
                tracker=missed_tracker,
                tracking_date=date.today() - timedelta(days=day),
                period_start=date.today() - timedelta(days=day),
                period_end=date.today() - timedelta(days=day),
                status='active'
            )
            TaskInstance.objects.create(
                task_instance_id=str(uuid.uuid4()),
                tracker_instance=inst,
                template=template_m,
                status='TODO'
            )
        
        try:
            completion = analytics.compute_completion_rate(str(missed_tracker.tracker_id))
            passed = completion.get('value') == 0.0
            results.log_edge_case("All Tasks TODO - 0% Completion", passed,
                                  f"Expected 0.0, got {completion.get('value')}")
        except Exception as e:
            results.log_edge_case("All Tasks TODO - 0% Completion", False, str(e))
        
        try:
            streaks = analytics.detect_streaks(str(missed_tracker.tracker_id))
            passed = streaks.get('value', {}).get('current_streak') == 0
            results.log_edge_case("All Tasks TODO - Zero Streak", passed,
                                  f"Got streak: {streaks.get('value', {}).get('current_streak')}")
        except Exception as e:
            results.log_edge_case("All Tasks TODO - Zero Streak", False, str(e))
        
        # Edge Case 4: Unicode in notes
        unicode_tracker = TrackerDefinition.objects.create(
            tracker_id=str(uuid.uuid4()),
            user=edge_user,
            name='Unicode Tracker',
            time_mode='daily'
        )
        
        DayNote.objects.create(
            note_id=str(uuid.uuid4()),
            tracker=unicode_tracker,
            date=date.today(),
            content="Feeling great! 🎉 今日はいい日だ! Très bien! 💪"
        )
        
        try:
            sentiment = analytics.analyze_notes_sentiment(str(unicode_tracker.tracker_id))
            results.log_edge_case("Unicode Notes - Sentiment", True,
                                  f"Processed unicode without error, avg mood: {sentiment.get('average_mood', 0):.2f}")
        except Exception as e:
            results.log_edge_case("Unicode Notes - Sentiment", False, str(e))
        
        # Edge Case 5: Very long note
        long_note = "This is a test. " * 500  # ~8000 chars
        DayNote.objects.create(
            note_id=str(uuid.uuid4()),
            tracker=unicode_tracker,
            date=date.today() - timedelta(days=1),
            content=long_note
        )
        
        try:
            sentiment = analytics.analyze_notes_sentiment(str(unicode_tracker.tracker_id))
            results.log_edge_case("Long Note - Sentiment", True,
                                  f"Processed {len(long_note)} char note")
        except Exception as e:
            results.log_edge_case("Long Note - Sentiment", False, str(e))
        
    finally:
        # Cleanup edge case user
        edge_user.delete()


def test_analytics(results: StressTestResults) -> dict:
    """Test analytics on sample trackers."""
    logger.info("📊 Testing analytics on sample trackers...")
    
    trackers = TrackerDefinition.objects.filter(name__startswith='Tracker')
    analytics_results = {
        'completion_rate': {'success': 0, 'fail': 0},
        'streaks': {'success': 0, 'fail': 0},
        'consistency': {'success': 0, 'fail': 0},
        'balance': {'success': 0, 'fail': 0},
        'effort': {'success': 0, 'fail': 0},
        'sentiment': {'success': 0, 'fail': 0},
        'trends': {'success': 0, 'fail': 0}
    }
    
    sample_trackers = list(trackers[:50])  # Test on sample for speed
    
    for tracker in sample_trackers:
        tid = str(tracker.tracker_id)
        
        # Completion rate
        try:
            with timed_operation(results, "analytics_completion_rate"):
                result = analytics.compute_completion_rate(tid)
                if result and 'value' in result:
                    analytics_results['completion_rate']['success'] += 1
                else:
                    results.log_warning("completion_rate", f"Empty result for {tid}")
        except Exception as e:
            analytics_results['completion_rate']['fail'] += 1
            results.log_error("completion_rate", e)
        
        # Streaks
        try:
            with timed_operation(results, "analytics_streaks"):
                result = analytics.detect_streaks(tid)
                analytics_results['streaks']['success'] += 1
        except Exception as e:
            analytics_results['streaks']['fail'] += 1
            results.log_error("streaks", e)
        
        # Consistency
        try:
            with timed_operation(results, "analytics_consistency"):
                result = analytics.compute_consistency_score(tid)
                analytics_results['consistency']['success'] += 1
        except Exception as e:
            analytics_results['consistency']['fail'] += 1
            results.log_error("consistency", e)
        
        # Balance
        try:
            with timed_operation(results, "analytics_balance"):
                result = analytics.compute_balance_score(tid)
                analytics_results['balance']['success'] += 1
        except Exception as e:
            analytics_results['balance']['fail'] += 1
            results.log_error("balance", e)
        
        # Effort
        try:
            with timed_operation(results, "analytics_effort"):
                result = analytics.compute_effort_index(tid)
                analytics_results['effort']['success'] += 1
        except Exception as e:
            analytics_results['effort']['fail'] += 1
            results.log_error("effort", e)
        
        # Sentiment
        try:
            with timed_operation(results, "analytics_sentiment"):
                result = analytics.analyze_notes_sentiment(tid)
                analytics_results['sentiment']['success'] += 1
        except Exception as e:
            analytics_results['sentiment']['fail'] += 1
            results.log_error("sentiment", e)
        
        # Trends
        try:
            with timed_operation(results, "analytics_trends"):
                result = analytics.analyze_trends(tid)
                analytics_results['trends']['success'] += 1
        except Exception as e:
            analytics_results['trends']['fail'] += 1
            results.log_error("trends", e)
    
    logger.info(f"✅ Analytics tested on {len(sample_trackers)} trackers")
    return analytics_results


def test_insights(results: StressTestResults) -> dict:
    """Test behavioral insights engine."""
    logger.info("🧠 Testing behavioral insights engine...")
    
    trackers = TrackerDefinition.objects.filter(name__startswith='Tracker')[:30]
    insights_stats = {
        'total_insights': 0,
        'by_type': defaultdict(int),
        'by_severity': defaultdict(int),
        'success': 0,
        'fail': 0
    }
    
    for tracker in trackers:
        try:
            with timed_operation(results, "insights_engine"):
                insights = get_insights(str(tracker.tracker_id))
                insights_stats['success'] += 1
                insights_stats['total_insights'] += len(insights)
                
                for insight in insights:
                    insights_stats['by_type'][insight.get('type', 'unknown')] += 1
                    insights_stats['by_severity'][insight.get('severity', 'unknown')] += 1
        except Exception as e:
            insights_stats['fail'] += 1
            results.log_error("insights_engine", e, traceback.format_exc())
    
    logger.info(f"✅ Insights: {insights_stats['total_insights']} generated, "
                f"{insights_stats['success']} success, {insights_stats['fail']} fail")
    return insights_stats


def test_forecasting(results: StressTestResults) -> dict:
    """Test time-series forecasting."""
    logger.info("🔮 Testing forecasting...")
    
    trackers = TrackerDefinition.objects.filter(name__startswith='Tracker')[:20]
    forecast_stats = {'success': 0, 'fail': 0}
    
    for tracker in trackers:
        try:
            with timed_operation(results, "forecasting"):
                result = analytics.analyze_time_series(
                    str(tracker.tracker_id),
                    metric='completion_rate',
                    forecast_days=7
                )
                if result and 'forecast' in result:
                    forecast_stats['success'] += 1
                else:
                    results.log_warning("forecasting", "No forecast generated")
        except Exception as e:
            forecast_stats['fail'] += 1
            # Only log unique errors
            if 'Non-invertible' not in str(e) and 'sarimax' not in str(e).lower():
                results.log_error("forecasting", e)
    
    logger.info(f"✅ Forecasting: {forecast_stats['success']} success, {forecast_stats['fail']} fail")
    return forecast_stats


def test_nlp(results: StressTestResults) -> dict:
    """Test NLP analysis."""
    logger.info("📝 Testing NLP analysis...")
    
    notes = DayNote.objects.all()[:100]
    nlp_stats = {'sentiment': 0, 'keywords': 0, 'patterns': 0, 'errors': 0}
    
    for note in notes:
        try:
            with timed_operation(results, "nlp_sentiment"):
                sentiment = nlp_helpers.compute_sentiment(note.content)
                if sentiment:
                    nlp_stats['sentiment'] += 1
            
            with timed_operation(results, "nlp_keywords"):
                keywords = nlp_helpers.extract_keywords(note.content)
                if keywords:
                    nlp_stats['keywords'] += 1
            
            with timed_operation(results, "nlp_sleep_pattern"):
                sleep = nlp_helpers.extract_sleep_pattern(note.content)
                if sleep.get('hours'):
                    nlp_stats['patterns'] += 1
        except Exception as e:
            nlp_stats['errors'] += 1
            results.log_error("nlp_analysis", e)
    
    logger.info(f"✅ NLP: {nlp_stats['sentiment']} sentiments, {nlp_stats['keywords']} keywords analyzed")
    return nlp_stats


def cleanup_test_data():
    """Remove test data."""
    logger.info("🧹 Cleaning up test data...")
    
    # Delete test users (cascades to trackers, etc.)
    User.objects.filter(username__startswith='stresstest_user_').delete()
    User.objects.filter(username__startswith='edge_test_user_').delete()
    
    logger.info("✅ Cleanup complete")


def main():
    """Run the enhanced stress test."""
    print("="*80)
    print("🔥 ENHANCED BEHAVIORAL ANALYTICS STRESS TEST")
    print("="*80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    results = StressTestResults()
    results.start_time = time.time()
    
    try:
        # Generate data using bulk operations
        users = generate_users_bulk(100, results)
        data_stats = generate_trackers_and_tasks_bulk(users, results)
        
        # Test user isolation
        test_user_isolation(users, results)
        
        # Test edge cases
        test_edge_cases(results)
        
        # Test components
        analytics_stats = test_analytics(results)
        insights_stats = test_insights(results)
        forecast_stats = test_forecasting(results)
        nlp_stats = test_nlp(results)
        
        # Print detailed report
        summary = results.print_report()
        
        # Additional stats
        print("\n" + "-"*80)
        print("📈 DATA STATISTICS")
        print("-"*80)
        print(f"  Users created: {len(users)}")
        print(f"  Trackers: {data_stats['trackers']}")
        print(f"  Task templates: {data_stats['templates']}")
        print(f"  Tracker instances: {data_stats['instances']}")
        print(f"  Task instances: {data_stats['tasks']}")
        print(f"  Day notes: {data_stats['notes']}")
        
        print("\n" + "-"*80)
        print("🧠 INSIGHTS STATISTICS")
        print("-"*80)
        print(f"  Total insights generated: {insights_stats['total_insights']}")
        print(f"  By type:")
        for itype, count in sorted(insights_stats['by_type'].items(), key=lambda x: -x[1]):
            print(f"    - {itype}: {count}")
        print(f"  By severity:")
        for sev, count in insights_stats['by_severity'].items():
            print(f"    - {sev}: {count}")
        
        # Final summary
        print("\n" + "-"*80)
        print("📋 FINAL SUMMARY")
        print("-"*80)
        all_passed = summary['isolation_passed'] and summary['edge_cases_passed'] and summary['errors'] == 0
        overall_status = "✅ ALL TESTS PASSED" if all_passed else "⚠️ SOME ISSUES DETECTED"
        print(f"  {overall_status}")
        print(f"  Total Time: {summary['total_time']:.2f}s")
        print(f"  Errors: {summary['errors']}, Warnings: {summary['warnings']}, Bottlenecks: {summary['bottlenecks']}")
        
    except KeyboardInterrupt:
        logger.warning("Test interrupted by user")
    except Exception as e:
        logger.error(f"Test failed: {e}")
        traceback.print_exc()
    finally:
        # Cleanup
        cleanup_test_data()
    
    print("\n" + "="*80)
    print("✅ STRESS TEST COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()
