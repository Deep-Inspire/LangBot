from __future__ import annotations

from typing import Any

from langbot_plugin.api.definition.components.tool.tool import Tool
from langbot_plugin.api.entities.builtin.provider import session as provider_session

from main import WecomAPIError, WecomAssistantPlugin


class GetUserProfile(Tool):
    """Fetch basic WeCom user profile details."""

    def __init__(self) -> None:
        super().__init__()
        self.plugin: WecomAssistantPlugin

    async def call(self, params: dict[str, Any], session: provider_session.Session, query_id: int) -> dict[str, Any]:
        user_id = (params.get("user_id") or "").strip()
        if not user_id:
            return {"error": "user_id is required"}

        try:
            client = self.plugin.require_client()
            profile = await client.get_user_profile(user_id)
        except WecomAPIError as exc:
            return {"error": exc.args[0], "errcode": exc.errcode}
        except Exception as exc:  # pragma: no cover - safeguard for unexpected errors
            return {"error": str(exc)}

        # Remove noisy fields that are not typically needed in chat responses
        cleaned = {k: v for k, v in profile.items() if k not in {"errcode", "errmsg"}}
        return cleaned
