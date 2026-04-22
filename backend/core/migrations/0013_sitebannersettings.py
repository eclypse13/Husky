from django.db import migrations, models


DEFAULT_MESSAGE = (
    "Сайт НКП СХ находится в работе.\n"
    "Публичное открытие будет на Национальной выставке 2026 года."
)


def create_default_banner(apps, schema_editor):
    SiteBannerSettings = apps.get_model("core", "SiteBannerSettings")
    SiteBannerSettings.objects.get_or_create(
        id=1,
        defaults={"is_enabled": True, "message": DEFAULT_MESSAGE},
    )


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0012_workinggroup_alter_boardmember_options_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteBannerSettings",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("is_enabled", models.BooleanField(default=True)),
                ("message", models.TextField(blank=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Site banner settings",
                "verbose_name_plural": "Site banner settings",
            },
        ),
        migrations.RunPython(create_default_banner, migrations.RunPython.noop),
    ]
