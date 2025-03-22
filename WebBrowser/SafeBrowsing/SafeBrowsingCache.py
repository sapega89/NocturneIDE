# -*- coding: utf-8 -*-

# Copyright (c) 2017 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a cache for Google Safe Browsing.
"""

#
# Some part of this code were ported from gglsbl.storage and adapted
# to QtSql.
#
# https://github.com/afilipovich/gglsbl
#

import os

from PyQt6.QtCore import (
    QByteArray,
    QCoreApplication,
    QCryptographicHash,
    QEventLoop,
    QObject,
)
from PyQt6.QtSql import QSql, QSqlDatabase, QSqlQuery

from .SafeBrowsingThreatList import ThreatList


class SafeBrowsingCache(QObject):
    """
    Class implementing a cache for Google Safe Browsing.
    """

    create_threat_list_stmt = """
        CREATE TABLE threat_list
        (threat_type character varying(128) NOT NULL,
         platform_type character varying(128) NOT NULL,
         threat_entry_type character varying(128) NOT NULL,
         client_state character varying(42),
         timestamp timestamp without time zone DEFAULT current_timestamp,
         PRIMARY KEY (threat_type, platform_type, threat_entry_type)
        )
    """
    drop_threat_list_stmt = """DROP TABLE IF EXISTS threat_list"""

    create_full_hashes_stmt = """
        CREATE TABLE full_hash
        (value BLOB NOT NULL,
         threat_type character varying(128) NOT NULL,
         platform_type character varying(128) NOT NULL,
         threat_entry_type character varying(128) NOT NULL,
         downloaded_at timestamp without time zone DEFAULT current_timestamp,
         expires_at timestamp without time zone
            NOT NULL DEFAULT current_timestamp,
         malware_threat_type varchar(32),
         PRIMARY KEY (value, threat_type, platform_type, threat_entry_type)
        )
    """
    drop_full_hashes_stmt = """DROP TABLE IF EXISTS full_hash"""

    create_hash_prefix_stmt = """
        CREATE TABLE hash_prefix
        (value BLOB NOT NULL,
         cue character varying(4) NOT NULL,
         threat_type character varying(128) NOT NULL,
         platform_type character varying(128) NOT NULL,
         threat_entry_type character varying(128) NOT NULL,
         timestamp timestamp without time zone DEFAULT current_timestamp,
         negative_expires_at timestamp without time zone
            NOT NULL DEFAULT current_timestamp,
         PRIMARY KEY (value, threat_type, platform_type, threat_entry_type),
         FOREIGN KEY(threat_type, platform_type, threat_entry_type)
         REFERENCES threat_list(threat_type, platform_type, threat_entry_type)
         ON DELETE CASCADE
        )
    """
    drop_hash_prefix_stmt = """DROP TABLE IF EXISTS hash_prefix"""

    create_full_hash_cue_idx = """
        CREATE INDEX idx_hash_prefix_cue ON hash_prefix (cue)
    """
    drop_full_hash_cue_idx = """DROP INDEX IF EXISTS idx_hash_prefix_cue"""

    create_full_hash_expires_idx = """
        CREATE INDEX idx_full_hash_expires_at ON full_hash (expires_at)
    """
    drop_full_hash_expires_idx = """
        DROP INDEX IF EXISTS idx_full_hash_expires_at
    """

    create_full_hash_value_idx = """
        CREATE INDEX idx_full_hash_value ON full_hash (value)
    """
    drop_full_hash_value_idx = """DROP INDEX IF EXISTS idx_full_hash_value"""

    maxProcessEventsTime = 500

    def __init__(self, dbPath, parent=None):
        """
        Constructor

        @param dbPath path to store the cache DB into
        @type str
        @param parent reference to the parent object
        @type QObject
        """
        super().__init__(parent)

        self.__connectionName = "SafeBrowsingCache"

        if not os.path.exists(dbPath):
            os.makedirs(dbPath)

        self.__dbFileName = os.path.join(dbPath, "SafeBrowsingCache.db")
        preparationNeeded = not os.path.exists(self.__dbFileName)

        self.__openCacheDb()
        if preparationNeeded:
            self.prepareCacheDb()

    def close(self):
        """
        Public method to close the database.
        """
        if QSqlDatabase.database(self.__connectionName).isOpen():
            QSqlDatabase.database(self.__connectionName).close()
            QSqlDatabase.removeDatabase(self.__connectionName)

    def __openCacheDb(self):
        """
        Private method to open the cache database.

        @return flag indicating the open state
        @rtype bool
        """
        db = QSqlDatabase.database(self.__connectionName, False)
        if not db.isValid():
            # the database connection is a new one
            db = QSqlDatabase.addDatabase("QSQLITE", self.__connectionName)
            db.setDatabaseName(self.__dbFileName)
            opened = db.open()
            if not opened:
                QSqlDatabase.removeDatabase(self.__connectionName)
        else:
            opened = True
        return opened

    def prepareCacheDb(self):
        """
        Public method to prepare the cache database.
        """
        db = QSqlDatabase.database(self.__connectionName)
        db.transaction()
        try:
            query = QSqlQuery(db)
            # step 1: drop old tables
            query.exec(self.drop_threat_list_stmt)
            query.exec(self.drop_full_hashes_stmt)
            query.exec(self.drop_hash_prefix_stmt)
            # step 2: drop old indices
            query.exec(self.drop_full_hash_cue_idx)
            query.exec(self.drop_full_hash_expires_idx)
            query.exec(self.drop_full_hash_value_idx)
            # step 3: create tables
            query.exec(self.create_threat_list_stmt)
            query.exec(self.create_full_hashes_stmt)
            query.exec(self.create_hash_prefix_stmt)
            # step 4: create indices
            query.exec(self.create_full_hash_cue_idx)
            query.exec(self.create_full_hash_expires_idx)
            query.exec(self.create_full_hash_value_idx)
        finally:
            del query
            db.commit()

    def lookupFullHashes(self, hashValues):
        """
        Public method to get a list of threat lists and expiration flag
        for the given hashes if a hash is on the block list.

        @param hashValues list of hash values to look up
        @type list of bytes
        @return list of tuples containing the threat list info and the
            expiration flag
        @rtype list of tuple of (ThreatList, bool)
        """
        queryStr = """
            SELECT threat_type, platform_type, threat_entry_type,
            expires_at < current_timestamp AS has_expired
            FROM full_hash WHERE value IN ({0})
        """
        output = []

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr.format(",".join(["?"] * len(hashValues))))
                for hashValue in hashValues:
                    query.addBindValue(
                        QByteArray(hashValue),
                        QSql.ParamTypeFlag.In | QSql.ParamTypeFlag.Binary,
                    )

                query.exec()

                while query.next():  # __IGNORE_WARNING_M523__
                    threatType = query.value(0)
                    platformType = query.value(1)
                    threatEntryType = query.value(2)
                    hasExpired = bool(query.value(3))
                    threatList = ThreatList(threatType, platformType, threatEntryType)
                    output.append((threatList, hasExpired))
                    QCoreApplication.processEvents(
                        QEventLoop.ProcessEventsFlag.AllEvents,
                        self.maxProcessEventsTime,
                    )
                del query
            finally:
                db.commit()

        return output

    def lookupHashPrefix(self, prefixes):
        """
        Public method to look up hash prefixes in the local cache.

        @param prefixes list of hash prefixes to look up
        @type list of bytes
        @return list of tuples containing the threat list, full hash and
            negative cache expiration flag
        @rtype list of tuple of (ThreatList, bytes, bool)
        """
        queryStr = """
            SELECT value,threat_type,platform_type,threat_entry_type,
            negative_expires_at < current_timestamp AS negative_cache_expired
            FROM hash_prefix WHERE cue IN ({0})
        """
        output = []

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr.format(",".join(["?"] * len(prefixes))))
                for prefix in prefixes:
                    query.addBindValue(prefix)

                query.exec()

                while query.next():  # __IGNORE_WARNING_M523__
                    fullHash = bytes(query.value(0))
                    threatType = query.value(1)
                    platformType = query.value(2)
                    threatEntryType = query.value(3)
                    negativeCacheExpired = bool(query.value(4))
                    threatList = ThreatList(threatType, platformType, threatEntryType)
                    output.append((threatList, fullHash, negativeCacheExpired))
                    QCoreApplication.processEvents(
                        QEventLoop.ProcessEventsFlag.AllEvents,
                        self.maxProcessEventsTime,
                    )
                del query
            finally:
                db.commit()

        return output

    def storeFullHash(self, threatList, hashValue, cacheDuration, malwareThreatType):
        """
        Public method to store full hash data in the cache database.

        @param threatList threat list info object
        @type ThreatList
        @param hashValue hash to be stored
        @type bytes
        @param cacheDuration duration the data should remain in the cache
        @type int or float
        @param malwareThreatType threat type of the malware
        @type str
        """
        insertQueryStr = """
            INSERT OR IGNORE INTO full_hash
                (value, threat_type, platform_type, threat_entry_type,
                 malware_threat_type, downloaded_at)
            VALUES
                (?, ?, ?, ?, ?, current_timestamp)
        """
        updateQueryStr = """
            UPDATE full_hash SET
            expires_at=datetime(current_timestamp, '+{0} SECONDS')
            WHERE value=? AND threat_type=? AND platform_type=? AND
            threat_entry_type=?
            """.format(
            int(cacheDuration)
        )

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(insertQueryStr)
                query.addBindValue(
                    QByteArray(hashValue),
                    QSql.ParamTypeFlag.In | QSql.ParamTypeFlag.Binary,
                )
                query.addBindValue(threatList.threatType)
                query.addBindValue(threatList.platformType)
                query.addBindValue(threatList.threatEntryType)
                query.addBindValue(malwareThreatType)
                query.exec()
                del query

                query = QSqlQuery(db)
                query.prepare(updateQueryStr)
                query.addBindValue(
                    QByteArray(hashValue),
                    QSql.ParamTypeFlag.In | QSql.ParamTypeFlag.Binary,
                )
                query.addBindValue(threatList.threatType)
                query.addBindValue(threatList.platformType)
                query.addBindValue(threatList.threatEntryType)
                query.exec()
                del query
            finally:
                db.commit()

    def deleteHashPrefixList(self, threatList):
        """
        Public method to delete hash prefixes for a given threat list.

        @param threatList threat list info object
        @type ThreatList
        """
        queryStr = """
            DELETE FROM hash_prefix
                WHERE threat_type=? AND platform_type=? AND threat_entry_type=?
        """

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr)
                query.addBindValue(threatList.threatType)
                query.addBindValue(threatList.platformType)
                query.addBindValue(threatList.threatEntryType)
                query.exec()
                del query
            finally:
                db.commit()

    def cleanupFullHashes(self, keepExpiredFor=43200):
        """
        Public method to clean up full hash entries expired more than the
        given time.

        @param keepExpiredFor time period in seconds of entries to be expired
        @type int or float
        """
        queryStr = """
            DELETE FROM full_hash
            WHERE expires_at=datetime(current_timestamp, '{0} SECONDS')
            """.format(
            int(keepExpiredFor)
        )

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr)
                query.exec()
                del query
            finally:
                db.commit()

    def updateHashPrefixExpiration(self, threatList, hashPrefix, negativeCacheDuration):
        """
        Public method to update the hash prefix expiration time.

        @param threatList threat list info object
        @type ThreatList
        @param hashPrefix hash prefix
        @type bytes
        @param negativeCacheDuration time in seconds the entry should remain
            in the cache
        @type int or float
        """
        queryStr = """
            UPDATE hash_prefix
            SET negative_expires_at=datetime(current_timestamp, '+{0} SECONDS')
            WHERE value=? AND threat_type=? AND platform_type=? AND
            threat_entry_type=?
            """.format(
            int(negativeCacheDuration)
        )

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr)
                query.addBindValue(
                    QByteArray(hashPrefix),
                    QSql.ParamTypeFlag.In | QSql.ParamTypeFlag.Binary,
                )
                query.addBindValue(threatList.threatType)
                query.addBindValue(threatList.platformType)
                query.addBindValue(threatList.threatEntryType)
                query.exec()
                del query
            finally:
                db.commit()

    def getThreatLists(self):
        """
        Public method to get the available threat lists.

        @return list of available threat lists
        @rtype list of tuples of (ThreatList, str)
        """
        queryStr = """
            SELECT threat_type,platform_type,threat_entry_type,client_state
            FROM threat_list
        """
        output = []

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr)

                query.exec()

                while query.next():  # __IGNORE_WARNING_M523__
                    threatType = query.value(0)
                    platformType = query.value(1)
                    threatEntryType = query.value(2)
                    clientState = query.value(3)
                    threatList = ThreatList(threatType, platformType, threatEntryType)
                    output.append((threatList, clientState))
                    QCoreApplication.processEvents(
                        QEventLoop.ProcessEventsFlag.AllEvents,
                        self.maxProcessEventsTime,
                    )
                del query
            finally:
                db.commit()

        return output

    def addThreatList(self, threatList):
        """
        Public method to add a threat list to the cache.

        @param threatList threat list to be added
        @type ThreatList
        """
        queryStr = """
            INSERT OR IGNORE INTO threat_list
                (threat_type, platform_type, threat_entry_type, timestamp)
            VALUES (?, ?, ?, current_timestamp)
        """

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr)
                query.addBindValue(threatList.threatType)
                query.addBindValue(threatList.platformType)
                query.addBindValue(threatList.threatEntryType)
                query.exec()
                del query
            finally:
                db.commit()

    def deleteThreatList(self, threatList):
        """
        Public method to delete a threat list from the cache.

        @param threatList threat list to be deleted
        @type ThreatList
        """
        queryStr = """
            DELETE FROM threat_list
                WHERE threat_type=? AND platform_type=? AND threat_entry_type=?
        """

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr)
                query.addBindValue(threatList.threatType)
                query.addBindValue(threatList.platformType)
                query.addBindValue(threatList.threatEntryType)
                query.exec()
                del query
            finally:
                db.commit()

    def updateThreatListClientState(self, threatList, clientState):
        """
        Public method to update the client state of a threat list.

        @param threatList threat list to update the client state for
        @type ThreatList
        @param clientState new client state
        @type str
        """
        queryStr = """
            UPDATE threat_list SET timestamp=current_timestamp, client_state=?
            WHERE threat_type=? AND platform_type=? AND threat_entry_type=?
        """

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr)
                query.addBindValue(clientState)
                query.addBindValue(threatList.threatType)
                query.addBindValue(threatList.platformType)
                query.addBindValue(threatList.threatEntryType)
                query.exec()
                del query
            finally:
                db.commit()

    def hashPrefixListChecksum(self, threatList):
        """
        Public method to calculate the SHA256 checksum for an alphabetically
        sorted concatenated list of hash prefixes.

        @param threatList threat list to calculate checksum for
        @type ThreatList
        @return SHA256 checksum
        @rtype bytes
        """
        queryStr = """
            SELECT value FROM hash_prefix
                WHERE threat_type=? AND platform_type=? AND threat_entry_type=?
                ORDER BY value
        """
        checksum = None

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            sha256Hash = QCryptographicHash(QCryptographicHash.Algorithm.Sha256)
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr)
                query.addBindValue(threatList.threatType)
                query.addBindValue(threatList.platformType)
                query.addBindValue(threatList.threatEntryType)

                query.exec()

                while query.next():  # __IGNORE_WARNING_M523__
                    sha256Hash.addData(query.value(0))
                    QCoreApplication.processEvents(
                        QEventLoop.ProcessEventsFlag.AllEvents,
                        self.maxProcessEventsTime,
                    )
                del query
            finally:
                db.commit()

            checksum = bytes(sha256Hash.result())

        return checksum

    def populateHashPrefixList(self, threatList, prefixes):
        """
        Public method to populate the hash prefixes for a threat list.

        @param threatList threat list of the hash prefixes
        @type ThreatList
        @param prefixes list of hash prefixes to be inserted
        @type HashPrefixList
        """
        queryStr = """
            INSERT INTO hash_prefix
                (value, cue, threat_type, platform_type, threat_entry_type,
                 timestamp)
                VALUES (?, ?, ?, ?, ?, current_timestamp)
        """

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                for prefix in prefixes:
                    query = QSqlQuery(db)
                    query.prepare(queryStr)
                    query.addBindValue(
                        QByteArray(prefix),
                        QSql.ParamTypeFlag.In | QSql.ParamTypeFlag.Binary,
                    )
                    query.addBindValue(prefix[:4].hex())
                    query.addBindValue(threatList.threatType)
                    query.addBindValue(threatList.platformType)
                    query.addBindValue(threatList.threatEntryType)
                    query.exec()
                    del query
                    QCoreApplication.processEvents(
                        QEventLoop.ProcessEventsFlag.AllEvents,
                        self.maxProcessEventsTime,
                    )
            finally:
                db.commit()

    def getHashPrefixValuesToRemove(self, threatList, indexes):
        """
        Public method to get the hash prefix values to be removed from the
        cache.

        @param threatList threat list to remove prefixes from
        @type ThreatList
        @param indexes list of indexes of prefixes to be removed
        @type list of int
        @return list of hash prefixes to be removed
        @rtype list of bytes
        """
        queryStr = """
            SELECT value FROM hash_prefix
                WHERE threat_type=? AND platform_type=? AND threat_entry_type=?
                ORDER BY value
        """
        indexes = set(indexes)
        output = []

        db = QSqlDatabase.database(self.__connectionName)
        if db.isOpen():
            db.transaction()
            try:
                query = QSqlQuery(db)
                query.prepare(queryStr)
                query.addBindValue(threatList.threatType)
                query.addBindValue(threatList.platformType)
                query.addBindValue(threatList.threatEntryType)

                query.exec()

                index = 0
                while query.next():  # __IGNORE_WARNING_M523__
                    if index in indexes:
                        prefix = bytes(query.value(0))
                        output.append(prefix)
                    index += 1
                    QCoreApplication.processEvents(
                        QEventLoop.ProcessEventsFlag.AllEvents,
                        self.maxProcessEventsTime,
                    )
                del query
            finally:
                db.commit()

        return output

    def removeHashPrefixIndices(self, threatList, indexes):
        """
        Public method to remove hash prefixes from the cache.

        @param threatList threat list to delete hash prefixes of
        @type ThreatList
        @param indexes list of indexes of prefixes to be removed
        @type list of int
        """
        queryStr = """
            DELETE FROM hash_prefix
            WHERE threat_type=? AND platform_type=? AND
            threat_entry_type=? AND value IN ({0})
            """
        batchSize = 40

        prefixesToRemove = self.getHashPrefixValuesToRemove(threatList, indexes)
        if prefixesToRemove:
            db = QSqlDatabase.database(self.__connectionName)
            if db.isOpen():
                db.transaction()
                try:
                    for index in range(0, len(prefixesToRemove), batchSize):
                        removeBatch = prefixesToRemove[index : (index + batchSize)]

                        query = QSqlQuery(db)
                        query.prepare(
                            queryStr.format(",".join(["?"] * len(removeBatch)))
                        )
                        query.addBindValue(threatList.threatType)
                        query.addBindValue(threatList.platformType)
                        query.addBindValue(threatList.threatEntryType)
                        for prefix in removeBatch:
                            query.addBindValue(
                                QByteArray(prefix),
                                QSql.ParamTypeFlag.In | QSql.ParamTypeFlag.Binary,
                            )
                        query.exec()
                        del query
                        QCoreApplication.processEvents(
                            QEventLoop.ProcessEventsFlag.AllEvents,
                            self.maxProcessEventsTime,
                        )
                finally:
                    db.commit()


#
# eflag: noqa = S608
