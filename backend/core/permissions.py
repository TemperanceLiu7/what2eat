"""接口权限守卫：把「已登录 / 已核验 / 未被禁言」翻译成业务错误码。

用函数而不是 DRF Permission 类，是为了让失败时返回的 ``code`` 精确可控
（``UNVERIFIED`` 403 / ``BANNED`` 403），前端按 code 分支即可。
"""
from __future__ import annotations

from .models import User
from .responses import BANNED, UNAUTHORIZED, UNVERIFIED, ApiError


def ensure_authenticated(user) -> User:
    if user is None or not getattr(user, "is_authenticated", False):
        raise ApiError(UNAUTHORIZED, "登录状态已失效，请重新登录", 401)
    return user


def ensure_verified(user) -> User:
    """已登录 + 已绑定学号。"""
    ensure_authenticated(user)
    if not user.is_verified:
        raise ApiError(UNVERIFIED, "请先完成学号核验")
    return user


def ensure_can_publish(user) -> User:
    """发布类操作（打卡 / 发起投票 / 投票）：已核验且未被禁言、封禁。"""
    ensure_verified(user)
    if user.is_banned:
        raise ApiError(BANNED, "该账号已被封禁，无法操作")
    if user.is_muted:
        raise ApiError(BANNED, "你正在禁言中，暂时不能发布内容")
    return user
