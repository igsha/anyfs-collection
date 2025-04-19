#!/usr/bin/env bash
set -e

which http jq grep > /dev/null

read TOKEN < <(http "https://kodik-add.com/add-players.min.js?v=2" | grep -Po 'token="\K[^"]+')
http "https://kodikapi.com/search?title=$1&token=$TOKEN" | \
    jq '[.results |
        map({(.title + (.year|tostring)):
            {"title": .title, "title_orig": .title_orig, "other_title": .other_title, "year": .year, "link": "https:\(.link)"}}
            ) | add | .[]]'
