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
    def _printentities(path, lst):
        print("entities", len(lst), path)
        for x in lst:
            print(x)

    @staticmethod
    def _printurl(path, url):
        print("url", path)
        print(url)

    @staticmethod
    def _printjson(path, data):
        Fetcher._printbytes(path, json.dumps(data, ensure_ascii=False, indent=2))

    def fetch(self, path):
        if path == "/":
            self._fetchroot()
        elif re.match(r"/[^/]+(/next)*$", path):
            pagenum = path.count("/next") + 1
            if path.startswith("/videos"):
                self._commonfetch(self._VIDEOURL.format(pagenum), path)
            elif path.startswith("/shorts"):
                self._commonfetch(self._SHORTSURL.format(pagenum), path)
            elif path.startswith("/playlists"):
                self._commonfetch(self._PLAYLISTURL.format(pagenum), path, isplaylist=True)
        elif (m := re.match(r"(/playlists(?:/next)*/[^/]+)(/next)*$", path)) and m[1] in self.idmap:
            info = self.idmap.pop(m[1])
            playlistid = info["id"]
            pagenum = path.count("/next", *m.regs[2]) + 1 if len(m.groups()) > 1 else 1
            initlist = info["initlist"] if pagenum == 1 else []
            self._commonfetch(self._PLAYLISTVIDEOURL.format(playlistid, pagenum), path, init=initlist)
        else:
            print("notfound", path)

    def _fetchroot(self):
        with urlopen(self._PROFILE) as f:
            data = json.load(f)

        name = data['name'] + ".txt"
        self._printentities("/", ["videos", "playlists", "shorts", name, "info.json"])
        self._printbytes("/" + name, data["description"])
        self._printjson("/info.json", data)

    def _fetchthumbnail(self, path, data):
        thumbnail_url = data["thumbnail_url"]
        name = "thumbnail." + thumbnail_url.split(".")[-1]
        self._printurl(os.path.join(path, name), thumbnail_url)
        return name

    def _fetchvideo(self, path, data):
        self._printbytes(path + "/video.m3u8", data["video_url"])
        self._printbytes(path + "/about.txt", data["description"])

        thumbnail = self._fetchthumbnail(path, data)
        self._printentities(path, ["video.m3u8", "about.txt", thumbnail])

    def _commonfetch(self, url, path, isplaylist=False, init=[]):
        try:
            with urlopen(url) as f:
                data = json.load(f)
        except HTTPError as ex:
            if ex.code == 404:
                print("notfound", path)
            else:
                raise

        lst = init.copy()
        for val in data["results"]:
            title = val["title"].replace("/", ",")
            lst.append(title)
            ppath = os.path.join(path, title)
            if isplaylist:
                playlistid = val["id"]
                thumbnail = self._fetchthumbnail(ppath, val)
                self._printbytes(ppath + "/playlist.m3u8", "{self.BASEURL}/plst/{playlistid}/")
                self.idmap[ppath] = dict(id=playlistid, initlist=[thumbnail, "playlist.m3u8"])
            else:
                self._fetchvideo(ppath, val)

        if data["has_next"]:
            lst.append("next")

        lst.append("info.json")
        self._printjson(path + "/info.json", data)
        self._printentities(path, lst)

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
    parser.add_argument("-s", "--slug", help="Return user id by its slug")
    parser.add_argument("-u", "--url", help="Return user id by its url")
    args = parser.parse_args()

    if args.slug is not None or args.url is not None:
        if args.slug is not None:
            userid = Fetcher.extractIdFromSlug(args.slug)
            message = f"Slug '{args.slug}'"
        else:
            userid = Fetcher.extractIdFromUrl(args.url)
            message = args.url

        if userid is None:
            print(message, "does not have id")
            sys.exit(1)

        print(message, "has id", userid)
        sys.exit(0)
    else:
        fetcher = Fetcher(args.userid)
        try:
            for path in sys.stdin:
                path = path.strip()
                fetcher.fetch(path)
                print("eom")
                sys.stdout.flush()
        except KeyboardInterrupt:
            pass
