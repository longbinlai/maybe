#!/bin/bash
# Maybe Finance Health Check Script
# Runs every 5 minutes via LaunchAgent, checks critical services and alerts via Feishu on failure.

set -euo pipefail

# ─── Configuration ────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

CONTAINERS=("maybe-web-1" "maybe-worker-1" "maybe-db-1" "maybe-redis-1" "maybe-qdrant-1")
DATAHUB_CACHE_DIR="${DATAHUB_CACHE_DIR:-${SCRIPT_DIR}/../datahub/cache}"
ALERT_LOCK_FILE="/tmp/health_check_last_alert"
ALERT_COOLDOWN=1800  # 30 minutes in seconds
OPENCLAW_CONFIG="$HOME/.openclaw/openclaw.json"

FEISHU_APP_ID="${FEISHU_APP_ID:-}"
FEISHU_CHAT_ID="${FEISHU_CHAT_ID:-}"

# ─── Globals ──────────────────────────────────────────────────────────────────

TOTAL_CHECKS=0
FAILED_CHECKS=0
FAILURES=()

# ─── Helpers ──────────────────────────────────────────────────────────────────

read_feishu_secret() {
    if [[ -f "$OPENCLAW_CONFIG" ]]; then
        python3 -c "
import json, sys
with open('$OPENCLAW_CONFIG') as f:
    cfg = json.load(f)
print(cfg['channels']['feishu']['accounts']['default']['appSecret'])
" 2>/dev/null
    else
        echo ""
    fi
}

get_feishu_tenant_token() {
    local app_secret="$1"
    local response
    response=$(curl -s -X POST "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal" \
        -H "Content-Type: application/json" \
        -d "{\"app_id\":\"${FEISHU_APP_ID}\",\"app_secret\":\"${app_secret}\"}")
    echo "$response" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tenant_access_token',''))" 2>/dev/null
}

should_send_alert() {
    if [[ ! -f "$ALERT_LOCK_FILE" ]]; then
        return 0
    fi
    local last_alert
    last_alert=$(cat "$ALERT_LOCK_FILE" 2>/dev/null || echo "0")
    local now
    now=$(date +%s)
    local diff=$(( now - last_alert ))
    if (( diff >= ALERT_COOLDOWN )); then
        return 0
    fi
    return 1
}

record_alert_time() {
    date +%s > "$ALERT_LOCK_FILE"
}

send_feishu_alert() {
    local message="$1"
    local app_secret
    app_secret=$(read_feishu_secret)
    if [[ -z "$app_secret" ]]; then
        echo "ERROR: Cannot read Feishu app secret from $OPENCLAW_CONFIG" >&2
        return 1
    fi

    local token
    token=$(get_feishu_tenant_token "$app_secret")
    if [[ -z "$token" ]]; then
        echo "ERROR: Failed to obtain Feishu tenant access token" >&2
        return 1
    fi

    local payload
    payload=$(python3 -c "
import json
print(json.dumps({
    'receive_id': '${FEISHU_CHAT_ID}',
    'msg_type': 'text',
    'content': json.dumps({'text': '''${message}'''})
}))
")

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X POST "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=chat_id" \
        -H "Authorization: Bearer ${token}" \
        -H "Content-Type: application/json" \
        -d "$payload")

    if [[ "$http_code" == "200" ]]; then
        echo "Feishu alert sent successfully."
        record_alert_time
    else
        echo "ERROR: Feishu alert failed with HTTP $http_code" >&2
    fi
}

record_check() {
    local name="$1"
    local status="$2"  # 0 = ok, non-zero = fail
    local detail="${3:-}"
    TOTAL_CHECKS=$(( TOTAL_CHECKS + 1 ))
    if [[ "$status" != "0" ]]; then
        FAILED_CHECKS=$(( FAILED_CHECKS + 1 ))
        FAILURES+=("${name}|${detail}")
        echo "FAIL: ${name} - ${detail}" >&2
    else
        echo "OK:   ${name}"
    fi
}

# ─── Check Functions ──────────────────────────────────────────────────────────

check_docker_containers() {
    local all_ok=true
    local failed_list=()
    for container in "${CONTAINERS[@]}"; do
        local state
        state=$(docker inspect -f '{{.State.Status}}' "$container" 2>/dev/null || echo "not_found")
        if [[ "$state" != "running" ]]; then
            all_ok=false
            failed_list+=("$container ($state)")
        fi
    done
    if $all_ok; then
        record_check "Docker containers" 0
    else
        local detail="${failed_list[*]}"
        record_check "Docker containers" 1 "$detail"
    fi
}

check_maybe_api() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:3000/up" 2>/dev/null || echo "000")
    if [[ "$http_code" == "200" ]]; then
        record_check "Maybe API" 0
    else
        record_check "Maybe API" 1 "HTTP $http_code"
    fi
}

check_qdrant() {
    local body
    body=$(curl -s --max-time 10 "http://localhost:6333/healthz" 2>/dev/null || echo "unreachable")
    if echo "$body" | grep -qiE "ok|passed|healthy"; then
        record_check "Qdrant" 0
    else
        record_check "Qdrant" 1 "response: $body"
    fi
}

check_ollama() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:11434/api/tags" 2>/dev/null || echo "000")
    if [[ "$http_code" == "200" ]]; then
        record_check "Ollama" 0
    else
        record_check "Ollama" 1 "HTTP $http_code"
    fi
}

check_openclaw_gateway() {
    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "http://localhost:3001/" 2>/dev/null || echo "000")
    # Any HTTP response (even 401/403) means the gateway is reachable
    if [[ "$http_code" != "000" ]]; then
        record_check "OpenClaw Gateway" 0
    else
        record_check "OpenClaw Gateway" 1 "unreachable"
    fi
}

check_datahub_cache() {
    local today
    today=$(date +%Y-%m-%d)
    if [[ -d "$DATAHUB_CACHE_DIR" ]]; then
        local count
        count=$(find "$DATAHUB_CACHE_DIR" -maxdepth 1 -name "*${today}*" -print 2>/dev/null | head -1)
        if [[ -n "$count" ]]; then
            record_check "DataHub cache" 0
        else
            record_check "DataHub cache" 1 "no cache file for today ($today)"
        fi
    else
        record_check "DataHub cache" 1 "directory not found: $DATAHUB_CACHE_DIR"
    fi
}

check_disk_space() {
    local usage
    usage=$(df / | awk 'NR==2 {gsub(/%/,""); print $5}')
    if (( usage <= 85 )); then
        record_check "Disk space" 0
    else
        record_check "Disk space" 1 "root partition at ${usage}%"
    fi
}

# ─── Main ─────────────────────────────────────────────────────────────────────

main() {
    echo "=== Health Check: $(date '+%Y-%m-%d %H:%M:%S') ==="

    check_docker_containers
    check_maybe_api
    check_qdrant
    check_ollama
    check_openclaw_gateway
    check_datahub_cache
    check_disk_space

    echo ""
    echo "Result: $(( TOTAL_CHECKS - FAILED_CHECKS ))/$TOTAL_CHECKS passed"

    if (( FAILED_CHECKS > 0 )); then
        # Build alert message
        local now_str
        now_str=$(date '+%Y-%m-%d %H:%M')
        local msg="⚠️ 系统健康检查告警\n\n时间：${now_str}\n状态：${FAILED_CHECKS}/${TOTAL_CHECKS} 项异常\n"

        for entry in "${FAILURES[@]}"; do
            local name="${entry%%|*}"
            local detail="${entry#*|}"
            msg="${msg}\n❌ ${name}: ${detail}"
        done

        local ok_count=$(( TOTAL_CHECKS - FAILED_CHECKS ))
        if (( ok_count > 0 )); then
            msg="${msg}\n\n其他 ${ok_count} 项检查正常。"
        fi

        echo ""
        echo -e "$msg" >&2

        # De-duplicate: only alert if cooldown has passed
        if should_send_alert; then
            send_feishu_alert "$(echo -e "$msg")"
        else
            local last_alert
            last_alert=$(cat "$ALERT_LOCK_FILE" 2>/dev/null || echo "unknown")
            local last_human
            last_human=$(date -r "$last_alert" '+%H:%M:%S' 2>/dev/null || echo "unknown")
            echo "Alert suppressed (last alert at ${last_human}, cooldown ${ALERT_COOLDOWN}s)."
        fi

        exit 1
    fi

    echo "All checks passed."
    exit 0
}

main "$@"
