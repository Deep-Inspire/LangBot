# components/event_listener/default.py
from __future__ import annotations

import json
import time
from typing import Any, Dict

from langbot_plugin.api.definition.components.common.event_listener import EventListener
from langbot_plugin.api.entities import context, events
import langbot_plugin.api.entities.builtin.platform.message as platform_message


class DefaultEventListener(EventListener):
    async def initialize(self):
        """
        Register handlers:
        1) On *NormalMessageReceived: extract source message id / message type, store into query vars.
        2) On NormalMessageResponded: pull stored vars, collect reply info, push to Redis, block default reply.
        """

        @self.handler(events.PersonNormalMessageReceived)
        @self.handler(events.GroupNormalMessageReceived)
        async def on_normal_message_received(event_context: context.EventContext):
            """
            Parse incoming WeCom message for id and type, keep them on the query for later logging.
            """
            event = event_context.event  # PersonNormalMessageReceived or GroupNormalMessageReceived
            msg_chain: platform_message.MessageChain = event.message_chain

            message_id: str | None = None
            message_type: str = "text"  # default

            # Walk the chain to locate source ids and infer message type.
            for comp in msg_chain:
                if isinstance(comp, platform_message.Source):
                    for attr in ("id", "message_id", "msg_id"):
                        value = getattr(comp, attr, None)
                        if value is not None:
                            message_id = str(value)
                            break

                if isinstance(comp, platform_message.Image):
                    message_type = "image"
                elif isinstance(comp, platform_message.File):
                    message_type = "file"
                elif isinstance(comp, platform_message.Voice):
                    message_type = "voice"

            await event_context.set_query_var("origin_message_id", message_id)
            await event_context.set_query_var("origin_message_type", message_type)

        @self.handler(events.NormalMessageResponded)
        async def on_llm_responded(event_context: context.EventContext):
            """
            After LLM replies: log to Redis then block LangBot default reply.
            """
            event: events.NormalMessageResponded = event_context.event

            customer_id = str(event.sender_id)
            launcher_id = str(event.launcher_id)
            reply_text = event.response_text
            ts = int(time.time())

            try:
                origin_message_id = await event_context.get_query_var("origin_message_id")
            except Exception:
                origin_message_id = None

            try:
                origin_message_type = await event_context.get_query_var("origin_message_type")
            except Exception:
                origin_message_type = None

            # Prefer adapter.bot_account_id for the WeCom bot id; fall back to bot_uuid.
            bot_account_id = None
            try:
                bot_account_id = getattr(event.query.adapter, "bot_account_id", None)
            except Exception:
                bot_account_id = None
            if bot_account_id is None and hasattr(event, "query") and event.query is not None:
                bot_account_id = getattr(event.query, "bot_uuid", None)

            cfg = self.plugin.get_config() or {}

            log_obj: Dict[str, Any] = {
                "customer_id": customer_id,
                "wecom_account_id": bot_account_id,
                "launcher_id": launcher_id,
                "timestamp": ts,
                "reply_text": reply_text,
                "message_id": origin_message_id,
                "message_type": origin_message_type,
            }

            redis_key = cfg.get("redis_key") or "langbot:wecom:llm_replies"

            try:
                redis = await self.plugin.get_redis()
                await redis.rpush(redis_key, json.dumps(log_obj, ensure_ascii=False))
            except Exception as e:
                print("[WeComRedisLogger] Failed to push log to Redis:", e)
                print("[WeComRedisLogger] Payload:", log_obj)

            # Prevent LangBot from sending the default reply and stop later listeners.
            event_context.prevent_default()
            event_context.prevent_postorder()
