"""分页：统一输出 ``data.items / total / page / page_size / pages``。"""
from __future__ import annotations

from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

from .responses import ok


class EnvelopePagination(PageNumberPagination):
    """默认每页大小由 settings.REST_FRAMEWORK['PAGE_SIZE'] 提供（10）。"""

    page_size_query_param = "page_size"   # ?page_size=20
    max_page_size = 100

    def get_paginated_response(self, data) -> Response:
        return ok(
            {
                "items": data,
                "total": self.page.paginator.count,
                "page": self.page.number,
                "page_size": self.get_page_size(self.request),
                "pages": self.page.paginator.num_pages,
            }
        )

    def get_paginated_response_schema(self, schema: dict) -> dict:
        return {
            "type": "object",
            "properties": {
                "ok": {"type": "boolean"},
                "message": {"type": "string"},
                "data": {
                    "type": "object",
                    "properties": {
                        "items": schema,
                        "total": {"type": "integer"},
                        "page": {"type": "integer"},
                        "page_size": {"type": "integer"},
                        "pages": {"type": "integer"},
                    },
                },
            },
        }
