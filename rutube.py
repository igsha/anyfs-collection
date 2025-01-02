#!/usr/bin/env python

import argparse
import json
import os
import re
import sys
from urllib.request import urlopen
from urllib.error import HTTPError


class PathMap:
    _BASEURL = "https://rutube.ru"

    def __init__(self, userid):
        self._VIDEOURL = f"{self._BASEURL}/api/video/person/{userid}/?origin__type=rtb,rst,ifrm,rspa&page={{}}"
        self._PLAYLISTURL = f"{self._BASEURL}/api/playlist/user/{userid}/?page={{}}"
        self._SHORTSURL = f"{self._BASEURL}/api/video/person/{userid}/?origin__type=rshorts&page={{}}"
        self._PROFILE = f"{self._BASEURL}/api/profile/user/{userid}/"
        self._PLAYLISTVIDEOURL = f"{self._BASEURL}/api/playlist/custom/{{}}/videos/?page={{}}"
        self.map = {}
        self.idmap = {}

    @staticmethod
    def _packbytes(buf):
        return f"bytes {len(buf.encode())}\n{buf}"

    @staticmethod
    def _packentities(lst):
        return f"entities {len(lst)}\n" + "".join(map(lambda x: x + "\n", lst))

    @staticmethod
    def _packurl(url):
        return f"url 1\n{url}\n"

    @staticmethod
    def _packtojson(data):
        return PathMap._packbytes(json.dumps(data, ensure_ascii=False, indent=2))

    def has(self, path):
        return path in self.map

    def get(self, path):
        return self.map[path]

    def update(self, path):
        if path == "/":
            self._updateroot()
        elif re.match(r"/[^/]+(/next)*$", path):
            pagenum = path.count("/next") + 1
            if path.startswith("/videos"):
                self._commonupdate(self._VIDEOURL.format(pagenum), path)
            elif path.startswith("/shorts"):
                self._commonupdate(self._SHORTSURL.format(pagenum), path)
            elif path.startswith("/playlists"):
                self._commonupdate(self._PLAYLISTURL.format(pagenum), path, isplaylist=True)
        elif m := re.match(r"(/playlists(?:/next)*/[^/]+)(/next)*$", path):
            ptitle = m[1]
            if ptitle in self.idmap:
                info = self.idmap[ptitle]
                playlistid = info["id"]
                pagenum = path.count("/next", *m.regs[2]) + 1 if len(m.groups()) > 1 else 1
                initlist = info["initlist"] if pagenum == 1 else []
                self._commonupdate(self._PLAYLISTVIDEOURL.format(playlistid, pagenum), path, init=initlist)

    def _updateroot(self):
        with urlopen(self._PROFILE) as f:
            data = json.load(f)

        name = data['name'] + ".txt"
        root = ["videos", "playlists", "shorts", name, "info.json"]
        self.map["/" + name] = self._packbytes(data["description"])
        self.map["/"] = self._packentities(root)
        self.map["/info.json"] = self._packtojson(data)

    def _updatethumbnail(self, path, data):
        thumbnail_url = data["thumbnail_url"]
        name = "thumbnail." + thumbnail_url.split(".")[-1]
        self.map[os.path.join(path, name)] = self._packurl(thumbnail_url)
        return name

    def _updatevideo(self, path, data):
        thumbnail = self._updatethumbnail(path, data)
        self.map[f"{path}/video.m3u8"] = self._packbytes(data["video_url"])
        self.map[f"{path}/about.txt"] = self._packbytes(data["description"])

        plst = ["video.m3u8", "about.txt", thumbnail]
        self.map[path] = self._packentities(plst)

    def _commonupdate(self, url, path, isplaylist=False, init=[]):
        try:
            with urlopen(url) as f:
                data = json.load(f)
        except HTTPError as ex:
            if ex.code == 404:
                return

            raise

        lst = init.copy()
        for val in data["results"]:
            title = val["title"].replace("/", ",")
            lst.append(title)
            ppath = os.path.join(path, title)
            if isplaylist:
                playlistid = val["id"]
                thumbnail = self._updatethumbnail(ppath, val)
                self.map[f"{ppath}/playlist.m3u8"] = self._packbytes(f"{self._BASEURL}/plst/{playlistid}/")
                self.idmap[ppath] = dict(id=playlistid, initlist=[thumbnail, "playlist.m3u8"])
            else:
                self._updatevideo(ppath, val)

        if data["has_next"]:
            lst.append("next")

        lst.append("info.json")
        self.map[f"{path}/info.json"] = self._packtojson(data)

        self.map[path] = self._packentities(lst)


if __name__ == "__main__":
    lst = {23704195: "RuTube", 31303018: "serials", 37213454: "karpavichus",
           32420212: "animach", 32427511:  "repich", 164395: "antropogenez.ru"}
    epilog = ", ".join(f"{k} - {v}" for k, v in lst.items())
    parser = argparse.ArgumentParser(description="Rutube api handler", epilog="Some channels: " + epilog)
    parser.add_argument("userid", help="Id of a rutube user", type=int)
    args = parser.parse_args()

    pathmap = PathMap(args.userid)
    try:
        for path in sys.stdin:
            path = path.strip()
            if len(path) > 2:
                path = path.rstrip("/")

            cur = "/"
            for p in path.split("/"):
                cur = os.path.join(cur, p)
                if pathmap.has(cur):
                    continue
                else:
                    pathmap.update(str(cur))

            if pathmap.has(path):
                sys.stdout.write(pathmap.get(path))
            else:
                sys.stdout.write("notfound 0\n")

            sys.stdout.flush()
    except KeyboardInterrupt:
        pass
