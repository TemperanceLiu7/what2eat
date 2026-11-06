"""Django 后台：菜品维护、举报审核、禁言/解禁。

三块重点：
1. 菜品维护 —— ``ShopAdmin`` 内联菜品 + ``DishAdmin`` 搜索/批量重算热度；
2. 举报审核 —— ``ReportAdmin`` 的「通过 / 驳回 / 通过并禁言」批量操作，
   通过时累计被举报人的 ``report_count``，到阈值自动禁言；
3. 禁言 / 解禁 —— ``UserAdmin`` 的批量操作，写 ``status`` + ``ban_until``，
   到期后 ``is_muted`` / ``is_banned`` 自动失效，不需要定时任务。
"""
from __future__ import annotations

from datetime import timedelta

from django.conf import settings
from django.contrib import admin, messages
from django.contrib.admin.exceptions import NotRegistered
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.db.models import Count, F
from django.utils import timezone

from .models import Checkin, Dish, Favorite, Like, Report, Shop, User, Vote, VoteRecord

UserModel = get_user_model()


# ---------------------------------------------------------------------------
# 用户：禁言 / 解禁的批量操作
# ---------------------------------------------------------------------------
try:  # django.contrib.auth.admin 会先注册默认 User，这里替换成自定义的
    admin.site.unregister(UserModel)
except NotRegistered:
    pass


@admin.register(UserModel)
class UserAdmin(BaseUserAdmin):
    list_display = (
        "id", "username", "name", "student_id", "college",
        "role", "status", "ban_until", "report_count", "is_staff",
    )
    list_filter = ("role", "status", "is_staff", "is_superuser", "college")
    search_fields = ("username", "name", "student_id", "college", "email")
    ordering = ("-date_joined", "-id")
    list_per_page = 30
    readonly_fields = ("last_login", "date_joined", "report_count")
    actions = ("action_mute_1_day", "action_mute_3_days", "action_mute_7_days",
               "action_ban", "action_unban")

    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "校园身份",
            {
                "fields": ("student_id", "name", "college", "role", "report_count"),
                "description": "学号落库即视为已核验；学号唯一，一个学号只能绑一个账号。",
            },
        ),
        (
            "风控",
            {
                "fields": ("status", "ban_until"),
                "description": "禁言/封禁到期时间留空表示长期有效；到期后自动失效。",
            },
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ("校园身份", {"fields": ("student_id", "name", "college", "role")}),
    )

    def _mute(self, request, queryset, days: int, label: str):
        until = timezone.now() + timedelta(days=days)
        updated = queryset.update(status=User.Status.MUTED, ban_until=until)
        self.message_user(
            request, f"已{label} {updated} 个账号，截止 {until:%Y-%m-%d %H:%M}", messages.SUCCESS
        )

    @admin.action(description="禁言 1 天")
    def action_mute_1_day(self, request, queryset):
        self._mute(request, queryset, 1, "禁言")

    @admin.action(description="禁言 3 天")
    def action_mute_3_days(self, request, queryset):
        self._mute(request, queryset, 3, "禁言")

    @admin.action(description="禁言 7 天")
    def action_mute_7_days(self, request, queryset):
        self._mute(request, queryset, 7, "禁言")

    @admin.action(description="封禁（长期）")
    def action_ban(self, request, queryset):
        updated = queryset.update(status=User.Status.BANNED, ban_until=None)
        self.message_user(request, f"已封禁 {updated} 个账号", messages.SUCCESS)

    @admin.action(description="解禁 / 恢复正常")
    def action_unban(self, request, queryset):
        updated = queryset.update(status=User.Status.NORMAL, ban_until=None)
        self.message_user(request, f"已解禁 {updated} 个账号", messages.SUCCESS)


# ---------------------------------------------------------------------------
# 档口 / 菜品维护
# ---------------------------------------------------------------------------
class DishInline(admin.TabularInline):
    model = Dish
    extra = 0
    fields = ("name", "price", "category", "likes", "favorites", "image")
    show_change_link = True


@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "type", "location", "status", "dish_count")
    list_filter = ("type", "status")
    search_fields = ("name", "location")
    list_editable = ("status",)
    inlines = (DishInline,)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(_dish_count=Count("dishes"))

    @admin.display(description="菜品数", ordering="_dish_count")
    def dish_count(self, obj: Shop) -> int:
        return obj._dish_count


@admin.register(Dish)
class DishAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "shop", "price", "category", "likes", "favorites", "heat")
    list_filter = ("shop", "category", "shop__type")
    search_fields = ("name", "description", "shop__name")
    list_editable = ("price", "category")
    list_select_related = ("shop",)
    autocomplete_fields = ("shop",)
    list_per_page = 30
    actions = ("action_recount", "action_reset_heat")

    @admin.display(description="热度", ordering="likes")
    def heat(self, obj: Dish) -> int:
        return obj.heat

    @admin.action(description="重新统计点赞 / 收藏数（以 likes、favorites 表为准）")
    def action_recount(self, request, queryset):
        dish_ids = list(queryset.values_list("id", flat=True))
        like_map = dict(
            Like.objects.filter(target_type="dish", target_id__in=dish_ids)
            .values_list("target_id")
            .annotate(total=Count("id"))
        )
        fav_map = dict(
            Favorite.objects.filter(target_type="dish", target_id__in=dish_ids)
            .values_list("target_id")
            .annotate(total=Count("id"))
        )
        for dish_id in dish_ids:
            Dish.objects.filter(pk=dish_id).update(
                likes=like_map.get(dish_id, 0), favorites=fav_map.get(dish_id, 0)
            )
        self.message_user(request, f"已重算 {len(dish_ids)} 道菜的计数", messages.SUCCESS)

    @admin.action(description="重置热度（点赞 / 收藏清零）")
    def action_reset_heat(self, request, queryset):
        updated = queryset.update(likes=0, favorites=0)
        self.message_user(request, f"已重置 {updated} 道菜的热度", messages.SUCCESS)


# ---------------------------------------------------------------------------
# 打卡 / 点赞 / 收藏
# ---------------------------------------------------------------------------
@admin.register(Checkin)
class CheckinAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "content_preview", "dish", "created_at")
    list_filter = ("created_at", "dish__shop")
    search_fields = ("content", "user__username", "user__name")
    list_select_related = ("user", "dish")
    date_hierarchy = "created_at"
    autocomplete_fields = ("user", "dish")
    readonly_fields = ("created_at",)

    @admin.display(description="内容")
    def content_preview(self, obj: Checkin) -> str:
        return obj.content[:40] + ("…" if len(obj.content) > 40 else "")


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "target_type", "target_id", "created_at")
    list_filter = ("target_type", "created_at")
    search_fields = ("user__username", "user__name")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)


@admin.register(Favorite)
class FavoriteAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "target_type", "target_id", "created_at")
    list_filter = ("target_type", "created_at")
    search_fields = ("user__username", "user__name")
    autocomplete_fields = ("user",)
    readonly_fields = ("created_at",)


# ---------------------------------------------------------------------------
# 举报审核
# ---------------------------------------------------------------------------
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = (
        "id", "reporter", "reported", "target_type", "target_id",
        "reason", "status", "created_at",
    )
    list_filter = ("status", "target_type", "created_at")
    search_fields = ("reason", "reporter__username", "reported__username", "reported__name")
    list_select_related = ("reporter", "reported")
    date_hierarchy = "created_at"
    readonly_fields = ("created_at",)
    actions = ("action_approve", "action_approve_and_mute", "action_reject")

    @admin.action(description="通过举报（计入被举报人违规次数）")
    def action_approve(self, request, queryset):
        approved = 0
        for report in queryset.filter(status=Report.Status.PENDING).select_related("reported"):
            reported = report.reported
            UserModel.objects.filter(pk=reported.pk).update(report_count=F("report_count") + 1)
            reported.refresh_from_db(fields=["report_count"])
            report.status = Report.Status.APPROVED
            report.result = f"举报属实，已计入违规次数（累计 {reported.report_count} 次）"
            report.save(update_fields=["status", "result"])
            self._maybe_auto_mute(reported)
            approved += 1
        self.message_user(request, f"已通过 {approved} 条举报", messages.SUCCESS)

    @admin.action(description="通过举报并禁言 3 天")
    def action_approve_and_mute(self, request, queryset):
        muted = 0
        for report in queryset.filter(status=Report.Status.PENDING).select_related("reported"):
            reported = report.reported
            UserModel.objects.filter(pk=reported.pk).update(report_count=F("report_count") + 1)
            reported.refresh_from_db(fields=["report_count"])
            reported.mute(days=3)
            report.status = Report.Status.APPROVED
            report.result = "举报属实，已禁言 3 天"
            report.save(update_fields=["status", "result"])
            muted += 1
        self.message_user(request, f"已通过并禁言 {muted} 条举报", messages.SUCCESS)

    @admin.action(description="驳回举报")
    def action_reject(self, request, queryset):
        updated = queryset.filter(status=Report.Status.PENDING).update(
            status=Report.Status.REJECTED, result="举报不成立，已驳回"
        )
        self.message_user(request, f"已驳回 {updated} 条举报", messages.SUCCESS)

    @staticmethod
    def _maybe_auto_mute(reported) -> None:
        threshold = int(getattr(settings, "AUTO_MUTE_REPORT_COUNT", 0))
        if threshold and reported.report_count >= threshold and not reported.is_banned:
            hours = int(getattr(settings, "AUTO_MUTE_HOURS", 24))
            reported.status = User.Status.MUTED
            reported.ban_until = timezone.now() + timedelta(hours=hours)
            reported.save(update_fields=["status", "ban_until"])


# ---------------------------------------------------------------------------
# 投票
# ---------------------------------------------------------------------------
class VoteRecordInline(admin.TabularInline):
    model = VoteRecord
    extra = 0
    fields = ("user", "option", "created_at")
    readonly_fields = ("created_at",)
    can_delete = False


@admin.register(Vote)
class VoteAdmin(admin.ModelAdmin):
    list_display = (
        "id", "title", "target", "status", "target_count", "need_display",
        "agree_count", "disagree_count", "deadline", "created_at",
    )
    list_filter = ("status", "created_at")
    search_fields = ("title", "target", "creator__username")
    list_select_related = ("creator",)
    date_hierarchy = "created_at"
    inlines = (VoteRecordInline,)
    readonly_fields = ("created_at", "agree_count", "disagree_count")
    actions = ("action_settle", "action_close")

    @admin.display(description="过半所需")
    def need_display(self, obj: Vote) -> int:
        return obj.need

    @admin.action(description="按当前票数结算选中投票")
    def action_settle(self, request, queryset):
        settled = 0
        for vote in queryset:
            before = vote.status
            vote.settle(save=False)
            if vote.status != before:
                vote.save(update_fields=["status"])
                settled += 1
        self.message_user(request, f"已结算 {settled} 个投票", messages.SUCCESS)

    @admin.action(description="立即截止")
    def action_close(self, request, queryset):
        updated = queryset.filter(status=Vote.Status.ONGOING).update(
            status=Vote.Status.EXPIRED
        )
        self.message_user(request, f"已截止 {updated} 个投票", messages.SUCCESS)


@admin.register(VoteRecord)
class VoteRecordAdmin(admin.ModelAdmin):
    list_display = ("id", "vote", "user", "option", "created_at")
    list_filter = ("option", "created_at")
    search_fields = ("vote__title", "user__username", "user__name")
    list_select_related = ("vote", "user")
    readonly_fields = ("created_at",)
