from django.db.models import DateTimeField
from django.db.models.expressions import F
from django.db.models.expressions import Func
from django.db.models.expressions import Value
from django.db.models.functions import Concat


class ConvertOADbDatetime(Func):
    """
    处理OA Oracle数据库 时间（字符串）和日期（字符串）字段，输出为DateTime类型
    """

    function = "TO_DATE"
    template = (
        "%(function)s(%(expressions)s, 'YYYY-MM-DD HH24:MI:SS') - INTERVAL '8' HOUR"
    )

    def __init__(
        self,
        date_field,
        time_field,
        *expressions,
        output_field=DateTimeField(),
        **extra,
    ):
        base_expressions = Concat(F(date_field), Value(" "), F(time_field))
        super().__init__(
            base_expressions, *expressions, output_field=output_field, extra=extra
        )
