#!/bin/bash

export EFS_USER_MOUNT_POINT=/octobot/user/

# load env file
ENV_FILE=.env
if [[ -f "$ENV_FILE" ]]; then
    source $ENV_FILE
fi

# start efs if file system id is provided
# https://github.com/aws/efs-utils
# 200 = 20sec timeout
if [[ -n "$EFS_FS_ENDPOINT" ]]; then
    mount -t nfs -o nfsvers=4.1,rsize=1048576,wsize=1048576,hard,timeo=200,retrans=2,noresvport $EFS_FS_ENDPOINT:/ $EFS_USER_MOUNT_POINT
fi

# mount efs mountpoint if file system id and mountpoint id is provided
# https://github.com/aws/efs-utils
if [[ -n "$EFS_FS_ID" && -n "$EFS_FS_MOUNTPOINT_ID" ]]; then
    mount -t efs -o tls,iam,accesspoint=$EFS_FS_MOUNTPOINT_ID $EFS_FS_ID:/ $EFS_USER_MOUNT_POINT
    amazon-efs-mount-watchdog &
fi
