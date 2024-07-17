from importlib import import_module

from django.conf import settings
from django.test.signals import setting_changed

SETTING_PREFIX = "DRF_OA_WORKFLOW"

# Django项目OA数据库连接别名
OA_DATABASE_ALIAS = "oa"

DEFAULT_SYNC_OA_USER_MODEL = "drf_oa_workflow.OaUserInfo"

DEFAULTS = {
    # Django settings中OA数据库连接的别名
    "OA_DATABASE_ALIAS": OA_DATABASE_ALIAS,
    # OA开放接口
    "APP_ID": "",
    "APP_RAW_SECRET": "",
    "APP_SPK": "",
    "OA_HOST": "",
    # OA继承统一认证配置
    "OA_SSO_TOKEN_APP_ID": "",
    # requests包
    "REQUESTS_LIBRARY": "requests",
    # DEBUG
    "DEBUG": False,
}


# List of settings that may be in string import notation.
IMPORT_STRINGS = [
    "REQUESTS_LIBRARY",
]


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if val is None:
        return None
    elif isinstance(val, str):  # noqa: RET505
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        return import_module(val)
    except ImportError as e:
        msg = f"Could not import '{val}' for API setting '{setting_name}'. {e.__class__.__name__}: {e}."  # noqa: E501
        raise ImportError(msg)


class APISettings:
    """
    OA流程引擎API调用配置
    """

    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        if user_settings:
            self._user_settings = user_settings
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if not hasattr(self, "_user_settings"):
            self._user_settings = getattr(settings, SETTING_PREFIX, {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError(f"Invalid API setting: '{attr}'")

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, "_user_settings"):
            delattr(self, "_user_settings")


api_settings = APISettings(None, DEFAULTS, IMPORT_STRINGS)


def reload_api_settings(*args, **kwargs):
    setting = kwargs["setting"]
    if setting == SETTING_PREFIX:
        api_settings.reload()


setting_changed.connect(reload_api_settings)
