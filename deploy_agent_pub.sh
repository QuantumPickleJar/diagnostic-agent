#!/bin/bash

# Parameters
PI_USER=pi                      # Change if your Pi username is not 'pi'
PI_HOST=raspberrypi.local       # Or the Pi's IP address or hostname
SRC_TAR="diagnostic-agent_fast-cross.tar"
DEST_DIR="~/Desktop/agent/"

# Check for override via arguments
if [[ $# -ge 1 ]]; then
  PI_HOST="$1"
fi

echo "Deploying $SRC_TAR to $PI_USER@$PI_HOST:$DEST_DIR ..."

rsync -avz --progress "$SRC_TAR" "$PI_USER@$PI_HOST:$DEST_DIR"

if [[ $? -eq 0 ]]; then
  echo "File deployed successfully!"
  echo "SSH into your Pi and run:"
  echo "    docker load -i $DEST_DIR$SRC_TAR"
else
  echo "Deployment failed. Check your connection and paths."
fi
