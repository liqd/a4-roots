from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0089_log_entry_data_json_null_to_object"),
        ("a4_candy_cms_settings", "0008_alter_organisationsettings_platform_name"),
    ]

    operations = [
        migrations.AddField(
            model_name="importantpages",
            name="ai_explanation",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="important_page_ai_explanation",
                to="wagtailcore.page",
            ),
        ),
    ]

