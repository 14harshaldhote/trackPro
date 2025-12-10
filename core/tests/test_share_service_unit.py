
from django.test import TestCase
from django.utils import timezone
from datetime import timedelta
import hashlib
import uuid
from core.services.share_service import ShareService
from core.models import ShareLink
from core.tests.factories import UserFactory, TrackerFactory, ShareLinkFactory

class TestShareServiceUnit(TestCase):

    def setUp(self):
        self.user = UserFactory.create(username="share_user")
        self.tracker = TrackerFactory.create(user=self.user)

    def test_create_share_link(self):
        # Basic
        link = ShareService.create_share_link(self.tracker, self.user.pk)
        assert link.tracker == self.tracker
        assert link.expires_at is None
        assert link.password_hash == ''
        
        # With expiry and password
        link2 = ShareService.create_share_link(
            self.tracker, 
            self.user.pk, 
            expires_in_days=7,
            password="secure"
        )
        assert link2.expires_at is not None
        assert link2.password_hash == hashlib.sha256("secure".encode()).hexdigest()

    def test_validate_and_use(self):
        # Success
        link = ShareLinkFactory.create(tracker=self.tracker, user=self.user)
        tracker, err = ShareService.validate_and_use(link.token)
        assert tracker is not None
        assert err == ""
        
        link.refresh_from_db()
        assert link.use_count == 1
        
        # Inactive
        link.is_active = False
        link.save()
        tracker, err = ShareService.validate_and_use(link.token)
        assert tracker is None
        assert "deactivated" in err
        
        # Expired
        link.is_active = True
        link.expires_at = timezone.now() - timedelta(days=1)
        link.save()
        tracker, err = ShareService.validate_and_use(link.token)
        assert tracker is None
        assert "expired" in err
        
        # Max uses
        link.expires_at = None
        link.max_uses = 1
        link.use_count = 1
        link.save()
        tracker, err = ShareService.validate_and_use(link.token)
        assert tracker is None
        assert "limit reached" in err
        
        # Password required
        link.max_uses = None
        link.password_hash = hashlib.sha256("pass".encode()).hexdigest()
        link.save()
        
        # Missing password
        tracker, err = ShareService.validate_and_use(link.token)
        assert tracker is None
        assert "Password required" in err
        
        # Wrong password
        tracker, err = ShareService.validate_and_use(link.token, "wrong")
        assert tracker is None
        assert "Invalid password" in err
        
        # Correct password
        tracker, err = ShareService.validate_and_use(link.token, "pass")
        assert tracker is not None
        
        # Invalid token
        tracker, err = ShareService.validate_and_use("invalid")
        assert tracker is None
        assert "Invalid share link" in err

    def test_deactivate_link(self):
        link = ShareLinkFactory.create(tracker=self.tracker, user=self.user)
        success, msg = ShareService.deactivate_link(link.token, self.user.pk)
        assert success is True
        
        link.refresh_from_db()
        assert link.is_active is False
        
        # Wrong user
        success, msg = ShareService.deactivate_link(link.token, 999)
        assert success is False

    def test_regenerate_token(self):
        link = ShareLinkFactory.create(tracker=self.tracker, user=self.user)
        old_token = link.token
        
        updated, msg = ShareService.regenerate_token(old_token, self.user.pk)
        assert updated is not None
        assert updated.token != old_token
        
        # Try finding usage of old token
        tracker, err = ShareService.validate_and_use(old_token)
        assert tracker is None
        
        # Wrong user
        updated, msg = ShareService.regenerate_token(updated.token, 999)
        assert updated is None

    def test_get_user_shares(self):
        ShareLinkFactory.create(tracker=self.tracker, user=self.user)
        shares = ShareService.get_user_shares(self.user.pk)
        assert len(shares) == 1

    def test_get_share_stats(self):
        link = ShareLinkFactory.create(tracker=self.tracker, user=self.user)
        stats = ShareService.get_share_stats(link.token, self.user.pk)
        assert stats is not None
        assert stats['use_count'] == 0
        
        # Wrong user
        assert ShareService.get_share_stats(link.token, 999) is None
