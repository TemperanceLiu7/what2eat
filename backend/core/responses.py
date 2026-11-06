"""统一响应信封 + 业务错误码。

成功：``{"ok": true, "data": {...}, "message": ""}``
失败：``{"ok": false, "code": "XXX", "message": "中文提示"}``

视图里成功用 :func:`ok`，失败直接 ``raise ApiError(...)``；DRF 原生异常
（ValidationError / NotAuthenticated / 404 …）由 :func:`exception_handler`
兜底转成同一形状，前端只需要处理一种信封。
"""
from __future__ import annotations

from typing import Any

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

# ---------------------------------------------------------------------------
# 业务错误码
# ---------------------------------------------------------------------------
UNVERIFIED = "UNVERIFIED"          # 未绑定学号
BANNED = "BANNED"                  # 禁言 / 封禁中
ALREADY_VOTED = "ALREADY_VOTED"    # 重复投票
VOTE_CLOSED = "VOTE_CLOSED"        # 投票已结束 / 已截止
INVALID_DATA = "INVALID_DATA"      # 参数不合法
UNAUTHORIZED = "UNAUTHORIZED"      # 登录失效
FORBIDDEN = "FORBIDDEN"            # 无权限
NOT_FOUND = "NOT_FOUND"            # 资源不存在
METHOD_NOT_ALLOWED = "METHOD_NOT_ALLOWED"
TOO_MANY_REQUESTS = "TOO_MANY_REQUESTS"
SERVER_ERROR = "SERVER_ERROR"

ERROR_STATUS: dict[str, int] = {
    UNVERIFIED: status.HTTP_403_FORBIDDEN,
    BANNED: status.HTTP_403_FORBIDDEN,
    ALREADY_VOTED: status.HTTP_409_CONFLICT,
    VOTE_CLOSED: status.HTTP_409_CONFLICT,
    INVALID_DATA: status.HTTP_400_BAD_REQUEST,
    UNAUTHORIZED: status.HTTP_401_UNAUTHORIZED,
    FORBIDDEN: status.HTTP_403_FORBIDDEN,
    NOT_FOUND: status.HTTP_404_NOT_FOUND,
    METHOD_NOT_ALLOWED: status.HTTP_405_METHOD_NOT_ALLOWED,
    TOO_MANY_REQUESTS: status.HTTP_429_TOO_MANY_REQUESTS,
    SERVER_ERROR: status.HTTP_500_INTERNAL_SERVER_ERROR,
}

DEFAULT_MESSAGES: dict[str, str] = {
    UNVERIFIED: "请先完成学号核验",
    BANNED: "该账号已被封禁，无法操作",
    ALREADY_VOTED: "你已经投过票了，每人只能投一次",
    VOTE_CLOSED: "投票已结束，不能再投",
    INVALID_DATA: "提交的数据不合法，请检查后重试",
    UNAUTHORIZED: "登录状态已失效，请重新登录",
    FORBIDDEN: "没有权限执行这个操作",
    NOT_FOUND: "请求的内容不存在",
    METHOD_NOT_ALLOWED: "请求方法不被允许",
    TOO_MANY_REQUESTS: "操作太频繁，歇一会儿再试",
    SERVER_ERROR: "服务器开小差了，请稍后再试",
}


# ---------------------------------------------------------------------------
# 信封
# ---------------------------------------------------------------------------
def ok(data: Any = None, message: str = "", status_code: int = status.HTTP_200_OK) -> Response:
    """成功响应：``{ok: true, data, message}``。"""
    return Response(
        {"ok": True, "data": {} if data is None else data, "message": message},
        status=status_code,
    )


def fail(
    code: str,
    message: str | None = None,
    status_code: int | None = None,
    data: Any = None,
) -> Response:
    """失败响应：``{ok: false, code, message}``（data 只在需要时附带）。"""
    payload: dict[str, Any] = {
        "ok": False,
        "code": code,
        "message": message or DEFAULT_MESSAGES.get(code, "请求失败"),
    }
    if data is not None:
        payload["data"] = data
    return Response(payload, status=status_code or ERROR_STATUS.get(code, 400))


# ---------------------------------------------------------------------------
# 业务异常：视图里 raise，交给下面的 exception_handler 转信封
# ---------------------------------------------------------------------------
class ApiError(APIException):
    """携带业务码的异常，例如 ``raise ApiError(UNVERIFIED)``。"""

    status_code = status.HTTP_400_BAD_REQUEST
    default_detail = "请求失败"
    default_code = INVALID_DATA

    def __init__(
        self,
        code: str = INVALID_DATA,
        message: str | None = None,
        status_code: int | None = None,
    ) -> None:
        self.biz_code = code
        self.message = message or DEFAULT_MESSAGES.get(code, self.default_detail)
        self.status_code = status_code or ERROR_STATUS.get(code, 400)
        super().__init__(detail=self.message, code=code)


# ---------------------------------------------------------------------------
# 异常兜底
# ---------------------------------------------------------------------------
def _first_message(detail: Any) -> str:
    """把 DRF 的嵌套 ErrorDetail 压成一句中文提示。"""
    if isinstance(detail, dict):
        for value in detail.values():
            text = _first_message(value)
            if text:
                return text
        return ""
    if isinstance(detail, (list, tuple)):
        for item in detail:
            text = _first_message(item)
            if text:
                return text
        return ""
    return str(detail) if detail is not None else ""


def exception_handler(exc, context):
    """接管 DRF 全部异常，返回统一失败信封。"""
    if isinstance(exc, ApiError):
        return fail(exc.biz_code, exc.message, exc.status_code)

    response = drf_exception_handler(exc, context)
    if response is None:  # 非 DRF 异常：交给 Django（DEBUG 下出堆栈页）
        return None

    from rest_framework.exceptions import (
        AuthenticationFailed,
        NotAuthenticated,
        NotFound,
        PermissionDenied,
        Throttled,
        ValidationError,
    )
    from django.http import Http404

    detail = getattr(exc, "detail", None)
    message = _first_message(detail)

    if isinstance(exc, (NotAuthenticated, AuthenticationFailed, Http404)):
        if isinstance(exc, Http404):
            return fail(NOT_FOUND, message or DEFAULT_MESSAGES[NOT_FOUND], 404)
        return fail(UNAUTHORIZED, message or DEFAULT_MESSAGES[UNAUTHORIZED], 401)
    if isinstance(exc, NotFound):
        return fail(NOT_FOUND, DEFAULT_MESSAGES[NOT_FOUND], 404)
    if isinstance(exc, PermissionDenied):
        return fail(FORBIDDEN, message or DEFAULT_MESSAGES[FORBIDDEN], 403)
    if isinstance(exc, Throttled):
        return fail(TOO_MANY_REQUESTS, DEFAULT_MESSAGES[TOO_MANY_REQUESTS], 429)
    if isinstance(exc, ValidationError):
        return fail(INVALID_DATA, message or DEFAULT_MESSAGES[INVALID_DATA], 400)

    # ParseError / UnsupportedMediaType / MethodNotAllowed 等
    if response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
        return fail(METHOD_NOT_ALLOWED, message or DEFAULT_MESSAGES[METHOD_NOT_ALLOWED], 405)
    if response.status_code == status.HTTP_400_BAD_REQUEST:
        return fail(INVALID_DATA, message or DEFAULT_MESSAGES[INVALID_DATA], 400)
    if response.status_code == status.HTTP_404_NOT_FOUND:
        return fail(NOT_FOUND, DEFAULT_MESSAGES[NOT_FOUND], 404)
    if response.status_code == status.HTTP_403_FORBIDDEN:
        return fail(FORBIDDEN, message or DEFAULT_MESSAGES[FORBIDDEN], 403)
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        return fail(UNAUTHORIZED, message or DEFAULT_MESSAGES[UNAUTHORIZED], 401)

    return fail(
        SERVER_ERROR,
        message or DEFAULT_MESSAGES[SERVER_ERROR],
        response.status_code if response.status_code >= 400 else 500,
    )
