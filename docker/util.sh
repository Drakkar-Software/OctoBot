#!/bin/bash

json_to_env() {
  for s in $(echo $1 | jq -r 'keys[] as $k | "export \($k)=\(.[$k])"'); do export $s; done
}
