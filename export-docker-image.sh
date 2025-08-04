# Now that git is clean, rebuild the image
docker buildx build --platform linux/arm64 --file Dockerfile.fast.cross --tag diagnostic-agent:fast-cross --load .
docker save diagnostic-agent:fast-cross -o diagnostic-agent_fast-cross.tar