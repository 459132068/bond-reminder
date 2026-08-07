# 新债提醒（可转债申购 / 上市微信推送）

每天定时检查 A 股可转债的新债申购和上市安排，把当天结果推送到微信。

- 数据源：东方财富数据中心公开接口 `RPT_BOND_CB_LIST`，不需要 API Key
- 申购日：`PUBLIC_START_DATE`（网上申购日）
- 上市日：`LISTING_DATE`
- 实现：纯 Python 标准库，无第三方依赖

## 快速开始

推荐用环境变量配置密钥，避免把密钥写进 `config.json`。Windows 下用 PowerShell 设置用户级环境变量：

```powershell
[Environment]::SetEnvironmentVariable('WXPUSHER_APP_TOKEN', '你的appToken', 'User')
[Environment]::SetEnvironmentVariable('WXPUSHER_UIDS', 'UID_xxx,UID_yyy', 'User')
```

其他渠道对应变量名见下文。设置后重新打开终端，脚本会自动读取。

1. 先手动验证，只打印不推送：

```bash
python bond_reminder.py --no-push
```

3. 用历史日期验证数据是否正常（例如 2026-08-06 有多个可申购新债）：

```bash
python bond_reminder.py --date 2026-08-06 --no-push
```

4. 确认消息没问题后正常运行：

```bash
python bond_reminder.py
```

## 微信推送渠道

### Server酱（最简单）

1. 打开 [Server酱](https://sct.ftqq.com/) 微信扫码登录。
2. 在 SendKey 页面复制 `SCT...` 开头的 Key。
3. 填到 `config.json`：

```json
{
  "type": "serverchan",
  "enabled": true,
  "sendkey": "SCT..."
}
```

也可以用环境变量 `SERVERCHAN_SENDKEY`。

### PushPlus

1. 打开 [PushPlus](https://www.pushplus.plus/) 微信扫码登录。
2. 复制个人中心的 token。
3. 填到 `config.json`（`type: "pushplus"`），或设置环境变量 `PUSHPLUS_TOKEN`。

### 企业微信群机器人

1. 在企业微信群中添加机器人，复制 Webhook 地址中 `key=` 后面的值。
2. 填到 `config.json`（`type: "wecom"`、`webhook_key`），或设置环境变量 `WECOM_WEBHOOK_KEY`。

### WxPusher

1. 打开 [WxPusher](https://wxpusher.zjiecode.com/) 申请应用，获取 `appToken`。
2. 关注 WxPusher 公众号，在应用管理里获取接收者的 `UID`；或者使用主题推送并拿到 `TopicId`。
3. 填到 `config.json`（`type: "wxpusher"`、`app_token`、`uids`，或 `topic_ids`），或设置环境变量 `WXPUSHER_APP_TOKEN` 和逗号分隔的 `WXPUSHER_UIDS` / `WXPUSHER_TOPIC_IDS`。
4. `uids` 和 `topic_ids` 至少填一个，否则推送会提示缺少接收者。

## 定时运行

### Windows 任务计划程序

打开“任务计划程序”，新建任务，触发器设为每天 09:00，操作设为：

```text
python D:\AI TEST\twen-codex\codex-bond-raminder\bond_reminder.py
```

如果 `python` 不在 PATH，请用 Python 完整路径。

### Linux / macOS crontab

```text
0 9 * * 1-5 cd /path/to/project && /usr/bin/python3 bond_reminder.py
```

### GitHub Actions（免费，免服务器）

仓库已包含 [.github/workflows/bond-reminder.yml](.github/workflows/bond-reminder.yml)。

1. 把项目推到 GitHub 仓库。
2. 在仓库 `Settings -> Secrets and variables -> Actions` 中配置对应密钥：
   - `SERVERCHAN_SENDKEY`
   - `PUSHPLUS_TOKEN`
   - `WECOM_WEBHOOK_KEY`
   - `WXPUSHER_APP_TOKEN`
   - `WXPUSHER_UIDS`
3. 推送后由 GitHub 每天自动执行。工作流里的 cron 是 UTC，`0 1 * * 1-5` 对应北京时间 09:00（工作日）。

## 配置项

- `lookahead_days`：提醒几天。`1` 只提醒今天，`2` 同时预告明天。
- `notify_when_empty`：没有新债时是否也推送“今日无新债”。设为 `false` 可跳过空提醒。
- 也可以用环境变量 `BOND_LOOKAHEAD_DAYS`、`BOND_NOTIFY_WHEN_EMPTY` 覆盖。

## 说明

- 当前范围是 A 股可转债（可转换公司债券）的新债申购和上市，不包括新股。
- 上市日由交易所数据更新，建议在交易日上午 09:00 前后运行，太早可能还没更新当天上市信息。
- 消息内容仅作提醒，不构成投资建议。
