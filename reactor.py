#!/usr/bin/env python

import argparse
import base64
from functools import reduce
import json
import os
from string import Template
import sys

from graphqlclient import GraphQLClient


class Fetcher:
    def __init__(self, tagname):
        self.client = GraphQLClient("https://api.joyreactor.cc/graphql")
        self.startPage = None
        self._URL = "https://img10.joyreactor.cc/pics/post/{}"
        self.tag = tagname
        self.template = Template('''
        {
            tag(name: "${tag}") {
                postPager(type: ALL) {
                    count
                    id
                    posts ${params} {
                        id
                        tags {
                            name
                        }
                        attributes {
                            id
                            type
                            ... on PostAttributePicture {
                                image {
                                    type
                                }
                            }
                            ... on PostAttributeEmbed {
                                value
                            }
                        }
                    }
                }
            }
        }
        ''')
        self.extmap = dict(jpeg="", png="", webm="webm/", mp4="mp4/", gif="")

    @staticmethod
    def _printbytes(path, buf):
        print("bytes size=", len(buf.encode()), " path=", path, sep="")
        sys.stdout.write(buf)

    @staticmethod
    def _printentity(path):
        print("entity path=", path, sep="")

    @staticmethod
    def _printurl(path, url, headers=[]):
        print("url headers=", len(headers), " path=", path, sep="")
        print(url)
        for h in headers:
            print(h)

    @staticmethod
    def _printjson(path, data):
        Fetcher._printbytes(path, json.dumps(data, ensure_ascii=False, indent=2))

    @staticmethod
    def _decodeId(x):
        return base64.b64decode(x).decode().split(":")[-1]

    def _parseResult(self, path, result, pagenum):
        def multireplace(s):
            return reduce(lambda acc, x: acc.replace(x, "-"), " /#", s)

        lst = []
        postPager = result['data']['tag']['postPager']
        for post in postPager['posts']:
            postId = self._decodeId(post['id'])
            postPath = os.path.join(path, postId)

            tags = list(map(lambda x: x['name'], post['tags']))
            prefix = "-".join(map(multireplace, tags[:3]))
            for attr in post['attributes']:
                imageId = self._decodeId(attr['id'])
                if attr['type'] == "PICTURE":
                    ext = attr['image']['type'].lower()
                    name = f"{prefix}-{imageId}.{ext}"
                    url = self._URL.format(self.extmap[ext] + name)
                    headers = ["referer:https://joyreactor.cc/"] if ext in ["webm", "mp4"] else []
                    self._printurl(f"{postPath}/{name}", url, headers)
                elif attr['type'] == "COUB":
                    url = "https://coub.com/view/" + attr["value"]
                    name = f"{prefix}-{imageId}.coub.m3u8"
                    self._printbytes(f"{postPath}/{name}", url)
                elif attr['type'] == "YOUTUBE":
                    url = "https://youtu.be/" + attr["value"]
                    name = f"{prefix}-{imageId}.youtube.m3u8"
                    self._printbytes(f"{postPath}/{name}", url)
                else:
                    print("ioerror", f"path={postPath}/{imageId}.{postId}.err")
                    print("FAIL", postId, attr, file=sys.stderr)

            self._printjson(postPath + "/info.json", post)

        if self.startPage is None:
            self.startPage = (int(postPager['count']) + 9) // 10

        if self.startPage - pagenum > 1:
            self._printentity(os.path.join(path, "next"))

    def fetch(self, path):
        pagenum = path.count("/next")
        if (pagenum > 0 and self.startPage is None) or (self.startPage is not None and pagenum >= self.startPage):
            print("notfound path=", path, sep="")

        params = "" if pagenum == 0 else f"(page: {self.startPage - pagenum})"
        result = self.client.execute(self.template.substitute(tag=self.tag, params=params))
        self._parseResult(path, json.loads(result), pagenum)
        print("eom")


def main():
    parser = argparse.ArgumentParser(description="Reactor api handler")
    parser.add_argument("tag", help="Tag to extract posts media", nargs="?", default="общее")
    args = parser.parse_args()

    fetcher = Fetcher(args.tag)
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
