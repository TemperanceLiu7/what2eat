"""业务模型：9 张表，表名与字段名严格遵守前端契约。

``users`` / ``shops`` / ``dishes`` / ``checkins`` / ``likes`` / ``favorites`` /
``reports`` / ``votes`` / ``votes_records``

字段名沿用前端（snake_case 落库），DRF 序列化层再补 ``shopId`` / ``desc`` /
``sourceLabel`` 这类 camelCase 别名，前端从 mock 切到真接口时渲染代码不用改。

几个约定：
- 学号已写入即视为「已核验」：``User.is_verified`` 是派生属性，不加额外字段。
- ``ban_until`` 只表示禁言/封禁的到期时间，过期后 ``is_muted`` / ``is_banned``
  自动变 False（不需要定时任务去刷状态）。
- ``seed`` 里的 3 条学籍是「占位账号」（不可登录、无可用密码），
  真实账号通过 ``/api/auth/bind-student/`` 三重核验后占用该学号，占位行随即删除。
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone


# ---------------------------------------------------------------------------
# 1. users
# ---------------------------------------------------------------------------
class User(AbstractUser):
    """继承 AbstractUser：自带 username / password / is_active / date_joined 等。"""

    class Role(models.TextChoices):
        STUDENT = "student", "学生"
        ADMIN = "admin", "管理员"

    class Status(models.TextChoices):
        NORMAL = "normal", "正常"
        MUTED = "muted", "禁言"
        BANNED = "banned", "封禁"

    student_id = models.CharField(
        "学号", max_length=32, unique=True, null=True, blank=True, db_index=True
    )
    name = models.CharField("姓名", max_length=32, blank=True, default="")
    college = models.CharField("学院", max_length=64, blank=True, default="")
    role = models.CharField(
        "角色", max_length=16, choices=Role.choices, default=Role.STUDENT
    )
    status = models.CharField(
        "状态", max_length=16, choices=Status.choices, default=Status.NORMAL
    )
    ban_until = models.DateTimeField("禁言/封禁截止", null=True, blank=True)
    report_count = models.PositiveIntegerField("被举报次数", default=0)

    class Meta:
        db_table = "users"
        verbose_name = "用户"
        verbose_name_plural = "用户"
        ordering = ["-date_joined", "-id"]

    def __str__(self) -> str:
        label = self.name or self.username
        return f"{label}({self.student_id})" if self.student_id else label

    # -- 派生状态 ---------------------------------------------------------
    @property
    def is_verified(self) -> bool:
        """已绑定学号 = 已通过三重核验。"""
        return bool(self.student_id)

    @property
    def is_banned(self) -> bool:
        if self.status != self.Status.BANNED:
            return False
        return self.ban_until is None or self.ban_until > timezone.now()

    @property
    def is_muted(self) -> bool:
        if self.status != self.Status.MUTED:
            return False
        return self.ban_until is None or self.ban_until > timezone.now()

    @property
    def is_roster_placeholder(self) -> bool:
        """seed 生成的「学籍占位账号」：有学号、但密码不可用且不是员工账号。"""
        return bool(self.student_id) and not self.has_usable_password() and not self.is_staff

    # -- 便捷方法（admin bulk action 复用）--------------------------------
    def mute(self, days: int = 3, reason: str = "") -> None:
        self.status = self.Status.MUTED
        self.ban_until = timezone.now() + timedelta(days=days)
        self.save(update_fields=["status", "ban_until"])

    def ban(self, days: int | None = None) -> None:
        self.status = self.Status.BANNED
        self.ban_until = timezone.now() + timedelta(days=days) if days else None
        self.save(update_fields=["status", "ban_until"])

    def unban(self) -> None:
        self.status = self.Status.NORMAL
        self.ban_until = None
        self.save(update_fields=["status", "ban_until"])


# ---------------------------------------------------------------------------
# 2. shops
# ---------------------------------------------------------------------------
class Shop(models.Model):
    class Type(models.TextChoices):
        CANTEEN = "canteen", "食堂"
        TAKEOUT = "takeout", "外卖"
        RESTAURANT = "restaurant", "饭店"
        NIGHT = "night", "夜市"

    class Status(models.TextChoices):
        OPEN = "open", "营业中"
        CLOSED = "closed", "休息中"
        HIDDEN = "hidden", "已下架"

    name = models.CharField("档口名称", max_length=64)
    type = models.CharField("来源类型", max_length=16, choices=Type.choices, db_index=True)
    location = models.CharField("位置", max_length=128, blank=True, default="")
    image = models.ImageField("图片", upload_to="shops/%Y/%m/", blank=True, null=True)
    status = models.CharField(
        "状态", max_length=16, choices=Status.choices, default=Status.OPEN, db_index=True
    )

    class Meta:
        db_table = "shops"
        verbose_name = "档口"
        verbose_name_plural = "档口"
        ordering = ["id"]

    def __str__(self) -> str:
        return self.name

    @property
    def source(self) -> str:
        """前端把档口类型叫 source（canteen/takeout/restaurant/night）。"""
        return self.type


# ---------------------------------------------------------------------------
# 3. dishes
# ---------------------------------------------------------------------------
class Dish(models.Model):
    shop = models.ForeignKey(
        Shop, verbose_name="档口", on_delete=models.CASCADE, related_name="dishes"
    )
    name = models.CharField("菜品名", max_length=64)
    image = models.ImageField("图片", upload_to="dishes/%Y/%m/", blank=True, null=True)
    description = models.CharField("简介", max_length=200, blank=True, default="")
    price = models.DecimalField("价格", max_digits=8, decimal_places=2, default=0)
    category = models.CharField("分类", max_length=32, blank=True, default="", db_index=True)
    likes = models.PositiveIntegerField("点赞数", default=0)
    favorites = models.PositiveIntegerField("收藏数", default=0)

    class Meta:
        db_table = "dishes"
        verbose_name = "菜品"
        verbose_name_plural = "菜品"
        ordering = ["-likes", "-favorites", "id"]
        indexes = [
            models.Index(fields=["shop", "category"], name="idx_dish_shop_cat"),
            models.Index(fields=["-likes"], name="idx_dish_likes"),
        ]
        constraints = [
            models.UniqueConstraint(fields=["shop", "name"], name="uniq_dish_shop_name"),
        ]

    def __str__(self) -> str:
        return f"{self.name}（{self.shop.name}）"

    @property
    def heat(self) -> int:
        """热度 = 点赞 + 收藏，加权随机与人气排序都用它。"""
        return int(self.likes or 0) + int(self.favorites or 0)


# ---------------------------------------------------------------------------
# 4. checkins
# ---------------------------------------------------------------------------
class Checkin(models.Model):
    """打卡。

    ``visibility`` 决定这条记录进哪个板块：
    - ``public``：发布到社区打卡广场，别人能看、能点赞、能举报
    - ``private``：只进「今天吃了啥」个人记录，不进社区，但**一样参与**个人偏好统计
      和随机推荐的去重窗口——所以不加入社区的同学也能攒出自己的口味画像。
    """

    class Visibility(models.TextChoices):
        PUBLIC = "public", "社区可见"
        PRIVATE = "private", "仅自己可见"

    user = models.ForeignKey(
        User, verbose_name="用户", on_delete=models.CASCADE, related_name="checkins"
    )
    content = models.TextField("打卡内容")
    image = models.ImageField("图片", upload_to="checkins/%Y/%m/", blank=True, null=True)
    dish = models.ForeignKey(
        Dish,
        verbose_name="关联菜品",
        on_delete=models.SET_NULL,
        related_name="checkins",
        null=True,
        blank=True,
    )
    # 识别出来的菜名（没关联到 dishes 表时也能记下来，用于偏好统计）
    dish_name = models.CharField("识别/填写的菜名", max_length=64, blank=True, default="")
    visibility = models.CharField(
        "可见范围",
        max_length=16,
        choices=Visibility.choices,
        default=Visibility.PUBLIC,
        db_index=True,
    )
    created_at = models.DateTimeField("发布时间", auto_now_add=True, db_index=True)

    class Meta:
        db_table = "checkins"
        verbose_name = "打卡"
        verbose_name_plural = "打卡"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="idx_checkin_user_time"),
            models.Index(fields=["dish"], name="idx_checkin_dish"),
            models.Index(fields=["visibility", "-created_at"], name="idx_checkin_visibility"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}@{self.created_at:%Y-%m-%d %H:%M}: {self.content[:20]}"

    @property
    def is_public(self) -> bool:
        return self.visibility == self.Visibility.PUBLIC


# ---------------------------------------------------------------------------
# 5. likes  6. favorites（结构相同，target_type + target_id 多态指向）
# ---------------------------------------------------------------------------
class TargetType(models.TextChoices):
    DISH = "dish", "菜品"
    SHOP = "shop", "档口"
    CHECKIN = "checkin", "打卡"
    USER = "user", "用户"


class Like(models.Model):
    user = models.ForeignKey(
        User, verbose_name="用户", on_delete=models.CASCADE, related_name="likes"
    )
    target_type = models.CharField("对象类型", max_length=16, choices=TargetType.choices)
    target_id = models.PositiveBigIntegerField("对象 ID")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "likes"
        verbose_name = "点赞"
        verbose_name_plural = "点赞"
        ordering = ["-id"]
        indexes = [models.Index(fields=["target_type", "target_id"], name="idx_like_target")]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "target_type", "target_id"], name="uniq_like_user_target"
            ),
        ]

    def __str__(self) -> str:
        return f"like {self.target_type}#{self.target_id} by {self.user_id}"


class Favorite(models.Model):
    user = models.ForeignKey(
        User, verbose_name="用户", on_delete=models.CASCADE, related_name="favorites"
    )
    target_type = models.CharField("对象类型", max_length=16, choices=TargetType.choices)
    target_id = models.PositiveBigIntegerField("对象 ID")
    created_at = models.DateTimeField("创建时间", auto_now_add=True)

    class Meta:
        db_table = "favorites"
        verbose_name = "收藏"
        verbose_name_plural = "收藏"
        ordering = ["-id"]
        indexes = [
            models.Index(fields=["target_type", "target_id"], name="idx_fav_target"),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "target_type", "target_id"], name="uniq_fav_user_target"
            ),
        ]

    def __str__(self) -> str:
        return f"fav {self.target_type}#{self.target_id} by {self.user_id}"


# ---------------------------------------------------------------------------
# 7. reports
# ---------------------------------------------------------------------------
class Report(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "待审核"
        APPROVED = "approved", "已通过"
        REJECTED = "rejected", "已驳回"

    reporter = models.ForeignKey(
        User, verbose_name="举报人", on_delete=models.CASCADE, related_name="reports_made"
    )
    reported = models.ForeignKey(
        User, verbose_name="被举报人", on_delete=models.CASCADE, related_name="reports_received"
    )
    target_type = models.CharField("对象类型", max_length=16, choices=TargetType.choices)
    target_id = models.PositiveBigIntegerField("对象 ID")
    reason = models.CharField("举报理由", max_length=200)
    status = models.CharField(
        "处理状态", max_length=16, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    result = models.CharField("处理结果", max_length=200, blank=True, default="")
    created_at = models.DateTimeField("举报时间", auto_now_add=True, db_index=True)

    class Meta:
        db_table = "reports"
        verbose_name = "举报"
        verbose_name_plural = "举报"
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["target_type", "target_id"], name="idx_report_target"),
            models.Index(fields=["status", "-created_at"], name="idx_report_status"),
        ]

    def __str__(self) -> str:
        return f"举报#{self.pk} {self.reporter_id}→{self.reported_id}"


# ---------------------------------------------------------------------------
# 8. votes
# ---------------------------------------------------------------------------
class Vote(models.Model):
    class Status(models.TextChoices):
        ONGOING = "ongoing", "进行中"
        PASSED = "passed", "通过"
        REJECTED = "rejected", "未通过"
        EXPIRED = "expired", "已截止"

    creator = models.ForeignKey(
        User, verbose_name="发起人", on_delete=models.CASCADE, related_name="votes_created"
    )
    title = models.CharField("标题", max_length=100)
    target = models.CharField("投票对象", max_length=100, blank=True, default="")
    status = models.CharField(
        "状态", max_length=16, choices=Status.choices, default=Status.ONGOING, db_index=True
    )
    deadline = models.DateTimeField("截止时间", db_index=True)
    target_count = models.PositiveSmallIntegerField("目标人数", default=6)
    agree_count = models.PositiveIntegerField("同意票数", default=0)
    disagree_count = models.PositiveIntegerField("反对票数", default=0)
    # 复审：指向被复审的原投票；为 NULL 表示这是普通投票
    review_of = models.ForeignKey(
        "self",
        verbose_name="复审的原投票",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reviews",
    )
    created_at = models.DateTimeField("创建时间", auto_now_add=True, db_index=True)

    class Meta:
        db_table = "votes"
        verbose_name = "投票"
        verbose_name_plural = "投票"
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["status", "-created_at"], name="idx_vote_status")]

    def __str__(self) -> str:
        return f"{self.title}（{self.get_status_display()}）"

    # -- 判定规则 ---------------------------------------------------------
    @property
    def need(self) -> int:
        """过半所需票数：floor(target_count / 2) + 1。"""
        return int(self.target_count) // 2 + 1

    @property
    def is_open(self) -> bool:
        return self.status == self.Status.ONGOING and self.deadline > timezone.now()

    @property
    def is_review(self) -> bool:
        """是否是一次复审投票。"""
        return self.review_of_id is not None

    @property
    def is_settled(self) -> bool:
        """是否已经出结果（通过 / 未通过 / 已截止）。"""
        return self.status != self.Status.ONGOING

    def settle(self, save: bool = False) -> str:
        """按过半规则结算状态；``save=True`` 时落库，返回结算后的状态。"""
        if self.status != self.Status.ONGOING:
            return self.status
        if self.agree_count >= self.need:
            self.status = self.Status.PASSED
        elif self.disagree_count >= self.need:
            self.status = self.Status.REJECTED
        else:
            return self.status
        if save:
            self.save(update_fields=["status"])
        return self.status


# ---------------------------------------------------------------------------
# 9. votes_records
# ---------------------------------------------------------------------------
class VoteRecord(models.Model):
    class Option(models.TextChoices):
        AGREE = "agree", "同意"
        DISAGREE = "disagree", "反对"

    vote = models.ForeignKey(
        Vote, verbose_name="投票", on_delete=models.CASCADE, related_name="records"
    )
    user = models.ForeignKey(
        User, verbose_name="投票人", on_delete=models.CASCADE, related_name="vote_records"
    )
    option = models.CharField("选项", max_length=16, choices=Option.choices)
    created_at = models.DateTimeField("投票时间", auto_now_add=True)

    class Meta:
        db_table = "votes_records"
        verbose_name = "投票记录"
        verbose_name_plural = "投票记录"
        ordering = ["-id"]
        # 防刷票：同一个人对同一个投票只能有一条记录
        constraints = [
            models.UniqueConstraint(fields=["vote", "user"], name="uniq_vote_user"),
        ]

    def __str__(self) -> str:
        return f"vote#{self.vote_id} {self.user_id}={self.option}"
