from __future__ import annotations

from django.core.management.base import BaseCommand

from movies.crawler import crawl_movies
from movies.models import Movie


class Command(BaseCommand):
    help = "Crawl a movie list page and import movies into DB."

    def add_arguments(self, parser):
        parser.add_argument("url", type=str)
        parser.add_argument("--limit", type=int, default=50)

    def handle(self, *args, **options):
        url = options["url"]
        limit = int(options["limit"])
        items = crawl_movies(url, limit=limit)
        created = 0
        for item in items:
            _, is_created = Movie.objects.get_or_create(
                title=item.title,
                year=item.year,
                detail_url=item.detail_url,
                defaults={"poster_url": item.poster_url, "source_url": url},
            )
            created += int(is_created)
        self.stdout.write(self.style.SUCCESS(f"Imported {len(items)} items, created {created} new movies."))

