# WeCom Assistant Plugin

A LangBot plugin that exposes common Enterprise WeChat (WeCom) operations as tools and commands. It reuses the official REST APIs (`message/send`, `user/get`) with token caching.

## Features
- Tools for sending WeCom messages (`text`/`markdown`) and fetching user profiles.
- `wecom` command for quick health check and ad‑hoc text sending.
- Token cache with auto refresh and safe-mode switch.

## Configuration (`manifest.yaml` -> `spec.config`)
| Field | Required | Description |
| --- | --- | --- |
| `corp_id` | yes | Enterprise ID (`corpid`) from the WeCom console. |
| `agent_secret` | yes | Secret of the internal app used to send messages. |
| `agent_id` | yes | AgentID of the internal app. |
| `contacts_secret` | no | Contact/通讯录 secret for richer profile reads. Falls back to `agent_secret` if omitted. |
| `base_url` | no | API base URL, default `https://qyapi.weixin.qq.com`. |
| `safe_mode` | no | When true, sends messages with `safe=1`. |

## Components
- Tools: `send_wecom_text`, `get_user_profile`
- Command: `wecom`

## Usage
1. Place this folder under `data/plugins` or load as a debug plugin via `lbp run`.
2. Fill the config in LangBot UI with your WeCom credentials.
3. Use tools in pipelines/agents or run chat commands:
   - `!wecom status` to verify connectivity.
   - `!wecom send <userid> hello from langbot` to push a quick message.

## Notes
- API errors are returned with `errcode` and the WeCom `errmsg` for easier debugging.
- `send_wecom_text` accepts `user_id`, `party_id`, or `tag_id` (any combination) following WeCom rules.
