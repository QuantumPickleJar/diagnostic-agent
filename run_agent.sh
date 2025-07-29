#!/bin/bash

PI_MODEL="/home/chatgpt-agent/models/tinyllama.gguf"
DEV_IP="192.168.0.153"
PORT=2222
USER=brick

if nc -z $DEV_IP $PORT; then
    echo "[+] Using remote model via SSH"
    open-interpreter --shell "ssh $USER@$DEV_IP" --system "$(cat system_prompt.txt)"
else
    echo "[-] Fallback: Using local model on Pi"
    ./llama.cpp/main -m $PI_MODEL -p "$(cat system_prompt.txt)"
fi  