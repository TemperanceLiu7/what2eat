"""业务视图。

统一约定：
- 成功走 ``ok(data, message)``，失败 ``raise ApiError(code, message)``；
- 需要「已核验 / 未被禁言」的地方用 ``core.permissions`` 里的守卫，
  错误码与前端 error 表一一对应（UNVERIFIED / BANNED / ALREADY_VOTED /
  VOTE_CLOSED / INVALID_DATA）；
- 列表接口统一分页 ``{items,total,page,page_size,pages}``。

四条核心接口（完整实现，带事务 / 权重 / 竞态处理）：
``GET /dishes/random/``、``POST /checkins/``、``POST /votes/{id}/cast/``、
``POST /auth/bind-student/``。
"""
from __future__ import annotations

import random
from datetime import timedelta

from django.conf import settings
from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.db.models import F, Q, Value
from django.db.models.functions import Greatest
from django.utils import timezone
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer as JWTRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema, inline_serializer
from rest_framework import serializers

from .authentication import OptionalJWTAuthentication
from .images import save_base64_image
from .models import Checkin, Dish, Favorite, Like, Report, Shop, TargetType, User, Vote, VoteRecord
from .pagination import EnvelopePagination
from .permissions import ensure_authenticated, ensure_can_publish, ensure_verified
from .responses import (
    ALREADY_VOTED,
    BANNED,
    FORBIDDEN,
    INVALID_DATA,
    NOT_FOUND,
    UNAUTHORIZED,
    VOTE_CLOSED,
    ApiError,
    ok,
)
from .vision import VisionError, provider_ready, recognize  # noqa: E402
from .serializers import (
    BindStudentSerializer,
    CheckinCreateSerializer,
    CheckinSerializer,
    DishSerializer,
    LoginSerializer,
    RegisterSerializer,
    ReportCreateSerializer,
    ReportSerializer,
    ToggleTargetSerializer,
    UserProfileSerializer,
    VoteCastSerializer,
    VoteCreateSerializer,
    VoteSerializer,
)

TARGET_MODELS = {
    TargetType.DISH: Dish,
    TargetType.SHOP: Shop,
    TargetType.CHECKIN: Checkin,
    TargetType.USER: User,
}
VALID_SOURCES = {"all", *Shop.Type.values}

# --- 接口文档用的公共片段 -------------------------------------------------
ENVELOPE = OpenApiResponse(
    OpenApiTypes.OBJECT, description="统一信封：{ok: true, data: {...}, message: ''}"
)
FAIL_ENVELOPE = OpenApiResponse(
    OpenApiTypes.OBJECT, description="失败信封：{ok: false, code: 'XXX', message: '中文提示'}"
)
PAGINATION_PARAMS = [
    OpenApiParameter("page", OpenApiTypes.INT, description="页码，默认 1"),
    OpenApiParameter("page_size", OpenApiTypes.INT, description="每页条数，默认 10，最大 100"),
]
SOURCE_PARAM = OpenApiParameter(
    "source",
    OpenApiTypes.STR,
    description="来源：all / canteen / takeout / restaurant / night",
)


# ---------------------------------------------------------------------------
# 通用小工具
# ---------------------------------------------------------------------------
def issue_tokens(user: User) -> dict:
    """签发 JWT；``token`` 是给前端 localStorage 直接用的 access。"""
    refresh = RefreshToken.for_user(user)
    access = str(refresh.access_token)
    return {"token": access, "access": access, "refresh": str(refresh)}


def resolve_target(target_type: str, target_id: int):
    """多态目标校验：dish/shop/checkin/user 必须真实存在。"""
    model = TARGET_MODELS.get(target_type)
    if model is None:
        raise ApiError(INVALID_DATA, "target_type 不合法")
    obj = model.objects.filter(pk=target_id).first()
    if obj is None:
        raise ApiError(INVALID_DATA, "操作对象不存在或已删除")
    return obj


def liked_dish_ids(user, dish_ids) -> set[int]:
    if not user or not getattr(user, "is_authenticated", False) or not dish_ids:
        return set()
    return set(
        Like.objects.filter(
            user=user, target_type=TargetType.DISH, target_id__in=list(dish_ids)
        ).values_list("target_id", flat=True)
    )


def favorited_dish_ids(user, dish_ids) -> set[int]:
    if not user or not getattr(user, "is_authenticated", False) or not dish_ids:
        return set()
    return set(
        Favorite.objects.filter(
            user=user, target_type=TargetType.DISH, target_id__in=list(dish_ids)
        ).values_list("target_id", flat=True)
    )


def dish_context(request, dishes) -> dict:
    ids = [d.id for d in dishes]
    return {
        "request": request,
        "liked_dish_ids": liked_dish_ids(request.user, ids),
        "favorited_dish_ids": favorited_dish_ids(request.user, ids),
    }


class EnvelopeListView(APIView):
    """列表接口的分页 + 信封封装，子类只关心 queryset 与序列化器。"""

    def paginate(self, queryset, request, serializer_class, context=None):
        paginator = EnvelopePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = serializer_class(page, many=True, context=context or {"request": request})
        return paginator.get_paginated_response(serializer.data)


# ---------------------------------------------------------------------------
# 认证：注册 / 登录 / 刷新 / 学号核验
# ---------------------------------------------------------------------------
class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["认证"],
        summary="注册",
        request=RegisterSerializer,
        responses={201: ENVELOPE, 400: FAIL_ENVELOPE},
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        user = User.objects.create_user(
            username=data["username"].strip(),
            password=data["password"],
            name=(data.get("name") or "").strip(),
            college=(data.get("college") or "").strip(),
            role=User.Role.STUDENT,
        )
        payload = issue_tokens(user)
        payload["user"] = UserProfileSerializer(user).data
        return ok(payload, "注册成功，请完成学号核验", status_code=201)


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["认证"],
        summary="登录（账号或学号）",
        request=LoginSerializer,
        responses={200: ENVELOPE, 401: FAIL_ENVELOPE, 403: FAIL_ENVELOPE},
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        account = serializer.validated_data["username"].strip()
        password = serializer.validated_data["password"]

        user = authenticate(request, username=account, password=password)
        if user is None:
            # 也允许直接拿学号当账号登录
            username = (
                User.objects.filter(student_id=account)
                .values_list("username", flat=True)
                .first()
            )
            if username:
                user = authenticate(request, username=username, password=password)
        if user is None:
            raise ApiError(UNAUTHORIZED, "账号或密码不正确", 401)
        if not user.is_active:
            raise ApiError(BANNED, "该账号已被停用，请联系管理员", 403)
        if user.is_banned:
            raise ApiError(BANNED, "该账号已被封禁，无法登录", 403)

        payload = issue_tokens(user)
        payload["user"] = UserProfileSerializer(user).data
        return ok(payload, f"登录成功，欢迎 {user.name or user.username}")


class TokenRefreshView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(
        tags=["认证"],
        summary="刷新 access token",
        request=inline_serializer(
            name="TokenRefreshRequest", fields={"refresh": serializers.CharField()}
        ),
        responses={200: ENVELOPE, 401: FAIL_ENVELOPE},
    )
    def post(self, request):
        refresh_value = str(request.data.get("refresh") or "")
        if not refresh_value:
            raise ApiError(INVALID_DATA, "缺少 refresh 参数")
        serializer = JWTRefreshSerializer(data={"refresh": refresh_value})
        try:
            serializer.is_valid(raise_exception=True)
        except (InvalidToken, TokenError) as exc:
            raise ApiError(UNAUTHORIZED, "登录状态已失效，请重新登录", 401) from exc
        data = serializer.validated_data
        access = data.get("access")
        return ok(
            {"access": access, "token": access, "refresh": data.get("refresh", refresh_value)},
            "令牌已刷新",
        )


class BindStudentView(APIView):
    """学号 + 姓名 + 学院 三重核验。

    数据来源是 ``users`` 表里的学籍记录（``seed`` 生成的 3 条占位账号就是学籍名单）。
    三条必须完全一致才通过；通过后把学号写到当前账号上，占位行删除，
    这样「一个学号只能绑一个账号」由 ``student_id`` 的 unique 约束保证。
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["认证"],
        summary="学号 + 姓名 + 学院 三重核验",
        request=BindStudentSerializer,
        responses={200: ENVELOPE, 400: FAIL_ENVELOPE, 401: FAIL_ENVELOPE, 403: FAIL_ENVELOPE},
    )
    def post(self, request):
        user = request.user
        if user.is_banned:
            raise ApiError(BANNED, "该账号已被封禁，无法操作")

        serializer = BindStudentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        student_id = serializer.validated_data["student_id"].strip()
        name = serializer.validated_data["name"].strip()
        college = serializer.validated_data["college"].strip()

        if not student_id or not name or not college:
            raise ApiError(INVALID_DATA, "学号、姓名、学院都要填")

        with transaction.atomic():
            if user.student_id and user.student_id != student_id:
                raise ApiError(
                    INVALID_DATA,
                    f"当前账号已绑定学号 {user.student_id}，如需更换请联系管理员",
                )

            roster = (
                User.objects.select_for_update()
                .filter(student_id=student_id, name=name, college=college)
                .first()
            )
            if roster is None:
                raise ApiError(INVALID_DATA, "学号、姓名与学院不匹配，未通过核验")

            if roster.pk == user.pk:
                pass  # 已经是本账号，三重一致，幂等通过
            elif roster.is_roster_placeholder:
                # 学籍占位行：释放学号后由当前账号占用
                roster.delete()
                user.student_id = student_id
                user.name = name
                user.college = college
                user.save(update_fields=["student_id", "name", "college"])
            else:
                raise ApiError(INVALID_DATA, "该学号已被其他账号绑定")

        payload = issue_tokens(user)
        payload["user"] = UserProfileSerializer(user).data
        payload["verified"] = True
        return ok(payload, f"核验通过，欢迎 {user.name}")


# ---------------------------------------------------------------------------
# 菜品：加权随机 / 分页列表
# ---------------------------------------------------------------------------
class RandomDishView(APIView):
    """加权随机推荐。

    权重 = ``RECOMMEND_WEIGHT_BASE``（默认 1）+ 热度 × ``RECOMMEND_WEIGHT_HEAT``（默认 0.06），
    热度 = 点赞 + 收藏，所以热门更容易中，冷门也有机会。
    已登录用户会排除自己最近 ``RECOMMEND_RECENT_LIMIT``（默认 4）条打卡里的菜品；
    如果排除后为空（都吃过了），就退回完整候选池，保证一定能抽到。
    """

    authentication_classes = [OptionalJWTAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["菜品"],
        summary="加权随机抽一道菜",
        description=(
            "权重 = 1 + (likes + favorites) × 0.06；已登录用户排除自己最近 4 条打卡里的菜品。"
            "该来源没有菜品时返回 404（前端视为「没抽到」）。"
        ),
        parameters=[SOURCE_PARAM],
        responses={200: ENVELOPE, 400: FAIL_ENVELOPE, 404: FAIL_ENVELOPE},
    )
    def get(self, request):
        source = (request.query_params.get("source") or "all").strip().lower()
        if source not in VALID_SOURCES:
            raise ApiError(
                INVALID_DATA, "source 只能是 all / canteen / takeout / restaurant / night"
            )

        queryset = Dish.objects.select_related("shop").filter(shop__status=Shop.Status.OPEN)
        if source != "all":
            queryset = queryset.filter(shop__type=source)
        pool = list(queryset)
        if not pool:
            # 前端把 404 当作「这个来源没菜」，会显示空状态而不是报错
            raise ApiError(NOT_FOUND, "这个来源暂时没有菜品", 404)

        recent_limit = int(getattr(settings, "RECOMMEND_RECENT_LIMIT", 4))
        recent_ids: list[int] = []
        if request.user.is_authenticated and recent_limit > 0:
            recent_ids = list(
                Checkin.objects.filter(user=request.user, dish__isnull=False)
                .order_by("-created_at", "-id")
                .values_list("dish_id", flat=True)[:recent_limit]
            )
        recent_set = set(recent_ids)

        candidates = [d for d in pool if d.id not in recent_set] or pool

        base = float(getattr(settings, "RECOMMEND_WEIGHT_BASE", 1.0))
        heat_factor = float(getattr(settings, "RECOMMEND_WEIGHT_HEAT", 0.06))
        weights = [max(base + dish.heat * heat_factor, 0.01) for dish in candidates]

        dish = random.choices(candidates, weights=weights, k=1)[0]
        picked_index = candidates.index(dish)

        return ok(
            {
                "dish": DishSerializer(dish, context=dish_context(request, [dish])).data,
                "source": source,
                "weight": round(weights[picked_index], 4),
                "poolSize": len(candidates),
                "excludedCount": len(recent_set),
            },
            "",
        )


class DishListView(EnvelopeListView):
    """``GET /api/dishes/``：分页列表，支持 source / shop / category / search。"""

    authentication_classes = [OptionalJWTAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["菜品"],
        summary="菜品分页列表",
        parameters=[
            SOURCE_PARAM,
            OpenApiParameter("shop", OpenApiTypes.INT, description="档口 ID"),
            OpenApiParameter("category", OpenApiTypes.STR, description="分类，如 面食"),
            OpenApiParameter("search", OpenApiTypes.STR, description="按菜名 / 简介 / 档口名搜索"),
            OpenApiParameter(
                "ordering",
                OpenApiTypes.STR,
                description="排序：-likes(默认) / likes / -price / price / -favorites / name / id",
            ),
            *PAGINATION_PARAMS,
        ],
        responses={200: ENVELOPE},
    )
    def get(self, request):
        queryset = Dish.objects.select_related("shop").filter(
            shop__status=Shop.Status.OPEN
        )

        source = (request.query_params.get("source") or "").strip().lower()
        if source and source != "all":
            if source not in VALID_SOURCES:
                raise ApiError(INVALID_DATA, "source 取值不合法")
            queryset = queryset.filter(shop__type=source)

        shop_id = request.query_params.get("shop") or request.query_params.get("shop_id")
        if shop_id:
            queryset = queryset.filter(shop_id=shop_id)

        category = (request.query_params.get("category") or "").strip()
        if category:
            queryset = queryset.filter(category=category)

        keyword = (request.query_params.get("search") or "").strip()
        if keyword:
            queryset = queryset.filter(
                Q(name__icontains=keyword)
                | Q(description__icontains=keyword)
                | Q(shop__name__icontains=keyword)
            )

        ordering = (request.query_params.get("ordering") or "-likes").strip()
        allowed_ordering = {
            "likes", "-likes", "favorites", "-favorites",
            "price", "-price", "id", "-id", "name", "-name",
        }
        if ordering not in allowed_ordering:
            ordering = "-likes"
        queryset = queryset.order_by(ordering, "-id")

        paginator = EnvelopePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        serializer = DishSerializer(
            page, many=True, context=dish_context(request, page)
        )
        return paginator.get_paginated_response(serializer.data)


# ---------------------------------------------------------------------------
# 打卡
# ---------------------------------------------------------------------------
class CheckinListCreateView(EnvelopeListView):
    """GET 打卡广场（匿名可看）/ POST 发布打卡（需已核验且未禁言）。"""

    authentication_classes = [OptionalJWTAuthentication]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    @extend_schema(
        tags=["打卡"],
        summary="打卡广场（匿名可看）",
        parameters=[
            OpenApiParameter("mine", OpenApiTypes.BOOL, description="true 只看自己的"),
            OpenApiParameter("dish", OpenApiTypes.INT, description="按菜品 ID 过滤"),
            OpenApiParameter("search", OpenApiTypes.STR, description="按内容搜索"),
            *PAGINATION_PARAMS,
        ],
        responses={200: ENVELOPE, 401: FAIL_ENVELOPE},
    )
    def get(self, request):
        queryset = Checkin.objects.select_related("user", "dish", "dish__shop").order_by(
            "-created_at", "-id"
        )

        mine = (request.query_params.get("mine") or "").lower()
        scope = (request.query_params.get("scope") or "").lower()
        if mine in {"1", "true", "yes"} or scope == "mine":
            # 个人板块：看自己的全部记录，含 private
            if not request.user.is_authenticated:
                raise ApiError(UNAUTHORIZED, "请先登录", 401)
            queryset = queryset.filter(user=request.user)
        else:
            # 社区板块：只看公开的；私密打卡不进广场，也不可被举报
            queryset = queryset.filter(visibility=Checkin.Visibility.PUBLIC)

        dish_id = request.query_params.get("dish") or request.query_params.get("dish_id")
        if dish_id:
            queryset = queryset.filter(dish_id=dish_id)

        keyword = (request.query_params.get("search") or "").strip()
        if keyword:
            queryset = queryset.filter(content__icontains=keyword)

        paginator = EnvelopePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)
        ids = [item.id for item in page]
        context = {"request": request}
        if request.user.is_authenticated and ids:
            context["liked_checkin_ids"] = set(
                Like.objects.filter(
                    user=request.user, target_type=TargetType.CHECKIN, target_id__in=ids
                ).values_list("target_id", flat=True)
            )
        serializer = CheckinSerializer(page, many=True, context=context)
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["打卡"],
        summary="发布打卡（需已核验且未禁言）",
        request=CheckinCreateSerializer,
        responses={201: ENVELOPE, 400: FAIL_ENVELOPE, 401: FAIL_ENVELOPE, 403: FAIL_ENVELOPE},
    )
    def post(self, request):
        user = request.user
        ensure_can_publish(user)

        serializer = CheckinCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        content = (data.get("content") or "").strip()
        if not content:
            raise ApiError(INVALID_DATA, "写点什么再发布吧")
        if len(content) > 500:
            raise ApiError(INVALID_DATA, "打卡内容最多 500 字")

        dish = self._resolve_dish(data)

        image_file = save_base64_image(request.data.get("image"), name_hint="checkin")

        checkin = Checkin(
            user=user,
            content=content,
            dish=dish,
            dish_name=(data.get("dish_name") or "").strip()[:64],
            visibility=data.get("visibility") or Checkin.Visibility.PUBLIC,
        )
        if image_file is not None:
            checkin.image = image_file
        checkin.save()

        serializer = CheckinSerializer(
            checkin, context={"request": request, "liked_checkin_ids": set()}
        )
        return ok(
            {
                "checkin": serializer.data,
                "id": checkin.id,
                "at": int(checkin.created_at.timestamp() * 1000),
            },
            "打卡成功",
            status_code=201,
        )

    @staticmethod
    def _resolve_dish(data: dict) -> Dish | None:
        """支持 dish_id / dish（ID）与 dish_name（按名字匹配已有菜品）。"""
        dish_id = data.get("dish_id") or data.get("dish")
        if dish_id:
            dish = Dish.objects.filter(pk=dish_id).first()
            if dish is None:
                raise ApiError(INVALID_DATA, "关联的菜品不存在")
            return dish
        dish_name = (data.get("dish_name") or "").strip()
        if dish_name:
            return Dish.objects.filter(name=dish_name).first()
        return None


# ---------------------------------------------------------------------------
# 点赞 / 收藏
# ---------------------------------------------------------------------------
class ToggleLikeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["互动"],
        summary="点赞 / 取消点赞",
        description="同一目标点一次是点赞，再点一次是取消；菜品会同步维护 likes 计数。",
        request=ToggleTargetSerializer,
        responses={200: ENVELOPE, 400: FAIL_ENVELOPE, 401: FAIL_ENVELOPE, 403: FAIL_ENVELOPE},
    )
    def post(self, request):
        user = ensure_authenticated(request.user)
        if user.is_banned:
            raise ApiError(BANNED, "该账号已被封禁，无法操作")

        serializer = ToggleTargetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_type = serializer.validated_data["target_type"]
        target_id = serializer.validated_data["target_id"]
        resolve_target(target_type, target_id)

        with transaction.atomic():
            like = Like.objects.filter(
                user=user, target_type=target_type, target_id=target_id
            ).first()
            liked = like is None
            if like is not None:
                like.delete()
            else:
                try:
                    Like.objects.create(
                        user=user, target_type=target_type, target_id=target_id
                    )
                except IntegrityError as exc:  # 唯一约束兜底并发双击
                    raise ApiError(INVALID_DATA, "操作太频繁，请稍后重试") from exc

            likes_count = None
            if target_type == TargetType.DISH:
                Dish.objects.filter(pk=target_id).update(
                    likes=Greatest(F("likes") + Value(1 if liked else -1), Value(0))
                )
                likes_count = (
                    Dish.objects.filter(pk=target_id).values_list("likes", flat=True).first()
                )

        return ok(
            {
                "target_type": target_type,
                "target_id": target_id,
                "liked": liked,
                "likes": likes_count,
            },
            "点赞成功" if liked else "已取消点赞",
        )


class ToggleFavoriteView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["互动"],
        summary="收藏 / 取消收藏",
        request=ToggleTargetSerializer,
        responses={200: ENVELOPE, 400: FAIL_ENVELOPE, 401: FAIL_ENVELOPE, 403: FAIL_ENVELOPE},
    )
    def post(self, request):
        user = ensure_authenticated(request.user)
        if user.is_banned:
            raise ApiError(BANNED, "该账号已被封禁，无法操作")

        serializer = ToggleTargetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        target_type = serializer.validated_data["target_type"]
        target_id = serializer.validated_data["target_id"]
        resolve_target(target_type, target_id)

        with transaction.atomic():
            favorite = Favorite.objects.filter(
                user=user, target_type=target_type, target_id=target_id
            ).first()
            favorited = favorite is None
            if favorite is not None:
                favorite.delete()
            else:
                try:
                    Favorite.objects.create(
                        user=user, target_type=target_type, target_id=target_id
                    )
                except IntegrityError as exc:
                    raise ApiError(INVALID_DATA, "操作太频繁，请稍后重试") from exc

            favorites_count = None
            if target_type == TargetType.DISH:
                Dish.objects.filter(pk=target_id).update(
                    favorites=Greatest(
                        F("favorites") + Value(1 if favorited else -1), Value(0)
                    )
                )
                favorites_count = (
                    Dish.objects.filter(pk=target_id)
                    .values_list("favorites", flat=True)
                    .first()
                )

        return ok(
            {
                "target_type": target_type,
                "target_id": target_id,
                "favorited": favorited,
                "favorites": favorites_count,
            },
            "收藏成功" if favorited else "已取消收藏",
        )


class FavoriteListView(EnvelopeListView):
    """我的收藏：菜品类收藏直接展开成菜品对象（前端按菜品列表渲染）。"""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["互动"],
        summary="我的收藏",
        description="菜品类收藏会把菜品对象展开到 items 里，前端可直接按菜品列表渲染。",
        parameters=[
            OpenApiParameter(
                "target_type",
                OpenApiTypes.STR,
                description="按对象类型过滤：dish / shop / checkin / user",
            ),
            *PAGINATION_PARAMS,
        ],
        responses={200: ENVELOPE, 401: FAIL_ENVELOPE},
    )
    def get(self, request):
        queryset = Favorite.objects.filter(user=request.user).order_by("-created_at", "-id")
        target_type = (request.query_params.get("target_type") or "").strip()
        if target_type in TargetType.values:
            queryset = queryset.filter(target_type=target_type)

        paginator = EnvelopePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)

        dish_ids = [
            fav.target_id for fav in page if fav.target_type == TargetType.DISH
        ]
        dishes = list(Dish.objects.select_related("shop").filter(id__in=dish_ids))
        dish_map = {
            dish.id: DishSerializer(dish, context=dish_context(request, dishes)).data
            for dish in dishes
        }

        items = []
        for fav in page:
            favorited_at = int(fav.created_at.timestamp() * 1000)
            if fav.target_type == TargetType.DISH:
                dish_data = dish_map.get(fav.target_id)
                if dish_data:
                    items.append(
                        {
                            **dish_data,
                            "target_type": fav.target_type,
                            "target_id": fav.target_id,
                            "favorite_id": fav.id,
                            "favoritedAt": favorited_at,
                        }
                    )
                    continue
            items.append(
                {
                    "target_type": fav.target_type,
                    "target_id": fav.target_id,
                    "favorite_id": fav.id,
                    "favoritedAt": favorited_at,
                    "dish": None,
                }
            )

        return paginator.get_paginated_response(items)


# ---------------------------------------------------------------------------
# 举报
# ---------------------------------------------------------------------------
class ReportCreateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["举报"],
        summary="举报内容 / 用户",
        description="同一人对同一条内容只能有一条待审核举报；累计到阈值会自动禁言被举报人。",
        request=ReportCreateSerializer,
        responses={201: ENVELOPE, 400: FAIL_ENVELOPE, 403: FAIL_ENVELOPE},
    )
    def post(self, request):
        user = ensure_verified(request.user)

        serializer = ReportCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        if data["reported_id"] == user.id:
            raise ApiError(INVALID_DATA, "不能举报自己")
        reported = User.objects.filter(pk=data["reported_id"]).first()
        if reported is None:
            raise ApiError(INVALID_DATA, "被举报的用户不存在")
        resolve_target(data["target_type"], data["target_id"])

        duplicated = Report.objects.filter(
            reporter=user,
            reported=reported,
            target_type=data["target_type"],
            target_id=data["target_id"],
            status=Report.Status.PENDING,
        ).exists()
        if duplicated:
            raise ApiError(INVALID_DATA, "你已经举报过这条内容，正在处理中")

        auto_muted = False
        with transaction.atomic():
            report = Report.objects.create(
                reporter=user,
                reported=reported,
                target_type=data["target_type"],
                target_id=data["target_id"],
                reason=data["reason"],
            )
            User.objects.filter(pk=reported.pk).update(report_count=F("report_count") + 1)
            reported.refresh_from_db(fields=["report_count", "status", "ban_until"])

            threshold = int(getattr(settings, "AUTO_MUTE_REPORT_COUNT", 0))
            if threshold and reported.report_count >= threshold and not reported.is_banned:
                reported.status = User.Status.MUTED
                reported.ban_until = timezone.now() + timedelta(
                    hours=int(getattr(settings, "AUTO_MUTE_HOURS", 24))
                )
                reported.save(update_fields=["status", "ban_until"])
                auto_muted = True

        return ok(
            {
                "report": ReportSerializer(report).data,
                "reportCount": reported.report_count,
                "autoMuted": auto_muted,
            },
            "举报已提交，等待审核",
            status_code=201,
        )


# ---------------------------------------------------------------------------
# 投票
# ---------------------------------------------------------------------------
class VoteListCreateView(EnvelopeListView):
    """GET 列表（匿名可看）/ POST 发起投票（需已核验且未禁言）。"""

    authentication_classes = [OptionalJWTAuthentication]

    def get_permissions(self):
        if self.request.method == "POST":
            return [IsAuthenticated()]
        return [AllowAny()]

    @extend_schema(
        tags=["投票"],
        summary="投票列表（匿名可看）",
        parameters=[
            OpenApiParameter(
                "status",
                OpenApiTypes.STR,
                description="过滤状态：ongoing / passed / rejected / expired",
            ),
            OpenApiParameter("mine", OpenApiTypes.BOOL, description="true 只看自己发起的"),
            *PAGINATION_PARAMS,
        ],
        responses={200: ENVELOPE, 401: FAIL_ENVELOPE},
    )
    def get(self, request):
        # 惰性结算：过期但还挂着 ongoing 的投票顺手标记，列表里状态才准
        Vote.objects.filter(
            status=Vote.Status.ONGOING, deadline__lte=timezone.now()
        ).update(status=Vote.Status.EXPIRED)

        queryset = Vote.objects.select_related("creator").order_by("-created_at", "-id")
        status_value = (request.query_params.get("status") or "").strip()
        if status_value in Vote.Status.values:
            queryset = queryset.filter(status=status_value)
        mine = (request.query_params.get("mine") or "").lower()
        if mine in {"1", "true", "yes"}:
            if not request.user.is_authenticated:
                raise ApiError(UNAUTHORIZED, "请先登录", 401)
            queryset = queryset.filter(creator=request.user)

        paginator = EnvelopePagination()
        page = paginator.paginate_queryset(queryset, request, view=self)

        my_options: dict[int, str] = {}
        if request.user.is_authenticated and page:
            my_options = dict(
                VoteRecord.objects.filter(
                    user=request.user, vote_id__in=[v.id for v in page]
                ).values_list("vote_id", "option")
            )
        serializer = VoteSerializer(
            page,
            many=True,
            context={
                "request": request,
                "my_options": my_options,
                # 这一页里哪些投票已经被复审过了，前端据此隐藏「申请复审」
                "reviewed_ids": set(
                    Vote.objects.filter(review_of__in=[v.id for v in page]).values_list(
                        "review_of_id", flat=True
                    )
                )
                if page
                else set(),
            },
        )
        return paginator.get_paginated_response(serializer.data)

    @extend_schema(
        tags=["投票"],
        summary="发起投票（需已核验且未禁言）",
        request=VoteCreateSerializer,
        responses={201: ENVELOPE, 400: FAIL_ENVELOPE, 403: FAIL_ENVELOPE},
    )
    def post(self, request):
        user = ensure_can_publish(request.user)

        serializer = VoteCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        title = data["title"].strip()
        if not title:
            raise ApiError(INVALID_DATA, "给投票起个标题")
        target = (data.get("target") or "").strip()

        deadline = timezone.now() + timedelta(
            hours=int(getattr(settings, "VOTE_DEFAULT_HOURS", 12))
        )
        vote = Vote.objects.create(
            creator=user,
            title=title,
            target=target,
            target_count=data["target_count"],
            deadline=deadline,
            status=Vote.Status.ONGOING,
        )
        return ok(
            {
                "vote": VoteSerializer(vote, context={"request": request}).data,
                "need": vote.need,
            },
            "投票已创建",
            status_code=201,
        )


class CastVoteView(APIView):
    """投票：事务 + ``(vote, user)`` 唯一约束防刷，过半立即结算。

    竞态处理：先做一次廉价预检（已投 / 已结束）避免无谓加锁，
    进事务后再 ``select_for_update`` 重新校验一次；真正兜底的是唯一约束，
    并发双击时 ``IntegrityError`` 同样翻译成 ``ALREADY_VOTED``。
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["投票"],
        summary="投票（agree / disagree）",
        description=(
            "need = floor(target_count / 2) + 1；agree >= need → passed，"
            "disagree >= need → rejected，已结算后返回 409 VOTE_CLOSED。"
        ),
        request=VoteCastSerializer,
        responses={200: ENVELOPE, 404: FAIL_ENVELOPE, 409: FAIL_ENVELOPE, 403: FAIL_ENVELOPE},
    )
    def post(self, request, pk: int):
        user = ensure_can_publish(request.user)

        serializer = VoteCastSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        option = serializer.validated_data["option"]

        vote = Vote.objects.filter(pk=pk).first()
        if vote is None:
            raise ApiError(NOT_FOUND, "投票不存在", 404)
        if vote.status != Vote.Status.ONGOING:
            raise ApiError(VOTE_CLOSED, "投票已结束，不能再投")
        if vote.deadline <= timezone.now():
            Vote.objects.filter(pk=vote.pk, status=Vote.Status.ONGOING).update(
                status=Vote.Status.EXPIRED
            )
            raise ApiError(VOTE_CLOSED, "投票已截止，不能再投")
        if VoteRecord.objects.filter(vote_id=vote.pk, user=user).exists():
            raise ApiError(ALREADY_VOTED)

        try:
            with transaction.atomic():
                locked = Vote.objects.select_for_update().filter(pk=pk).first()
                if locked is None:
                    raise ApiError(NOT_FOUND, "投票不存在", 404)
                if locked.status != Vote.Status.ONGOING:
                    raise ApiError(VOTE_CLOSED, "投票已结束，不能再投")
                if locked.deadline <= timezone.now():
                    raise ApiError(VOTE_CLOSED, "投票已截止，不能再投")
                if VoteRecord.objects.filter(vote=locked, user=user).exists():
                    raise ApiError(ALREADY_VOTED)

                VoteRecord.objects.create(vote=locked, user=user, option=option)

                if option == VoteRecord.Option.AGREE:
                    locked.agree_count = F("agree_count") + 1
                else:
                    locked.disagree_count = F("disagree_count") + 1
                locked.save(update_fields=["agree_count", "disagree_count"])
                locked.refresh_from_db()

                # 过半判定：agree >= need → passed；disagree >= need → rejected
                locked.settle(save=True)
        except IntegrityError as exc:
            raise ApiError(ALREADY_VOTED) from exc

        return ok(
            {
                "vote": VoteSerializer(
                    locked, context={"request": request, "my_options": {locked.id: option}}
                ).data,
                "my_option": option,
            },
            "投票成功",
        )


class ReviewVoteView(APIView):
    """申请复审：对已出结果的投票，扩大目标人数重新投一次。

    规则（对应文档 3.7 的「申请复审」）：
    - 只有参与过该投票的人、或发起人本人可以申请
    - 原投票必须已经出结果（通过 / 未通过 / 已截止）
    - 一次投票只能复审一次；复审投票本身不能再被复审
    - 复审的目标人数放大到 1.5 倍（至少 +2，封顶 VOTE_TARGET_COUNT_MAX）
    - 最终以复审结果为准（列表按时间倒序，复审天然排在前面）
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["投票"],
        summary="申请复审（扩大参与人数重新投票）",
        description=(
            "参与者或发起人可对已结算的投票申请复审；"
            "新投票的 target_count 为原来的 1.5 倍（至少 +2）。"
        ),
        responses={201: ENVELOPE, 400: FAIL_ENVELOPE, 403: FAIL_ENVELOPE, 404: FAIL_ENVELOPE},
    )
    def post(self, request, pk: int):
        user = ensure_can_publish(request.user)

        with transaction.atomic():
            original = Vote.objects.select_for_update().filter(pk=pk).first()
            if original is None:
                raise ApiError(NOT_FOUND, "投票不存在", 404)

            if original.is_review:
                raise ApiError(INVALID_DATA, "复审投票不能再申请复审")

            if original.status == Vote.Status.ONGOING:
                raise ApiError(INVALID_DATA, "投票还在进行中，等出结果后再申请复审")

            if Vote.objects.filter(review_of=original).exists():
                raise ApiError(INVALID_DATA, "这个投票已经复审过了")

            participated = VoteRecord.objects.filter(vote=original, user=user).exists()
            if not participated and original.creator_id != user.id:
                raise ApiError(FORBIDDEN, "只有参与过这次投票的人才能申请复审")

            max_count = int(getattr(settings, "VOTE_TARGET_COUNT_MAX", 99))
            expanded = original.target_count + max(2, original.target_count // 2)
            new_count = min(max_count, expanded)

            deadline = timezone.now() + timedelta(
                hours=int(getattr(settings, "VOTE_DEFAULT_HOURS", 12))
            )
            review = Vote.objects.create(
                creator=user,
                title=f"复审：{original.title}"[:100],
                target=original.target,
                target_count=new_count,
                deadline=deadline,
                status=Vote.Status.ONGOING,
                review_of=original,
            )

        return ok(
            {
                "vote": VoteSerializer(review, context={"request": request}).data,
                "need": review.need,
                "originalId": original.id,
                "targetCount": new_count,
            },
            f"已发起复审，参与人数扩大到 {new_count} 人",
            status_code=201,
        )

# ---------------------------------------------------------------------------
# 个人板块：今天吃了啥（图片识别） + 个人偏好画像
# ---------------------------------------------------------------------------
class RecognizeView(APIView):
    """POST /api/recognize/ —— 把打卡图片交给视觉模型，返回菜品候选。

    没配 ``LLM_API_KEY`` 时返回 ``ready: false``，前端降级成手动选菜，
    不报错、不阻断打卡流程。
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["个人"],
        summary="识别图片里的菜品",
        description="入参 image 为 data URI 或纯 base64；返回最多 3 个候选菜名。",
        responses={200: ENVELOPE, 400: FAIL_ENVELOPE, 401: FAIL_ENVELOPE},
    )
    def post(self, request):
        image = (request.data.get("image") or "").strip()
        if not image:
            raise ApiError(INVALID_DATA, "没有收到图片")
        if len(image) > 7_000_000:
            raise ApiError(INVALID_DATA, "图片太大了，压缩后再试")

        if not provider_ready():
            return ok(
                {"dishes": [], "note": "未配置视觉模型，请手动选择菜品", "ready": False},
                "识别服务未启用",
            )

        try:
            result = recognize(image)
        except VisionError as exc:
            return ok(
                {"dishes": [], "note": str(exc)[:120], "ready": True},
                "识别失败，可以手动填写",
            )

        return ok({**result, "ready": True}, "识别完成")


class PreferencesView(APIView):
    """GET /api/preferences/ —— 从我的打卡里算个人偏好画像。

    私密打卡**也算**：不进社区，但一样用来形成个人口味偏好。
    """

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["个人"],
        summary="个人饮食偏好（来自全部打卡，含私密）",
        responses={200: ENVELOPE, 401: FAIL_ENVELOPE},
    )
    def get(self, request):
        from collections import Counter
        from datetime import timedelta

        from django.utils import timezone

        qs = (
            Checkin.objects.filter(user=request.user)
            .select_related("dish", "dish__shop")
            .order_by("-created_at")
        )
        items = list(qs[:100])

        names = Counter()
        categories = Counter()
        sources = Counter()
        for c in items:
            name = c.dish.name if c.dish_id else (c.dish_name or "").strip()
            if name:
                names[name] += 1
            if c.dish_id and c.dish.category:
                categories[c.dish.category] += 1
            if c.dish_id and c.dish.shop_id:
                sources[c.dish.shop.get_type_display()] += 1

        week_ago = timezone.now() - timedelta(days=7)
        last7 = [c for c in items if c.created_at >= week_ago]

        return ok(
            {
                "totalCheckins": len(items),
                "last7Days": len(last7),
                "privateCount": sum(
                    1 for c in items if c.visibility == Checkin.Visibility.PRIVATE
                ),
                "topDishes": [{"name": n, "count": c} for n, c in names.most_common(5)],
                "topCategories": [
                    {"name": n, "count": c} for n, c in categories.most_common(5)
                ],
                "topSources": [{"name": n, "count": c} for n, c in sources.most_common(5)],
            }
        )


class HealthView(APIView):
    """GET /api/health/ —— 存活 + 数据库连通性探针（Render 健康检查用）。

    不查业务表，只做 ``SELECT 1``：数据库刚建好、还没 migrate 时返回 503，
    前端与监控都能立刻看出来是「库没通」而不是「服务没起来」。
    """

    authentication_classes = []
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["运维"],
        summary="健康检查（含数据库连通性）",
        responses={200: ENVELOPE, 503: FAIL_ENVELOPE},
    )
    def get(self, request):
        from django.db import connection

        db_ok, db_error = True, ""
        try:
            with connection.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        except Exception as exc:  # noqa: BLE001 - 探针要吞掉一切异常并如实上报
            db_ok, db_error = False, f"{type(exc).__name__}: {exc}"

        if not db_ok:
            return Response(
                {
                    "ok": False,
                    "code": "DB_UNAVAILABLE",
                    "message": "数据库连接失败",
                    "data": {"service": "what2eat-api", "database": "down", "detail": db_error},
                },
                status=503,
            )

        return ok(
            {
                "service": "what2eat-api",
                "database": "up",
                "dishes": Dish.objects.count(),
                "shops": Shop.objects.count(),
            },
            "ok",
        )
