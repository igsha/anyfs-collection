#!/usr/bin/env bash
set -e

which http rg xq > /dev/null

read -r BASEURL < <(awk -F/ '{printf "%s//%s/%s\n", $1, $3, $4 }' <<< "$1")
http "$1" \
    | rg --multiline-dotall -UPo '<div class="serial-translations-box".*?</div>' \
    | xq -r '.div.select.option[] |
            "\(.["@data-title"]): '$BASEURL'/\(.["@data-media-id"])/\(.["@data-media-hash"])/720p"'
