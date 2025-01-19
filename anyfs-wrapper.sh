#!/usr/bin/env bash
set -e

SCRIPTNAME="${BASH_SOURCE[0]##*/}"
WRAPPERPROG="${SCRIPTNAME#anyfs-}"
SCRIPTDIR="${BASH_SOURCE[0]%/*}"

export PATH+=:"$SCRIPTDIR" # for local launch
ANYFSPROG="$(which anyfs)"
APIHANDLERPROG="$(which "$WRAPPERPROG")"

ANYFSARGS=()
OTHERARGS=()
ISANYFSARGS=1
for ((IDX=1; IDX <= $#; ++IDX)); do
    if [[ "${@:$IDX:1}" == "--" ]]; then
        ISANYFSARGS=0
        continue
    fi

    if [[ $ISANYFSARGS -eq 1 ]]; then
        ANYFSARGS+=("${@:$IDX:1}")
    else
        OTHERARGS+=("${@:$IDX:1}")
    fi
done

"$ANYFSPROG" "${ANYFSARGS[@]}" -c "$APIHANDLERPROG" "${OTHERARGS[@]}"
