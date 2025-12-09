from django.apps import AppConfig
import sys


class CoreConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "core"

    def ready(self):
        # Import signals to register them
        # This enables automatic goal updates when tasks change
        try:
            from core.signals import task_signals  # noqa - imports register the signals
        except ImportError:
            pass  # Signals not yet created
        
        # Prevent scheduler from starting twice (reloader)
        if 'runserver' in sys.argv:
            from core.integrations import scheduler
            
            # Note: Commenting out initial check to avoid DB access during app initialization
            # The scheduler will run the check on its first interval instead
            # If you need immediate checking, run: python manage.py check_trackers (custom command)
            
            # try:
            #     services.check_all_trackers()
            # except Exception as e:
            #     print(f"⚠️ Initial tracker check failed: {e}")
                
            scheduler.start_scheduler()
