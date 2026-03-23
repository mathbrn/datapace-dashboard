"""
Addon mitmproxy pour capturer les requetes API chinoises en temps reel.
Utilise par chinese_api_discovery.py.

Ecrit les requetes interessantes dans mitmproxy_flows/live_capture.jsonl
"""

import json
import time
import os
from pathlib import Path

FLOWS_DIR = Path(__file__).parent / "mitmproxy_flows"
CAPTURE_FILE = FLOWS_DIR / "live_capture.jsonl"

TARGET_DOMAINS = [
    "geexek.com", "mararun.com", "zuicool.com", "iranshao.com",
    "runchina.org.cn", "timer.geexek.com", "saas-user-gw.mararun.com",
    "enroll.geexek.com", "manage.geexek.com",
    # Platforms de resultats
    "runninginchina.org", "shang-ma.com",
    # Grands marathons chinois
    "wuximarathon.com", "wuhanmarathon.org", "chengdu-marathon",
    "xmim.org", "gzmarathon.cn", "lzmarathon.com",
    "hzmarathon.com", "dlmarathon.org",
    "sz-marathon.com", "cqmarathon.com",
    # Plateformes de chronometrage
    "芝华安方", "chiptime", "zhihuaanfang",
]

IGNORED_EXTENSIONS = {'.js', '.css', '.png', '.jpg', '.gif', '.ico', '.woff',
                      '.woff2', '.svg', '.ttf', '.map'}
IGNORED_DOMAINS = {'cnzz.com', 'baidu.com', 'qq.com', 'google.com',
                   'googleapis.com', 'gstatic.com', 'doubleclick.net'}


class ChineseAPICapture:
    def __init__(self):
        FLOWS_DIR.mkdir(exist_ok=True)
        self.count = 0

    def response(self, flow):
        host = flow.request.host
        path = flow.request.path

        # Skip ignored domains
        if any(d in host for d in IGNORED_DOMAINS):
            return

        # Skip static assets
        ext = os.path.splitext(path.split("?")[0])[1].lower()
        if ext in IGNORED_EXTENSIONS:
            return

        # Check if it's a target domain or has API keywords
        is_target = any(d in host for d in TARGET_DOMAINS)
        content_type = flow.response.headers.get("content-type", "").lower()
        is_json = "json" in content_type
        has_api_kw = any(kw in path.lower() for kw in
                         ["/api/", "/v1/", "/v2/", "/score", "/result",
                          "/race", "/event", "/competition", "/query",
                          "/search", "/list", ".do", "/ranking", "/finisher"])

        if not (is_target or (is_json and has_api_kw)):
            return

        # Extract auth headers
        auth_headers = {}
        for name in ["authorization", "token", "x-api-key", "x-token",
                      "cookie", "x-access-token"]:
            val = flow.request.headers.get(name)
            if val:
                auth_headers[name] = val

        # Get response body preview
        body_preview = ""
        if is_json and flow.response.content:
            try:
                body_preview = flow.response.content.decode("utf-8", errors="replace")[:50000]
            except Exception:
                pass

        entry = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "method": flow.request.method,
            "url": flow.request.url,
            "host": host,
            "path": path,
            "status": flow.response.status_code,
            "content_type": content_type,
            "response_size": len(flow.response.content) if flow.response.content else 0,
            "auth_headers": auth_headers,
            "is_json": is_json,
            "body_preview": body_preview,
        }

        # Write to capture file
        with open(CAPTURE_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

        self.count += 1
        auth_tag = " [AUTH]" if auth_headers else ""
        json_tag = " [JSON]" if is_json else ""
        print(f"  [{flow.response.status_code}] {flow.request.method} "
              f"https://{host}{path[:80]}{auth_tag}{json_tag}")


addons = [ChineseAPICapture()]
