#!/usr/bin/env python

import argparse
import json
import m3u8
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
        self._PLAYOPTIONS = f"{self.BASEURL}/api/play/options/{{}}/"
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

    @staticmethod
    def _printlink(path, realpath):
        print("link", path)
        print(realpath)

    def fetch(self, path):
        try:
            if path == "/":
                self._printroot()
            elif m := re.match(r"/hashes/(\w{32})/video", path):
                self._printoptions(path, m[1])
            elif m := re.match(r"/hashes/(\d+)/videos", path):
                self._printplaylist(path, m[1])
            elif re.match(r"/[^/]+(/next)*$", path):
                pagenum = path.count("/next") + 1
                if path.startswith("/videos"):
                    self._printcommon(self._VIDEOURL.format(pagenum), path)
                elif path.startswith("/shorts"):
                    self._printcommon(self._SHORTSURL.format(pagenum), path)
                elif path.startswith("/playlists"):
                    self._printcommon(self._PLAYLISTURL.format(pagenum), path)
            else:
                print("notfound", path)
        except HTTPError as ex:
            if ex.code == 404:
                print("notfound", path)
            else:
                raise

    def _printroot(self):
        with urlopen(self._PROFILE) as f:
            data = json.load(f)

        for x in ["", "videos", "playlists", "shorts", "hashes"]:
            self._printentity("/" + x)

        self._printbytes(f"/{data['name']}.txt", data["description"])
        self._printjson("/info.json", data)

    def _printthumbnail(self, path, data):
        thumbnail_url = data["thumbnail_url"]
        name = "thumbnail." + thumbnail_url.split(".")[-1]
        self._printurl(os.path.join(path, name), thumbnail_url)

    def _printvideo(self, path, data):
        self._printbytes(path + "/video.url", data["video_url"])
        self._printbytes(path + "/about.txt", data["description"])
        self._printthumbnail(path, data)
        self._printentity(path + "/video")

    def _printoptions(self, path, videoid):
        with urlopen(self._PLAYOPTIONS.format(videoid)) as f:
            data = json.load(f)

        mplay = m3u8.load(data["video_balancer"]["m3u8"])
        for name, url in {str(p.stream_info): p.absolute_uri for p in mplay.playlists}.items():
            self._printbytes(f"{path}/{name}.m3u8", url)

    def _printcommon(self, url, path):
        with urlopen(url) as f:
            data = json.load(f)

        for val in data["results"]:
            title = val["title"].replace("/", ",")
            ppath = "/hashes/" + str(val["id"])
            self._printlink(os.path.join(path, title), ppath)
            self._printentity(ppath)
            if "videos_count" in val:
                self._printthumbnail(ppath, val)
                self._printbytes(ppath + "/playlist.url", f"{self.BASEURL}/plst/{val['id']}/")
                self._printentity(ppath + "/videos")
            else:
                self._printvideo(ppath, val)

        if data["has_next"]:
            self._printentity(path + "/next")

        self._printjson(path + "/info.json", data)

    def _printplaylist(self, path, playlistid):
        self._printcommon(f"{self.BASEURL}/api/playlist/custom/{playlistid}/videos/", path)

    @staticmethod
    def extractIdFromUrl(url):
        reg = re.compile(r'"userChannelId":\s*(\d+)')
        try:
            with urlopen(url) as f:
                for line in f:
                    if m := reg.search(line.decode()):
                        return m[1]
                else:
                    return None
        except HTTPError as ex:
            if ex.code == 404:
                return None
            else:
                raise

    @staticmethod
    def extractIdFromSlug(slug):
        return Fetcher.extractIdFromUrl(f"{Fetcher.BASEURL}/u/{slug}")


if __name__ == "__main__":
    lst = {"RuTube": 23704195, "karpavichus": 37213454, "animach": 32420212, "repich": 32427511, "science": 164395}
    epilog = ", ".join(f"{k} ({v})" for k, v in lst.items())
    parser = argparse.ArgumentParser(description="Rutube api handler", epilog="Some channels: " + epilog)
    parser.add_argument("userid", help="Id of a rutube user", type=int, nargs='?')
    parser.add_argument("-s", "--slug", help="Connect by user slug")
    parser.add_argument("-u", "--url", help="Connect by user url")
    parser.add_argument("-p", "--print", help="Just print user id", action="store_true")
    args = parser.parse_args()

    if args.userid is not None:
        userid = args.userid
    elif args.slug is not None:
        userid = Fetcher.extractIdFromSlug(args.slug)
    elif args.url is not None:
        userid = Fetcher.extractIdFromUrl(args.url)
    else:
        print("Incorrect usage, see --help", file=sys.stderr)
        sys.exit(1)

    if args.print:
        if userid is None:
            print("UserId is not found")
            sys.exit(2)
        else:
            print(userid)
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
