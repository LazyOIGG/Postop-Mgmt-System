from typing import Any, Optional


class ApiResponse:
    """统一 API 响应封装"""

    @staticmethod
    def ok(data: Any = None, message: str = "操作成功") -> dict:
        return {"success": True, "code": 200, "message": message, "data": data}

    @staticmethod
    def fail(message: str = "操作失败", code: int = 400, data: Any = None) -> dict:
        return {"success": False, "code": code, "message": message, "data": data}

    @staticmethod
    def paginated(items: list, total: int, page: int = 1, page_size: int = 20) -> dict:
        return {
            "success": True,
            "code": 200,
            "message": "操作成功",
            "data": items,
            "pagination": {
                "total": total,
                "page": page,
                "page_size": page_size,
                "pages": (total + page_size - 1) // page_size,
            },
        }
