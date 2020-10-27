#!/usr/bin/env bash


RETRIES=4
INITIAL_TIMEOUT=3

function with_backoff {
  local timeout=$INITIAL_TIMEOUT
  local retry=0
  local exitCode=0

  while true
  do
    "$@"
    exitCode=$?

    if [[ $exitCode == 0 ]]
    then
      break
    fi

    if [[ $retry == $RETRIES ]]
    then
      break
    fi

    retry=$(( retry + 1 ))

    echo "Failed with code $exitCode. Retrying in $timeout seconds"

    timeout=$(( timeout * 2 ))
    sleep $timeout

  done

  if [[ $exitCode != 0 ]]
  then
    echo "Failed with code $exitCode. Giving up after repeated failures"
  fi

  return $exitCode
}

with_backoff $@