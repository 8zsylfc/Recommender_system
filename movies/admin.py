from django.contrib import admin

from .models import Movie, Rating


@admin.register(Movie)
class MovieAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "year", "detail_url", "created_at")
    search_fields = ("title",)
    list_filter = ("year",)


@admin.register(Rating)
class RatingAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "movie", "score", "updated_at")
    list_filter = ("score",)
    search_fields = ("user__username", "movie__title")

