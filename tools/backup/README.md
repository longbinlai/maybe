# Maybe Finance 备份系统

自动备份 Maybe Finance 数据库和 OpenClaw 记忆文件到 NAS。

## 架构

```
┌─────────────────────────────────────────────────────────┐
│                    本地系统                              │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ PostgreSQL   │  │ OpenClaw     │  │ OpenClaw     │  │
│  │ Database     │  │ MEMORY.md    │  │ Config       │  │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  │
│         │                 │                 │           │
│         └─────────────────┴─────────────────┘           │
│                           │                             │
│                    backup.sh                            │
│                           │                             │
└───────────────────────────┼─────────────────────────────┘
                            │ SMB
                            ▼
┌─────────────────────────────────────────────────────────┐
│                    NAS (192.168.1.185)                   │
│                                                         │
│  maybe_backups/                                         │
│  ├── backup_20260525_143022/                            │
│  │   ├── maybe_production_20260525_143022.sql          │
│  │   ├── openclaw_memory_20260525_143022.tar.gz        │
│  │   ├── MEMORY_20260525_143022.md                     │
│  │   ├── openclaw_config_20260525_143022.json          │
│  │   ├── manifest_20260525_143022.txt                  │
│  │   └── .verified                                     │
│  └── backup_20260601_143022/                            │
│      └── ...                                            │
└─────────────────────────────────────────────────────────┘
```

## 配置

1. 复制配置模板：
   ```bash
   cp .env.nas.example .env.nas
   ```

2. 编辑 `.env.nas`，填写 NAS 配置：
   ```bash
   NAS_IP=192.168.1.185
   NAS_SHARE=backup
   NAS_USER=admin
   NAS_PASSWORD=your_password
   NAS_MOUNT_POINT=/Volumes/nas_backup
   BACKUP_RETENTION_DAYS=30
   ```

**注意**：`.env.nas` 已在 `.gitignore` 中排除，不会提交到 git。

## 手动备份

```bash
# 执行备份
./tools/backup/backup.sh
```

备份脚本会：
1. 导出 PostgreSQL 数据库
2. 打包 OpenClaw 记忆文件
3. 复制 OpenClaw 配置
4. 挂载 NAS（如果未挂载）
5. 创建带时间戳的备份目录
6. 复制所有文件到 NAS
7. 验证备份完整性
8. 清理过期备份（如果配置了保留天数）

## 恢复备份

```bash
# 列出所有可用备份
./tools/backup/restore.sh --list

# 恢复最新备份
./tools/backup/restore.sh

# 恢复指定备份
./tools/backup/restore.sh backup_20260525_143022

# 仅恢复数据库
./tools/backup/restore.sh --db-only backup_20260525_143022

# 仅恢复记忆文件
./tools/backup/restore.sh --memory-only backup_20260525_143022

# 仅恢复配置
./tools/backup/restore.sh --config-only backup_20260525_143022
```

恢复脚本会：
1. 挂载 NAS（如果未挂载）
2. 显示备份清单
3. 备份当前数据到 `/tmp/`
4. 恢复指定内容
5. 重建 OpenClaw 记忆索引

## 自动备份

### 方案 1: macOS LaunchAgent（推荐）

已创建 LaunchAgent 配置，每周日晚上 22:00 自动备份：

```bash
# 加载 LaunchAgent
launchctl load ~/Library/LaunchAgents/com.maybe.backup.plist

# 检查状态
launchctl list | grep maybe

# 手动触发
launchctl start com.maybe.backup

# 查看日志
tail -f /tmp/maybe-backup.log

# 卸载
launchctl unload ~/Library/LaunchAgents/com.maybe.backup.plist
```

### 方案 2: cron

```bash
# 编辑 crontab
crontab -e

# 添加每周日 22:00 的备份任务
0 22 * * 0 /Users/longbinlai/Documents/git/maybe/tools/backup/backup.sh >> /tmp/maybe-backup.log 2>&1
```

## 备份内容

每次备份包含：

| 文件 | 说明 |
|------|------|
| `maybe_production_*.sql` | PostgreSQL 数据库完整导出 |
| `openclaw_memory_*.tar.gz` | OpenClaw 记忆目录（`memory/*.md`） |
| `MEMORY_*.md` | OpenClaw 主记忆文件 |
| `openclaw_config_*.json` | OpenClaw 配置文件 |
| `manifest_*.txt` | 备份清单（包含恢复说明） |
| `.verified` | 验证标记（表示备份完整） |

## 安全注意事项

1. **NAS 密码**：存储在 `.env.nas` 中，已排除在 git 之外
2. **数据库密码**：使用 Docker 容器内连接，不暴露密码
3. **备份加密**：当前未加密，建议 NAS 端启用加密
4. **访问控制**：确保 NAS 共享目录权限设置正确

## 故障排除

### NAS 挂载失败

```bash
# 检查 NAS 是否在线
ping 192.168.1.185

# 检查 SMB 服务
nc -z 192.168.1.185 445

# 手动挂载测试
mkdir -p /Volumes/nas_backup
mount_smbfs //admin@192.168.1.185/backup /Volumes/nas_backup
```

### 数据库备份失败

```bash
# 检查 Docker 容器
docker ps | grep maybe-db

# 手动测试备份
docker exec maybe-db-1 pg_dump -U maybe_user maybe_production > /tmp/test.sql
```

### 恢复失败

```bash
# 检查当前数据已备份到 /tmp/
ls -lh /tmp/maybe_current_*.sql
ls -lh /tmp/openclaw_memory_current_*.tar.gz

# 手动恢复数据库
docker exec -i maybe-db-1 psql -U maybe_user maybe_production < backup_file.sql

# 手动恢复记忆
tar -xzf openclaw_memory_*.tar.gz -C ~/.openclaw/workspace/
```

## 备份策略建议

1. **保留策略**：设置 `BACKUP_RETENTION_DAYS=30` 保留最近 30 天
2. **异地备份**：定期将 NAS 备份同步到云端（如 iCloud、OneDrive）
3. **验证恢复**：每季度测试一次恢复流程
4. **监控日志**：检查 `/tmp/maybe-backup.log` 确保备份成功

## 文件结构

```
tools/backup/
├── README.md          # 本文档
├── backup.sh          # 备份脚本
└── restore.sh         # 恢复脚本

.env.nas               # NAS 配置（不提交 git）
.env.nas.example       # NAS 配置模板

~/Library/LaunchAgents/
└── com.maybe.backup.plist  # 自动备份配置
```

## 更新历史

- **2026-05-26**: 初始版本，支持数据库和 OpenClaw 记忆备份
