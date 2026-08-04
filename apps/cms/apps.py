from django.apps import AppConfig


class CmsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.cms"
    verbose_name = "Content Management"

    def ready(self):
        from apps.cms.signals import connect_cms_signals
        connect_cms_signals()
