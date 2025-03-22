# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing an URL representation suitable for Google Safe Browsing.
"""

import contextlib
import hashlib
import posixpath
import re
import socket
import struct
import urllib.parse

from eric7 import Preferences


class SafeBrowsingUrl:
    """
    Class implementing an URL representation suitable for Google Safe Browsing.
    """

    #
    # Modeled after the URL class of the gglsbl package.
    # https://github.com/afilipovich/gglsbl
    #
    def __init__(self, url):
        """
        Constructor

        @param url URL to be embedded
        @type str
        """
        self.__url = url

    def hashes(self):
        """
        Public method to get the hashes of all possible permutations of the URL
        in canonical form.

        @yield URL hashes
        @ytype bytes
        """
        for variant in self.permutations(self.canonical()):
            urlHash = self.digest(variant)
            yield urlHash

    def canonical(self):
        """
        Public method to convert the URL to the canonical form.

        @return canonical form of the URL
        @rtype str
        """

        def fullUnescape(u):
            """
            Method to recursively unescape an URL.

            @param u URL string to unescape
            @type str
            @return unescaped URL string
            @rtype str
            """
            uu = urllib.parse.unquote(u)
            if uu == u:
                return uu
            else:
                return fullUnescape(uu)

        def quote(s):
            """
            Method to quote a string.

            @param string to be quoted
            @type str
            @return quoted string
            @rtype str
            """
            safeChars = "!\"$&'()*+,-./:;<=>?@[\\]^_`{|}~"
            return urllib.parse.quote(s, safe=safeChars)

        url = self.__url.strip()
        url = url.replace("\n", "").replace("\r", "").replace("\t", "")
        url = url.split("#", 1)[0]
        if url.startswith("//"):
            url = Preferences.getWebBrowser("DefaultScheme")[:-3] + url
        if len(url.split("://")) <= 1:
            url = Preferences.getWebBrowser("DefaultScheme") + url
        url = quote(fullUnescape(url))
        urlParts = urllib.parse.urlsplit(url)
        if not urlParts[0]:
            url = Preferences.getWebBrowser("DefaultScheme") + url
            urlParts = urllib.parse.urlsplit(url)
        protocol = urlParts.scheme
        host = fullUnescape(urlParts.hostname)
        path = fullUnescape(urlParts.path)
        query = urlParts.query
        if not query and "?" not in url:
            query = None
        if not path:
            path = "/"
        path = posixpath.normpath(path).replace("//", "/")
        if path[-1] != "/":
            path += "/"
        port = urlParts.port
        host = host.strip(".")
        host = re.sub(r"\.+", ".", host).lower()
        if host.isdigit():
            with contextlib.suppress(OSError):
                host = socket.inet_ntoa(struct.pack("!I", int(host)))
        if host.startswith("0x") and "." not in host:
            with contextlib.suppress(OSError):
                host = socket.inet_ntoa(struct.pack("!I", int(host, 16)))
        quotedPath = quote(path)
        quotedHost = quote(host)
        if port is not None:
            quotedHost = "{0}:{1}".format(quotedHost, port)
        canonicalUrl = "{0}://{1}{2}".format(protocol, quotedHost, quotedPath)
        if query is not None:
            canonicalUrl = "{0}?{1}".format(canonicalUrl, query)
        return canonicalUrl

    @staticmethod
    def permutations(url):
        """
        Static method to determine all permutations of host name and path
        which can be applied to blocked URLs.

        @param url URL string to be permuted
        @type str
        @yield permutated URL strings
        @ytype str
        """

        def hostPermutations(host):
            """
            Method to generate the permutations of the host name.

            @param host host name
            @type str
            @yield permutated host names
            @ytype str
            """
            if re.match(r"\d+\.\d+\.\d+\.\d+", host):
                yield host
                return
            parts = host.split(".")
            partsLen = min(len(parts), 5)
            if partsLen > 4:
                yield host
            for i in range(partsLen - 1):
                yield ".".join(parts[i - partsLen :])

        def pathPermutations(path):
            """
            Method to generate the permutations of the path.

            @param path path to be processed
            @type str
            @yield permutated paths
            @ytype str
            """
            yield path
            query = None
            if "?" in path:
                path, query = path.split("?", 1)
            if query is not None:
                yield path
            pathParts = path.split("/")[0:-1]
            curPath = ""
            for i in range(min(4, len(pathParts))):
                curPath = curPath + pathParts[i] + "/"
                yield curPath

        protocol, addressStr = urllib.parse.splittype(url)
        host, path = urllib.parse.splithost(addressStr)
        _user, host = urllib.parse.splituser(host)
        host, port = urllib.parse.splitport(host)
        host = host.strip("/")
        seenPermutations = set()
        for h in hostPermutations(host):
            for p in pathPermutations(path):
                u = "{0}{1}".format(h, p)
                if u not in seenPermutations:
                    yield u
                    seenPermutations.add(u)

    @staticmethod
    def digest(url):
        """
        Static method to calculate the SHA256 digest of an URL string.

        @param url URL string
        @type str
        @return SHA256 digest of the URL string
        @rtype bytes
        """
        return hashlib.sha256(url.encode("utf-8")).digest()
