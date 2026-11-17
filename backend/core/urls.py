"""API 路由：与前端契约（``what2eat/src/api/README.md``）逐条对应。

    POST   /api/auth/register/           注册
    POST   /api/auth/token/              登录，返回 access/refresh
    POST   /api/auth/token/refresh/      刷新
    POST   /api/auth/bind-student/       学号 + 姓名 + 学院 三重核验
    GET    /api/dishes/random/?source=   加权随机（排除最近 4 条打卡）
    GET    /api/dishes/                  分页列表
    POST   /api/checkins/                发布打卡
    GET    /api/checkins/                分页列表
    POST   /api/likes/toggle/            点赞 / 取消
    POST   /api/favorites/toggle/        收藏 / 取消
    GET    /api/favorites/               我的收藏
    POST   /api/reports/                 举报
    POST   /api/votes/                   发起投票
    POST   /api/votes/{id}/cast/         投票（事务 + 唯一约束 + 过半结算）
    GET    /api/votes/                   列表
"""
from django.urls import path

from . import views

app_name = "api"

urlpatterns = [
    # 运维
    path("health/", views.HealthView.as_view(), name="health"),
    # 认证
    path("auth/register/", views.RegisterView.as_view(), name="register"),
    path("auth/token/", views.LoginView.as_view(), name="token"),
    path("auth/token/refresh/", views.TokenRefreshView.as_view(), name="token-refresh"),
    path("auth/bind-student/", views.BindStudentView.as_view(), name="bind-student"),
    # 菜品
    path("dishes/random/", views.RandomDishView.as_view(), name="dish-random"),
    path("dishes/", views.DishListView.as_view(), name="dish-list"),
    # 打卡
    path("checkins/", views.CheckinListCreateView.as_view(), name="checkin-list"),
    # 点赞 / 收藏
    path("likes/toggle/", views.ToggleLikeView.as_view(), name="like-toggle"),
    path("favorites/toggle/", views.ToggleFavoriteView.as_view(), name="favorite-toggle"),
    path("favorites/", views.FavoriteListView.as_view(), name="favorite-list"),
    # 举报
    path("reports/", views.ReportCreateView.as_view(), name="report-create"),
    # 投票
    path("votes/", views.VoteListCreateView.as_view(), name="vote-list"),
    path("votes/<int:pk>/cast/", views.CastVoteView.as_view(), name="vote-cast"),
    path("votes/<int:pk>/review/", views.ReviewVoteView.as_view(), name="vote-review"),
    # 个人板块
    path("recognize/", views.RecognizeView.as_view(), name="recognize"),
    path("preferences/", views.PreferencesView.as_view(), name="preferences"),
]
