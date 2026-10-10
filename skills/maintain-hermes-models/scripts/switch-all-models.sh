#!/usr/bin/env bash
# 一键把「某个 / 所有 profile 的默认模型」切到目标：探活端点 → 报名(--dry-run) → 真写 → 回读。
#
#   scripts/switch-all-models.sh <模型 id> [provider] [base_url] [--key-env <变量名>] [--dry-run] [--selftest]
#   scripts/switch-all-models.sh deepseek-flash deepseek https://api.deepseek.com/v1
#
# 只编排同目录那两支脚本（switch-profile-models.py / verify-profile-models.py），本脚本自己不写任何文件。
# 探活的 key **只从环境变量取**（默认 `<PROVIDER 大写>_API_KEY`）；没设就跳过探活并明说，不报错。
# 退出码：0 切换+回读都过 · 1 切换或回读有失败项 · 2 用法错。
set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
DRY=0
SELFTEST=0
KEY_ENV=""
POS=()
while [ $# -gt 0 ]; do
  case "$1" in
    --dry-run) DRY=1; shift ;;
    --selftest) SELFTEST=1; shift ;;
    --key-env) KEY_ENV="${2:-}"; shift 2 ;;
    -h|--help) sed -n '2,10p' "$0"; exit 0 ;;
    *) POS+=("$1"); shift ;;
  esac
done
MODEL="${POS[0]:-}"
PROVIDER="${POS[1]:-deepseek}"
BASE_URL="${POS[2]:-https://api.deepseek.com/v1}"
SWITCH="$HERE/switch-profile-models.py"
VERIFY="$HERE/verify-profile-models.py"

# 步骤顺序是这篇脚本的全部内容：探活必须早于真写（别名写错时你要改的是 N 份文件）。
if [ "$SELFTEST" = 1 ]; then
  rc=0
  order=""
  for m in "S1 探活" "S2 报名" "S3 真写" "S4 回读"; do
    n=$(grep -n "^# $m" "$0" | head -1 | cut -d: -f1)
    [ -n "$n" ] || { echo "selftest: 缺少步骤标记 '^# $m'"; rc=1; }
    order="$order ${n:-0}"
  done
  set -- $order
  [ "$1" -lt "$2" ] && [ "$2" -lt "$3" ] && [ "$3" -lt "$4" ] || { echo "selftest: 步骤顺序错：$order"; rc=1; }
  for s in "$SWITCH" "$VERIFY"; do
    [ -f "$s" ] || { echo "selftest: 缺兄弟脚本 $s"; rc=1; }
  done
  [ "$DRY" = 1 ] && grep -q -- '--dry-run' "$0" || true
  [ "$rc" = 0 ] && echo "selftest: ok（四步顺序 + 两支兄弟脚本都在）"
  exit "$rc"
fi

if [ -z "$MODEL" ]; then
  echo "用法：$0 <模型 id> [provider] [base_url] [--key-env <变量名>] [--dry-run]" >&2
  exit 2
fi
for s in "$SWITCH" "$VERIFY"; do
  [ -f "$s" ] || { echo "找不到 $s（两支脚本要和本脚本同目录）" >&2; exit 2; }
done

FAIL=0
echo "== 目标：model=$MODEL provider=$PROVIDER base_url=$BASE_URL"

# S1 探活：一条 curl，确认模型别名真的存在（端点的返回体自己会报 model 名）
[ -n "$KEY_ENV" ] || KEY_ENV="$(echo "$PROVIDER" | tr 'a-z-' 'A-Z_')_API_KEY"
KEY="${!KEY_ENV:-}"   # 间接展开：取那个变量的值，没设就是空（不 dump 整个环境）
if [ -n "$KEY" ]; then
  echo "== S1 探活 ${BASE_URL}（key 取自环境变量 ${KEY_ENV}）"
  curl -s --noproxy '*' -m 30 "$BASE_URL/chat/completions" \
    -H "Authorization: Bearer $KEY" -H "Content-Type: application/json" \
    -d "{\"model\":\"$MODEL\",\"messages\":[{\"role\":\"user\",\"content\":\"hi\"}],\"max_tokens\":16}"
  echo
else
  echo "== S1 跳过探活：环境变量 $KEY_ENV 没设（自己 export 一个再跑，或确认别名来自别处的证据）"
  FAIL=1
fi

# S2 报名：--dry-run 列出会改谁 / 谁 already
echo "== S2 报名（--dry-run）"
python3 -B "$SWITCH" --model "$MODEL" --provider "$PROVIDER" --base-url "$BASE_URL" --dry-run || FAIL=1

if [ "$DRY" = 1 ]; then
  echo "== --dry-run：到此为止，一个字节都没写"
  exit "$FAIL"
fi

# S3 真写（每份文件整份备份到 backups/model-switch-<ts>/）
echo "== S3 真写"
python3 -B "$SWITCH" --model "$MODEL" --provider "$PROVIDER" --base-url "$BASE_URL" || FAIL=1

# S4 回读：config 侧（✅/❌）+ 运行侧（最近一次真实调用算到哪个端点）+ 严格加载器有没有拒收
echo "== S4 回读 config 侧 + 运行侧"
python3 -B "$VERIFY" --expect-model "$MODEL" --expect-base-url "$BASE_URL" || FAIL=1
echo "== S4 回读 hermes profile list（Model 列出现 -- 就是那份 config 被严格加载器拒收）"
hermes profile list || true

[ "$FAIL" = 0 ] && echo "== 全绿" || echo "== 有失败项，见上面逐条"
exit "$FAIL"
