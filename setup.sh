#!/bin/bash
# One-time setup on a Mac: Python packages, local speech-to-text, natural voice, local AI brain.
set -e
cd "$(dirname "$0")"
ROOT="$PWD"
echo "== Python packages"
python3 -m venv host/venv
host/venv/bin/pip install -q -r host/requirements.txt
echo "== Natural voice (Piper, ~120 MB)"
mkdir -p host/voices
B=https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/ryan/high
[ -f host/voices/ryan.onnx ] || curl -fL -o host/voices/ryan.onnx $B/en_US-ryan-high.onnx
[ -f host/voices/ryan.onnx.json ] || curl -fL -o host/voices/ryan.onnx.json $B/en_US-ryan-high.onnx.json
echo "== Local AI brain (Ollama + llama3.2:3b, ~2 GB)"
mkdir -p ai/models
if [ ! -x ai/ollama ]; then
  curl -fL -o ai/ollama.tgz https://github.com/ollama/ollama/releases/latest/download/ollama-darwin.tgz
  (cd ai && tar xzf ollama.tgz && rm ollama.tgz)
fi
(cd ai && OLLAMA_MODELS="$ROOT/ai/models" HOME="$ROOT/ai" nohup ./ollama serve > serve.log 2>&1 &)
sleep 3
(cd ai && OLLAMA_MODELS="$ROOT/ai/models" HOME="$ROOT/ai" ./ollama pull llama3.2:3b)
echo "Done. Upload firmware/defuse/defuse.ino to the Mega, then run ./START.command"
