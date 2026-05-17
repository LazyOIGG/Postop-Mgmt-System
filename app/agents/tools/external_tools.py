from .base import Tool
from .registry import tool_registry

# ── Tool schema ───────────────────────────────────────────────────

GET_WEATHER_SCHEMA = {
    "type": "object",
    "properties": {
        "city": {
            "type": "string",
            "description": "城市名称"
        }
    },
    "required": ["city"]
}

# ── Tool handler ──────────────────────────────────────────────────

async def _get_weather(city: str) -> str:
    return f"天气查询功能即将上线，暂时无法获取「{city}」的天气信息。请注意根据天气适当增减衣物。"


# ── Register tool ─────────────────────────────────────────────────

get_weather_tool = Tool(
    name="get_weather",
    description="查询城市天气信息（预留功能）。",
    parameters=GET_WEATHER_SCHEMA,
    handler=_get_weather
)

tool_registry.register(get_weather_tool)
