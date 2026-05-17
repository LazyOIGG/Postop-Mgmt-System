from typing import Dict, List
from .base import Tool


class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get_openai_tools(self, tool_names: List[str]) -> List[Dict]:
        schemas = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool.name,
                        "description": tool.description,
                        "parameters": tool.parameters
                    }
                })
        return schemas

    async def execute(self, name: str, args: Dict) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"[错误] 未找到工具: {name}"
        try:
            result = await tool.handler(**args)
            return str(result)
        except Exception as e:
            return f"[工具执行失败] {name}: {str(e)}"


tool_registry = ToolRegistry()
