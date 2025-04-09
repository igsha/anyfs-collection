#!/usr/bin/env python

import argparse
import base64
import json
import re
import sys

from bs4 import BeautifulSoup as Soup
import requests


class Fetcher:
    BASEURL = "https://kodik.info"

    def __init__(self, url):
        self.url = url
        self._TEMPLATE = self.BASEURL + "/{}/{}/{}/720p"

    @staticmethod
    def _printbytes(path, buf):
        print("bytes", len(buf.encode()), path)
        sys.stdout.write(buf)

    @staticmethod
    def _printentity(path):
        print("entity", path)

    @staticmethod
    def _printjson(path, data):
        Fetcher._printbytes(path, json.dumps(data, ensure_ascii=False, indent=2))

    @staticmethod
    def _printlink(path, realpath):
        print("link", path)
        print(realpath)

    def fetch(self, path):
        if path == "/":
            self._printroot()
        elif (m := re.match(r"/.hashes/([^/]+)/(\d+)\+(\w+)", path)):
            if m[1] == "serial" or m[1] == "season":
                self._extractseries(m[0], m[1], m[2], m[3])
            else:
                self._extractvideo(m[0], m[1], m[2], m[3])
        else:
            print("notfound", path)

        print("eom")

    def _printroot(self):
        soup = Soup(requests.get(self.url).text, features="lxml")
        title = soup.find("title").text
        title = title.replace("/", "-")

        container = soup.find("div", {"class": "serial-translations-box"}).find("select")
        for x in container.find_all("option"):
            datahash = x.get_attribute_list("data-media-hash")[0]
            dataid = x.get_attribute_list("data-media-id")[0]
            datatype = x.get_attribute_list("data-media-type")[0]
            dataname = x.get_attribute_list("data-title")[0]
            realpath = f"/.hashes/{datatype}/{dataid}+{datahash}"
            self._printlink(f"/{title}/{dataname}", realpath)

    def _extractseries(self, path, stype, dataid, datahash):
        url = self._TEMPLATE.format(stype, dataid, datahash)
        soup = Soup(requests.get(url).text, features="lxml")
        seriesbox = soup.find("div", {"class": "serial-series-box"})
        container = seriesbox.find("select")
        lst = []
        for x in container.find_all("option"):
            dataid = x.get_attribute_list("data-id")[0]
            datahash = x.get_attribute_list("data-hash")[0]
            title = x.get_attribute_list("data-title")[0]
            self._printlink(f"{path}/{title}", f"/.hashes/seria/{dataid}+{datahash}")
            lst.append(f"./{title}/720.m3u8")

        self._printbytes(path + "/playlist.m3u8", "\n".join(lst) + "\n")

    def _extractvideo(self, path, datatype, dataid, datahash):
        url = f"https://kodik.info/ftor?type={datatype}&id={dataid}&hash={datahash}"
        data = requests.get(url).json()
        self._printjson(path + "/info.json", data)
        for resolution, val in data["links"].items():
            #text = "#EXTM3U\n#EXT-X-VERSION:3\n#EXTINF:,My title\n"
            text = self._decode(val[0]["src"])
            self._printbytes(f"{path}/{resolution}.m3u8", text)

    @staticmethod
    def _rotN(data):
        alphabet = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        rotated = alphabet
        for r in range(25):
            rotated = rotated[1:] + rotated[0]
            trans = str.maketrans(alphabet + alphabet.lower(), rotated + rotated.lower())
            transformed = data.translate(trans)
            decoded = base64.b64decode(transformed + '=' * (-len(transformed) % 4)) # fix padding
            if decoded.endswith(b".m3u8"):
                return decoded.decode()

        raise RuntimeError("Exhausted rot tries")

    @staticmethod
    def _decode(data):
        if not data.endswith(".m3u8"):
            data = __class__._rotN(data)

        return re.sub(r'^//', 'https://', data)


def main():
    parser = argparse.ArgumentParser(description="Kodik handler")
    parser.add_argument("url", help="Url of the serial")
    args = parser.parse_args()

    fetcher = Fetcher(args.url)
    try:
        for path in sys.stdin:
            path = path.strip()
            fetcher.fetch(path)
            sys.stdout.flush()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
