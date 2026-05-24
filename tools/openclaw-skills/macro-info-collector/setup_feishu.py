#!/usr/bin/env python3
"""
飞书推送测试工具

帮助你快速配置和测试飞书推送功能
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from scripts.collect_macro_info import MacroInfoCollector


def test_webhook(webhook_url: str) -> bool:
    """测试 webhook 是否可用"""
    import requests
    
    print(f"\n🔍 测试 webhook: {webhook_url[:50]}...")
    
    try:
        # 发送测试消息
        response = requests.post(
            webhook_url,
            json={
                "msg_type": "text",
                "content": {
                    "text": "🎉 飞书推送配置成功！\n\n这是来自宏观经济信息助手的测试消息。"
                }
            },
            timeout=10,
        )
        
        if response.status_code == 200:
            print("✅ Webhook 测试成功！请检查飞书群聊是否收到消息。")
            return True
        else:
            print(f"❌ Webhook 测试失败：HTTP {response.status_code}")
            print(f"   响应：{response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Webhook 测试失败：{e}")
        return False


def interactive_setup():
    """交互式配置"""
    print("="*80)
    print("飞书推送配置助手")
    print("="*80)
    print()
    print("请按照以下步骤操作：")
    print()
    print("1. 打开飞书，进入你想接收推送的群聊")
    print("2. 点击群设置 → 群机器人 → 添加机器人")
    print("3. 选择「自定义机器人」")
    print("4. 输入机器人名称：宏观经济信息助手")
    print("5. 复制 Webhook URL")
    print()
    
    webhook_url = input("请粘贴 Webhook URL（或按 Ctrl+C 退出）：").strip()
    
    if not webhook_url:
        print("❌ 未输入 Webhook URL")
        return False
    
    if not webhook_url.startswith("https://open.feishu.cn/open-apis/bot/v2/hook/"):
        print("⚠️  Webhook URL 格式可能不正确")
        print("   正确格式：https://open.feishu.cn/open-apis/bot/v2/hook/xxxx-xxxx-xxxx")
        confirm = input("是否继续？(y/N): ").strip().lower()
        if confirm != 'y':
            return False
    
    # 测试 webhook
    if not test_webhook(webhook_url):
        return False
    
    # 保存到配置文件
    config_path = Path(__file__).parent / "config" / "feishu.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    
    config_content = f"""# 飞书配置

feishu:
  webhook_url: "{webhook_url}"
"""
    
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"\n✅ 配置已保存到：{config_path}")
    print()
    print("="*80)
    print("配置完成！")
    print("="*80)
    print()
    print("现在你可以：")
    print()
    print("1. 测试完整的信息推送：")
    print("   python3 scripts/collect_macro_info.py --send-feishu")
    print()
    print("2. 设置定时推送（每天早上 9 点）：")
    print("   查看 FEISHU_SETUP.md 中的说明")
    print()
    
    # 询问是否立即测试完整推送
    test_full = input("是否立即测试完整推送？(Y/n): ").strip().lower()
    if test_full != 'n':
        print("\n📊 正在收集宏观经济数据...")
        collector = MacroInfoCollector()
        collector.collect_all()
        collector.send_to_feishu()
    
    return True


def main():
    """主函数"""
    try:
        interactive_setup()
    except KeyboardInterrupt:
        print("\n\n❌ 用户取消配置")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 配置失败：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
