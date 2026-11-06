"""不依赖 django-cors-headers 的最小 CORS 中间件。

前端是独立的 Vite 站点（:5173），必须跨域访问 :8000。
放行规则来自 settings：``CORS_ALLOWED_ORIGINS`` 白名单，
``CORS_ALLOW_ALL_ORIGINS=True`` 时回显任意 Origin（仅开发环境默认开启）。

预检（OPTIONS + Access-Control-Request-Method）直接回 204，不进 URL 路由，
避免 DRF 因为「OPTIONS 没有权限」返回 401 把浏览器预检卡死。
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponse


class CorsMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        origin = request.META.get("HTTP_ORIGIN", "")
        is_preflight = request.method == "OPTIONS" and bool(
            request.META.get("HTTP_ACCESS_CONTROL_REQUEST_METHOD")
        )

        if is_preflight:
            response = HttpResponse(status=204)
        else:
            response = self.get_response(request)

        if origin and self._allowed(origin):
            response["Access-Control-Allow-Origin"] = origin
            response["Access-Control-Allow-Methods"] = getattr(
                settings, "CORS_ALLOW_METHODS", "GET,POST,PUT,PATCH,DELETE,OPTIONS"
            )
            response["Access-Control-Allow-Headers"] = getattr(
                settings,
                "CORS_ALLOW_HEADERS",
                "Authorization,Content-Type,Accept,X-Requested-With",
            )
            response["Access-Control-Max-Age"] = "600"
            # 带 Origin 的响应必须声明 Vary，避免被缓存串味
            vary = response.headers.get("Vary")
            response["Vary"] = f"{vary}, Origin" if vary else "Origin"

        return response

    @staticmethod
    def _allowed(origin: str) -> bool:
        if getattr(settings, "CORS_ALLOW_ALL_ORIGINS", False):
            return True
        return origin in set(getattr(settings, "CORS_ALLOWED_ORIGINS", ()))
