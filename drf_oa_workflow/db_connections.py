import oracledb

from .settings import api_settings

# from django.conf import settings


try:
    oracledb.init_oracle_client()
except Exception as e:  # noqa
    pass


def get_oa_oracle_connection():
    """
    OA 数据库连接
    """
    return oracledb.connect(
        user=api_settings.OA_DB_USER,
        password=api_settings.OA_DB_PASSWORD,
        host=api_settings.OA_DB_HOST,
        port=api_settings.OA_DB_PORT,
        service_name=api_settings.OA_DB_SERVER_NAME,
    )
