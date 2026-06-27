from __future__ import annotations

import random

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from movies.models import Movie, Rating


class Command(BaseCommand):
    help = "Generate fake users and random ratings for testing."

    def add_arguments(self, parser):
        parser.add_argument("--users", type=int, default=100, help="Number of users to create")
        parser.add_argument("--min-ratings", type=int, default=5, help="Minimum ratings per user")
        parser.add_argument("--max-ratings", type=int, default=30, help="Maximum ratings per user")

    def handle(self, *args, **options):
        User = get_user_model()
        num_users = options["users"]
        min_ratings = options["min_ratings"]
        max_ratings = options["max_ratings"]

        movies = list(Movie.objects.all())
        if not movies:
            self.stdout.write(self.style.ERROR("No movies found. Please crawl movies first."))
            return

        self.stdout.write(f"Found {len(movies)} movies in database.")

        created_users = 0
        created_ratings = 0

        for i in range(num_users):
            username = f"testuser_{i+1:03d}"
            user, created = User.objects.get_or_create(
                username=username,
                defaults={"email": f"{username}@example.com"},
            )
            if created:
                user.set_password("testpass123")
                user.save()
                created_users += 1

            num_ratings = random.randint(min_ratings, max_ratings)
            sampled_movies = random.sample(movies, min(num_ratings, len(movies)))

            for movie in sampled_movies:
                score = random.choices(
                    population=[1, 2, 3, 4, 5],
                    weights=[5, 10, 20, 35, 30],
                )[0]
                _, rating_created = Rating.objects.get_or_create(
                    user=user,
                    movie=movie,
                    defaults={"score": score},
                )
                if rating_created:
                    created_ratings += 1

            if (i + 1) % 20 == 0:
                self.stdout.write(f"Processed {i + 1}/{num_users} users...")

        self.stdout.write(
            self.style.SUCCESS(
                f"Done! Created {created_users} new users, {created_ratings} new ratings."
            )
        )
