from __future__ import annotations

from typing import Any, AsyncGenerator

from langbot_plugin.api.definition.components.command.command import Command
from langbot_plugin.api.entities.builtin.command.context import CommandReturn, ExecuteContext

from main import WecomAPIError, WecomAssistantPlugin


class Wecom(Command):
    """Command utilities for quick WeCom checks."""

    def __init__(self) -> None:
        super().__init__()
        self.plugin: WecomAssistantPlugin

    async def initialize(self):
        await super().initialize()
        self.subcommand("status", help="Check WeCom connectivity")(self.status)
        self.subcommand(
            "send",
            help="Send quick text message",
            usage="wecom send <userid> <text>",
        )(self.quick_send)
        self.subcommand("*", help="Show help")(self.show_help)

    async def status(self, ctx: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
        try:
            result = await self.plugin.require_client().ping()
            ip_list = result.get("ip_list")
            message = "WeCom API reachable."
            if ip_list:
                message += f" IPs: {', '.join(ip_list)}"
            yield CommandReturn(text=message)
        except WecomAPIError as exc:
            yield CommandReturn(text=f"WeCom auth failed: {exc.errcode} {exc}")
        except Exception as exc:  # pragma: no cover - safeguard for unexpected errors
            yield CommandReturn(text=f"Unexpected error: {exc}")

    async def quick_send(self, ctx: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
        if len(ctx.crt_params) < 2:
            yield CommandReturn(text="Usage: wecom send <userid> <text>")
            return

        user_id = ctx.crt_params[0]
        content = " ".join(ctx.crt_params[1:]).strip()
        if not content:
            yield CommandReturn(text="Message content cannot be empty.")
            return

        try:
            resp = await self.plugin.require_client().send_message(to_user=user_id, content=content)
            invalid = resp.get("invaliduser") or resp.get("invalidparty") or resp.get("invalidtag")
            if invalid:
                yield CommandReturn(text=f"Sent with warning: invalid target {invalid}")
            else:
                yield CommandReturn(text="Message sent successfully.")
        except WecomAPIError as exc:
            yield CommandReturn(text=f"Send failed: {exc.errcode} {exc}")
        except Exception as exc:  # pragma: no cover - safeguard for unexpected errors
            yield CommandReturn(text=f"Unexpected error: {exc}")

    async def show_help(self, ctx: ExecuteContext) -> AsyncGenerator[CommandReturn, None]:
        help_lines = [
            "wecom status - validate token and network",
            "wecom send <userid> <text> - push a quick message via the configured app",
        ]
        yield CommandReturn(text="\n".join(help_lines))
