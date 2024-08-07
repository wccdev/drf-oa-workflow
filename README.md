# drf-oa-workflow


[![pypi](https://img.shields.io/pypi/v/drf-oa-workflow.svg)](https://pypi.wochacha.cn/simple/drf-oa-workflow/)
[![python](https://img.shields.io/pypi/pyversions/drf-oa-workflow.svg)](https://pypi.wochacha.cn/simple/drf-oa-workflow/)
[![Build Status](https://github.com/wccdev/drf-oa-workflow/actions/workflows/python-publish.yml/badge.svg)](https://github.com/wccdev/drf-oa-workflow/actions/workflows/python-publish.yml)
[![codecov](https://codecov.io/gh/wccdev/drf-oa-workflow/branch/main/graphs/badge.svg)](https://codecov.io/github/wccdev/drf-oa-workflow)



Skeleton project created by Cookiecutter PyPackage


* Documentation: <https://wccdev.github.io/drf-oa-workflow>
* GitHub: <https://github.com/wccdev/drf-oa-workflow>
* PyPI: <https://pypi.wochacha.cn/simple/drf-oa-workflow/>
* Free software: MIT


## Installation
- 使用 pip:
```bash
pip install drf-oa-workflow

```
- 使用 poetry:
```bash
poetry add drf-oa-workflow
```

## Usage
- 在 django setting中注册本应用 `'drf_oa_workflow'`, 添加相关的配置
```python
INSTALLED_APPS = [
    "django.contrib.admin",
    ...,
    "django.contrib.auth",
    "xxxx.users",  # （项目指定AUTH_USER_MODEL的APP, 如果有）
    ...,
    "drf_oa_workflow",
]

# 由oa提供
DRF_OA_WORKFLOW = {
    # 项目OA需要的链接的数据别名
    "OA_DATABASE_ALIAS": "oa",

    # oa接口应用id
    "APP_ID": "xxxx",
    # oa接口应用secret
    "APP_RAW_SECRET": "xxxx-xxx-xxxx",
    # oa接口应用spk
    "APP_SPK": "xxxxxxxxxx",
    # oa接口服务地址(域名)
    "OA_HOST": "https://oa.demo.com",

    # -----以下可选----- #
    # requests包 Requests HTTP Library, 可使用自定义封装请求日志的requests代替
    "REQUESTS_LIBRARY": "requests",
}
```

### ~~1.全局使用~~(暂不推荐)
- 在 django setting中注册中间件 `'drf_oa_workflow.middleware.OaWFRequestMiddleware'`:
```python
MIDDLEWARE = [
    ...,
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    ...,
    "drf_oa_workflow.middleware.OaWFRequestMiddleware",
]
```


### 2.局部使用
- 在需要使用的视图上继承
```python
from drf_oa_workflow.mixin import OaWFApiViewMixin
from rest_framework.views import APIView


class YourViewSet(OaWFApiViewMixin, APIView):
    ...
```

#### 注意!!!
- 上述两种使用方法需要项目的`AUTH_USER_MODEL`提供属性`oa_user_id`

- `oa_user_id`为当前登入用户request.user在oa系统中对应的user_id
```python
from django.db.models import Model
class User(Model):
    ...

    class Meta:
        ...

    @property
    def oa_user_id(self):\
        # TODO 获取对应oa用户逻辑
        if hasattr(self, "oauserinfo"):
            return self.oauserinfo.user_id
        # 或者自定义逻辑
        oa_user_id = "1"
        return oa_user_id
```

- 完成上述步骤，即可在视图中使用
```python
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import action


# from drf_oa_workflow.mixin import OaWFApiViewMixin
# class YourViewSet(OaWFApiViewMixin, APIView):  # 未注册中间件方式
class YourViewSet(APIView):
    @action(detail=False)
    def test(self, request, *args, **kwargs):
        workflow = request.oa_wf_api
        # 待办流程
        workflow.get_todo_list(workflow_id=12345, page=1, page_size=10)
        # 已办流程
        workflow.get_handled_list(workflow_id=12345, page=1, page_size=10)
        # 可创建流程
        workflow.get_create_list()
        # ...
        return Response()
```

### 3.使用类
```python
from drf_oa_workflow.utils import OaWorkFlow

workflow = OaWorkFlow()
# 调用前必须使用register_user方法
# 注册需要调用流程接口的oa用户id
oa_user_id = "TODO"  # TODO
workflow.register_user(oa_user_id)

# 待办流程
workflow.get_todo_list(workflow_id=12345, page=1, page_size=10)
# 已办流程
workflow.get_handled_list(workflow_id=12345, page=1, page_size=10)
# 可创建流程
workflow.get_create_list()
# ...
```

### 4.使用现成接口 (TODO, 开发中)
```python
from django.urls import include, path

urlpatterns = [
    ...,
    path("api/", include("drf_oa_workflow.urls"))
]
```

### 5.同步OA账号到当前项目
- 同步数据前需要在项目设置DRF_OA_WORKFLOW中配置OA数据库连接以及指定用户表信息
#### 5.1 设置保存数据的表
- 5.1.1 使用drf-oa-workflow内置表
drf_oa_workflow已经设置了相关表，可执直接执行迁移命令生成
详情请查看drf_oa_workflow.models.OaUserInfo
```python
from django.contrib.auth import get_user_model
from django.db import models

UserModel = get_user_model()


class OaUserInfo(models.Model):
    user_id = models.IntegerField(unique=True, primary_key=True, verbose_name="OA用户数据ID")
    staff_code = models.OneToOneField(
        UserModel,
        on_delete=models.DO_NOTHING,
        to_field=UserModel.USERNAME_FIELD,
        db_column="staff_code",
        db_constraint=False,
        verbose_name="OA用户工号",
    )
    dept_id = models.IntegerField(null=True, verbose_name="OA用户部门ID")
```
```bash
python manage.py migrate drf_oa_workflow

```

- 5.1.2 使用你自己的表
```python
from django.db.models import CharField
from drf_oa_workflow.models import AbstractOaUserInfo


class YouOAUserModel(AbstractOaUserInfo):
    extra_field1 = CharField(max_length=20, blank=True, verbose_name="额外字段1")
    extra_field2 = CharField(max_length=20, blank=True, verbose_name="额外字段2")

    class Meta:
        abstract = True
        verbose_name = verbose_name_plural = "OA用户信息"
        db_table = "xxxxx"
```

#### 注意!!!
如果项目使用5.1.2方式中的OA用户模型，请在项目配置中配置SYNC_OA_USER_MODEL变量
```python
# 指定项目使用的OA用户模型： SYNC_OA_USER_MODEL = "模型所属APP.模型类名"
# 如果不配置，项目默认OA用户模型仍为drf_oa_workflow.models.OaUserInfo
# 参考Django AUTH_USER_MODEL变量
SYNC_OA_USER_MODEL = "xxxx.YouOAUserModel"
```

#### 5.2 在admin后台添加drf_oa_workflow中的定时任务
需要celery以及django-celery-beat
![img.png](static/sync_user_task.png)

#### 5.3 项目User获取同步到的oa用户信息
```python
from django.contrib.auth import get_user_model

user = get_user_model().objects.select_related("oauserinfo").first()
if hasattr(user, "oauserinfo"):
    print(user.oauserinfo.user_id)
    print(user.oauserinfo.staff_code)
    print(user.oauserinfo.staff_code_id)
    print(user.oauserinfo.dept_id)
```
