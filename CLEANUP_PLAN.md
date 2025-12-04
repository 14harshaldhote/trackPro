# Cleanup Plan - Files to Remove

## Files to Remove (Safe)

### In `core/` - Legacy Files Now in New Structure:
- [x] `constants.py` - Moved to `utils/constants.py`  
- [x] `time_utils.py` - Moved to `utils/time_utils.py`
- [x] `metric_helpers.py` - Moved to `helpers/metric_helpers.py`
- [x] `nlp_utils.py` - Moved to `helpers/nlp_helpers.py`
- [x] `crud.py` - Moved to `repositories/base_repository.py`
- [x] `services.py` - Moved to `services/instance_service.py`
- [x] `scheduler.py` - Moved to `integrations/scheduler.py`
- [x] `integrity.py` - Moved to `integrations/integrity.py`
- [x] `exports.py` - Moved to `exports/exporter.py`

### In `core/` - Truly Legacy/Unused:
- [x] `db_engine.py` - Old Excel-based DB (replaced by MySQL)
- [x] `schemas.py` - Not needed with Django ORM
- [x] `_compat.py` - Temporary compatibility file (not needed)

### In `root/` - Test/Temporary Files:
- [x] `cleanup_data.py` - One-time script
- [x] `test_mysql.py` - Test script
- [x] `verify_tracker.py` - Test script
- [x] `create_database.sql` - Database already created

## Files to KEEP

### Essential:
- ✅ `core/views.py` - Main views (working)
- ✅ `core/_analytics_old.py` - Analytics (working via package)
- ✅ `core/models.py` - Database models
- ✅ `core/admin.py` - Admin config
- ✅ `core/urls.py` - URL routing
- ✅ `core/apps.py` - App config
- ✅ `core/templates.py` - Template management
- ✅ All new package folders

### Documentation:
- ✅ `AUTHENTICATION_SETUP.md`
- ✅ `BUGFIXES_SUMMARY.md`
- ✅ `MYSQL_MIGRATION_SUMMARY.md`
- ✅ `REFACTORING_SUMMARY.md`

### Essential Folders:
- ✅ `tackerIOS/` - Keep (as requested)
- ✅ `api/` - API functionality
- ✅ `trackerWeb/` - Django project
- ✅ `core/` - Main app

---

**Total to Remove:** 16 files
**Safety:** High - all are duplicates or test files
