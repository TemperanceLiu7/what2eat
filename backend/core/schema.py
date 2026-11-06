"""drf-spectacular 扩展：让自带 JWT 和「宽容版 JWT」在文档里都显示 Bearer 认证。"""
from __future__ import annotations

from drf_spectacular.extensions import OpenApiAuthenticationExtension


class OptionalJWTAuthenticationScheme(OpenApiAuthenticationExtension):
    """``core.authentication.OptionalJWTAuthentication`` 的安全方案。

    与内置 ``JWTAuthentication`` 共用同名的 ``jwtAuth`` 方案，
    文档里只出现一个 Bearer 定义。
    """

    target_class = "core.authentication.OptionalJWTAuthentication"
    name = "jwtAuthOptional"

    def get_security_definition(self, auto_schema):
        return {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
            "description": "Authorization: Bearer <access>",
        }
