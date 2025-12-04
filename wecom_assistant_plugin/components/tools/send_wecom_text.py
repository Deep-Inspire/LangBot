from __future__ import annotations

from typing import Any

from langbot_plugin.api.definition.components.tool.tool import Tool
from langbot_plugin.api.entities.builtin.provider import session as provider_session

from main import WecomAPIError, WecomAssistantPlugin


class SendWecomText(Tool):
    """Tool for sending WeCom text or markdown messages."""

    def __init__(self) -> None:
        super().__init__()
        self.plugin: WecomAssistantPlugin

    async def call(self, params: dict[str, Any], session: provider_session.Session, query_id: int) -> dict[str, Any]:
        content = (params.get("content") or "").strip()
        if not content:
            return {"error": "content is required"}

        if not any(params.get(key) for key in ("user_id", "party_id", "tag_id")):
            return {"error": "At least one of user_id, party_id, or tag_id is required"}

        msgtype = (params.get("msgtype") or "text").lower()
        if msgtype not in {"text", "markdown"}:
            msgtype = "text"

        try:
            client = self.plugin.require_client()
            resp = await client.send_message(
                to_user=params.get("user_id") or None,
                to_party=params.get("party_id") or None,
                to_tag=params.get("tag_id") or None,
                content=content,
                msgtype=msgtype,
                safe=params.get("safe"),
            )
        except WecomAPIError as exc:
            return {"error": exc.args[0], "errcode": exc.errcode}
        except Exception as exc:  # pragma: no cover - safeguard for unexpected errors
            return {"error": str(exc)}

        return {
            "status": "ok",
            "invaliduser": resp.get("invaliduser", ""),
            "invalidparty": resp.get("invalidparty", ""),
            "invalidtag": resp.get("invalidtag", ""),
        }
