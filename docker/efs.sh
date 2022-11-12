#!/bin/bash

export EFS_MOUNT_POINT=/octobot/user/

# load env file
ENV_FILE=.env
if [[ -f "$ENV_FILE" ]]; then
    source $ENV_FILE
fi

# start efs if file system id is provided
# https://github.com/aws/efs-utils
if [[ -n "$EFS_FS_ID" ]]; then
    sudo mount -t efs -o tls,iam $EFS_FS_ID $EFS_MOUNT_POINT
fi
