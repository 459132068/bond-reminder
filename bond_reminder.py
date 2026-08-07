#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""每日新债（可转债）申购/上市微信提醒。

数据源：东方财富数据中心公开接口 RPT_BOND_CB_LIST。
推送渠道：Server酱、PushPlus、企业微信群机器人、WxPusher。
"""

import argparse
import json
import os
import sys
import traceback
import urllib.parse
import urllib.request
from datetime import date, timedelta
from pathlib import Path

EASTMONEY_API = "https://datacenter-web.eastmoney.com/api/data/v1/get"
EASTMONEY_REPORT = "RPT_BOND_CB_LIST"
PAGE_SIZE = 500
DEFAULT_CONFIG = Path(__file__).resolve().parent / "config.json"
WEEKDAY = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]


def http_request(url, data=None, headers=None, timeout=20):
    """发送 HTTP 请求并返回响应文本。"""
    request = urllib.request.Request(url, data=data, headers=headers or {})
    request.add_header(
        "User-Agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")


def http_get_json(url):
    return json.loads(http_request(url))


def http_post_json(url, payload):
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    text = http_request(
        url,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8"},
    )
    return json.loads(text)


def fetch_bond_rows():
    """拉取全部可转债列表，返回包含申购日/上市日的行。"""
    rows = []
    page = 1
    while True:
        params = {
            "reportName": EASTMONEY_REPORT,
            "columns": "ALL",
            "source": "WEB",
            "client": "WEB",
            "pageSize": PAGE_SIZE,
            "pageNumber": page,
        }
        url = EASTMONEY_API + "?" + urllib.parse.urlencode(params)
        payload = http_get_json(url)
        result = payload.get("result") or {}
        page_rows = result.get("data") or []
        rows.extend(page_rows)
        total = result.get("count") or len(page_rows)
        if not page_rows or len(rows) >= total or page >= 5:
            break
        page += 1
    return rows


def date_only(value):
    """把 '2026-08-06 00:00:00' 之类的时间截成日期。"""
    if not value:
        return None
    text = str(value).strip()
    return text[:10] if len(text) >= 10 else None


def fmt(value, default="-"):
    if value is None:
        return default
    text = str(value).strip()
    return text if text else default


def collect_events(rows, start, days):
    """按日期归类申购和上市事件。"""
    targets = {
        (start + timedelta(days=offset)).isoformat(): offset
        for offset in range(days)
    }
    events = {}
    for row in rows:
        for kind, field in (("申购", "PUBLIC_START_DATE"), ("上市", "LISTING_DATE")):
            day = date_only(row.get(field))
            if day in targets:
                events.setdefault(day, {"申购": [], "上市": []})
                events[day][kind].append(row)
    return events


def build_message(events, start, days):
    lines = ["**新债提醒 · {}（{}）**".format(start.isoformat(), WEEKDAY[start.weekday()])]
    for offset in range(days):
        day = (start + timedelta(days=offset)).isoformat()
        label = "今日" if offset == 0 else ("明日" if offset == 1 else day)
        day_events = events.get(day, {"申购": [], "上市": []})
        apply_rows = day_events.get("申购", [])
        list_rows = day_events.get("上市", [])

        lines.append("")
        lines.append("**{}可申购（{} 只）**".format(label, len(apply_rows)))
        for index, row in enumerate(apply_rows, 1):
            lines.append("{}. **{}**（{}）".format(
                index,
                fmt(row.get("SECURITY_NAME_ABBR")),
                fmt(row.get("SECURITY_CODE")),
            ))
            lines.append("    申购：{} {}".format(
                fmt(row.get("CORRECODE")),
                fmt(row.get("CORRECODE_NAME_ABBR"), ""),
            ))
            lines.append("    正股：{}（{}）｜评级：{}｜规模：{} 亿".format(
                fmt(row.get("SECURITY_SHORT_NAME")),
                fmt(row.get("CONVERT_STOCK_CODE")),
                fmt(row.get("RATING")),
                fmt(row.get("ACTUAL_ISSUE_SCALE")),
            ))
        if not apply_rows:
            lines.append("    {}无新债申购。".format(label))

        lines.append("")
        lines.append("**{}上市（{} 只）**".format(label, len(list_rows)))
        for index, row in enumerate(list_rows, 1):
            lines.append("{}. **{}**（{}）".format(
                index,
                fmt(row.get("SECURITY_NAME_ABBR")),
                fmt(row.get("SECURITY_CODE")),
            ))
            lines.append("    正股：{}（{}）｜评级：{}｜规模：{} 亿".format(
                fmt(row.get("SECURITY_SHORT_NAME")),
                fmt(row.get("CONVERT_STOCK_CODE")),
                fmt(row.get("RATING")),
                fmt(row.get("ACTUAL_ISSUE_SCALE")),
            ))
        if not list_rows:
            lines.append("    {}无新债上市。".format(label))
    return "\n".join(lines)


def push_serverchan(channel, title, content):
    key = channel.get("sendkey") or os.getenv("SERVERCHAN_SENDKEY", "")
    if not key:
        return False, "缺少 sendkey"
    body = urllib.parse.urlencode(
        {"title": title, "desp": content}
    ).encode("utf-8")
    text = http_request(
        "https://sctapi.ftqq.com/{}.send".format(key),
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    result = json.loads(text)
    return result.get("code") == 0, result.get("message") or text


def push_pushplus(channel, title, content):
    token = channel.get("token") or os.getenv("PUSHPLUS_TOKEN", "")
    if not token:
        return False, "缺少 token"
    result = http_post_json(
        "https://www.pushplus.plus/send",
        {
            "token": token,
            "title": title,
            "content": content,
            "template": "markdown",
        },
    )
    return result.get("code") == 200, result.get("msg") or json.dumps(
        result, ensure_ascii=False
    )


def push_wecom(channel, title, content):
    key = channel.get("webhook_key") or os.getenv("WECOM_WEBHOOK_KEY", "")
    if not key:
        return False, "缺少 webhook_key"
    result = http_post_json(
        "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key={}".format(key),
        {"msgtype": "markdown", "markdown": {"content": content}},
    )
    return result.get("errcode") == 0, result.get("errmsg") or str(result)


def push_wxpusher(channel, title, content):
    app_token = channel.get("app_token") or os.getenv("WXPUSHER_APP_TOKEN", "")
    uids = channel.get("uids") or [
        item for item in os.getenv("WXPUSHER_UIDS", "").split(",") if item
    ]
    topic_ids = channel.get("topic_ids") or [
        item for item in os.getenv("WXPUSHER_TOPIC_IDS", "").split(",") if item
    ]
    if not app_token:
        return False, "缺少 app_token"
    if not uids and not topic_ids:
        return False, "缺少 uids 或 topic_ids"
    payload = {
        "appToken": app_token,
        "content": content,
        "summary": title,
        "contentType": 2,
    }
    if uids:
        payload["uids"] = uids
    if topic_ids:
        payload["topicIds"] = topic_ids
    result = http_post_json("https://wxpusher.zjiecode.com/api/send/message", payload)
    return result.get("code") == 1000, result.get("msg") or json.dumps(
        result, ensure_ascii=False
    )


PUSHERS = {
    "serverchan": push_serverchan,
    "pushplus": push_pushplus,
    "wecom": push_wecom,
    "wxpusher": push_wxpusher,
}


def load_config(config_path):
    if os.path.exists(config_path):
        with open(config_path, encoding="utf-8") as fp:
            return json.load(fp)
    return {}


def env_value(name, default=""):
    value = os.getenv(name, "")
    return value if value else default


def load_channels(config):
    channels = list(config.get("push_channels", []))
    env_channels = []
    if os.getenv("SERVERCHAN_SENDKEY"):
        env_channels.append(
            {"type": "serverchan", "enabled": True, "sendkey": os.getenv("SERVERCHAN_SENDKEY")}
        )
    if os.getenv("PUSHPLUS_TOKEN"):
        env_channels.append(
            {"type": "pushplus", "enabled": True, "token": os.getenv("PUSHPLUS_TOKEN")}
        )
    if os.getenv("WECOM_WEBHOOK_KEY"):
        env_channels.append(
            {"type": "wecom", "enabled": True, "webhook_key": os.getenv("WECOM_WEBHOOK_KEY")}
        )
    if os.getenv("WXPUSHER_APP_TOKEN"):
        env_channels.append(
            {
                "type": "wxpusher",
                "enabled": True,
                "app_token": os.getenv("WXPUSHER_APP_TOKEN"),
                "uids": [
                    item for item in os.getenv("WXPUSHER_UIDS", "").split(",") if item
                ],
                "topic_ids": [
                    item
                    for item in os.getenv("WXPUSHER_TOPIC_IDS", "").split(",")
                    if item
                ],
            }
        )
    if env_channels:
        channels = env_channels

    enabled = []
    for channel in channels:
        if not channel.get("enabled"):
            continue
        ctype = channel.get("type")
        if ctype == "serverchan" and (channel.get("sendkey") or os.getenv("SERVERCHAN_SENDKEY")):
            enabled.append(channel)
        elif ctype == "pushplus" and (channel.get("token") or os.getenv("PUSHPLUS_TOKEN")):
            enabled.append(channel)
        elif ctype == "wecom" and (channel.get("webhook_key") or os.getenv("WECOM_WEBHOOK_KEY")):
            enabled.append(channel)
        elif ctype == "wxpusher" and (
            channel.get("app_token") or os.getenv("WXPUSHER_APP_TOKEN")
        ):
            enabled.append(channel)
    return enabled


def send_all(channels, title, content):
    failed = []
    for channel in channels:
        pusher = PUSHERS.get(channel.get("type"))
        if not pusher:
            failed.append((channel.get("type"), "未知渠道"))
            print("[{}] 失败：未知渠道".format(channel.get("type")))
            continue
        try:
            ok, message = pusher(channel, title, content)
        except Exception as exc:  # noqa: BLE001
            ok, message = False, str(exc)
        if ok:
            print("[{}] 推送成功".format(channel.get("type")))
        else:
            failed.append((channel.get("type"), message))
            print("[{}] 推送失败：{}".format(channel.get("type"), message))
    return failed


def main():
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(description="每日新债（可转债）申购/上市微信提醒")
    parser.add_argument(
        "--config",
        default=os.getenv("BOND_REMINDER_CONFIG", str(DEFAULT_CONFIG)),
        help="配置文件路径，默认 config.json",
    )
    parser.add_argument(
        "--date",
        help="提醒日期 YYYY-MM-DD，默认今天",
    )
    parser.add_argument(
        "--days",
        type=int,
        help="提醒几天，1=只提醒今天，2=今天+明天",
    )
    parser.add_argument(
        "--no-push",
        action="store_true",
        help="只打印消息，不推送",
    )
    args = parser.parse_args()

    config = load_config(args.config)
    if args.days is not None:
        lookahead = args.days
    elif config.get("lookahead_days") is not None:
        lookahead = int(config["lookahead_days"])
    else:
        lookahead = int(env_value("BOND_LOOKAHEAD_DAYS", "1"))
    if config.get("notify_when_empty") is not None:
        notify_when_empty = bool(config["notify_when_empty"])
    else:
        notify_when_empty = env_value(
            "BOND_NOTIFY_WHEN_EMPTY", "true"
        ).lower() in ("1", "true", "yes")
    start = date.fromisoformat(args.date) if args.date else date.today()

    print("正在拉取新债数据...")
    try:
        rows = fetch_bond_rows()
    except Exception:  # noqa: BLE001
        traceback.print_exc()
        return 2

    events = collect_events(rows, start, lookahead)
    message = build_message(events, start, lookahead)
    print()
    print(message)

    has_events = any(
        day_events["申购"] or day_events["上市"]
        for day_events in events.values()
    )
    if args.no_push:
        return 0

    channels = load_channels(config)
    if not channels:
        print("没有已启用的推送渠道，只打印不推送。")
        return 0
    if not has_events and not notify_when_empty:
        print("今日无新债，且 notify_when_empty 为 false，跳过推送。")
        return 0

    title = "新债提醒 · {}".format(start.isoformat())
    failed = send_all(channels, title, message)
    if failed:
        print("有渠道推送失败：{}".format(
            ", ".join("{}: {}".format(ctype, msg) for ctype, msg in failed)
        ))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
