"""序列化层：输出兼容前端字段（camelCase 别名），输入做严格校验。

前端原来读的是 ``src/data/db.js`` 的视图对象，字段名是 camelCase
（``shopId`` / ``desc`` / ``sourceLabel`` / ``targetCount`` …）。后端库里用
snake_case，这一层把两边对齐：同一个值同时给 ``description`` 和 ``desc``，
前端只改 import 不用改模板。
"""
from __future__ import annotations

from django.conf import settings
from rest_framework import serializers

from .models import Checkin, Dish, Favorite, Like, Report, Shop, TargetType, User, Vote, VoteRecord

# 前端首页靠 emoji 占位，库里没有这个字段，按分类/来源算出来
SOURCE_LABELS = {
    Shop.Type.CANTEEN: "食堂",
    Shop.Type.TAKEOUT: "外卖",
    Shop.Type.RESTAURANT: "饭店",
    Shop.Type.NIGHT: "夜市",
}
SHOP_EMOJI = {
    Shop.Type.CANTEEN: "🍚",
    Shop.Type.TAKEOUT: "🛵",
    Shop.Type.RESTAURANT: "🍽️",
    Shop.Type.NIGHT: "🌙",
}
CATEGORY_EMOJI = {
    "盖饭": "🍛",
    "热菜": "🍖",
    "香锅": "🌶️",
    "冒菜": "🥘",
    "面食": "🍜",
    "火锅": "🍲",
    "快餐": "🍱",
    "小吃": "🥟",
    "饮品": "🥤",
}
DEFAULT_DISH_EMOJI = "🍽️"


def absolute_url(serializer: serializers.BaseSerializer, file_field) -> str:
    """把 ImageField 转成可被前端直接 <img src> 的绝对地址。"""
    if not file_field:
        return ""
    try:
        url = file_field.url
    except (ValueError, AttributeError):
        return ""
    request = serializer.context.get("request")
    return request.build_absolute_uri(url) if request is not None else url


# ---------------------------------------------------------------------------
# 用户
# ---------------------------------------------------------------------------
class UserBriefSerializer(serializers.ModelSerializer):
    """嵌在打卡/投票里的精简用户。"""

    studentId = serializers.SerializerMethodField()
    verified = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ("id", "username", "name", "student_id", "studentId", "college", "role", "verified")
        read_only_fields = fields

    def get_studentId(self, obj: User):
        return obj.student_id

    def get_verified(self, obj: User) -> bool:
        return obj.is_verified


class UserProfileSerializer(serializers.ModelSerializer):
    """登录 / 核验 / 注册接口返回的当前用户。"""

    studentId = serializers.SerializerMethodField()
    verified = serializers.SerializerMethodField()
    banned = serializers.SerializerMethodField()
    muted = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id", "username", "student_id", "studentId", "name", "college",
            "role", "status", "verified", "banned", "muted",
            "ban_until", "report_count", "is_staff",
        )
        read_only_fields = fields

    def get_studentId(self, obj: User):
        return obj.student_id

    def get_verified(self, obj: User) -> bool:
        return obj.is_verified

    def get_banned(self, obj: User) -> bool:
        return obj.is_banned

    def get_muted(self, obj: User) -> bool:
        return obj.is_muted


# ---------------------------------------------------------------------------
# 档口 / 菜品
# ---------------------------------------------------------------------------
class ShopBriefSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    emoji = serializers.SerializerMethodField()
    source = serializers.CharField(source="type", read_only=True)

    class Meta:
        model = Shop
        fields = ("id", "name", "type", "source", "location", "image", "status", "emoji")
        read_only_fields = fields

    def get_image(self, obj: Shop) -> str:
        return absolute_url(self, obj.image)

    def get_emoji(self, obj: Shop) -> str:
        return SHOP_EMOJI.get(obj.type, "🍽️")


class ShopSerializer(ShopBriefSerializer):
    dishCount = serializers.SerializerMethodField()

    class Meta(ShopBriefSerializer.Meta):
        fields = ShopBriefSerializer.Meta.fields + ("dishCount",)
        read_only_fields = fields

    def get_dishCount(self, obj: Shop) -> int:
        return getattr(obj, "dish_count", obj.dishes.count())


class DishBriefSerializer(serializers.ModelSerializer):
    image = serializers.SerializerMethodField()
    emoji = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = ("id", "name", "image", "price", "category", "emoji")
        read_only_fields = fields

    def get_image(self, obj: Dish) -> str:
        return absolute_url(self, obj.image)

    def get_emoji(self, obj: Dish) -> str:
        return CATEGORY_EMOJI.get(obj.category, DEFAULT_DISH_EMOJI)


class DishSerializer(serializers.ModelSerializer):
    shop = ShopBriefSerializer(read_only=True)
    shopId = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    desc = serializers.SerializerMethodField()
    emoji = serializers.SerializerMethodField()
    source = serializers.SerializerMethodField()
    sourceLabel = serializers.SerializerMethodField()
    heat = serializers.IntegerField(read_only=True)
    liked = serializers.SerializerMethodField()
    favorited = serializers.SerializerMethodField()

    class Meta:
        model = Dish
        fields = (
            "id", "name", "shopId", "shop", "image", "description", "desc",
            "price", "category", "emoji", "likes", "favorites", "heat",
            "source", "sourceLabel", "liked", "favorited",
        )
        read_only_fields = fields

    def get_shopId(self, obj: Dish):
        return obj.shop_id

    def get_image(self, obj: Dish) -> str:
        return absolute_url(self, obj.image)

    def get_desc(self, obj: Dish) -> str:
        return obj.description

    def get_emoji(self, obj: Dish) -> str:
        return CATEGORY_EMOJI.get(obj.category, DEFAULT_DISH_EMOJI)

    def get_source(self, obj: Dish) -> str:
        return obj.shop.type if obj.shop_id else Shop.Type.CANTEEN

    def get_sourceLabel(self, obj: Dish) -> str:
        source = obj.shop.type if obj.shop_id else Shop.Type.CANTEEN
        return SOURCE_LABELS.get(source, "食堂")

    def get_liked(self, obj: Dish) -> bool:
        liked = self.context.get("liked_dish_ids")
        return bool(liked is not None and obj.id in liked)

    def get_favorited(self, obj: Dish) -> bool:
        favorited = self.context.get("favorited_dish_ids")
        return bool(favorited is not None and obj.id in favorited)


# ---------------------------------------------------------------------------
# 打卡
# ---------------------------------------------------------------------------
class CheckinSerializer(serializers.ModelSerializer):
    user = UserBriefSerializer(read_only=True)
    userId = serializers.SerializerMethodField()
    who = serializers.SerializerMethodField()
    studentId = serializers.SerializerMethodField()
    image = serializers.SerializerMethodField()
    dish = DishBriefSerializer(read_only=True)
    dishId = serializers.SerializerMethodField()
    dishName = serializers.SerializerMethodField()
    at = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()
    liked = serializers.SerializerMethodField()
    isMine = serializers.SerializerMethodField()

    class Meta:
        model = Checkin
        fields = (
            "id", "user", "userId", "who", "studentId", "content", "image",
            "dish", "dishId", "dishName", "at", "created_at", "createdAt", "liked",
            "visibility", "isMine",
        )
        read_only_fields = fields

    def get_isMine(self, obj: Checkin) -> bool:
        user = self.context.get("request").user if self.context.get("request") else None
        return bool(user and user.is_authenticated and obj.user_id == user.id)

    def get_userId(self, obj: Checkin):
        return obj.user_id

    def get_who(self, obj: Checkin) -> str:
        return obj.user.name or obj.user.username

    def get_studentId(self, obj: Checkin):
        return obj.user.student_id

    def get_image(self, obj: Checkin) -> str:
        return absolute_url(self, obj.image)

    def get_dishId(self, obj: Checkin):
        return obj.dish_id

    def get_dishName(self, obj: Checkin) -> str:
        if obj.dish_id:
            return obj.dish.name
        return obj.dish_name or ""

    def get_at(self, obj: Checkin) -> int:
        return int(obj.created_at.timestamp() * 1000)

    def get_createdAt(self, obj: Checkin) -> str:
        return obj.created_at.isoformat()

    def get_liked(self, obj: Checkin) -> bool:
        liked = self.context.get("liked_checkin_ids")
        return bool(liked is not None and obj.id in liked)


class CheckinCreateSerializer(serializers.Serializer):
    """POST /api/checkins/ 的入参（前端传 content / image(base64) / dish_name）。"""

    content = serializers.CharField(max_length=500, trim_whitespace=True)
    image = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=7_000_000
    )
    dish_id = serializers.IntegerField(required=False, allow_null=True)
    dish = serializers.IntegerField(required=False, allow_null=True)
    dish_name = serializers.CharField(
        required=False, allow_blank=True, default="", max_length=64
    )
    visibility = serializers.ChoiceField(
        choices=Checkin.Visibility.values,
        required=False,
        default=Checkin.Visibility.PUBLIC,
        error_messages={"invalid_choice": "visibility 只能是 public / private"},
    )


# ---------------------------------------------------------------------------
# 投票
# ---------------------------------------------------------------------------
class VoteSerializer(serializers.ModelSerializer):
    creator = UserBriefSerializer(read_only=True)
    targetCount = serializers.SerializerMethodField()
    agree = serializers.SerializerMethodField()
    disagree = serializers.SerializerMethodField()
    need = serializers.SerializerMethodField()
    statusText = serializers.SerializerMethodField()
    deadlineAt = serializers.SerializerMethodField()
    createdAt = serializers.SerializerMethodField()
    my_option = serializers.SerializerMethodField()
    isReview = serializers.SerializerMethodField()
    reviewOf = serializers.SerializerMethodField()
    reviewedBy = serializers.SerializerMethodField()

    class Meta:
        model = Vote
        fields = (
            "id", "title", "target", "status", "statusText", "deadline", "deadlineAt",
            "target_count", "targetCount", "agree_count", "disagree_count",
            "agree", "disagree", "need", "creator", "created_at", "createdAt", "my_option",
            "isReview", "reviewOf", "reviewedBy",
        )
        read_only_fields = fields

    def get_targetCount(self, obj: Vote) -> int:
        return obj.target_count

    def get_agree(self, obj: Vote) -> int:
        return obj.agree_count

    def get_disagree(self, obj: Vote) -> int:
        return obj.disagree_count

    def get_need(self, obj: Vote) -> int:
        return obj.need

    def get_statusText(self, obj: Vote) -> str:
        return obj.get_status_display()

    def get_deadlineAt(self, obj: Vote) -> int:
        return int(obj.deadline.timestamp() * 1000)

    def get_createdAt(self, obj: Vote) -> str:
        return obj.created_at.isoformat()

    def get_my_option(self, obj: Vote):
        options = self.context.get("my_options")
        if options is not None:
            return options.get(obj.id)
        user = self.context.get("user")
        if user is None or not getattr(user, "is_authenticated", False):
            return None
        return (
            VoteRecord.objects.filter(vote=obj, user=user)
            .values_list("option", flat=True)
            .first()
        )

    def get_isReview(self, obj: Vote) -> bool:
        return obj.is_review

    def get_reviewOf(self, obj: Vote):
        return obj.review_of_id

    def get_reviewedBy(self, obj: Vote):
        """这条投票已经被复审过了吗？给前端决定要不要显示「申请复审」。"""
        reviewed = self.context.get("reviewed_ids")
        if reviewed is None:
            return None
        return obj.id in reviewed


class VoteCreateSerializer(serializers.Serializer):
    title = serializers.CharField(max_length=100, trim_whitespace=True)
    target = serializers.CharField(
        max_length=100, required=False, allow_blank=True, default="", trim_whitespace=True
    )
    target_count = serializers.IntegerField(
        required=False,
        default=6,
        min_value=2,
        max_value=99,
        error_messages={
            "min_value": "目标人数至少 2 人",
            "max_value": "目标人数最多 99 人",
        },
    )

    def validate_target_count(self, value: int) -> int:
        low = int(getattr(settings, "VOTE_TARGET_COUNT_MIN", 2))
        high = int(getattr(settings, "VOTE_TARGET_COUNT_MAX", 99))
        if not low <= value <= high:
            raise serializers.ValidationError(f"目标人数需在 {low}~{high} 之间")
        return value


class VoteCastSerializer(serializers.Serializer):
    option = serializers.ChoiceField(
        choices=[VoteRecord.Option.AGREE, VoteRecord.Option.DISAGREE],
        error_messages={"invalid_choice": "option 只能是 agree 或 disagree"},
    )


# ---------------------------------------------------------------------------
# 点赞 / 收藏 / 举报
# ---------------------------------------------------------------------------
class ToggleTargetSerializer(serializers.Serializer):
    target_type = serializers.ChoiceField(
        choices=TargetType.values,
        error_messages={"invalid_choice": "target_type 只能是 dish/shop/checkin/user"},
    )
    target_id = serializers.IntegerField(
        min_value=1, error_messages={"invalid": "target_id 必须是数字", "min_value": "target_id 不合法"}
    )


class FavoriteSerializer(serializers.ModelSerializer):
    dish = serializers.SerializerMethodField()
    favoritedAt = serializers.SerializerMethodField()

    class Meta:
        model = Favorite
        fields = ("id", "target_type", "target_id", "dish", "created_at", "favoritedAt")
        read_only_fields = fields

    def get_dish(self, obj: Favorite):
        return self.context.get("dish_map", {}).get(obj.target_id)

    def get_favoritedAt(self, obj: Favorite) -> int:
        return int(obj.created_at.timestamp() * 1000)


class LikeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Like
        fields = ("id", "target_type", "target_id", "created_at")
        read_only_fields = fields


class ReportSerializer(serializers.ModelSerializer):
    reporter = UserBriefSerializer(read_only=True)
    reported = UserBriefSerializer(read_only=True)

    class Meta:
        model = Report
        fields = (
            "id", "reporter", "reported", "target_type", "target_id",
            "reason", "status", "result", "created_at",
        )
        read_only_fields = fields


class ReportCreateSerializer(serializers.Serializer):
    reported_id = serializers.IntegerField(min_value=1)
    target_type = serializers.ChoiceField(
        choices=TargetType.values,
        error_messages={"invalid_choice": "target_type 只能是 dish/shop/checkin/user"},
    )
    target_id = serializers.IntegerField(min_value=1)
    reason = serializers.CharField(max_length=200, trim_whitespace=True)


# ---------------------------------------------------------------------------
# 认证
# ---------------------------------------------------------------------------
class LoginSerializer(serializers.Serializer):
    username = serializers.CharField(
        max_length=150, error_messages={"blank": "请输入账号"}
    )
    password = serializers.CharField(
        max_length=128, trim_whitespace=False, write_only=True,
        error_messages={"blank": "请输入密码"},
    )


class RegisterSerializer(serializers.Serializer):
    """注册：账号 + 密码 + 学号/姓名/学院。

    注意：注册**不写** ``student_id``。学号要经过 ``/api/auth/bind-student/``
    的「学号 + 姓名 + 学院」三重核验后才会落库，否则随便填个学号就成「已核验」了。
    这里只把姓名/学院记到资料里，响应里 ``verified`` 仍为 ``false``。
    """

    username = serializers.CharField(min_length=3, max_length=150)
    password = serializers.CharField(
        min_length=6, max_length=128, trim_whitespace=False, write_only=True
    )
    student_id = serializers.CharField(
        max_length=32, required=False, allow_blank=True, default=""
    )
    name = serializers.CharField(max_length=32, required=False, allow_blank=True, default="")
    college = serializers.CharField(
        max_length=64, required=False, allow_blank=True, default=""
    )

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("账号不能为空")
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError("这个账号已经被注册了")
        return value

    def validate_password(self, value: str) -> str:
        if len(value) < 6:
            raise serializers.ValidationError("密码至少 6 位")
        return value


class BindStudentSerializer(serializers.Serializer):
    student_id = serializers.CharField(
        max_length=32, error_messages={"blank": "请填写学号"}
    )
    name = serializers.CharField(max_length=32, error_messages={"blank": "请填写姓名"})
    college = serializers.CharField(
        max_length=64, error_messages={"blank": "请填写学院"}
    )



