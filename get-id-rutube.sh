#!/usr/bin/env bash
set -e

which jq curl > /dev/null

read -r INIT < <(curl -sL "$1" | grep -Po "window\.reduxState\s*=\s*\K{.+(?=;)")
readarray -t SUBS < <(grep -Po "\\\\x[[:xdigit:]]{2}" <<< "$INIT" | sort -u)
for __key in "${SUBS[@]}"; do
    __val=$(printf "$__key")
    INIT="${INIT//"$__key"/"$__val"}"
done

if [[ -n "$JSON" ]]; then
    echo "$INIT"
else
    jq -r '.api.queries | with_entries(select(.key|match("channelInfo.+")))[].data.id' <<< "$INIT"
fi
