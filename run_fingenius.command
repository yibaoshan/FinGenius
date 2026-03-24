#!/bin/bash

set -u

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "========================================"
echo " FinGenius Launcher (macOS)"
echo "========================================"
echo

find_python_cmd() {
  local candidate=""

  for candidate in /opt/homebrew/bin/python3.12 python3.12; do
    if command -v "$candidate" >/dev/null 2>&1; then
      echo "$candidate"
      return 0
    fi
  done

  if command -v python3 >/dev/null 2>&1; then
    local py_ok
    py_ok="$(python3 - <<'PY'
import sys
print("1" if sys.version_info >= (3, 12) else "0")
PY
)"
    if [[ "$py_ok" == "1" ]]; then
      echo "python3"
      return 0
    fi
  fi

  return 1
}

ensure_venv_and_deps() {
  local py_cmd="$1"

  if [[ ! -x ".venv/bin/python" ]]; then
    echo "未检测到虚拟环境，开始自动创建 .venv ..."
    echo "使用解释器: $py_cmd"
    "$py_cmd" -m venv .venv || return 1
  fi

  echo
  echo "检查依赖是否完整..."
  if ! .venv/bin/python -c "import openai, pydantic, rich" >/dev/null 2>&1; then
    echo "依赖不完整，开始安装 requirements.txt（将显示实时进度）..."
    .venv/bin/python -m pip install --upgrade pip || return 1
    .venv/bin/pip install -r requirements.txt || return 1
  else
    echo "依赖检查通过。"
  fi
}

PY_CMD="$(find_python_cmd || true)"
if [[ -z "${PY_CMD}" ]]; then
  echo "未找到 Python 3.12+，无法自动初始化环境。"
  echo "请先安装 Python 3.12（推荐 Homebrew）："
  echo "  brew install python@3.12"
  echo
  read -r -p "按回车键退出..."
  exit 1
fi

if ! ensure_venv_and_deps "$PY_CMD"; then
  echo
  echo "环境初始化失败。请检查网络、Python 安装和 pip 错误日志。"
  read -r -p "按回车键退出..."
  exit 1
fi

if [[ ! -f "config/config.toml" ]]; then
  echo "未找到配置文件: config/config.toml"
  echo "请先复制并填写配置："
  echo "  cp config/config.example.toml config/config.toml"
  echo
  read -r -p "按回车键退出..."
  exit 1
fi

if ! grep -qE '^[[:space:]]*api_key[[:space:]]*=[[:space:]]*".+"' "config/config.toml"; then
  echo "config/config.toml 中未检测到有效 api_key。"
  echo "请先填写 LLM API Key。"
  echo
  read -r -p "按回车键退出..."
  exit 1
fi

read -r -p "请输入股票代码（例如 000001）: " STOCK_CODE
while [[ -z "${STOCK_CODE// }" ]]; do
  read -r -p "股票代码不能为空，请重新输入: " STOCK_CODE
done

echo
echo "参数说明："
echo "1) max_steps（每个专家最多分析几步）"
echo "   - 越大越深入，但越慢、成本越高。"
echo "   - 建议：先用 1 或 2。"
echo "2) debate_rounds（专家互相辩论几轮）"
echo "   - 越大讨论越充分，但总耗时更长。"
echo "   - 建议：先用 1。"
echo
echo "推荐新手配置：max_steps=1, debate_rounds=1（先跑通）"
echo

read -r -p "请输入 max_steps（每个专家最多分析几步，默认 2）: " MAX_STEPS
MAX_STEPS="${MAX_STEPS:-2}"

read -r -p "请输入 debate_rounds（专家辩论轮数，默认 1）: " DEBATE_ROUNDS
DEBATE_ROUNDS="${DEBATE_ROUNDS:-1}"

read -r -p "是否启用 TTS 播报？(y/N): " ENABLE_TTS
ENABLE_TTS="${ENABLE_TTS:-N}"

CMD=( ".venv/bin/python" "main.py" "$STOCK_CODE" "--max-steps" "$MAX_STEPS" "--debate-rounds" "$DEBATE_ROUNDS" )
if [[ "$ENABLE_TTS" =~ ^[Yy]$ ]]; then
  CMD+=( "--tts" )
fi

echo
echo "即将执行: ${CMD[*]}"
echo

"${CMD[@]}"
RUN_STATUS=$?

echo
if [[ $RUN_STATUS -eq 0 ]]; then
  LATEST_HTML="$(ls -1t report/html/*.html 2>/dev/null | head -n 1 || true)"
  if [[ -n "$LATEST_HTML" ]]; then
    ABS_HTML_PATH="$(cd "$(dirname "$LATEST_HTML")" && pwd)/$(basename "$LATEST_HTML")"
    echo "运行完成。"
    echo "报告文件路径：$ABS_HTML_PATH"
    echo "正在使用系统默认浏览器打开报告..."
    open "$ABS_HTML_PATH"
  else
    echo "运行完成，但未找到 report/html 下的 HTML 报告。"
  fi
else
  echo "运行失败，退出码: $RUN_STATUS"
fi

echo
read -r -p "按回车键退出..."
