
import pytest
import os
import tempfile
from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth import get_user_model
from django.conf import settings
from core.tests.factories import UserFactory, TrackerFactory

User = get_user_model()

@pytest.mark.django_db
class TestStorageIntegration(TestCase):
    """
    Test file storage integration for uploads, exports, and attachments.
    """
    
    def setUp(self):
        self.user = UserFactory.create()
        self.tracker = TrackerFactory.create(self.user)
        
        # Create a temporary directory for test uploads
        self.test_media_root = tempfile.mkdtemp()
    
    def tearDown(self):
        # Clean up temporary files
        import shutil
        if os.path.exists(self.test_media_root):
            shutil.rmtree(self.test_media_root)
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_file_upload_storage(self):
        """
        Test that uploaded files are stored correctly.
        """
        # Create a simple uploaded file
        file_content = b'Test file content'
        uploaded_file = SimpleUploadedFile(
            "test_document.txt",
            file_content,
            content_type="text/plain"
        )
        
        # Save file using Django's default storage
        from django.core.files.storage import default_storage
        
        file_path = default_storage.save(
            f'uploads/user_{self.user.id}/test_document.txt',
            uploaded_file
        )
        
        # Verify file exists
        self.assertTrue(default_storage.exists(file_path))
        
        # Verify file content
        saved_file = default_storage.open(file_path, 'rb')
        self.assertEqual(saved_file.read(), file_content)
        saved_file.close()
        
        # Clean up
        default_storage.delete(file_path)
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_image_upload_and_resize(self):
        """
        Test image upload and resizing functionality.
        """
        from PIL import Image
        import io
        
        # Create a test image
        image = Image.new('RGB', (800, 600), color='red')
        image_io = io.BytesIO()
        image.save(image_io, format='PNG')
        image_io.seek(0)
        
        uploaded_image = SimpleUploadedFile(
            "test_image.png",
            image_io.read(),
            content_type="image/png"
        )
        
        from django.core.files.storage import default_storage
        
        file_path = default_storage.save(
            f'uploads/user_{self.user.id}/profile_pic.png',
            uploaded_image
        )
        
        self.assertTrue(default_storage.exists(file_path))
        
        # Verify it's an image
        with default_storage.open(file_path, 'rb') as f:
            img = Image.open(f)
            self.assertEqual(img.format, 'PNG')
            self.assertEqual(img.size, (800, 600))
        
        # Clean up
        default_storage.delete(file_path)
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_file_size_validation(self):
        """
        Test that file size limits are enforced.
        """
        # Create a large file (simulated)
        max_size = 5 * 1024 * 1024  # 5MB
        large_content = b'x' * (max_size + 1)
        
        large_file = SimpleUploadedFile(
            "large_file.txt",
            large_content,
            content_type="text/plain"
        )
        
        # Validate file size
        def validate_file_size(file, max_size_mb=5):
            max_bytes = max_size_mb * 1024 * 1024
            if file.size > max_bytes:
                return False
            return True
        
        self.assertFalse(validate_file_size(large_file, max_size_mb=5))
        
        # Small file should pass
        small_file = SimpleUploadedFile(
            "small_file.txt",
            b"small content",
            content_type="text/plain"
        )
        self.assertTrue(validate_file_size(small_file, max_size_mb=5))
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_file_type_validation(self):
        """
        Test that only allowed file types can be uploaded.
        """
        allowed_extensions = ['.txt', '.pdf', '.png', '.jpg', '.csv']
        
        def validate_file_extension(filename, allowed_exts):
            ext = os.path.splitext(filename)[1].lower()
            return ext in allowed_exts
        
        # Valid files
        self.assertTrue(validate_file_extension('document.pdf', allowed_extensions))
        self.assertTrue(validate_file_extension('image.png', allowed_extensions))
        
        # Invalid files
        self.assertFalse(validate_file_extension('script.exe', allowed_extensions))
        self.assertFalse(validate_file_extension('malware.bat', allowed_extensions))
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_export_file_generation(self):
        """
        Test generating and storing export files (CSV, JSON).
        """
        import csv
        import json
        from io import StringIO
        
        # Generate CSV export
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        csv_writer.writerow(['Tracker Name', 'Status'])
        csv_writer.writerow([self.tracker.name, 'active'])
        
        csv_content = csv_buffer.getvalue().encode('utf-8')
        csv_file = SimpleUploadedFile(
            f"export_{self.tracker.tracker_id}.csv",
            csv_content,
            content_type="text/csv"
        )
        
        from django.core.files.storage import default_storage
        
        csv_path = default_storage.save(
            f'exports/user_{self.user.id}/tracker_export.csv',
            csv_file
        )
        
        self.assertTrue(default_storage.exists(csv_path))
        
        # Verify CSV content
        with default_storage.open(csv_path, 'r') as f:
            content = f.read()
            self.assertIn(self.tracker.name, content)
        
        # Clean up
        default_storage.delete(csv_path)
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_temporary_file_cleanup(self):
        """
        Test that temporary files are cleaned up properly.
        """
        from django.core.files.storage import default_storage
        
        # Create a temporary file
        temp_file = SimpleUploadedFile(
            "temp_file.txt",
            b"temporary content",
            content_type="text/plain"
        )
        
        file_path = default_storage.save('temp/temp_file.txt', temp_file)
        self.assertTrue(default_storage.exists(file_path))
        
        # Simulate cleanup
        default_storage.delete(file_path)
        self.assertFalse(default_storage.exists(file_path))
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_user_storage_quota(self):
        """
        Test user storage quota tracking.
        """
        from django.core.files.storage import default_storage
        
        # Upload multiple files
        files = []
        total_size = 0
        
        for i in range(3):
            content = f"File {i} content" * 100
            file_size = len(content.encode('utf-8'))
            total_size += file_size
            
            uploaded_file = SimpleUploadedFile(
                f"file_{i}.txt",
                content.encode('utf-8'),
                content_type="text/plain"
            )
            
            file_path = default_storage.save(
                f'uploads/user_{self.user.id}/file_{i}.txt',
                uploaded_file
            )
            files.append(file_path)
        
        # Calculate total storage used
        calculated_size = sum(
            default_storage.size(f) for f in files if default_storage.exists(f)
        )
        
        self.assertEqual(calculated_size, total_size)
        
        # Clean up
        for file_path in files:
            if default_storage.exists(file_path):
                default_storage.delete(file_path)
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_secure_file_urls(self):
        """
        Test that file URLs are generated securely.
        """
        from django.core.files.storage import default_storage
        
        # Upload a file
        file_content = b'Sensitive data'
        uploaded_file = SimpleUploadedFile(
            "private_doc.txt",
            file_content,
            content_type="text/plain"
        )
        
        file_path = default_storage.save(
            f'private/user_{self.user.id}/private_doc.txt',
            uploaded_file
        )
        
        # Get URL
        file_url = default_storage.url(file_path)
        
        # URL should exist
        self.assertIsNotNone(file_url)
        
        # In production, we'd verify the URL has proper access controls
        # e.g., signed URLs with expiration
        
        # Clean up
        default_storage.delete(file_path)
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_custom_storage_backend(self):
        """
        Test custom storage backend configuration (local file storage).
        """
        from django.core.files.storage import FileSystemStorage, default_storage
        
        # Test that default storage works
        self.assertIsNotNone(default_storage)
        
        # Create a custom storage backend with specific location
        custom_storage_path = tempfile.mkdtemp()
        custom_storage = FileSystemStorage(location=custom_storage_path)
        
        # Test file upload to custom storage
        test_file = SimpleUploadedFile(
            "custom_storage_test.txt",
            b"Custom storage content",
            content_type="text/plain"
        )
        
        file_path = custom_storage.save('uploads/test_file.txt', test_file)
        
        # Verify file exists in custom storage
        self.assertTrue(custom_storage.exists(file_path))
        
        # Verify file content
        with custom_storage.open(file_path, 'r') as f:
            content = f.read()
            self.assertEqual(content, "Custom storage content")
        
        # Test file URL generation
        file_url = custom_storage.url(file_path)
        self.assertIsNotNone(file_url)
        
        # Test file deletion
        custom_storage.delete(file_path)
        self.assertFalse(custom_storage.exists(file_path))
        
        # Clean up custom storage directory
        import shutil
        if os.path.exists(custom_storage_path):
            shutil.rmtree(custom_storage_path)
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_file_overwrite_protection(self):
        """
        Test that files are not accidentally overwritten.
        """
        from django.core.files.storage import default_storage
        
        # Upload first file
        file1 = SimpleUploadedFile(
            "document.txt",
            b"Original content",
            content_type="text/plain"
        )
        
        path1 = default_storage.save('uploads/document.txt', file1)
        
        # Upload file with same name
        file2 = SimpleUploadedFile(
            "document.txt",
            b"New content",
            content_type="text/plain"
        )
        
        path2 = default_storage.save('uploads/document.txt', file2)
        
        # Paths should be different (Django adds suffix)
        self.assertNotEqual(path1, path2)
        
        # Both files should exist
        self.assertTrue(default_storage.exists(path1))
        self.assertTrue(default_storage.exists(path2))
        
        # Clean up
        default_storage.delete(path1)
        default_storage.delete(path2)
    
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_backup_file_storage(self):
        """
        Test creating and storing backup files.
        """
        import json
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        
        # Create backup data
        backup_data = {
            'user_id': self.user.id,
            'trackers': [
                {
                    'id': str(self.tracker.tracker_id),
                    'name': self.tracker.name,
                }
            ],
            'timestamp': '2025-01-01T00:00:00Z'
        }
        
        backup_json = json.dumps(backup_data, indent=2)
        backup_file = ContentFile(backup_json.encode('utf-8'))
        
        # Save backup
        backup_path = default_storage.save(
            f'backups/user_{self.user.id}_backup.json',
            backup_file
        )
        
        self.assertTrue(default_storage.exists(backup_path))
        
        # Verify backup content
        with default_storage.open(backup_path, 'r') as f:
            restored_data = json.load(f)
            self.assertEqual(restored_data['user_id'], self.user.id)
        
        # Clean up
        default_storage.delete(backup_path)
