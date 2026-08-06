import requests
import datetime
import os
from zoneinfo import ZoneInfo

APPID = os.getenv("WX_APPID")
APPSECRET = os.getenv("WX_APPSECRET")
OPENID = os.getenv("WX_OPENID")
TEMPLATE_ID = os.getenv("WX_TEMPLATE_ID")

beijing_tz = ZoneInfo("Asia/Shanghai")
today = datetime.datetime.now(beijing_tz).strftime("%Y-%m-%d")
print(f"✅ 当前查询日期（北京时间）：{today}")

buy_text = "无"
list_text = "无"
need_push = False

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

# ========= 使用集思录可转债日历接口 =========
try:
    url = "https://www.jisilu.cn/data/cbnew/cb_list/"
    resp = requests.get(url, headers=headers, timeout=25)
    raw_data = resp.json()
    sub_list = []
    online_list = []
    for item in raw_data["rows"]:
        cell = item["cell"]
        # 今日申购
        if cell.get("apply_date") == today:
            sub_list.append(f"{cell['bond_nm']}({cell['bond_id']})")
        # 今日上市
        if cell.get("list_date") == today:
            online_list.append(f"{cell['bond_nm']}({cell['bond_id']})")

    if sub_list:
        need_push = True
        buy_text = "\n".join(sub_list)
    if online_list:
        need_push = True
        list_text = "\n".join(online_list)

    print(f"今日申购数量:{len(sub_list)} ,上市数量:{len(online_list)}")
except Exception as e:
    print(f"数据接口请求异常: {str(e)}")

# 没有新债，直接结束不推送
if not need_push:
    print(f"{today} 今日无新债申购/上市，静默")
else:
    print("❗检测到新债，准备推送微信通知")
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}"
    token_resp = requests.get(token_url).json()
    access_token = token_resp.get("access_token")
    if not access_token:
        print("获取access_token失败", token_resp)
    else:
        send_url = f"https://api.weixin.qq.com/cgi-bin/message/template/send?access_token={access_token}"
        post_data = {
            "touser": OPENID,
            "template_id": TEMPLATE_ID,
            "data": {
                "first": {"value": "可转债每日提醒", "color": "#0066cc"},
                "date": {"value": today},
                "buy": {"value": buy_text.strip()},
                "list": {"value": list_text.strip()},
                "remark": {"value": "理性打新，投资有风险"}
            }
        }
        push_result = requests.post(send_url, json=post_data).json()
        print("推送结果：", push_result)
