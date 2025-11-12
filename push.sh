#!/bin/sh
# This script builds a Docker image for the Ringobot and pushes it to Docker Hub.
docker build -t jorgeygari/ringobot . && docker push jorgeygari/ringobot:latest
