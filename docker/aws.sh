#!/bin/bash

source util.sh

# https://docs.aws.amazon.com/AmazonECS/latest/developerguide/task-metadata-endpoint-v4.html
if [[ -n "$ECS_CONTAINER_METADATA_URI_V4" ]]; then
  AWS_TASK_WITH_TAGS_DETAILS=$(curl --silent "$ECS_CONTAINER_METADATA_URI_V4/taskWithTags")
  AWS_TASK_TAGS=$(echo $AWS_TASK_WITH_TAGS_DETAILS | jq -r ".TaskTags")
  json_to_env "$AWS_TASK_TAGS"
fi
