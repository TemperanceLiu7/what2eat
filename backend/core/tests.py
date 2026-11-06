"""接口自检：``python manage.py test``。

覆盖四条核心接口的完整链路（这三条用户明确要求「完整可用」）：
- ``/api/auth/bind-student/`` 三重核验 + 学号唯一
- ``/api/dishes/random/`` 加权随机 + 排除最近 4 条打卡 + source 过滤
- ``/api/checkins/`` 未核验 403 / 禁言 403 / 正常发布
- ``/api/votes/{id}/cast/`` 事务 + 唯一约束 + 过半结算
另外顺手覆盖点赞/收藏/收藏列表/举报和分页信封。
"""
from __future__ import annotations

from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from .models import Checkin, Dish, Favorite, Like, Report, Shop, User, Vote, VoteRecord

REGISTER = "/api/auth/register/"
BIND = "/api/auth/bind-student/"
TOKEN = "/api/auth/token/"
RANDOM = "/api/dishes/random/"
DISHES = "/api/dishes/"
CHECKINS = "/api/checkins/"
LIKE = "/api/likes/toggle/"
FAVORITE = "/api/favorites/toggle/"
FAVORITES = "/api/favorites/"
REPORTS = "/api/reports/"
VOTES = "/api/votes/"


class BaseApiTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.canteen = Shop.objects.create(
            name="一食堂·三层小炒", type=Shop.Type.CANTEEN, location="东区一食堂 3F"
        )
        cls.night = Shop.objects.create(
            name="夜市·烤冷面", type=Shop.Type.NIGHT, location="北门夜市"
        )
        cls.dish_a = Dish.objects.create(
            shop=cls.canteen, name="牛肉拉面", price="13.00", category="面食",
            description="一清二白三红四绿", likes=47, favorites=14,
        )
        cls.dish_b = Dish.objects.create(
            shop=cls.canteen, name="干拌面", price="11.00", category="面食", likes=22, favorites=6
        )
        cls.dish_night = Dish.objects.create(
            shop=cls.night, name="烤冷面", price="9.00", category="小吃", likes=58, favorites=19
        )
        # 学籍名单（seed 里的占位账号等价物）
        for sid, name, college in (
            ("20230001", "张同学", "计算机学院"),
            ("20230002", "李同学", "外国语学院"),
            ("20230003", "王同学", "机械工程学院"),
        ):
            user = User(username=f"roster_{sid}", student_id=sid, name=name, college=college)
            user.set_unusable_password()
            user.save()

    # -- 便捷方法 ---------------------------------------------------------
    def new_client(self, username: str = "stu1") -> tuple[APIClient, str]:
        client = APIClient()
        response = client.post(
            REGISTER,
            {"username": username, "password": "pass1234", "name": username},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        token = response.json()["data"]["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        return client, token

    def bind(self, client: APIClient, sid="20230001", name="张同学", college="计算机学院"):
        return client.post(
            BIND, {"student_id": sid, "name": name, "college": college}, format="json"
        )

    def verified_client(self, username="stu1", sid="20230001", name="张同学", college="计算机学院"):
        client, _ = self.new_client(username)
        response = self.bind(client, sid, name, college)
        self.assertEqual(response.status_code, 200, response.content)
        return client


class AuthTests(BaseApiTest):
    def test_register_login_and_envelope(self):
        client, token = self.new_client("stu_a")
        self.assertTrue(token)

        payload = client.get(CHECKINS).json()
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["message"], "")
        self.assertIn("items", payload["data"])

        login = APIClient().post(TOKEN, {"username": "stu_a", "password": "pass1234"}, format="json")
        self.assertEqual(login.status_code, 200)
        data = login.json()["data"]
        self.assertIn("access", data)
        self.assertIn("refresh", data)
        self.assertIn("token", data)
        self.assertEqual(data["user"]["username"], "stu_a")
        self.assertFalse(data["user"]["verified"])

    def test_login_wrong_password_returns_unauthorized_code(self):
        self.new_client("stu_b")
        response = APIClient().post(TOKEN, {"username": "stu_b", "password": "wrong"}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")

    def test_register_duplicate_username(self):
        self.new_client("dup")
        response = APIClient().post(
            REGISTER, {"username": "dup", "password": "pass1234"}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_DATA")

    def test_bind_student_requires_matching_triple(self):
        client, _ = self.new_client("stu_c")

        wrong = self.bind(client, sid="20230001", name="张同学", college="外国语学院")
        self.assertEqual(wrong.status_code, 400)
        self.assertEqual(wrong.json()["code"], "INVALID_DATA")

        ok = self.bind(client)
        self.assertEqual(ok.status_code, 200, ok.content)
        self.assertTrue(ok.json()["ok"])
        self.assertTrue(ok.json()["data"]["user"]["verified"])
        self.assertEqual(ok.json()["data"]["user"]["student_id"], "20230001")

        me = User.objects.get(username="stu_c")
        self.assertTrue(me.is_verified)
        # 占位账号已被删除，学号不会被二次占用
        self.assertFalse(User.objects.filter(username="roster_20230001").exists())

    def test_bind_student_is_unique_per_account(self):
        self.verified_client("stu_d")
        other, _ = self.new_client("stu_e")
        response = self.bind(other)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_DATA")
        self.assertIn("已被其他账号绑定", response.json()["message"])

    def test_bind_student_requires_login(self):
        response = APIClient().post(
            BIND, {"student_id": "20230001", "name": "张同学", "college": "计算机学院"}, format="json"
        )
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")


class RandomDishTests(BaseApiTest):
    def test_random_returns_single_dish_with_shop(self):
        response = APIClient().get(RANDOM, {"source": "canteen"})
        self.assertEqual(response.status_code, 200, response.content)
        body = response.json()
        self.assertTrue(body["ok"])
        dish = body["data"]["dish"]
        self.assertIn(dish["id"], [self.dish_a.id, self.dish_b.id])
        self.assertIn("shop", dish)
        self.assertEqual(dish["source"], "canteen")
        self.assertIn("likes", dish)

    def test_random_source_filters(self):
        response = APIClient().get(RANDOM, {"source": "night"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["data"]["dish"]["id"], self.dish_night.id)

    def test_random_invalid_source(self):
        response = APIClient().get(RANDOM, {"source": "spaceship"})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_DATA")

    def test_random_empty_source_returns_404(self):
        response = APIClient().get(RANDOM, {"source": "takeout"})
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["code"], "NOT_FOUND")

    def test_random_excludes_recent_four_checkins(self):
        """4 道菜被最近打卡占掉后，只剩第 5 道可抽 —— 结果必然唯一。"""
        shop = Shop.objects.create(name="新档口", type=Shop.Type.RESTAURANT)
        dishes = [
            Dish.objects.create(shop=shop, name=f"菜{i}", price="10.00", category="热菜")
            for i in range(5)
        ]
        client = self.verified_client("stu_f", "20230003", "王同学", "机械工程学院")
        user = User.objects.get(username="stu_f")
        for dish in dishes[:4]:
            client.post(
                CHECKINS, {"content": f"吃了{dish.name}", "dish_id": dish.id}, format="json"
            )
        Checkin.objects.filter(user=user).count()
        self.assertEqual(Checkin.objects.filter(user=user).count(), 4)

        for _ in range(5):
            response = client.get(RANDOM, {"source": "restaurant"})
            self.assertEqual(response.status_code, 200, response.content)
            self.assertEqual(response.json()["data"]["dish"]["id"], dishes[4].id)


class CheckinTests(BaseApiTest):
    def test_checkin_requires_verified(self):
        client, _ = self.new_client("stu_g")
        response = client.post(CHECKINS, {"content": "好吃"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "UNVERIFIED")

    def test_checkin_requires_login(self):
        response = APIClient().post(CHECKINS, {"content": "好吃"}, format="json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["code"], "UNAUTHORIZED")

    def test_checkin_create_and_list(self):
        client = self.verified_client("stu_h")
        response = client.post(
            CHECKINS,
            {"content": "三食堂牛肉面，加了个蛋", "dish_name": "牛肉拉面"},
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        body = response.json()
        self.assertTrue(body["ok"])
        self.assertEqual(body["message"], "打卡成功")
        self.assertEqual(body["data"]["checkin"]["dishName"], "牛肉拉面")
        self.assertTrue(body["data"]["checkin"]["at"] > 0)

        listing = client.get(CHECKINS).json()["data"]
        self.assertEqual(listing["total"], 1)
        item = listing["items"][0]
        self.assertEqual(item["content"], "三食堂牛肉面，加了个蛋")
        self.assertEqual(item["who"], "张同学")  # 绑定学籍后姓名以学籍为准
        self.assertFalse(item["liked"])

    def test_checkin_muted_user_blocked(self):
        client = self.verified_client("stu_i", "20230002", "李同学", "外国语学院")
        user = User.objects.get(username="stu_i")
        user.status = User.Status.MUTED
        user.ban_until = timezone.now() + timedelta(days=1)
        user.save(update_fields=["status", "ban_until"])

        response = client.post(CHECKINS, {"content": "还能发吗"}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "BANNED")

    def test_checkin_blank_content_rejected(self):
        client = self.verified_client("stu_j", "20230002", "李同学", "外国语学院")
        response = client.post(CHECKINS, {"content": "   "}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_DATA")


class LikeFavoriteTests(BaseApiTest):
    def test_like_toggle_updates_counter(self):
        client = self.verified_client("stu_k")
        first = client.post(
            LIKE, {"target_type": "dish", "target_id": self.dish_a.id}, format="json"
        )
        self.assertEqual(first.status_code, 200, first.content)
        self.assertTrue(first.json()["data"]["liked"])
        self.dish_a.refresh_from_db()
        self.assertEqual(self.dish_a.likes, 48)

        second = client.post(
            LIKE, {"target_type": "dish", "target_id": self.dish_a.id}, format="json"
        )
        self.assertFalse(second.json()["data"]["liked"])
        self.dish_a.refresh_from_db()
        self.assertEqual(self.dish_a.likes, 47)
        self.assertEqual(Like.objects.count(), 0)

    def test_favorite_toggle_and_list(self):
        client = self.verified_client("stu_l")
        response = client.post(
            FAVORITE, {"target_type": "dish", "target_id": self.dish_a.id}, format="json"
        )
        self.assertTrue(response.json()["data"]["favorited"])
        self.dish_a.refresh_from_db()
        self.assertEqual(self.dish_a.favorites, 15)

        items = client.get(FAVORITES).json()["data"]["items"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["id"], self.dish_a.id)   # 菜品类收藏直接展开
        self.assertEqual(items[0]["name"], "牛肉拉面")
        self.assertTrue(items[0]["favorited"])
        self.assertEqual(Favorite.objects.count(), 1)

    def test_toggle_rejects_unknown_target(self):
        client = self.verified_client("stu_m")
        response = client.post(
            LIKE, {"target_type": "dish", "target_id": 999999}, format="json"
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "INVALID_DATA")


class VoteTests(BaseApiTest):
    def test_cast_vote_is_idempotent_guarded(self):
        client = self.verified_client("stu_n")
        created = client.post(
            VOTES, {"title": "今晚吃不吃鸡公煲", "target": "西门鸡公煲", "target_count": 3}, format="json"
        )
        self.assertEqual(created.status_code, 201, created.content)
        vote = created.json()["data"]["vote"]
        self.assertEqual(vote["status"], "ongoing")
        self.assertEqual(vote["need"], 2)  # floor(3/2)+1

        cast = client.post(f"{VOTES}{vote['id']}/cast/", {"option": "agree"}, format="json")
        self.assertEqual(cast.status_code, 200, cast.content)
        self.assertEqual(cast.json()["data"]["vote"]["agree_count"], 1)
        self.assertEqual(cast.json()["data"]["vote"]["status"], "ongoing")

        again = client.post(f"{VOTES}{vote['id']}/cast/", {"option": "disagree"}, format="json")
        self.assertEqual(again.status_code, 409)
        self.assertEqual(again.json()["code"], "ALREADY_VOTED")

    def test_vote_passes_after_majority(self):
        creator = self.verified_client("stu_o")
        vote = creator.post(VOTES, {"title": "去吃火锅", "target_count": 3}, format="json").json()["data"]["vote"]

        creator.post(f"{VOTES}{vote['id']}/cast/", {"option": "agree"}, format="json")
        other = self.verified_client("stu_p", "20230002", "李同学", "外国语学院")
        result = other.post(f"{VOTES}{vote['id']}/cast/", {"option": "agree"}, format="json")

        body = result.json()["data"]["vote"]
        self.assertEqual(body["agree_count"], 2)
        self.assertEqual(body["status"], "passed")
        self.assertEqual(body["statusText"], "通过")

        third = self.verified_client("stu_q", "20230003", "王同学", "机械工程学院")
        closed = third.post(f"{VOTES}{vote['id']}/cast/", {"option": "disagree"}, format="json")
        self.assertEqual(closed.status_code, 409)
        self.assertEqual(closed.json()["code"], "VOTE_CLOSED")

    def test_vote_rejected_after_majority_disagree(self):
        creator = self.verified_client("stu_r")
        vote = creator.post(VOTES, {"title": "吃不吃夜宵", "target_count": 2}, format="json").json()["data"]["vote"]
        need = vote["need"]
        self.assertEqual(need, 2)

        creator.post(f"{VOTES}{vote['id']}/cast/", {"option": "disagree"}, format="json")
        other = self.verified_client("stu_s", "20230002", "李同学", "外国语学院")
        body = other.post(f"{VOTES}{vote['id']}/cast/", {"option": "disagree"}, format="json").json()["data"]["vote"]
        self.assertEqual(body["status"], "rejected")

    def test_vote_expired_deadline(self):
        client = self.verified_client("stu_t")
        vote = client.post(VOTES, {"title": "过期投票", "target_count": 2}, format="json").json()["data"]["vote"]
        Vote.objects.filter(pk=vote["id"]).update(deadline=timezone.now() - timedelta(minutes=1))

        response = client.post(f"{VOTES}{vote['id']}/cast/", {"option": "agree"}, format="json")
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["code"], "VOTE_CLOSED")
        self.assertEqual(Vote.objects.get(pk=vote["id"]).status, Vote.Status.EXPIRED)

    def test_vote_requires_verified(self):
        client, _ = self.new_client("stu_u")
        response = client.post(VOTES, {"title": "没核验能不能投票", "target_count": 3}, format="json")
        self.assertEqual(response.status_code, 403)
        self.assertEqual(response.json()["code"], "UNVERIFIED")

    def test_vote_list_includes_my_option(self):
        client = self.verified_client("stu_v")
        vote = client.post(VOTES, {"title": "列表回显", "target_count": 4}, format="json").json()["data"]["vote"]
        client.post(f"{VOTES}{vote['id']}/cast/", {"option": "agree"}, format="json")

        listing = client.get(VOTES).json()["data"]
        self.assertEqual(listing["total"], 1)
        self.assertEqual(listing["items"][0]["my_option"], "agree")
        self.assertEqual(listing["items"][0]["agree"], 1)


class ReportAndPaginationTests(BaseApiTest):
    def test_report_increments_report_count(self):
        client = self.verified_client("stu_w")
        author = self.verified_client("stu_x", "20230002", "李同学", "外国语学院")
        checkin = author.post(CHECKINS, {"content": "内容有问题"}, format="json").json()["data"]["checkin"]
        reported = User.objects.get(username="stu_x")

        response = client.post(
            REPORTS,
            {
                "reported_id": reported.id,
                "target_type": "checkin",
                "target_id": checkin["id"],
                "reason": "内容与食堂无关",
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201, response.content)
        self.assertEqual(response.json()["data"]["reportCount"], 1)
        self.assertEqual(Report.objects.count(), 1)

        duplicate = client.post(
            REPORTS,
            {
                "reported_id": reported.id,
                "target_type": "checkin",
                "target_id": checkin["id"],
                "reason": "再举报一次",
            },
            format="json",
        )
        self.assertEqual(duplicate.status_code, 400)
        self.assertEqual(duplicate.json()["code"], "INVALID_DATA")

    def test_dish_list_pagination_envelope(self):
        for i in range(12):
            Dish.objects.create(
                shop=self.canteen, name=f"批量菜{i}", price="10.00", category="热菜"
            )
        response = APIClient().get(DISHES, {"page": 1, "page_size": 5})
        self.assertEqual(response.status_code, 200)
        data = response.json()["data"]
        self.assertEqual(data["page_size"], 5)
        self.assertEqual(len(data["items"]), 5)
        self.assertEqual(data["total"], 15)
        self.assertEqual(data["pages"], 3)

        page2 = APIClient().get(DISHES, {"page": 2, "page_size": 5}).json()["data"]
        self.assertEqual(page2["page"], 2)
        self.assertEqual(len(page2["items"]), 5)

    def test_cors_preflight(self):
        response = APIClient().options(
            RANDOM,
            HTTP_ORIGIN="http://localhost:5173",
            HTTP_ACCESS_CONTROL_REQUEST_METHOD="GET",
        )
        self.assertEqual(response.status_code, 204)
        self.assertEqual(response["Access-Control-Allow-Origin"], "http://localhost:5173")
