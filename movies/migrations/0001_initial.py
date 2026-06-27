from __future__ import annotations

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Movie",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(db_index=True, max_length=255)),
                ("year", models.PositiveIntegerField(blank=True, null=True)),
                ("detail_url", models.URLField(blank=True, default="")),
                ("poster_url", models.URLField(blank=True, default="")),
                ("source_url", models.URLField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"unique_together": {("title", "year", "detail_url")}},
        ),
        migrations.CreateModel(
            name="Rating",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveSmallIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("movie", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="movies.movie")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={"unique_together": {("user", "movie")}},
        ),
        migrations.AddIndex(
            model_name="rating",
            index=models.Index(fields=["user", "movie"], name="rating_user_movie_idx"),
        ),
    ]

