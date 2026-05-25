#!/bin/bash
# Maybe Finance 备份脚本
# 功能：备份数据库和 OpenClaw 记忆到 NAS

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 加载配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.nas"

if [ ! -f "$ENV_FILE" ]; then
    log_error "配置文件不存在: $ENV_FILE"
    log_error "请复制 .env.nas.example 为 .env.nas 并填写配置"
    exit 1
fi

source "$ENV_FILE"

# 验证配置
if [ -z "$NAS_IP" ] || [ -z "$NAS_SHARE" ] || [ -z "$NAS_USER" ] || [ -z "$NAS_PASSWORD" ]; then
    log_error "NAS 配置不完整，请检查 $ENV_FILE"
    exit 1
fi

# 生成时间戳
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
DATE_PREFIX=$(date +"%Y%m%d")
BACKUP_DIR="backup_${TIMESTAMP}"

log_info "开始备份 - $TIMESTAMP"

# 创建临时目录
TEMP_DIR=$(mktemp -d)
trap "rm -rf $TEMP_DIR" EXIT

log_info "临时目录: $TEMP_DIR"

# 1. 备份 PostgreSQL 数据库
log_info "备份 PostgreSQL 数据库..."
DB_BACKUP_FILE="$TEMP_DIR/maybe_production_${TIMESTAMP}.sql"

if docker exec maybe-db-1 pg_dump -U maybe_user maybe_production > "$DB_BACKUP_FILE" 2>/dev/null; then
    DB_SIZE=$(du -h "$DB_BACKUP_FILE" | cut -f1)
    log_info "数据库备份成功: $DB_SIZE"
else
    log_error "数据库备份失败"
    exit 1
fi

# 2. 备份 OpenClaw 记忆文件
log_info "备份 OpenClaw 记忆文件..."
MEMORY_DIR="$HOME/.openclaw/workspace/memory"
MEMORY_FILE="$HOME/.openclaw/workspace/MEMORY.md"

if [ -d "$MEMORY_DIR" ]; then
    tar -czf "$TEMP_DIR/openclaw_memory_${TIMESTAMP}.tar.gz" -C "$HOME/.openclaw/workspace" memory/ 2>/dev/null
    MEMORY_SIZE=$(du -h "$TEMP_DIR/openclaw_memory_${TIMESTAMP}.tar.gz" | cut -f1)
    log_info "记忆目录备份成功: $MEMORY_SIZE"
else
    log_warn "记忆目录不存在: $MEMORY_DIR"
fi

if [ -f "$MEMORY_FILE" ]; then
    cp "$MEMORY_FILE" "$TEMP_DIR/MEMORY_${TIMESTAMP}.md"
    log_info "MEMORY.md 备份成功"
else
    log_warn "MEMORY.md 不存在: $MEMORY_FILE"
fi

# 3. 备份 OpenClaw 配置
log_info "备份 OpenClaw 配置..."
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"
if [ -f "$OPENCLAW_CONFIG" ]; then
    cp "$OPENCLAW_CONFIG" "$TEMP_DIR/openclaw_config_${TIMESTAMP}.json"
    log_info "OpenClaw 配置备份成功"
else
    log_warn "OpenClaw 配置不存在: $OPENCLAW_CONFIG"
fi

# 4. 创建备份清单
log_info "创建备份清单..."
MANIFEST_FILE="$TEMP_DIR/manifest_${TIMESTAMP}.txt"
cat > "$MANIFEST_FILE" << EOF
Maybe Finance 备份清单
======================
备份时间: $(date)
备份目录: $BACKUP_DIR

备份内容:
EOF

ls -lh "$TEMP_DIR"/* >> "$MANIFEST_FILE"

cat >> "$MANIFEST_FILE" << EOF

系统信息:
- macOS 版本: $(sw_vers -productVersion)
- Docker 版本: $(docker --version)
- 项目路径: $PROJECT_ROOT

恢复说明:
1. 数据库: psql -U maybe_user -d maybe_production < maybe_production_${TIMESTAMP}.sql
2. 记忆文件: tar -xzf openclaw_memory_${TIMESTAMP}.tar.gz -C ~/.openclaw/workspace/
3. MEMORY.md: cp MEMORY_${TIMESTAMP}.md ~/.openclaw/workspace/MEMORY.md
4. OpenClaw 配置: cp openclaw_config_${TIMESTAMP}.json ~/.openclaw/openclaw.json
EOF

# 5. 挂载 NAS
log_info "挂载 NAS: //$NAS_USER@$NAS_IP/$NAS_SHARE"
MOUNT_POINT="${NAS_MOUNT_POINT:-/Volumes/nas_backup}"

# 创建挂载点
if [ ! -d "$MOUNT_POINT" ]; then
    sudo mkdir -p "$MOUNT_POINT"
fi

# 检查是否已挂载
if mount | grep -q "$MOUNT_POINT"; then
    log_info "NAS 已挂载，跳过挂载步骤"
else
    # 挂载 SMB 共享
    if mount_smbfs "//$NAS_USER:$NAS_PASSWORD@$NAS_IP/$NAS_SHARE" "$MOUNT_POINT" 2>/dev/null; then
        log_info "NAS 挂载成功"
    else
        log_error "NAS 挂载失败"
        log_error "请检查:"
        log_error "  1. NAS IP 地址是否正确: $NAS_IP"
        log_error "  2. 共享名称是否正确: $NAS_SHARE"
        log_error "  3. 用户名和密码是否正确"
        log_error "  4. NAS 是否在线"
        exit 1
    fi
fi

# 6. 创建 NAS 备份目录
NAS_BACKUP_PATH="$MOUNT_POINT/maybe_backups/$BACKUP_DIR"
log_info "创建备份目录: $NAS_BACKUP_PATH"
mkdir -p "$NAS_BACKUP_PATH"

# 7. 复制备份文件到 NAS
log_info "复制备份文件到 NAS..."
if cp -v "$TEMP_DIR"/* "$NAS_BACKUP_PATH/" 2>&1 | while read line; do log_info "  $line"; done; then
    log_info "备份文件复制成功"
else
    log_error "备份文件复制失败"
    exit 1
fi

# 8. 验证备份
log_info "验证备份完整性..."
VERIFY_FILE="$NAS_BACKUP_PATH/.verified"
if [ -f "$NAS_BACKUP_PATH/manifest_${TIMESTAMP}.txt" ] && [ -f "$NAS_BACKUP_PATH/maybe_production_${TIMESTAMP}.sql" ]; then
    touch "$VERIFY_FILE"
    log_info "备份验证通过"
else
    log_error "备份验证失败：缺少关键文件"
    exit 1
fi

# 9. 清理旧备份
if [ -n "$BACKUP_RETENTION_DAYS" ] && [ "$BACKUP_RETENTION_DAYS" -gt 0 ]; then
    log_info "清理 ${BACKUP_RETENTION_DAYS} 天前的备份..."
    
    # 找到所有备份目录
    find "$MOUNT_POINT/maybe_backups" -maxdepth 1 -type d -name "backup_*" | while read backup_dir; do
        # 提取日期
        dir_name=$(basename "$backup_dir")
        dir_date=$(echo "$dir_name" | sed 's/backup_\([0-9]\{8\}\)_.*/\1/')
        
        # 计算天数差
        current_date=$(date +%Y%m%d)
        days_diff=$(( ( $(date -j -f "%Y%m%d" "$current_date" +%s) - $(date -j -f "%Y%m%d" "$dir_date" +%s) ) / 86400 ))
        
        if [ "$days_diff" -gt "$BACKUP_RETENTION_DAYS" ]; then
            log_info "删除旧备份: $dir_name (${days_diff}天前)"
            rm -rf "$backup_dir"
        fi
    done
fi

# 10. 卸载 NAS（可选）
# 如果希望保持 NAS 挂载以便手动访问，可以注释掉这部分
# log_info "卸载 NAS..."
# umount "$MOUNT_POINT"
# log_info "NAS 已卸载"

# 11. 输出备份摘要
log_info "========================================="
log_info "备份完成！"
log_info "========================================="
log_info "备份位置: $NAS_BACKUP_PATH"
log_info "备份清单: $NAS_BACKUP_PATH/manifest_${TIMESTAMP}.txt"
log_info ""
log_info "备份文件列表:"
ls -lh "$NAS_BACKUP_PATH" | grep -v "^total" | grep -v "^d" | awk '{print "  " $9 " (" $5 ")"}'
log_info ""
log_info "恢复命令:"
log_info "  ./tools/backup/restore.sh $BACKUP_DIR"
log_info "========================================="

exit 0
