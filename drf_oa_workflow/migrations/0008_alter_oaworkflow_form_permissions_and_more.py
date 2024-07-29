# Generated by Django 5.0.3 on 2024-07-26 16:39

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('drf_oa_workflow', '0007_oaworkflowtype_oaworkflow_oaworkflownode_and_more'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AlterField(
            model_name='oaworkflow',
            name='form_permissions',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='节点表单权限'),
        ),
        migrations.AlterField(
            model_name='oaworkflownode',
            name='form_permissions',
            field=models.JSONField(blank=True, default=dict, null=True, verbose_name='节点表单权限'),
        ),
        migrations.CreateModel(
            name='WorkflowApproval',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.SmallIntegerField(choices=[(0, '无效'), (1, '有效')], default=1, verbose_name='状态')),
                ('deleted_at', models.DateTimeField(blank=True, editable=False, null=True, verbose_name='删除时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='新增时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('code', models.CharField(blank=True, default='', max_length=128, verbose_name='流程编号')),
                ('title', models.CharField(blank=True, default='', max_length=256, verbose_name='流程标题')),
                ('workflow_request_id', models.CharField(max_length=128, verbose_name='OA流程实例ID')),
                ('object_id', models.PositiveIntegerField(null=True, verbose_name='业务数据ID')),
                ('approval_status', models.SmallIntegerField(choices=[(1, '审批中'), (2, '审批通过'), (3, '审批拒绝')], default=1, verbose_name='审批状态')),
                ('action', models.SmallIntegerField(choices=[(1, '新增'), (2, '变更'), (3, '启用'), (4, '停用'), (5, '作废')], default=1, verbose_name='触发类型')),
                ('archived_at', models.DateTimeField(blank=True, null=True, verbose_name='流程结束时间')),
                ('front_form_info', models.JSONField(default=dict, null=True, verbose_name='流程表单信息(前端)')),
                ('content_type', models.ForeignKey(null=True, on_delete=django.db.models.deletion.DO_NOTHING, to='contenttypes.contenttype', verbose_name='业务类型')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='修改人')),
                ('workflow', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='drf_oa_workflow.oaworkflow', verbose_name='流程')),
            ],
            options={
                'verbose_name': '流程审核',
                'verbose_name_plural': '流程审核',
                'db_table': 'workflow_approval',
            },
        ),
        migrations.CreateModel(
            name='WorkflowApprovalOperation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', models.SmallIntegerField(choices=[(0, '无效'), (1, '有效')], default=1, verbose_name='状态')),
                ('deleted_at', models.DateTimeField(blank=True, editable=False, null=True, verbose_name='删除时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='新增时间')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='更新时间')),
                ('oa_node_id', models.IntegerField(verbose_name='OA流程节点ID')),
                ('operation_type', models.SmallIntegerField(choices=[(0, '不走流程提交'), (1, '提交'), (2, '批准'), (3, '保存'), (4, '转发'), (5, '转发收回'), (6, '转办'), (7, '批注'), (8, '退回'), (9, '撤回'), (10, '意见征询'), (11, '重新提交'), (12, '强制收回'), (13, '删除流程'), (50, '终止')], verbose_name='操作类型')),
                ('remark', models.TextField(blank=True, default='', verbose_name='意见')),
                ('oa_log_id', models.IntegerField(null=True, verbose_name='OA流程审批记录ID')),
                ('approval', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='operations', to='drf_oa_workflow.workflowapproval', verbose_name='流程记录')),
                ('created_by', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='创建人')),
                ('updated_by', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL, verbose_name='修改人')),
            ],
            options={
                'verbose_name': '流程操作记录',
                'verbose_name_plural': '流程操作记录',
                'db_table': 'workflow_approval_operation',
            },
        ),
    ]
