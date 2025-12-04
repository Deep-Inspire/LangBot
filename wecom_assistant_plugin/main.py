from __future__ import annotations

import time
from typing import Any, Dict, Optional

import httpx
from langbot_plugin.api.definition.plugin import BasePlugin


class WecomAPIError(Exception):
    """Raised when WeCom API responds with an error."""

    def __init__(self, message: str, errcode: Optional[int] = None):
        super().__init__(message)
        self.errcode = errcode


class WecomApiClient:
    """Lightweight Enterprise WeChat API helper with token caching."""

    def __init__(
        self,
        corp_id: str,
        agent_secret: str,
        agent_id: int,
        base_url: str,
        contacts_secret: Optional[str] = None,
        safe_mode: bool = False,
    ) -> None:
        self.corp_id = corp_id
        self.agent_secret = agent_secret
        self.contacts_secret = contacts_secret
        self.agent_id = agent_id
        self.base_url = base_url.rstrip("/")
        self.safe_mode = safe_mode
        self._token_cache: Dict[str, tuple[str, float]] = {}

    async def _fetch_token(self, secret: str) -> str:
        url = f"{self.base_url}/cgi-bin/gettoken"
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                url,
                params={"corpid": self.corp_id, "corpsecret": secret},
                timeout=15,
            )
            data = resp.json()

        if data.get("errcode") != 0:
            raise WecomAPIError(
                f"Failed to fetch access_token: {data.get('errmsg')}", data.get("errcode")
            )

        expires_at = time.time() + max(data.get("expires_in", 7200) - 120, 0)
        token = data["access_token"]
        self._token_cache[secret] = (token, expires_at)
        return token

    async def _get_token(self, secret: str) -> str:
        cached = self._token_cache.get(secret)
        if cached and cached[1] > time.time():
            return cached[0]
        return await self._fetch_token(secret)

    async def _request(
        self,
        method: str,
        path: str,
        secret: str,
        *,
        params: Optional[dict[str, Any]] = None,
        json: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        token = await self._get_token(secret)
        url = f"{self.base_url}{path}"
        merged_params = {"access_token": token, **(params or {})}

        async with httpx.AsyncClient() as client:
            resp = await client.request(method, url, params=merged_params, json=json, timeout=20)
            data = resp.json()

        errcode = data.get("errcode", 0)
        if errcode not in (0, None):
            if errcode in (40014, 42001, 42009):
                self._token_cache.pop(secret, None)
            raise WecomAPIError(data.get("errmsg", "WeCom API error"), errcode)

        return data

    async def send_message(
        self,
        *,
        to_user: Optional[str] = None,
        to_party: Optional[str] = None,
        to_tag: Optional[str] = None,
        content: str,
        msgtype: str = "text",
        safe: Optional[bool] = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "touser": to_user or "",
            "toparty": to_party or "",
            "totag": to_tag or "",
            "agentid": self.agent_id,
            "safe": 1 if (safe if safe is not None else self.safe_mode) else 0,
        }

        if msgtype == "markdown":
            payload.update({"msgtype": "markdown", "markdown": {"content": content}})
        else:
            payload.update({"msgtype": "text", "text": {"content": content}})

        return await self._request(
            "POST",
            "/cgi-bin/message/send",
            self.agent_secret,
            json=payload,
        )

    async def get_user_profile(self, user_id: str) -> dict[str, Any]:
        secret = self.contacts_secret or self.agent_secret
        return await self._request(
            "GET",
            "/cgi-bin/user/get",
            secret,
            params={"userid": user_id},
        )

    async def ping(self) -> dict[str, Any]:
        # Lightweight endpoint to validate the token without side effects.
        return await self._request(
            "GET",
            "/cgi-bin/get_api_domain_ip",
            self.contacts_secret or self.agent_secret,
        )


class WecomAssistantPlugin(BasePlugin):
    """Entry point for the WeCom assistant plugin."""

    def __init__(self) -> None:
        super().__init__()
        self.client: Optional[WecomApiClient] = None

    async def initialize(self) -> None:
        cfg = self.get_config() or {}
        required_fields = ["corp_id", "agent_secret", "agent_id"]
        missing = [field for field in required_fields if not cfg.get(field)]
        if missing:
            raise ValueError(f"Missing required config: {', '.join(missing)}")

        self.client = WecomApiClient(
            corp_id=str(cfg.get("corp_id")),
            agent_secret=str(cfg.get("agent_secret")),
            agent_id=int(cfg.get("agent_id")),
            contacts_secret=str(cfg.get("contacts_secret")) if cfg.get("contacts_secret") else None,
            base_url=str(cfg.get("base_url") or "https://qyapi.weixin.qq.com"),
            safe_mode=bool(cfg.get("safe_mode", False)),
        )

    def require_client(self) -> WecomApiClient:
        if self.client is None:
            raise RuntimeError("WeCom client is not initialized")
        return self.client

    def __del__(self) -> None:
        # No explicit cleanup required for now.
        pass
