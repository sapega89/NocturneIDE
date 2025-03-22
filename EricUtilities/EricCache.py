# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing classes used for caching objects.
"""

from PyQt6.QtCore import QDateTime, QTimer


class EricCache:
    """
    Class implementing a LRU cache of a specific size.

    If the maximum number of entries is exceeded, the least recently used item
    is removed from the cache. A cache hit moves the entry to the front of the
    cache.
    """

    def __init__(self, size=100):
        """
        Constructor

        @param size maximum number of entries that may be stored in the cache
        @type int
        @exception ValueError raised to indicate an illegal 'size' parameter
        """
        if size < 0:
            raise ValueError("'size' parameter must be positive.")

        self.__size = size

        # internal objects
        self.__keyList = []
        self.__store = {}  # stores the cache entries
        self.__accesStore = {}  # stores the last access date and times
        self.__hits = 0
        self.__misses = 0
        self.__maxsize = 0
        self.__maxCacheTime = 0  # 0 seconds means aging is disabled

        self.__cacheTimer = QTimer()
        self.__cacheTimer.setSingleShot(True)
        self.__cacheTimer.timeout.connect(self.__pruneCache)

    def __moveLast(self, key):
        """
        Private method to move a cached item to the MRU position.

        @param key key of the item to be retrieved
        @type any hashable type that can be used as a dict key
        """
        self.__keyList.remove(key)
        self.__keyList.append(key)

    def __adjustToSize(self):
        """
        Private method to adjust the cache to its size.
        """
        if self.__size:
            removeList = self.__keyList[: -self.__size]
            self.__keyList = self.__keyList[-self.__size :]
            for key in removeList:
                del self.__store[key]
                del self.__accesStore[key]
        else:
            self.reset()

    def getSize(self):
        """
        Public method to get the maximum size of the cache.

        @return maximum number of entries of the cache
        @rtype int
        """
        return self.__size

    def setSize(self, newSize):
        """
        Public method to change the maximum size of the cache.

        @param newSize maximum number of entries that may be stored in the
            cache
        @type int
        """
        if newSize >= 0:
            self.__size = newSize
            self.__adjustToSize()

    def getMaximumCacheTime(self):
        """
        Public method to get the maximum time entries may exist in the cache.

        @return maximum cache time in seconds
        @rtype int
        """
        return self.__maxCacheTime

    def setMaximumCacheTime(self, time):
        """
        Public method to set the maximum time entries may exist in the cache.

        @param time maximum cache time in seconds
        @type int
        """
        if time != self.__maxCacheTime:
            self.__cacheTimer.stop()
            self.__pruneCache()
            self.__maxCacheTime = time
            if self.__maxCacheTime > 0:
                self.__cacheTimer.setInterval(self.__maxCacheTime * 1000)
                self.__cacheTimer.start()

    def get(self, key):
        """
        Public method to get an entry from the cache given its key.

        If the key is present in the cache, it is moved to the MRU position.

        @param key key of the item to be retrieved
        @type any hashable type that can be used as a dict key
        @return cached item for the given key or None, if the key is not
            present
        @rtype object or None
        """
        if key in self.__store:
            self.__hits += 1
            self.__moveLast(key)
            self.__accesStore[key] = QDateTime.currentDateTimeUtc()
            return self.__store[key]
        else:
            self.__misses += 1
            return None

    def add(self, key, item):
        """
        Public method to add an item to the cache.

        If the key is already in use, the cached item is replaced by the new
        one given and is moved to the MRU position

        @param key key of the item to be retrieved
        @type any hashable type that can be used as a dict key
        @param item item to be cached under the given key
        @type object
        """
        if key in self.__store:
            self.__moveLast(key)
        else:
            self.__keyList.append(key)
        self.__store[key] = item
        self.__accesStore[key] = QDateTime.currentDateTimeUtc()

        self.__adjustToSize()

        self.__maxsize = max(self.__maxsize, len(self.__keyList))

    def remove(self, key):
        """
        Public method to remove an item from the cache.

        @param key key of the item to be retrieved
        @type any hashable type that can be used as a dict key
        """
        if key in self.__store:
            del self.__store[key]
            del self.__accesStore[key]
            self.__keyList.remove(key)

    def clear(self):
        """
        Public method to clear the cache.
        """
        self.__keyList = []
        self.__store = {}
        self.__accesStore = {}

    def reset(self):
        """
        Public method to reset the cache.

        This is like clear() but sets the various counters to their initial
        value as well.
        """
        self.clear()
        self.__hits = 0
        self.__misses = 0
        self.__maxsize = 0

    def length(self):
        """
        Public method to get the current length of the cache.

        @return current length of the cache
        @rtype int
        """
        return len(self.__keyList)

    def info(self):
        """
        Public method to get some information about the cache.

        @return dictionary containing the cache info
        @rtype dict (with keys "hits", "misses", "maxsize", "currsize")
        """
        return {
            "hits": self.__hits,
            "misses": self.__misses,
            "maxsize": self.__maxsize,
            "currsize": self.length(),
        }

    def __pruneCache(self):
        """
        Private slot to prune outdated cache entries and restart the timer.
        """
        if self.__maxCacheTime > 0:
            current = QDateTime.currentDateTimeUtc()

            keysToBeDeleted = []
            for key, lastAccessTime in self.__accesStore.items():
                if lastAccessTime.secsTo(current) > self.__maxCacheTime:
                    keysToBeDeleted.append(key)
            for key in keysToBeDeleted:
                self.remove(key)

            self.__cacheTimer.start()
