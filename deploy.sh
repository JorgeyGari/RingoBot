#!/bin/sh
# Build and publish the bot image, or update the running container on the server.
#   ./deploy.sh push   # local machine: build, tag, push to Docker Hub
#   ./deploy.sh up     # server machine: pull the new image, restart, prune
set -eu

IMAGE=jorgeygari/ringobot

case "${1:-}" in
push)
    TAG=$(git rev-parse --short HEAD)
    docker build --platform linux/amd64 -t "$IMAGE:$TAG" -t "$IMAGE:latest" .
    docker push "$IMAGE:$TAG"
    docker push "$IMAGE:latest"
    echo "pushed $IMAGE:$TAG"
    ;;
up)
    # jre-server only ships the standalone docker-compose binary
    if command -v docker-compose >/dev/null 2>&1; then
        COMPOSE=docker-compose
    else
        COMPOSE="docker compose"
    fi
    # Deliberate word splitting: "docker compose" is two words
    $COMPOSE pull
    $COMPOSE up -d
    docker image prune -f
    $COMPOSE logs --tail=20 ringobot
    ;;
*)
    echo "usage: $0 push|up" >&2
    exit 1
    ;;
esac
