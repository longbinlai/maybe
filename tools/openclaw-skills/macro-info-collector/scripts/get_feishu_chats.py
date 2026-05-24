#!/usr/bin/env python3
"""
获取飞书群聊 chat_id

使用"家庭理财助手"机器人的 API 查询所有群聊，并显示 chat_id
"""

import json
import requests
from pathlib import Path


def get_feishu_chats():
    """获取所有飞书群聊"""
    # 从 OpenClaw 配置读取飞书应用信息
    openclaw_config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not openclaw_config_path.exists():
        print("❌ 未找到 OpenClaw 配置文件")
        return
    
    with open(openclaw_config_path) as f:
        openclaw_config = json.load(f)
    
    feishu_config = openclaw_config.get("channels", {}).get("feishu", {})
    app_id = feishu_config.get("appId")
    app_secret = feishu_config.get("appSecret")
    
    if not app_id or not app_secret:
        print("❌ OpenClaw 配置中未找到飞书 appId 或 appSecret")
        return
    
    print(f"📱 使用应用：{app_id}")
    print()
    
    # 获取 tenant_access_token
    token_url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    token_response = requests.post(
        token_url,
        json={
            "app_id": app_id,
            "app_secret": app_secret
        },
        timeout=10,
    )
    
    if token_response.status_code != 200:
        print(f"❌ 获取 token 失败：{token_response.status_code}")
        return
    
    token_data = token_response.json()
    if token_data.get("code") != 0:
        print(f"❌ 获取 token 失败：{token_data.get('msg')}")
        return
    
    access_token = token_data.get("tenant_access_token")
    
    # 获取群聊列表
    chats_url = "https://open.feishu.cn/open-apis/im/v1/chats"
    headers = {
        "Authorization": f"Bearer {access_token}",
    }
    
    chats_response = requests.get(
        chats_url,
        headers=headers,
        params={"page_size": 50},
        timeout=10,
    )
    
    if chats_response.status_code != 200:
        print(f"❌ 获取群聊列表失败：{chats_response.status_code}")
        return
    
    chats_data = chats_response.json()
    if chats_data.get("code") != 0:
        print(f"❌ 获取群聊列表失败：{chats_data.get('msg')}")
        return
    
    items = chats_data.get("data", {}).get("items", [])
    
    print("="*80)
    print(f"📋 找到 {len(items)} 个群聊")
    print("="*80)
    print()
    
    for item in items:
        chat_id = item.get("chat_id")
        name = item.get("name", "(未命名)")
        chat_type = item.get("chat_type", "unknown")
        member_count = item.get("user_count", 0)
        
        print(f"群聊名称：{name}")
        print(f"  chat_id: {chat_id}")
        print(f"  类型：{chat_type}")
        print(f"  成员数：{member_count}")
        print()
    
    print("="*80)
    print("💡 使用方法：")
    print("="*80)
    print()
    print("1. 复制你想推送的群聊的 chat_id")
    print("2. 编辑配置文件：")
    print("   nano tools/openclaw-skills/macro-info-collector/config/feishu.yaml")
    print()
    print("3. 添加 chat_id：")
    print("   feishu:")
    print("     chat_id: \"你的chat_id\"")
    print()


if __name__ == "__main__":
    get_feishu_chats()
