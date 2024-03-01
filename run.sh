#!/bin/bash
set -e
docker run \
    --rm \
    --name intemo-logger \
    -e intemo_user=$intemo_user \
    -e intemo_pass=$intemo_pass \
    -e INTEMO_ACTION=$INTEMO_ACTION \
    intemo-logger
 