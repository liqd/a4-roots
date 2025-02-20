# Generated by Django 4.2.18 on 2025-02-19 18:35

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("wagtailcore", "0094_alter_page_locale"),
        ("learning_nuggets", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="LearnCenterPage",
            fields=[
                (
                    "page_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="wagtailcore.page",
                    ),
                ),
            ],
            options={
                "verbose_name": "Learn Center",
            },
            bases=("wagtailcore.page",),
        ),
        migrations.AlterModelOptions(
            name="learningcategory",
            options={
                "ordering": ["order", "name"],
                "verbose_name": "Learning Category",
                "verbose_name_plural": "Learning Categories",
            },
        ),
        migrations.AlterModelOptions(
            name="learningnuggetpage",
            options={"verbose_name": "Learning Nugget"},
        ),
        migrations.AddField(
            model_name="learningcategory",
            name="order",
            field=models.IntegerField(default=0),
        ),
    ]
