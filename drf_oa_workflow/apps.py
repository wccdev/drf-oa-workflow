from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

from .settings import DEFAULT_SYNC_OA_USER_MODEL


class OaWorkflowApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "drf_oa_workflow"
    verbose_name = _("OA流程模块")

    def ready(self):
        from django.conf import settings

        if not hasattr(settings, "SYNC_OA_USER_MODEL"):
            settings.SYNC_OA_USER_MODEL = DEFAULT_SYNC_OA_USER_MODEL
