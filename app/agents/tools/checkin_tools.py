from app.db.session import db_instance
from .base import Tool
from .registry import tool_registry

# ── Tool schemas ──────────────────────────────────────────────────

GET_RECENT_CHECKINS_SCHEMA = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "description": "用户名"
        },
        "days": {
            "type": "integer",
            "description": "查询最近几天的数据，默认7天"
        }
    },
    "required": ["username"]
}

GET_CHECKIN_TREND_SCHEMA = {
    "type": "object",
    "properties": {
        "username": {
            "type": "string",
            "description": "用户名"
        },
        "days": {
            "type": "integer",
            "description": "统计最近几天的趋势，默认7天"
        }
    },
    "required": ["username"]
}

# ── Tool handlers ─────────────────────────────────────────────────

async def _get_recent_checkins(username: str, days: int = 7) -> str:
    records = db_instance.get_recent_checkins_for_overview(username, days)
    if not records:
        return f"最近 {days} 天暂无打卡记录。"
    lines = [f"最近 {len(records)} 天打卡记录："]
    for r in records:
        cdate = r.get("checkin_date", "未知日期")
        temp = r.get("temperature", "-")
        bp = r.get("blood_pressure", "-")
        abnormal = "⚠️异常" if r.get("abnormal_flag") else "正常"
        lines.append(f"  {cdate} | 体温:{temp}℃ | 血压:{bp} | {abnormal}")
    return "\n".join(lines)


async def _get_checkin_trend(username: str, days: int = 7) -> str:
    records = db_instance.get_daily_checkins(username, days)
    if not records:
        return f"最近 {days} 天暂无打卡数据，无法生成趋势分析。"

    temps = []
    abnormals = 0
    for r in records:
        t = r.get("temperature")
        if t is not None:
            temps.append(float(t))
        if r.get("abnormal_flag"):
            abnormals += 1

    summary = f"最近 {len(records)} 天（共 {days} 天查询范围）打卡趋势：\n"
    if temps:
        avg_temp = sum(temps) / len(temps)
        summary += f"- 平均体温：{avg_temp:.1f}℃\n"
    summary += f"- 异常天数：{abnormals} 天\n"
    if abnormals > 0:
        summary += "⚠️ 存在异常记录，建议关注身体状况。"
    else:
        summary += "各项指标总体平稳。"
    return summary


# ── Register tools ────────────────────────────────────────────────

get_recent_checkins_tool = Tool(
    name="get_recent_checkins",
    description="查询用户最近的健康打卡记录。当用户询问打卡情况、最近身体数据时使用。",
    parameters=GET_RECENT_CHECKINS_SCHEMA,
    handler=_get_recent_checkins
)

get_checkin_trend_tool = Tool(
    name="get_checkin_trend",
    description="分析用户近期健康打卡趋势（体温、异常情况）。当用户询问健康趋势、恢复情况时使用。",
    parameters=GET_CHECKIN_TREND_SCHEMA,
    handler=_get_checkin_trend
)

tool_registry.register(get_recent_checkins_tool)
tool_registry.register(get_checkin_trend_tool)
