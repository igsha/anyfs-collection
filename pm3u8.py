#!/usr/bin/env python

import argparse
from copy import deepcopy
import json
import re
import sys

import m3u8
import requests


class Fetcher:
    def __init__(self, url, name, referer):
        self.referer = referer
        headers = {}
        if self.referer is not None:
            headers = {"referer":self.referer}

        self.lst = m3u8.load(url, headers=headers)
        self.name = name if name is not None else "video"

    @staticmethod
    def printbytes(path, buf):
        if isinstance(buf, str):
            buf = buf.encode()

        print("bytes size=", len(buf), " path=", path, sep="", flush=True)
        sys.stdout.buffer.write(buf)
        sys.stdout.flush()

    @staticmethod
    def printurl(path, url, headers=[], hide=False):
        print("url headers=", len(headers), sep="", end="")
        if hide:
            print(" hide=true", end="")

        print(" path=", path, sep="")
        print(url)
        for h in headers:
            print(h)

    @staticmethod
    def printjson(path, data):
        Fetcher.printbytes(path, json.dumps(data, ensure_ascii=False, indent=2))

    def fetch(self, path):
        if path == "/":
            normalized = deepcopy(self.lst)
            for s in normalized.segments:
                s.uri = s.get_path_from_uri()

            self.printbytes("/" + self.name + ".m3u8", normalized.dumps())
        else:
            for seg in self.lst.segments:
                if seg.get_path_from_uri() == path[1:]:
                    headers = []
                    if self.referer is not None:
                        headers.append(f"Referer:{self.referer}")

                    self.printurl(path, seg.absolute_uri, headers=headers)
                    break
            else:
                print("notfound path=", path, sep="")

        print("eom")


def main():
    parser = argparse.ArgumentParser(description="M3U8 api handler")
    parser.add_argument("url", help="Url of m3u8 list")
    parser.add_argument("-n", "--name", help="Name the list to show in player")
    parser.add_argument("-r", "--referer", help="Provide referer header")
    args = parser.parse_args()

    fetcher = Fetcher(args.url, args.name, args.referer)
    try:
        for path in sys.stdin:
            path = path.strip()
            if len(path) > 2:
                path = path.rstrip("/")

            fetcher.fetch(path)
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
