#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request


COMMANDS = {"/topicid", "/config", "/logserver"}


def call_api(token, method, payload=None):
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = None
    headers = {}

    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as err:
        body = err.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Telegram API HTTP {err.code}: {body}") from err
    except urllib.error.URLError as err:
        raise RuntimeError(f"Telegram API request failed: {err}") from err

    parsed = json.loads(body)
    if not parsed.get("ok"):
        raise RuntimeError(f"Telegram API error: {body}")
    return parsed["result"]


def command_name(text):
    parts = text.strip().split(maxsplit=1)
    if not parts:
        return ""
    first = parts[0]
    return first.split("@", 1)[0].lower()


def yaml_snippet(chat_id, thread_id, level):
    if thread_id is None:
        return "\n".join(
            [
                '  - type: "TGBot"',
                '    API_KEY: "<bot token>"',
                "    chats:",
                f"      {chat_id}: {level}",
            ]
        )

    return "\n".join(
        [
            '  - type: "TGBot"',
            '    API_KEY: "<bot token>"',
            "    topics:",
            f"      - chat_id: {chat_id}",
            f"        message_thread_id: {thread_id}",
            f"        level: {level}",
        ]
    )


def response_text(message, level):
    chat = message.get("chat", {})
    chat_id = chat.get("id")
    chat_title = chat.get("title") or chat.get("username") or chat.get("first_name") or "unknown"
    chat_type = chat.get("type", "unknown")
    thread_id = message.get("message_thread_id")

    lines = [
        "Logserver Telegram target:",
        f"chat_id: {chat_id}",
        f"chat_type: {chat_type}",
        f"chat_title: {chat_title}",
    ]

    if thread_id is None:
        lines.append("message_thread_id: <not present; this message is not inside a forum topic>")
    else:
        lines.append(f"message_thread_id: {thread_id}")

    lines.extend(["", "Config snippet:", "```yaml", yaml_snippet(chat_id, thread_id, level), "```"])
    return "\n".join(lines)


def send_reply(token, message, text):
    payload = {
        "chat_id": message["chat"]["id"],
        "text": text,
        "reply_to_message_id": message["message_id"],
        "allow_sending_without_reply": True,
    }
    if "message_thread_id" in message:
        payload["message_thread_id"] = message["message_thread_id"]
    call_api(token, "sendMessage", payload)


def poll(token, level, once):
    offset = None
    print("Waiting for /topicid, /config, or /logserver. Press Ctrl+C to stop.", flush=True)

    while True:
        query = {"timeout": 60, "allowed_updates": json.dumps(["message"])}
        if offset is not None:
            query["offset"] = offset
        method = "getUpdates?" + urllib.parse.urlencode(query)
        updates = call_api(token, method)

        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message")
            if not message:
                continue

            text = message.get("text", "")
            if command_name(text) not in COMMANDS:
                continue

            answer = response_text(message, level)
            print(answer)
            print("-" * 60, flush=True)
            send_reply(token, message, answer)

            if once:
                return

        if not updates:
            time.sleep(1)


def main():
    parser = argparse.ArgumentParser(
        description="Reply with Telegram chat/topic IDs for logserver TGBot config."
    )
    parser.add_argument("--token", default=os.environ.get("TELEGRAM_BOT_TOKEN"), help="Telegram bot token")
    parser.add_argument("--level", type=int, default=20, help="Log level for generated snippets")
    parser.add_argument("--once", action="store_true", help="Exit after answering the first command")
    args = parser.parse_args()

    if not args.token:
        print("Pass --token or set TELEGRAM_BOT_TOKEN.", file=sys.stderr)
        return 2

    try:
        poll(args.token, args.level, args.once)
    except KeyboardInterrupt:
        print("\nStopped.", file=sys.stderr)
        return 130
    except RuntimeError as err:
        print(err, file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
