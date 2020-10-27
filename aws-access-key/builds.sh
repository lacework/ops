#!/bin/bash -e
export IMAGE_NAME=burhansibailw/iam-access-key-alert-test
if [ "$IS_PULL_REQUEST" != true ]; then
  sudo docker build -t $IMAGE_NAME:$BRANCH.$SHIPPABLE_BUILD_NUMBER .
  sudo docker push $IMAGE_NAME:$BRANCH.$SHIPPABLE_BUILD_NUMBER
else
  echo "skipping because it's a PR"
fi