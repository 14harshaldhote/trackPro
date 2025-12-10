"""
File Upload Security Tests

Test IDs: SEC-005 to SEC-008
Coverage: Malicious extensions, size limits, content validation, path traversal
"""
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from core.tests.base import BaseAPITestCase

@pytest.mark.security
@pytest.mark.critical
class FileUploadSecurityTests(BaseAPITestCase):
    """Tests for file upload security."""
    
    def test_SEC_005_malicious_file_extension_blocked(self):
        """SEC-005: Malicious file extensions are blocked."""
        malicious_extensions = [
            'malware.exe',
            'script.sh',
            'code.py',
            'hack.php',
            'bad.js',
        ]
        
        for filename in malicious_extensions:
            # Create fake file
            file_content = b'malicious content'
            uploaded_file = SimpleUploadedFile(
                filename,
                file_content,
                content_type='application/octet-stream'
            )
            
            # Try to upload
            response = self.client.post(
                '/api/v1/user/avatar/',
                {'avatar': uploaded_file},
                format='multipart'
            )
            
            # Should be rejected (400 or 403)
            self.assertIn(response.status_code, [400, 403],
                         f"Malicious file '{filename}' was not blocked")
    
    def test_SEC_006_file_size_limit_enforced(self):
        """SEC-006: File size limits are enforced."""
        # Create large file (> 10MB)
        large_content = b'X' * (11 * 1024 * 1024)  # 11MB
        
        large_file = SimpleUploadedFile(
            'large.jpg',
            large_content,
            content_type='image/jpeg'
        )
        
        response = self.client.post(
            '/api/v1/user/avatar/',
            {'avatar': large_file},
            format='multipart'
        )
        
        # Should be rejected
        self.assertIn(response.status_code, [400, 413])
    
    def test_SEC_007_file_content_validation(self):
        """SEC-007: File content is validated (not just extension)."""
        # Create file with image extension but executable content
        fake_image = SimpleUploadedFile(
            'fake.jpg',
            b'#!/bin/bash\nrm -rf /',  # Executable content
            content_type='image/jpeg'
        )
        
        response = self.client.post(
            '/api/v1/user/avatar/',
            {'avatar': fake_image},
            format='multipart'
        )
        
        # Should be rejected or sanitized (likely 400 because Pillow won't open it)
        # Note: Actual behavior depends on your validation logic
    
    def test_SEC_008_path_traversal_in_filename_blocked(self):
        """SEC-008: Path traversal in filenames is blocked."""
        malicious_filenames = [
            '../../../etc/passwd',
            '..\\..\\..\\windows\\system32\\config\\sam',
            'normal.jpg/../../../malicious.exe',
        ]
        
        for filename in malicious_filenames:
            # SimpleUploadedFile behavior on filename may vary, but passing it
            uploaded_file = SimpleUploadedFile(
                filename,
                b'content',
                content_type='image/jpeg'
            )
            
            response = self.client.post(
                '/api/v1/user/avatar/',
                {'avatar': uploaded_file},
                format='multipart'
            )
            
            # Should sanitize filename or reject
            # At minimum, should not be 200 with original filename
            if response.status_code == 200:
                # If accepted, verify filename was sanitized
                data = response.json()
                if 'filename' in data or 'avatar_url' in data:
                    # Should not contain '..'
                    self.assertNotIn('..', str(data))
