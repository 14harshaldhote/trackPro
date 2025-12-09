"""
Share Service

Handle share link validation, access control, and usage tracking.
Implements security edge cases from finalePhase.md Section 6.6

Written from scratch for Version 1.0
"""
import hashlib
from typing import Tuple, Optional
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from core.models import ShareLink, TrackerDefinition
import logging

logger = logging.getLogger(__name__)


class ShareService:
    """Service for managing share link operations."""
    
    @staticmethod
    def create_share_link(
        tracker: TrackerDefinition,
        user_id: int,
        permission_level: str = 'view',
        expires_in_days: int = None,
        max_uses: int = None,
        password: str = None
    ) -> ShareLink:
        """
        Create a new share link for a tracker.
        
        Args:
            tracker: The tracker to share
            user_id: User creating the share link
            permission_level: 'view', 'comment', or 'edit'
            expires_in_days: Number of days until expiration (None = no expiry)
            max_uses: Maximum number of uses (None = unlimited)
            password: Optional password protection
            
        Returns:
            Created ShareLink object
        """
        expires_at = None
        if expires_in_days:
            expires_at = timezone.now() + timezone.timedelta(days=expires_in_days)
        
        password_hash = None
        if password:
            password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        share_link = ShareLink.objects.create(
            tracker=tracker,
            created_by_id=user_id,
            permission_level=permission_level,
            expires_at=expires_at,
            max_uses=max_uses,
            password_hash=password_hash
        )
        
        return share_link
    
    @staticmethod
    def validate_and_use(
        token: str,
        password: str = None
    ) -> Tuple[Optional[TrackerDefinition], str]:
        """
        Validate share link and increment usage.
        
        Uses SELECT FOR UPDATE to handle race conditions with max_uses.
        See finalePhase.md Section 6.6 for edge case handling.
        
        Args:
            token: Share link token
            password: Optional password for protected links
            
        Returns:
            Tuple of (tracker or None, error_message)
        """
        try:
            # Use select_for_update to prevent race conditions
            with transaction.atomic():
                share = ShareLink.objects.select_for_update().get(token=token)
                
                # Check if link is active
                if not share.is_active:
                    return None, "Share link has been deactivated"
                
                # Check expiration
                if share.expires_at and share.expires_at < timezone.now():
                    return None, "Share link has expired"
                
                # Check usage limit
                if share.max_uses and share.use_count >= share.max_uses:
                    return None, "Share link usage limit reached"
                
                # Check password if required
                if share.password_hash:
                    if not password:
                        return None, "Password required"
                    
                    provided_hash = hashlib.sha256(password.encode()).hexdigest()
                    if provided_hash != share.password_hash:
                        return None, "Invalid password"
                
                # Increment usage count
                share.use_count = F('use_count') + 1
                share.save(update_fields=['use_count'])
                
                return share.tracker, ""
                
        except ShareLink.DoesNotExist:
            return None, "Invalid share link"
        except Exception as e:
            logger.error(f"Error validating share link: {e}")
            return None, "An error occurred while validating the share link"
    
    @staticmethod
    def deactivate_link(token: str, user_id: int) -> Tuple[bool, str]:
        """
        Deactivate a share link.
        
        Args:
            token: Share link token
            user_id: User requesting deactivation (must be owner)
            
        Returns:
            Tuple of (success, message)
        """
        try:
            share = ShareLink.objects.get(
                token=token,
                created_by_id=user_id
            )
            
            share.is_active = False
            share.save(update_fields=['is_active'])
            
            return True, "Share link deactivated successfully"
            
        except ShareLink.DoesNotExist:
            return False, "Share link not found or you don't have permission"
    
    @staticmethod
    def regenerate_token(token: str, user_id: int) -> Tuple[Optional[ShareLink], str]:
        """
        Regenerate a share link token (for security).
        
        This creates a new token for an existing share link,
        making the old token immediately invalid.
        
        Args:
            token: Current share link token
            user_id: User requesting regeneration (must be owner)
            
        Returns:
            Tuple of (updated ShareLink or None, message)
        """
        import uuid
        
        try:
            with transaction.atomic():
                share = ShareLink.objects.select_for_update().get(
                    token=token,
                    created_by_id=user_id
                )
                
                # Generate new token
                share.token = uuid.uuid4()
                share.save(update_fields=['token'])
                
                return share, "Token regenerated successfully"
                
        except ShareLink.DoesNotExist:
            return None, "Share link not found or you don't have permission"
    
    @staticmethod
    def get_user_shares(user_id: int) -> list:
        """
        Get all active share links created by a user.
        
        Args:
            user_id: User whose shares to retrieve
            
        Returns:
            List of ShareLink objects with related tracker data
        """
        return ShareLink.objects.filter(
            created_by_id=user_id,
            is_active=True
        ).select_related('tracker').order_by('-created_at')
    
    @staticmethod
    def get_share_stats(token: str, user_id: int) -> Optional[dict]:
        """
        Get usage statistics for a share link.
        
        Args:
            token: Share link token
            user_id: User requesting stats (must be owner)
            
        Returns:
            Dict with usage stats or None
        """
        try:
            share = ShareLink.objects.get(
                token=token,
                created_by_id=user_id
            )
            
            return {
                'token': str(share.token),
                'tracker_id': str(share.tracker_id),
                'tracker_name': share.tracker.name,
                'permission_level': share.permission_level,
                'use_count': share.use_count,
                'max_uses': share.max_uses,
                'is_active': share.is_active,
                'expires_at': share.expires_at.isoformat() if share.expires_at else None,
                'created_at': share.created_at.isoformat(),
                'has_password': share.password_hash is not None,
                'is_expired': share.expires_at and share.expires_at < timezone.now()
            }
            
        except ShareLink.DoesNotExist:
            return None
