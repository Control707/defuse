#!/bin/bash
# DEFUSE - double-click this file (or run ./START.command) to start the talking AI bomb.
cd "$(dirname "$0")"
ROOT="$PWD"
# 1) local AI brain (Ollama, runs on this Mac, no account needed)
if ! curl -s -m 2 localhost:11434/api/version >/dev/null; then
  echo "Starting the AI brain..."
  (cd ai && OLLAMA_MODELS="$ROOT/ai/models" HOME="$ROOT/ai" nohup ./ollama serve > serve.log 2>&1 &)
  for i in $(seq 1 20); do curl -s -m 1 localhost:11434/api/version >/dev/null && break; sleep 1; done
fi
echo "Warming up the AI (10-20 s)..."
curl -s -m 60 localhost:11434/api/generate -d '{"model":"llama3.2:3b","prompt":"hi","stream":false,"keep_alive":"2h"}' >/dev/null
# 2) the bomb host: voice out + always-on mic in
export OLLAMA_MODEL=llama3.2:3b
cd host
exec ./venv/bin/python defuse_host.py --mic ${VOICE:+--voice "$VOICE"} "$@"
