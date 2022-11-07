#!/bin/bash

export S3FS_MOUNT_POINT=/octobot/user

# load env file
ENV_FILE=.env
if [[ -f "$ENV_FILE" ]]; then
    source $ENV_FILE
fi

# start s3fs if bucket name is provided
# https://github.com/s3fs-fuse/s3fs-fuse
if [[ -n "$S3FS_BUCKET_NAME" ]]; then
   s3fs $S3FS_BUCKET_NAME $S3FS_MOUNT_POINT -o use_cache=/tmp -o iam_role=auto -o allow_other -o umask=000
fi
