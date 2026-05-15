import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('recommendations', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='RecommendationFeedback',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('run_id', models.UUIDField(blank=True, null=True)),
                ('area_id', models.CharField(default='', max_length=255)),
                ('sector', models.CharField(default='', max_length=50)),
                ('rating', models.IntegerField()),
                ('feedback_text', models.TextField(blank=True, default='')),
                ('helpful_action_indices', models.JSONField(default=list)),
                ('unhelpful_action_indices', models.JSONField(default=list)),
                ('anon_id', models.CharField(max_length=64)),
                ('forwarded_to_n8n', models.BooleanField(default=False)),
                ('submitted_at', models.DateTimeField(auto_now_add=True)),
                ('forwarded_at', models.DateTimeField(blank=True, null=True)),
            ],
            options={
                'db_table': 'recommendation_feedback',
                'indexes': [
                    models.Index(fields=['forwarded_to_n8n', 'submitted_at'],
                                 name='recommendat_forward_idx'),
                    models.Index(fields=['run_id'], name='recommendat_run_idx'),
                ],
            },
        ),
    ]
