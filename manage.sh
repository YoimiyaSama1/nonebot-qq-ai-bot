#!/usr/bin/env bash
# NoneBot2 机器人管理脚本: ./manage.sh {start|stop|restart|status|log}
set -u
DIR="$(cd "$(dirname "$0")" && pwd)"
PY="$HOME/.venvs/nonebot/bin/python"
LOG="/tmp/qqbot.log"
PIDFILE="/tmp/qqbot.pid"
PATTERN="nonebot/bin/python .*bot.py"

find_pids() { pgrep -f "$PATTERN" 2>/dev/null | grep -v "$$" || true; }

case "${1:-}" in
  start)
    if [ -n "$(find_pids)" ]; then echo "已经在运行: $(find_pids | tr '\n' ' ')"; exit 0; fi
    cd "$DIR"
    nohup "$PY" bot.py > "$LOG" 2>&1 &
    echo $! > "$PIDFILE"
    sleep 2
    echo "已启动, pid $(cat "$PIDFILE"), 日志: $LOG"
    ;;
  stop)
    pids="$(find_pids)"
    if [ -z "$pids" ]; then echo "未在运行"; exit 0; fi
    kill $pids 2>/dev/null
    sleep 2
    pids="$(find_pids)"
    [ -n "$pids" ] && kill -9 $pids 2>/dev/null
    rm -f "$PIDFILE"
    echo "已停止"
    ;;
  restart)
    "$0" stop >/dev/null 2>&1; sleep 1; "$0" start
    ;;
  status)
    pids="$(find_pids)"
    [ -n "$pids" ] && echo "运行中: $pids" || echo "未运行"
    ;;
  log)
    tail -n "${2:-30}" "$LOG"
    ;;
  *)
    echo "用法: $0 {start|stop|restart|status|log}"; exit 1
    ;;
esac
