#!/bin/bash
#
# The script should be used to build the `$CONTAINER_NAME`
# container and push it to hub.docker.com
#

log_message () {
    typeset SEVERITY=$1
    typeset MESSAGE="$2"
    if [ "$DEBUG" == "0" -a "$SEVERITY" == "DEBUG" ]; then
        return
    else
        echo `date` $SEVERITY "$MESSAGE"
    fi
}

DATE=`git log -1 --date=short --format="%cd"`
BRANCH=`git rev-parse --abbrev-ref HEAD`
FULL_COMMIT=`git log -1 --date=short --format="%h"`

if [ -z "$DATE" -o -z "$BRANCH" -o -z "$FULL_COMMIT" ]; then
	log_message ERROR "Failed to learn either git date, branch or full commit details - aborting..."
	exit 1
fi

if [ -z "$TAG" ]; then
	TAG=${DATE}_${BRANCH}_${FULL_COMMIT}
fi

CONTAINER_NAME="iam-access-key-alert-test"

log_message INFO "Will process the following container: $CONTAINER_NAME"
log_message INFO "Using container tag $TAG"

log_message INFO "Building container $CONTAINER_NAME ..."
docker build --force-rm=true -t burhansibailw/$CONTAINER_NAME . -f aws-access-key/Dockerfile
if [ $? -ne 0 ]; then
    log_message ERROR "Failed to build container $CONTAINER_NAME"
    exit 1
fi

log_message INFO "Pushing the new container to hub.docker.com with tag $TAG..."
docker tag $DOCKER_TAG_OPTIONS burhansibailw/$CONTAINER_NAME:latest burhansibailw/$CONTAINER_NAME:$TAG
bash ./aws-access-key/with_backoff.sh docker push burhansibailw/$CONTAINER_NAME:$TAG
if [ $? -ne 0 ]; then
    log_message ERROR "Failed to push container $CONTAINER_NAME to hub.docker.com"
    exit 1
fi


log_message INFO "Successfully completed the process"