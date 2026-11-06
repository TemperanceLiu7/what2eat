"""JWT 认证的小扩展。

公开列表接口（随机推荐、打卡广场、投票列表）允许匿名访问，但如果浏览器里
存着过期 token，标准 ``JWTAuthentication`` 会直接抛 401，把「游客可看」变成
「登录态过期就白屏」。这里在公开接口上改用宽容版：token 不合法就当匿名。
"""
from __future__ import annotations

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed, InvalidToken


class OptionalJWTAuthentication(JWTAuthentication):
    """解析失败不报错，直接按匿名用户处理。"""

    def authenticate(self, request):
        try:
            return super().authenticate(request)
        except (AuthenticationFailed, InvalidToken):
            return None
