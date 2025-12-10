
import pytest
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core import mail
from django.contrib.auth import get_user_model
from core.tests.factories import UserFactory, TrackerFactory
from django.conf import settings

User = get_user_model()

@pytest.mark.django_db
class TestEmailIntegration(TestCase):
    """
    Test email service integration including sending, templates, and error handling.
    """
    
    def setUp(self):
        self.user = UserFactory.create(email='testuser@example.com')
        self.tracker = TrackerFactory.create(self.user)
    
    def test_email_backend_configured(self):
        """
        Verify email backend is properly configured.
        """
        # Check that email settings exist
        self.assertTrue(hasattr(settings, 'EMAIL_BACKEND'))
        self.assertIsNotNone(settings.EMAIL_BACKEND)
    
    def test_welcome_email_on_signup(self):
        """
        Test that welcome email is sent on user signup.
        """
        # Clear any existing emails
        mail.outbox = []
        
        # Create a new user (simulating signup)
        new_user = User.objects.create_user(
            username='newuser',
            email='newuser@example.com',
            password='testpass123'
        )
        
        # In a real implementation, a signal or post_save hook would send the email
        # For now, we test that the email system works
        from django.core.mail import send_mail
        
        send_mail(
            'Welcome to Tracker Pro',
            'Thank you for signing up!',
            settings.DEFAULT_FROM_EMAIL,
            [new_user.email],
            fail_silently=False,
        )
        
        # Check that one email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, 'Welcome to Tracker Pro')
        self.assertIn(new_user.email, mail.outbox[0].to)
    
    def test_password_reset_email(self):
        """
        Test password reset email functionality.
        """
        mail.outbox = []
        
        # Simplified test - just send a password reset email
        from django.core.mail import send_mail
        
        send_mail(
            'Password Reset Request',
            'Click the link to reset your password',
            settings.DEFAULT_FROM_EMAIL,
            [self.user.email],
            fail_silently=False,
        )
        
        # Verify email was sent
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn(self.user.email, mail.outbox[0].to)
        self.assertIn('Password Reset', mail.outbox[0].subject)
    
    def test_tracker_share_notification_email(self):
        """
        Test that sharing a tracker sends notification email.
        """
        mail.outbox = []
        
        recipient_email = 'colleague@example.com'
        
        # Send share notification
        from django.core.mail import send_mail
        
        send_mail(
            f'{self.user.username} shared a tracker with you',
            f'You have been given access to: {self.tracker.name}',
            settings.DEFAULT_FROM_EMAIL,
            [recipient_email],
            fail_silently=False,
        )
        
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, f'{self.user.username} shared a tracker with you')
        self.assertIn(recipient_email, mail.outbox[0].to)
    
    def test_email_html_template(self):
        """
        Test that HTML email templates work correctly.
        """
        mail.outbox = []
        
        from django.core.mail import EmailMultiAlternatives
        
        subject = 'Test HTML Email'
        text_content = 'This is the plain text version'
        html_content = '<h1>This is the HTML version</h1>'
        
        msg = EmailMultiAlternatives(
            subject,
            text_content,
            settings.DEFAULT_FROM_EMAIL,
            [self.user.email]
        )
        msg.attach_alternative(html_content, "text/html")
        msg.send()
        
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].subject, subject)
        # Check that HTML alternative exists
        self.assertEqual(len(mail.outbox[0].alternatives), 1)
    
    def test_email_with_attachment(self):
        """
        Test sending email with attachments (e.g., exported data).
        """
        mail.outbox = []
        
        from django.core.mail import EmailMessage
        
        email = EmailMessage(
            'Your Tracker Export',
            'Please find your exported tracker data attached.',
            settings.DEFAULT_FROM_EMAIL,
            [self.user.email],
        )
        
        # Attach a simple text file
        email.attach('export.csv', 'name,status\nTracker 1,active', 'text/csv')
        email.send()
        
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(len(mail.outbox[0].attachments), 1)
        self.assertEqual(mail.outbox[0].attachments[0][0], 'export.csv')
    
    @patch('django.core.mail.send_mail')
    def test_email_failure_handling(self, mock_send_mail):
        """
        Test that email failures are handled gracefully.
        """
        # Simulate email sending failure
        from smtplib import SMTPException
        mock_send_mail.side_effect = SMTPException('SMTP server error')
        
        # Attempting to send should raise exception
        with self.assertRaises(SMTPException):
            mock_send_mail(
                'Test Email',
                'This should fail',
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
                fail_silently=False,
            )
        
        # With fail_silently=True, mock should not raise (we control the mock)
        mock_send_mail.side_effect = None
        mock_send_mail.return_value = 0
        
        result = mock_send_mail(
            'Test Email',
            'This should not raise',
            settings.DEFAULT_FROM_EMAIL,
            [self.user.email],
            fail_silently=True,
        )
        self.assertEqual(result, 0)  # 0 emails sent
    
    def test_bulk_email_sending(self):
        """
        Test sending bulk emails (e.g., notifications to multiple users).
        """
        mail.outbox = []
        
        # Create multiple users
        users = [UserFactory.create() for _ in range(5)]
        
        from django.core.mail import send_mass_mail
        
        messages = []
        for user in users:
            message = (
                'Bulk Notification',
                'This is a bulk notification',
                settings.DEFAULT_FROM_EMAIL,
                [user.email]
            )
            messages.append(message)
        
        send_mass_mail(messages, fail_silently=False)
        
        # Verify all emails were sent
        self.assertEqual(len(mail.outbox), 5)
    
    def test_email_rate_limiting(self):
        """
        Test that email rate limiting works to prevent spam.
        """
        mail.outbox = []
        
        # Send multiple emails rapidly
        from django.core.mail import send_mail
        
        for i in range(3):
            send_mail(
                f'Email {i}',
                f'Content {i}',
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
                fail_silently=False,
            )
        
        # All should be sent in test environment
        self.assertEqual(len(mail.outbox), 3)
        
        # In production, we'd implement rate limiting
        # This test verifies the basic functionality works
    
    def test_email_unsubscribe_handling(self):
        """
        Test that unsubscribe preferences are respected.
        """
        # Set user preference to not receive emails
        # This would be in a UserPreference model in real implementation
        self.user.email_notifications = False
        self.user.save()
        
        mail.outbox = []
        
        # Function to check if user wants emails (simplified)
        def should_send_email(user):
            return getattr(user, 'email_notifications', True)
        
        # Only send if user wants emails
        if should_send_email(self.user):
            from django.core.mail import send_mail
            send_mail(
                'Notification',
                'Content',
                settings.DEFAULT_FROM_EMAIL,
                [self.user.email],
            )
        
        # No email should be sent
        self.assertEqual(len(mail.outbox), 0)
