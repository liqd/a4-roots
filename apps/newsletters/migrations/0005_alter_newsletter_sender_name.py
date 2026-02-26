from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("a4_candy_newsletters", "0004_alter_newsletter_body"),
    ]

    operations = [
        migrations.AlterField(
            model_name="newsletter",
            name="sender_name",
            field=models.CharField(
                blank=True,
                max_length=254,
                verbose_name="Name",
            ),
        ),
    ]
