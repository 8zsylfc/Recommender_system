from __future__ import annotations

from django.conf import settings
from django.db import models


class Movie(models.Model):
    title = models.CharField(max_length=255, db_index=True)
    year = models.PositiveIntegerField(null=True, blank=True)
    detail_url = models.URLField(blank=True, default="")
    poster_url = models.URLField(blank=True, default="")
    source_url = models.URLField(blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("title", "year", "detail_url")

    def __str__(self) -> str:
        return f"{self.title} ({self.year})" if self.year else self.title


class Rating(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    movie = models.ForeignKey(Movie, on_delete=models.CASCADE)
    score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "movie")
        indexes = [models.Index(fields=["user", "movie"])]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.movie_id}={self.score}"

