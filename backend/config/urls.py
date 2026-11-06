"""项目路由。

    /admin/             Django 后台（菜品维护 / 举报审核 / 禁言解禁）
    /api/...            业务接口（见 core/urls.py）
    /api/schema/        OpenAPI 3 schema
    /api/docs/          Swagger UI（drf-spectacular）
    /media/...          开发环境由 Django 直接托管上传的图片（生产交给 Nginx）
"""
from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

admin.site.site_header = "今天吃什么 · 后台管理"
admin.site.site_title = "今天吃什么"
admin.site.index_title = "校园随机推荐系统"

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema", permission_classes=[]),
        name="swagger-ui",
    ),
    path("api/", include("core.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
