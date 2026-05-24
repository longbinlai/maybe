# 飞书推送配置指南

## 快速配置步骤

### 第一步：在飞书群聊中创建机器人

1. 打开你想接收推送的飞书群聊
2. 点击右上角 **群设置** (⚙️)
3. 选择 **群机器人**
4. 点击 **添加机器人**
5. 选择 **自定义机器人**
6. 输入机器人名称：`宏观经济信息助手`
7. 输入描述（可选）：`每日推送宏观经济信息摘要`
8. 点击 **添加**
9. **复制 Webhook URL**（格式：`https://open.feishu.cn/open-apis/bot/v2/hook/xxxx-xxxx-xxxx`）

### 第二步：配置 Webhook URL

编辑配置文件：

```bash
# 打开配置文件
open tools/openclaw-skills/macro-info-collector/config/feishu.yaml
```

将复制的 webhook URL 粘贴到配置文件中：

```yaml
feishu:
  webhook_url: "https://open.feishu.cn/open-apis/bot/v2/hook/你的实际URL"
```

保存文件。

### 第三步：测试推送

```bash
cd ~/Documents/git/maybe/tools/openclaw-skills/macro-info-collector

# 测试发送到飞书
python3 scripts/collect_macro_info.py --send-feishu
```

如果看到 `✅ 已发送到飞书`，说明配置成功！

### 第四步：设置定时任务（可选）

如果你想每天自动推送：

```bash
# 使用 cron 设置每天早上 9 点推送
crontab -e

# 添加以下行（每天早上 9:00）
0 9 * * * cd ~/Documents/git/maybe/tools/openclaw-skills/macro-info-collector && /usr/bin/python3 scripts/collect_macro_info.py --send-feishu >> /tmp/macro-info-cron.log 2>&1
```

或者使用 macOS 的 launchd（更推荐）：

```bash
# 创建 launchd 配置文件
cat > ~/Library/LaunchAgents/com.maybe.macro-info-collector.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.maybe.macro-info-collector</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/longbinlai/Documents/git/maybe/tools/openclaw-skills/macro-info-collector/scripts/collect_macro_info.py</string>
        <string>--send-feishu</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/longbinlai/Documents/git/maybe/tools/openclaw-skills/macro-info-collector</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/macro-info-collector.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/macro-info-collector.error.log</string>
</dict>
</plist>
EOF

# 加载定时任务
launchctl load ~/Library/LaunchAgents/com.maybe.macro-info-collector.plist
```

## 验证定时任务

```bash
# 查看已加载的定时任务
launchctl list | grep macro-info-collector

# 手动触发测试
launchctl start com.maybe.macro-info-collector

# 查看日志
tail -f /tmp/macro-info-collector.log
```

## 常见问题

### Q: 发送失败，提示 "未配置飞书 webhook URL"

**A:** 检查 `config/feishu.yaml` 文件：
- 确保 `webhook_url` 字段已填写
- 确保 URL 格式正确（以 `https://open.feishu.cn/open-apis/bot/v2/hook/` 开头）

### Q: 发送失败，提示 "发送失败：400"

**A:** Webhook URL 可能已失效，需要重新创建机器人。

### Q: 发送失败，提示 "发送失败：401"

**A:** Webhook URL 可能被禁用，检查飞书群设置中的机器人状态。

### Q: 定时任务没有执行

**A:** 
1. 检查定时任务是否已加载：`launchctl list | grep macro-info-collector`
2. 检查日志：`cat /tmp/macro-info-collector.error.log`
3. 手动测试：`python3 scripts/collect_macro_info.py --send-feishu`

## 高级配置

### 每周推送

如果你想每周推送一次（比如每周一）：

```bash
# 修改 launchd 配置
cat > ~/Library/LaunchAgents/com.maybe.macro-info-collector.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.maybe.macro-info-collector</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/longbinlai/Documents/git/maybe/tools/openclaw-skills/macro-info-collector/scripts/collect_macro_info.py</string>
        <string>--send-feishu</string>
        <string>--weekly</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/longbinlai/Documents/git/maybe/tools/openclaw-skills/macro-info-collector</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Weekday</key>
        <integer>1</integer>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/macro-info-collector.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/macro-info-collector.error.log</string>
</dict>
</plist>
EOF

# 重新加载
launchctl unload ~/Library/LaunchAgents/com.maybe.macro-info-collector.plist
launchctl load ~/Library/LaunchAgents/com.maybe.macro-info-collector.plist
```

### 多个群聊推送

如果你想推送到多个群聊，可以修改代码支持多个 webhook：

```bash
# 编辑配置文件
cat > tools/openclaw-skills/macro-info-collector/config/feishu.yaml << 'EOF'
feishu:
  webhook_urls:
    - "https://open.feishu.cn/open-apis/bot/v2/hook/群聊1的URL"
    - "https://open.feishu.cn/open-apis/bot/v2/hook/群聊2的URL"
EOF
```

然后修改 `collect_macro_info.py` 中的 `send_to_feishu` 方法支持多个 URL。

## 下一步

配置完成后，你可以：

1. ✅ 手动测试推送
2. ✅ 设置定时任务
3. ✅ 验证推送效果
4. 🔄 根据需求调整推送频率和内容
