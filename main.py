import requests
import datetime
import os

# 从github secrets读取密钥
APPID = os.getenv("WX_APPID")
APPSECRET = os.getenv("WX_APPSECRET")
OPENID = os.getenv("WX_OPENID")
TEMPLATE_ID = os.getenv("WX_TEMPLATE_ID")

today = datetime.date.today().strftime("%Y-%m-%d")
buy_text = "无"
list_text = "无"
need_push = False

# ========== 东方财富接口获取新债数据 ==========
# 今日申购
sub_url = f'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_BOND_CB_PUBLISH&columns=ALL&filter=(PUBLISHDATE="{today}")'
try:
    res = requests.get(sub_url, timeout=20)
    data = res.json()
    sub_list = data["result"]["data"]
    if sub_list:
        need_push = True
        buy_text = ""
        for item in sub_list:
            buy_text += f"{item['SECURITYSHORTNAME']}({item['SECURITYCODE']})\n"
except Exception as e:
    buy_text = f"获取异常:{str(e)}"

# 今日上市
list_url = f'https://datacenter.eastmoney.com/securities/api/data/v1/get?reportName=RPT_BOND_CB_LIST&columns=ALL&filter=(LISTDATE="{today}")'
try:
    res = requests.get(list_url, timeout=20)
    data = res.json()
    list_data = data["result"]["data"]
    if list_data:
        need_push = True
        list_text = ""
        for item in list_data:
            list_text += f"{item['SECURITYSHORTNAME']}({item['SECURITYCODE']})\n"
except Exception as e:
    list_text = f"获取异常:{str(e)}"

# 没有新债，直接结束不推送
if not need_push:
    print(f"{today} 今日无新债申购/上市，静默")
else:
    # 1. 获取access_token
    token_url = f"https://api.weixin.qq.com/cgi-bin/token?grant_type=client_credential&appid={APPID}&secret={APPSECRET}"
    token_resp = requests.get(token_url).json()
    access_token = token_resp.get("access_token")
    if not access_token:
        print("获取access_token失败", token_resp)
    else:
        # 2. 推送模板消息
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
