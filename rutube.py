#!/usr/bin/env python

import argparse
import json
import os
import re
import sys
from urllib.request import urlopen
from urllib.error import HTTPError


class Fetcher:
    BASEURL = "https://rutube.ru"

    def __init__(self, userid):
        self._VIDEOURL = f"{self.BASEURL}/api/video/person/{userid}/?origin__type=rtb,rst,ifrm,rspa&page={{}}"
        self._PLAYLISTURL = f"{self.BASEURL}/api/playlist/user/{userid}/?page={{}}"
        self._SHORTSURL = f"{self.BASEURL}/api/video/person/{userid}/?origin__type=rshorts&page={{}}"
        self._PROFILE = f"{self.BASEURL}/api/profile/user/{userid}/"
        self._PLAYLISTVIDEOURL = f"{self.BASEURL}/api/playlist/custom/{{}}/videos/?page={{}}"
        self.idmap = {}

    @staticmethod
    def _printbytes(path, buf):
        print("bytes", len(buf.encode()), path)
        sys.stdout.write(buf)

    @staticmethod
    def _printentity(path):
        print("entity", path)

    @staticmethod
    def _printurl(path, url):
        print("url", path)
        print(url)

    @staticmethod
    def _printjson(path, data):
        Fetcher._printbytes(path, json.dumps(data, ensure_ascii=False, indent=2))

    def fetch(self, path):
        if path == "/":
            self._printroot()
        elif re.match(r"/[^/]+(/next)*$", path):
            pagenum = path.count("/next") + 1
            if path.startswith("/videos"):
                self._printcommon(self._VIDEOURL.format(pagenum), path)
            elif path.startswith("/shorts"):
                self._printcommon(self._SHORTSURL.format(pagenum), path)
            elif path.startswith("/playlists"):
                self._printcommon(self._PLAYLISTURL.format(pagenum), path, isplaylist=True)
        elif (m := re.match(r"(/playlists(?:/next)*/[^/]+)(/next)*$", path)) and m[1] in self.idmap:
            info = self.idmap.pop(m[1])
            playlistid = info["id"]
            pagenum = path.count("/next", *m.regs[2]) + 1 if len(m.groups()) > 1 else 1
            initlist = info["initlist"] if pagenum == 1 else []
            self._printcommon(self._PLAYLISTVIDEOURL.format(playlistid, pagenum), path, init=initlist)
        else:
            print("notfound", path)

    def _printroot(self):
        with urlopen(self._PROFILE) as f:
            data = json.load(f)

        for x in ["", "videos", "playlists", "shorts"]:
            self._printentity("/" + x)

        self._printbytes(f"/{data['name']}.txt", data["description"])
        self._printjson("/info.json", data)

    def _printthumbnail(self, path, data):
        thumbnail_url = data["thumbnail_url"]
        name = "thumbnail." + thumbnail_url.split(".")[-1]
        self._printurl(os.path.join(path, name), thumbnail_url)

    def _printvideo(self, path, data):
        self._printbytes(path + "/video.m3u8", data["video_url"])
        self._printbytes(path + "/about.txt", data["description"])
        self._printthumbnail(path, data)

    def _printcommon(self, url, path, isplaylist=False, init=[]):
        try:
            with urlopen(url) as f:
                data = json.load(f)
        except HTTPError as ex:
            if ex.code == 404:
                print("notfound", path)
            else:
                raise

        for val in data["results"]:
            title = val["title"].replace("/", ",")
            ppath = os.path.join(path, title)
            self._printentity(ppath)
            if isplaylist:
                playlistid = val["id"]
                self._printthumbnail(ppath, val)
                self._printbytes(ppath + "/playlist.m3u8", f"{self.BASEURL}/plst/{playlistid}/")
                self.idmap[ppath] = dict(id=playlistid, initlist=["playlist.m3u8"])
            else:
                self._printvideo(ppath, val)

        if data["has_next"]:
            self._printentity(path + "/next")

        self._printjson(path + "/info.json", data)

    @staticmethod
    def extractIdFromUrl(url):
        reg = re.compile(r'"userChannelId":\s*(\d+)')
        try:
            with urlopen(url) as f:
                for line in f:
                    m = reg.search(line.decode())
                    if m is None:
                        continue

                    return m[1]
        except HTTPError as ex:
            if ex.code == 404:
                return None
            else:
                raise

        raise RuntimeError("The URL does not contain slug")

    @staticmethod
    def extractIdFromSlug(slug):
        return Fetcher.extractIdFromUrl(f"{Fetcher.BASEURL}/u/{slug}")


if __name__ == "__main__":
    lst = {23704195: "RuTube", 31303018: "serials", 37213454: "karpavichus",
           32420212: "animach", 32427511:  "repich", 164395: "antropogenez.ru"}
    epilog = ", ".join(f"{k} - {v}" for k, v in lst.items())
    parser = argparse.ArgumentParser(description="Rutube api handler", epilog="Some channels: " + epilog)
    parser.add_argument("userid", help="Id of a rutube user", type=int, nargs='?')
    parser.add_argument("-s", "--slug", help="Connect by user slug")
    parser.add_argument("-u", "--url", help="Connect by user url")
    parser.add_argument("-c", "--convert", help="Do not connect just find out user id", action="store_true")
    args = parser.parse_args()

    if args.userid is not None:
        userid = args.userid
        message = f"User {userid}"
    if args.slug is not None:
        userid = Fetcher.extractIdFromSlug(args.slug)
        message = f"Slug '{args.slug}'"
    elif args.url is not None:
        userid = Fetcher.extractIdFromUrl(args.url)
        message = args.url

    if args.convert:
        if userid is None:
            print(message, "does not have id")
            sys.exit(1)
        else:
            print(message, "has id", userid)
            sys.exit(0)
    else:
        fetcher = Fetcher(userid)
        try:
            for path in sys.stdin:
                path = path.strip()
                fetcher.fetch(path)
                print("eom")
                sys.stdout.flush()
        except KeyboardInterrupt:
            pass
