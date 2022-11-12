#!/bin/bash

export S3FS_MOUNT_POINT=/octobot/user
export S3FS_CACHE_DIR=/tmp/s3fs

# load env file
ENV_FILE=.env
if [[ -f "$ENV_FILE" ]]; then
    source $ENV_FILE
fi

# start s3fs if bucket name is provided
# https://github.com/s3fs-fuse/s3fs-fuse
# https://www.mankier.com/1/s3fs#Performance_Considerations-Performance_of_S3_requests
if [[ -n "$S3FS_BUCKET_NAME" ]]; then
    mkdir -p $S3FS_CACHE_DIR
    s3fs $S3FS_BUCKET_NAME $S3FS_MOUNT_POINT -o endpoint=$S3FS_BUCKET_REGION -o iam_role=auto -o allow_other -o umask=000 -o enable_noobj_cache -o notsup_compat_dir -o parallel_count=20 -o multireq_max=2000 -o list_object_max_keys=9000 -o max_stat_cache_size=900,000 -o use_cache=$S3FS_CACHE_DIR -o check_cache_dir_exist
fi
