
import pytest
from core.utils import pagination_helpers, skeleton_helpers
from core.tests.factories import TrackerFactory, UserFactory, InstanceFactory
from core.models import TrackerDefinition
from django.test import TestCase

class TestPaginationHelpers(TestCase):
    def setUp(self):
        self.user = UserFactory.create(username="page_user")
        for i in range(50):
            TrackerFactory.create(user=self.user, created_at='2023-01-01', tracker_id=f"id-{i}")

    def test_cursor_paginator(self):
        qs = TrackerDefinition.objects.filter(user=self.user).order_by('created_at')
        # Create unique created_at if possible or use id field for cursor
        # Actually factory uses random UUID. I can use tracker_id as cursor field if sortable.
        # Factories don't guarantee strict creation order unless I check.
        # Let's use TrackerDefinition object ids which are UUIDs. Sorting by UUID string works.
        
        paginator = pagination_helpers.CursorPaginator(qs, cursor_field='tracker_id', page_size=10)
        
        # First page
        res = paginator.paginate()
        assert len(res['items']) == 10
        assert res['pagination']['has_more'] is True
        cursor = res['pagination']['next_cursor']
        assert cursor is not None
        
        # Second page
        res2 = paginator.paginate(cursor=cursor)
        assert len(res2['items']) == 10
        # Check items differ (simple check)
        assert res['items'][0].tracker_id != res2['items'][0].tracker_id

    def test_paginated_response(self):
        items = [{'id': 1}, {'id': 2}]
        res = pagination_helpers.paginated_response(
            items=items,
            serializer_func=lambda x: x,
            has_more=False,
            next_cursor=None
        )
        assert res.status_code == 200
        import json
        data = json.loads(res.content)
        assert len(data['data']) == 2
        assert data['pagination']['has_more'] is False

    def test_offset_pagination(self):
        qs = TrackerDefinition.objects.filter(user=self.user)
        # Total 50
        
        # Page 1, size 20
        res = pagination_helpers.offset_pagination(qs, page=1, per_page=20)
        assert len(res['items']) == 20
        assert res['pagination']['has_next'] is True
        
        # Page 3, size 20 (items 41-50, count 10)
        res3 = pagination_helpers.offset_pagination(qs, page=3, per_page=20)
        assert len(res3['items']) == 10
        assert res3['pagination']['has_next'] is False


class TestSkeletonHelpers:
    def test_generate_panel_skeleton(self):
        types = ['dashboard', 'today', 'week', 'trackers', 'tracker_detail', 'analytics', 'list']
        for t in types:
            s = skeleton_helpers.generate_panel_skeleton(t)
            assert s is not None
            assert 'type' in s
        
        # Default
        s = skeleton_helpers.generate_panel_skeleton('unknown')
        assert s['type'] == 'list'

    def test_generate_modal_skeleton(self):
        types = ['add-task', 'edit-task', 'add-tracker', 'quick-add']
        for t in types:
            s = skeleton_helpers.generate_modal_skeleton(t)
            assert s is not None
        
        # Default
        s = skeleton_helpers.generate_modal_skeleton('unknown')
        assert s['type'] == 'generic_form'

    def test_get_modal_config(self):
        types = ['add-task', 'edit-task', 'add-tracker', 'quick-add']
        for t in types:
            c = skeleton_helpers.get_modal_config(t)
            assert 'presentation' in c
            
        # Default
        c = skeleton_helpers.get_modal_config('unknown')
        assert c['presentation'] == 'sheet'
