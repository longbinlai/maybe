#!/bin/bash
# Maybe Finance 恢复脚本
# 功能：从 NAS 备份恢复数据库和 OpenClaw 记忆

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
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

log_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# 显示帮助
show_help() {
    cat << EOF
Maybe Finance 恢复脚本

用法:
  $0 [选项] [备份目录名]

选项:
  -l, --list          列出所有可用备份
  -d, --dir <name>    指定备份目录名（如 backup_20260525_143022）
  --db-only           仅恢复数据库
  --memory-only       仅恢复 OpenClaw 记忆
  --config-only       仅恢复 OpenClaw 配置
  -h, --help          显示此帮助信息

示例:
  $0 --list                          # 列出所有备份
  $0 backup_20260525_143022          # 恢复指定备份
  $0 --db-only backup_20260525_143022  # 仅恢复数据库
  $0                                 # 恢复最新备份

EOF
    exit 0
}

# 加载配置
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env.nas"

if [ ! -f "$ENV_FILE" ]; then
    log_error "配置文件不存在: $ENV_FILE"
    exit 1
fi

source "$ENV_FILE"

# 验证配置
if [ -z "$NAS_BACKUP_DIR" ]; then
    log_error "NAS_BACKUP_DIR 未配置，请检查 $ENV_FILE"
    exit 1
fi

# 检查 NAS 备份目录
if [ ! -d "$NAS_BACKUP_DIR" ]; then
    log_error "NAS 备份目录不存在: $NAS_BACKUP_DIR"
    log_error "请确保 NAS 已挂载到该路径"
    exit 1
fi

# 解析参数
LIST_ONLY=false
DB_ONLY=false
MEMORY_ONLY=false
CONFIG_ONLY=false
BACKUP_DIR=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -l|--list)
            LIST_ONLY=true
            shift
            ;;
        -d|--dir)
            BACKUP_DIR="$2"
            shift 2
            ;;
        --db-only)
            DB_ONLY=true
            shift
            ;;
        --memory-only)
            MEMORY_ONLY=true
            shift
            ;;
        --config-only)
            CONFIG_ONLY=true
            shift
            ;;
        -h|--help)
            show_help
            ;;
        *)
            if [[ "$1" =~ ^backup_ ]]; then
                BACKUP_DIR="$1"
            else
                log_error "未知参数: $1"
                show_help
            fi
            shift
            ;;
    esac
done

# 列出所有备份
list_backups() {
    if [ ! -d "$NAS_BACKUP_DIR" ]; then
        log_warn "备份目录不存在: $NAS_BACKUP_DIR"
        exit 0
    fi
    
    echo ""
    log_info "可用备份列表："
    echo "========================================="
    
    find "$NAS_BACKUP_DIR" -maxdepth 1 -type d -name "backup_*" | sort -r | while read backup_dir; do
        dir_name=$(basename "$backup_dir")
        
        # 解析日期
        dir_date=$(echo "$dir_name" | sed 's/backup_\([0-9]\{8\}\)_\([0-9]\{6\}\).*/\1 \2/')
        formatted_date=$(echo "$dir_date" | awk '{print substr($1,1,4)"-"substr($1,5,2)"-"substr($1,7,2)" "substr($2,1,2)":"substr($2,3,2)":"substr($2,5,2)}')
        
        # 计算大小
        size=$(du -sh "$backup_dir" 2>/dev/null | cut -f1)
        
        # 检查验证标记
        verified=""
        if [ -f "$backup_dir/.verified" ]; then
            verified=" ✓"
        fi
        
        echo "  📦 $dir_name ($formatted_date) - $size$verified"
        
        # 显示文件列表
        ls -1 "$backup_dir" 2>/dev/null | grep -v "^\.verified$" | sed 's/^/     /'
        echo ""
    done
    
    echo "========================================="
    log_info "提示: 使用 '$0 <备份目录名>' 恢复指定备份"
}

# 恢复备份
restore_backup() {
    local backup_path="$1"
    
    if [ ! -d "$backup_path" ]; then
        log_error "备份目录不存在: $backup_path"
        exit 1
    fi
    
    log_info "开始恢复备份: $(basename "$backup_path")"
    
    # 显示备份清单
    MANIFEST=$(find "$backup_path" -name "manifest_*.txt" | head -1)
    if [ -f "$MANIFEST" ]; then
        echo ""
        log_info "备份清单："
        cat "$MANIFEST"
        echo ""
    fi
    
    # 确认恢复
    if [ -z "$DB_ONLY" ] && [ -z "$MEMORY_ONLY" ] && [ -z "$CONFIG_ONLY" ]; then
        log_warn "这将恢复所有备份内容（数据库、记忆、配置）"
        read -p "是否继续？(y/N) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            log_info "已取消"
            exit 0
        fi
    fi
    
    # 1. 恢复数据库
    if [ -z "$MEMORY_ONLY" ] && [ -z "$CONFIG_ONLY" ]; then
        DB_FILE=$(find "$backup_path" -name "maybe_production_*.sql" | head -1)
        
        if [ -f "$DB_FILE" ]; then
            log_step "恢复数据库..."
            
            # 备份当前数据库
            log_info "备份当前数据库..."
            CURRENT_BACKUP="/tmp/maybe_current_$(date +%Y%m%d_%H%M%S).sql"
            docker exec maybe-db-1 pg_dump -U maybe_user maybe_production > "$CURRENT_BACKUP" 2>/dev/null
            log_info "当前数据库已备份到: $CURRENT_BACKUP"
            
            # 恢复
            log_info "正在恢复数据库..."
            if docker exec -i maybe-db-1 psql -U maybe_user maybe_production < "$DB_FILE" 2>&1 | grep -q "ERROR"; then
                log_error "数据库恢复过程中出现错误"
                log_warn "当前数据库已备份，可手动恢复: $CURRENT_BACKUP"
                exit 1
            fi
            
            log_info "数据库恢复成功"
        else
            log_warn "备份中未找到数据库文件"
        fi
    fi
    
    # 2. 恢复 OpenClaw 记忆
    if [ -z "$DB_ONLY" ] && [ -z "$CONFIG_ONLY" ]; then
        MEMORY_TAR=$(find "$backup_path" -name "openclaw_memory_*.tar.gz" | head -1)
        MEMORY_MD=$(find "$backup_path" -name "MEMORY_*.md" | head -1)
        
        if [ -f "$MEMORY_TAR" ]; then
            log_step "恢复 OpenClaw 记忆目录..."
            
            # 备份当前记忆
            if [ -d "$HOME/.openclaw/workspace/memory" ]; then
                CURRENT_MEMORY_BACKUP="/tmp/openclaw_memory_current_$(date +%Y%m%d_%H%M%S).tar.gz"
                tar -czf "$CURRENT_MEMORY_BACKUP" -C "$HOME/.openclaw/workspace" memory/ 2>/dev/null
                log_info "当前记忆已备份到: $CURRENT_MEMORY_BACKUP"
            fi
            
            # 恢复
            tar -xzf "$MEMORY_TAR" -C "$HOME/.openclaw/workspace/"
            log_info "记忆目录恢复成功"
        fi
        
        if [ -f "$MEMORY_MD" ]; then
            log_step "恢复 MEMORY.md..."
            
            # 备份当前 MEMORY.md
            if [ -f "$HOME/.openclaw/workspace/MEMORY.md" ]; then
                cp "$HOME/.openclaw/workspace/MEMORY.md" "/tmp/MEMORY_current_$(date +%Y%m%d_%H%M%S).md"
                log_info "当前 MEMORY.md 已备份"
            fi
            
            cp "$MEMORY_MD" "$HOME/.openclaw/workspace/MEMORY.md"
            log_info "MEMORY.md 恢复成功"
        fi
    fi
    
    # 3. 恢复 OpenClaw 配置
    if [ -z "$DB_ONLY" ] && [ -z "$MEMORY_ONLY" ]; then
        CONFIG_FILE=$(find "$backup_path" -name "openclaw_config_*.json" | head -1)
        
        if [ -f "$CONFIG_FILE" ]; then
            log_step "恢复 OpenClaw 配置..."
            
            # 备份当前配置
            if [ -f "$HOME/.openclaw/openclaw.json" ]; then
                cp "$HOME/.openclaw/openclaw.json" "/tmp/openclaw_config_current_$(date +%Y%m%d_%H%M%S).json"
                log_info "当前配置已备份"
            fi
            
            cp "$CONFIG_FILE" "$HOME/.openclaw/openclaw.json"
            log_info "OpenClaw 配置恢复成功"
            
            log_warn "需要重启 OpenClaw Gateway 以应用配置"
            log_info "运行: openclaw gateway restart"
        fi
    fi
    
    # 4. 重建记忆索引
    if [ -z "$DB_ONLY" ] && [ -z "$CONFIG_ONLY" ]; then
        log_step "重建记忆索引..."
        if command -v openclaw &> /dev/null; then
            PATH="/opt/homebrew/bin:$PATH" openclaw memory index --force
            log_info "记忆索引重建成功"
        else
            log_warn "openclaw 命令不可用，请手动重建索引"
            log_info "运行: openclaw memory index --force"
        fi
    fi
    
    log_info "========================================="
    log_info "恢复完成！"
    log_info "========================================="
    log_info "已恢复:"
    [ -z "$MEMORY_ONLY" ] && [ -z "$CONFIG_ONLY" ] && log_info "  ✓ 数据库"
    [ -z "$DB_ONLY" ] && [ -z "$CONFIG_ONLY" ] && log_info "  ✓ OpenClaw 记忆"
    [ -z "$DB_ONLY" ] && [ -z "$MEMORY_ONLY" ] && log_info "  ✓ OpenClaw 配置"
    log_info ""
    log_info "下一步:"
    log_info "  1. 验证数据是否正确"
    log_info "  2. 重启 OpenClaw Gateway: openclaw gateway restart"
    log_info "  3. 检查 Maybe Finance: open http://localhost:3000"
    log_info ""
    log_info "如需回滚，当前数据已备份到 /tmp/"
    log_info "========================================="
}

# 主流程
if [ "$LIST_ONLY" = true ]; then
    list_backups
    exit 0
fi

# 如果未指定备份目录，使用最新的
if [ -z "$BACKUP_DIR" ]; then
    log_info "未指定备份目录，使用最新备份..."
    BACKUP_DIR=$(find "$NAS_BACKUP_DIR" -maxdepth 1 -type d -name "backup_*" | sort -r | head -1 | xargs basename)

    if [ -z "$BACKUP_DIR" ]; then
        log_error "未找到任何备份"
        exit 1
    fi

    log_info "最新备份: $BACKUP_DIR"
fi

BACKUP_PATH="$NAS_BACKUP_DIR/$BACKUP_DIR"

# 执行恢复
restore_backup "$BACKUP_PATH"

exit 0
