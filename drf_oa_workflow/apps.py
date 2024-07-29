from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class OaWorkflowApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "drf_oa_workflow"
    verbose_name = _("OA流程模块")

    def ready(self):
        from django.conf import settings

        from .settings import DEFAULT_SYNC_OA_USER_MODEL
        from .settings import SETTING_PREFIX
        from .settings import SYSTEM_IDENTIFIER_KEY
        from .settings import api_settings

        if not hasattr(settings, "SYNC_OA_USER_MODEL"):
            settings.SYNC_OA_USER_MODEL = DEFAULT_SYNC_OA_USER_MODEL

        if not api_settings.SYSTEM_IDENTIFIER:
            raise ValueError(
                "若要使用drf-oa-workflow，"
                "请先在django settings中给本系统设置一个唯一标识:"
                f"\n{SETTING_PREFIX} = {'{'}"
                f'\n    "{SYSTEM_IDENTIFIER_KEY}": "xxxxx",'
                "\n    ..."
                "\n}"
            )
