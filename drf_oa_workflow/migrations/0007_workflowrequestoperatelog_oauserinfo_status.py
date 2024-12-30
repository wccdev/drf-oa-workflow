# Generated by Django 5.1.4 on 2024-12-30 06:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drf_oa_workflow', '0006_workflowtype'),
    ]

    operations = [
        migrations.CreateModel(
            name='WorkflowRequestOperateLog',
            fields=[
                ('ID', models.IntegerField(primary_key=True, serialize=False)),
                ('ISREMARK', models.IntegerField(null=True, verbose_name='操作状态')),
                ('OPERATEDATE', models.CharField(blank=True, max_length=200, verbose_name='操作日期')),
                ('OPERATETIME', models.CharField(blank=True, max_length=200, verbose_name='操作时间')),
                ('OPERATETYPE', models.CharField(blank=True, choices=[('forward', '转发'), ('chuanyue', '传阅'), ('submit', '提交'), ('reject', '退回'), ('intervenor', '干预'), ('trans', '转办'), ('take', '意见征询'), ('takForward', '征询转办'), ('takEnd', '结束征询'), ('forceover', '强制归档'), ('forwardreply', '转发批注'), ('takereply', '意见征询回复'), ('withdraw', '撤回')], max_length=200, verbose_name='操作类型')),
                ('OPERATENAME', models.CharField(blank=True, max_length=200, verbose_name='操作类型中文名称')),
                ('OPERATECODE', models.IntegerField(choices=[(-2, '转发'), (0, '传阅'), (1, '提交'), (2, '退回'), (3, '干预'), (4, '转办'), (5, '意见征询'), (6, '征询转办'), (7, '结束征询'), (9, '强制归档'), (10, '转发批注'), (11, '意见征询回复'), (12, '撤回')], null=True, verbose_name='操作类型代码')),
                ('ISINVALID', models.CharField(blank=True, max_length=20, verbose_name='是否执行了强制收回')),
                ('INVALIDDATE', models.CharField(blank=True, max_length=200, verbose_name='强制收回操作日期')),
                ('INVALIDTIME', models.CharField(blank=True, max_length=200, verbose_name='强制收回操作时间')),
            ],
            options={
                'verbose_name': 'OA流程操作记录日志主表',
                'verbose_name_plural': 'OA流程操作记录日志主表',
                'db_table': 'ECOLOGY"."WORKFLOW_REQUESTOPERATELOG',
                'managed': False,
            },
        ),
        migrations.AddField(
            model_name='oauserinfo',
            name='status',
            field=models.IntegerField(choices=[(0, '试用'), (1, '正式'), (2, '临时'), (3, '试用延期'), (4, '解聘'), (5, '离职'), (6, '退休'), (7, '无效')], null=True, verbose_name='OA用户状态'),
        ),
    ]
