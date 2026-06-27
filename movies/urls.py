from django.urls import path

from . import views

urlpatterns = [
    path("", views.home, name="home"),
    path("crawl/", views.crawl, name="crawl"),
    path("movies/<int:movie_id>/", views.movie_detail, name="movie_detail"),
    path("recommendations/", views.recommendations, name="recommendations"),
    path("my-ratings/", views.my_ratings, name="my_ratings"),
    path("similar-users/", views.similar_users, name="similar_users"),
    path("common-ratings/<int:user_id>/", views.common_ratings, name="common_ratings"),
    path("manage/dashboard/", views.admin_dashboard, name="admin_dashboard"),
    path("manage/ratings/", views.admin_all_ratings, name="admin_all_ratings"),
    path("manage/movies/", views.admin_all_movies, name="admin_all_movies"),
    path("accounts/login/", views.login_view, name="login"),
    path("accounts/logout/", views.logout_view, name="logout"),
    path("accounts/register/", views.register, name="register"),
]

