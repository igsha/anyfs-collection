#!/usr/bin/env python

import argparse
from io import BytesIO
import json
import re
import shutil
import sys

from PIL import Image
import requests


class Fetcher:
    def __init__(self, url):
        parts = re.match(r"(?P<domain>https?://[^/]+)/(?P<lang>[^/]+)/(?P<name>[^/]+/[^/]+).*", url)
        self.name = parts.group("name")
        self.domain = parts.group("domain")

    @staticmethod
    def printbytes(path, buf):
        if isinstance(buf, str):
            buf = buf.encode()

        print("bytes size=", len(buf), " path=", path, sep="", flush=True)
        sys.stdout.buffer.write(buf)
        sys.stdout.flush()

    @staticmethod
    def printurl(path, url, headers=[]):
        print("url headers=", len(headers), " path=", path, sep="")
        print(url)
        for h in headers:
            print(h)

    @staticmethod
    def printjson(path, data):
        Fetcher.printbytes(path, json.dumps(data, ensure_ascii=False, indent=2))

    def fetch(self, path):
        if path == "/":
            data = requests.get(f"https://api.cdnlibs.org/api/{self.name}").json()
            self.printjson("/info.json", data)
            self.printurl("/poster.jpg", data["data"]["cover"]["default"])

            data = requests.get(f"https://api.cdnlibs.org/api/{self.name}/chapters").json()
            self.printjson("/chapters.json", data)
            text = ""
            for item in data["data"]:
                text += "./" + item["volume"] + "-" + item["number"] + ".pdf\n"
                text += "./" + item["volume"] + "-" + item["number"] + "\n"

            self.printbytes("/chapters.txt", text)
        elif m := re.match(r"/(\d+)-(\d+)", path):
            data = requests.get(f"https://api.cdnlibs.org/api/{self.name}/chapter?volume={m[1]}&number={m[2]}").json()
            self.printjson(path + "/info.json", data)
            for item in data["data"]["pages"]:
                url = "https://img33.imgslib.link" + item["url"]
                with requests.get(url, stream=True, headers={"referer": self.domain}) as f:
                    print("bytes size=", f.raw.headers["content-length"], " path=", path + "/" + item["image"], sep="", flush=True)
                    shutil.copyfileobj(f.raw, sys.stdout.buffer)
                    sys.stdout.flush()
        elif m := re.match(r"/(\d+)-(\d+)\.pdf", path):
            data = requests.get(f"https://api.cdnlibs.org/api/{self.name}/chapter?volume={m[1]}&number={m[2]}").json()
            images = []
            for item in data["data"]["pages"]:
                url = "https://img33.imgslib.link" + item["url"]
                with requests.get(url, stream=True, headers={"referer": self.domain}) as f:
                    images.append(Image.open(f.raw))

            temp = BytesIO()
            newimages[0].save(temp, format="PDF", resolution=100.0, save_all=True, append_images=newimages[1:])
            self.printbytes(path, temp.getvalue())
        else:
            print("notfound path=", path, sep="")

        print("eom")


def main():
    parser = argparse.ArgumentParser(description="Mangalib api handler")
    parser.add_argument("url", help="Url with manga")
    args = parser.parse_args()

    fetcher = Fetcher(args.url)
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
