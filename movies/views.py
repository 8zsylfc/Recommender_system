from __future__ import annotations

import random

from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.db.models import Avg, Q
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from movies.crawler import crawl_movies
from movies.forms import CrawlForm, RatingForm
from movies.models import Movie, Rating
from movies.recommender.cf import find_similar_users
from movies.recommender.service import recommend_movies_for_user


def is_admin(user):
    return user.is_authenticated and user.is_staff


def home(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    random_mode = request.GET.get("random") == "1"
    
    movies = Movie.objects.all()
    if q:
        if q.isdigit():
            movies = movies.filter(Q(title__icontains=q) | Q(year=int(q)))
        else:
            movies = movies.filter(title__icontains=q)
    
    if random_mode:
        # 随机模式：先随机排序，再让有海报的排在前面
        movies = movies.order_by('?')[:50]
        # 转换为列表后按海报存在性排序（保持随机顺序的基础上，有海报的优先）
        movies_list = list(movies)
        movies_list.sort(key=lambda m: (not m.poster_url, random.random()))
        movies = movies_list
    else:
        # 有海报的优先展示，然后按创建时间倒序
        movies = movies.order_by("-poster_url", "-created_at")[:50]
    
    return render(request, "home.html", {"movies": movies, "q": q, "random_mode": random_mode})


@login_required
@user_passes_test(is_admin)
def crawl(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = CrawlForm(request.POST)
        if form.is_valid():
            url = form.cleaned_data["url"]
            limit = int(form.cleaned_data["limit"])
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
            return render(
                request,
                "crawl.html",
                {"form": form, "items": items, "created": created, "source_url": url},
            )
    else:
        form = CrawlForm()
    return render(request, "crawl.html", {"form": form})


def movie_detail(request: HttpRequest, movie_id: int) -> HttpResponse:
    movie = get_object_or_404(Movie, id=movie_id)
    avg_score = Rating.objects.filter(movie_id=movie.id).aggregate(avg=Avg("score"))["avg"]
    user_rating = None
    if request.user.is_authenticated:
        user_rating = Rating.objects.filter(user_id=request.user.id, movie_id=movie.id).first()

    if request.method == "POST":
        if not request.user.is_authenticated:
            return redirect("login")
        form = RatingForm(request.POST)
        if form.is_valid():
            score = int(form.cleaned_data["score"])
            Rating.objects.update_or_create(
                user_id=request.user.id, movie_id=movie.id, defaults={"score": score}
            )
            return redirect("movie_detail", movie_id=movie.id)
    else:
        form = RatingForm(initial={"score": user_rating.score if user_rating else None})

    return render(
        request,
        "movie_detail.html",
        {"movie": movie, "avg_score": avg_score, "user_rating": user_rating, "form": form},
    )


@login_required
def recommendations(request: HttpRequest) -> HttpResponse:
    method = (request.GET.get("method") or "mf").strip().lower()
    if method not in ("mf", "cf"):
        method = "mf"
    movies = recommend_movies_for_user(request.user, method=method, top_n=12)
    return render(request, "recommendations.html", {"movies": movies, "method": method})


@login_required
def my_ratings(request: HttpRequest) -> HttpResponse:
    score_filter = request.GET.get("score")
    ratings_qs = Rating.objects.filter(user=request.user).select_related("movie").order_by("-updated_at")
    if score_filter and score_filter.isdigit():
        score_filter = int(score_filter)
        ratings_qs = ratings_qs.filter(score=score_filter)
    else:
        score_filter = None
    return render(request, "my_ratings.html", {"ratings": ratings_qs, "score_filter": score_filter})


@login_required
def similar_users(request: HttpRequest) -> HttpResponse:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    rating_rows = list(Rating.objects.values_list("user_id", "movie_id", "score"))
    similar = find_similar_users(
        user_id=int(request.user.id),
        rating_rows=[(int(u), int(m), float(s)) for (u, m, s) in rating_rows],
        top_n=10,
        min_common=2,
    )
    user_ids = [s.user_id for s in similar]
    users_by_id = {u.id: u for u in User.objects.filter(id__in=user_ids)}
    similar_with_users = []
    for s in similar:
        if s.user_id in users_by_id:
            similar_with_users.append({
                "user": users_by_id[s.user_id],
                "similarity": s.similarity,
                "common_movies": s.common_movies,
            })
    return render(request, "similar_users.html", {"similar_users": similar_with_users})


@login_required
def common_ratings(request: HttpRequest, user_id: int) -> HttpResponse:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    target_user = get_object_or_404(User, id=user_id)
    
    my_ratings = {
        r.movie_id: r.score
        for r in Rating.objects.filter(user=request.user).select_related("movie")
    }
    target_ratings = {
        r.movie_id: r.score
        for r in Rating.objects.filter(user_id=user_id).select_related("movie")
    }
    
    common_movie_ids = set(my_ratings.keys()) & set(target_ratings.keys())
    
    movies = Movie.objects.filter(id__in=common_movie_ids)
    movies_by_id = {m.id: m for m in movies}
    
    common_ratings_list = []
    for movie_id in common_movie_ids:
        if movie_id in movies_by_id:
            common_ratings_list.append({
                "movie_id": movie_id,
                "movie_title": movies_by_id[movie_id].title,
                "movie_year": movies_by_id[movie_id].year,
                "movie_poster": movies_by_id[movie_id].poster_url,
                "my_score": my_ratings[movie_id],
                "target_score": target_ratings[movie_id],
            })
    
    common_ratings_list.sort(key=lambda x: abs(x["my_score"] - x["target_score"]))
    
    return JsonResponse({
        "username": target_user.username,
        "common_ratings": common_ratings_list,
    })


def login_view(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = authenticate(
                request,
                username=form.cleaned_data.get("username"),
                password=form.cleaned_data.get("password"),
            )
            if user is not None:
                login(request, user)
                return redirect("home")
    else:
        form = AuthenticationForm(request)
    return render(request, "login.html", {"form": form})


def logout_view(request: HttpRequest) -> HttpResponse:
    logout(request)
    return redirect("home")


def register(request: HttpRequest) -> HttpResponse:
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("home")
    else:
        form = UserCreationForm()
    return render(request, "register.html", {"form": form})


@login_required
@user_passes_test(is_admin)
def admin_dashboard(request: HttpRequest) -> HttpResponse:
    from django.contrib.auth import get_user_model
    from movies.recommender.model_storage import get_model_meta, model_exists
    
    User = get_user_model()
    
    total_users = User.objects.count()
    total_movies = Movie.objects.count()
    total_ratings = Rating.objects.count()
    model_meta = get_model_meta()
    has_model = model_exists()
    
    return render(request, "admin/dashboard.html", {
        "total_users": total_users,
        "total_movies": total_movies,
        "total_ratings": total_ratings,
        "model_meta": model_meta,
        "has_model": has_model,
    })


@login_required
@user_passes_test(is_admin)
def admin_all_ratings(request: HttpRequest) -> HttpResponse:
    from django.contrib.auth import get_user_model
    User = get_user_model()
    
    user_filter = request.GET.get("user")
    movie_filter = request.GET.get("movie")
    score_filter = request.GET.get("score")
    
    ratings_qs = Rating.objects.select_related("user", "movie").order_by("-updated_at")
    
    if user_filter:
        ratings_qs = ratings_qs.filter(user__username__icontains=user_filter)
    if movie_filter:
        ratings_qs = ratings_qs.filter(movie__title__icontains=movie_filter)
    if score_filter and score_filter.isdigit():
        ratings_qs = ratings_qs.filter(score=int(score_filter))
    
    ratings_qs = ratings_qs[:200]
    
    return render(request, "admin/all_ratings.html", {
        "ratings": ratings_qs,
        "user_filter": user_filter or "",
        "movie_filter": movie_filter or "",
        "score_filter": score_filter or "",
    })


@login_required
@user_passes_test(is_admin)
def admin_all_movies(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    year_filter = request.GET.get("year")
    
    movies_qs = Movie.objects.all()
    
    if q:
        movies_qs = movies_qs.filter(title__icontains=q)
    if year_filter and year_filter.isdigit():
        movies_qs = movies_qs.filter(year=int(year_filter))
    
    movies_qs = movies_qs.annotate(avg_score=Avg("rating__score")).order_by("-created_at")
    
    return render(request, "admin/all_movies.html", {
        "movies": movies_qs,
        "q": q,
        "year_filter": year_filter or "",
    })
