from __future__ import annotations

from django.contrib.auth.models import AbstractBaseUser
from django.db.models import Avg

from movies.models import Movie, Rating
from movies.recommender.cf import user_based_cf_recommendations
from movies.recommender.mf import mf_recommendations_for_user, train_mf_sgd
from movies.recommender.model_storage import load_model


def top_movies_fallback(top_n: int = 10) -> list[Movie]:
    movie_ids = list(
        Rating.objects.values("movie_id")
        .annotate(avg_score=Avg("score"))
        .order_by("-avg_score")
        .values_list("movie_id", flat=True)[:top_n]
    )
    movies_by_id = {m.id: m for m in Movie.objects.filter(id__in=movie_ids)}
    return [movies_by_id[mid] for mid in movie_ids if mid in movies_by_id]


def recommend_movies_for_user(user: AbstractBaseUser, method: str = "mf", top_n: int = 10) -> list[Movie]:
    all_movie_ids = list(Movie.objects.values_list("id", flat=True))
    rating_rows = list(Rating.objects.values_list("user_id", "movie_id", "score"))
    rated_movie_ids = set(Rating.objects.filter(user_id=user.id).values_list("movie_id", flat=True))

    if not rating_rows or not all_movie_ids:
        return []

    rec_ids: list[int] = []
    if method == "cf":
        res = user_based_cf_recommendations(
            user_id=int(user.id),
            rating_rows=[(int(u), int(m), float(s)) for (u, m, s) in rating_rows],
            all_movie_ids=[int(mid) for mid in all_movie_ids],
            top_n=top_n,
        )
        rec_ids = res.movie_ids
    else:
        model = load_model()
        
        if model is None:
            model = train_mf_sgd(
                rating_rows=[(int(u), int(m), float(s)) for (u, m, s) in rating_rows],
                k=20,
                steps=35,
                lr=0.01,
                reg=0.02,
            )
        
        if model is not None:
            preds = mf_recommendations_for_user(
                model=model,
                user_id=int(user.id),
                rated_movie_ids={int(x) for x in rated_movie_ids},
                top_n=top_n,
            )
            rec_ids = [mid for (mid, _) in preds]

    if not rec_ids:
        return top_movies_fallback(top_n=top_n)

    movies_by_id = {m.id: m for m in Movie.objects.filter(id__in=rec_ids)}
    movies = [movies_by_id[mid] for mid in rec_ids if mid in movies_by_id]
    movies.sort(key=lambda m: not bool(m.poster_url))
    return movies
