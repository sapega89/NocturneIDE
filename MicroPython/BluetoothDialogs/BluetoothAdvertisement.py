# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a class to parse and store the Bluetooth device advertisement data.
"""

import contextlib
import os
import struct
import uuid

import yaml

ADV_IND = 0
ADV_DIRECT_IND = 1
ADV_SCAN_IND = 2
ADV_NONCONN_IND = 3
SCAN_RSP = 4

ADV_TYPE_UUID16_INCOMPLETE = 0x02
ADV_TYPE_UUID16_COMPLETE = 0x03
ADV_TYPE_UUID32_INCOMPLETE = 0x04
ADV_TYPE_UUID32_COMPLETE = 0x05
ADV_TYPE_UUID128_INCOMPLETE = 0x06
ADV_TYPE_UUID128_COMPLETE = 0x07
ADV_TYPE_SHORT_NAME = 0x08
ADV_TYPE_COMPLETE_NAME = 0x09
ADV_TYPE_TX_POWER_LEVEL = 0x0A
ADV_TYPE_SVC_DATA = 0x16
ADV_TYPE_MANUFACTURER = 0xFF

ManufacturerIDs = None
ServiceIDs = None


def _loadManufacturerIDs():
    """
    Function to load the manufacturer IDs.
    """
    global ManufacturerIDs

    idsFile = os.path.join(
        os.path.dirname(__file__), "data", "company_identifiers.yaml"
    )
    with contextlib.suppress(OSError):
        with open(idsFile, "r") as f:
            idsDict = yaml.safe_load(f)

        ManufacturerIDs = {
            entry["value"]: entry["name"] for entry in idsDict["company_identifiers"]
        }


def _loadServiceUUIDs():
    """
    Function to load the service UUIDs.
    """
    global ServiceIDs

    ServiceIDs = {}

    for uuidFilename in ("member_uuids.yaml", "sdo_uuids.yaml", "service_uuids.yaml"):
        uuidFilepath = os.path.join(os.path.dirname(__file__), "data", uuidFilename)
        with contextlib.suppress(OSError):
            with open(uuidFilepath, "r") as f:
                uuidDict = yaml.safe_load(f)

            ServiceIDs.update({u["uuid"]: u["name"] for u in uuidDict["uuids"]})


class BluetoothAdvertisement:
    """
    Class to parse and store the Bluetooth device advertisement data.
    """

    def __init__(self, address):
        """
        Constructor

        @param address address of the device advertisement
        @type str
        """
        self.__address = address
        self.__rssi = 0
        self.__connectable = False

        self.__advData = None
        self.__respData = None

    def update(self, advType, rssi, advData):
        """
        Public method to update the advertisement data.

        @param advType type of advertisement data
        @type int
        @param rssi RSSI value in dBm
        @type int
        @param advData advertisement data
        @type bytes
        """
        if rssi != self.__rssi:
            self.__rssi = rssi

        if advType in (ADV_IND, ADV_NONCONN_IND):
            if advData != self.__advData:
                self.__advData = advData
                self.__connectable = advType == ADV_IND
        elif advType == ADV_SCAN_IND:
            self.__advData = advData
        elif advType == SCAN_RSP and advData and advData != self.__respData:
            self.__respData = advData

    def __str__(self):
        """
        Special method to generate a string representation.

        @return string representation
        @rtype str
        """
        return "Scan result: {0} {1}".format(self.__address, self.__rssi)

    def __decodeField(self, *advType):
        """
        Private method to get all fields of the specified types.

        @param *advType type of fields to be extracted
        @type int
        @yield requested fields
        @ytype bytes
        """
        # Advertising payloads are repeated packets of the following form:
        #   1 byte data length (N + 1)
        #   1 byte type (see constants at top)
        #   N bytes type-specific data
        for payload in (self.__advData, self.__respData):
            if not payload:
                continue

            i = 0
            while i + 1 < len(payload):
                if payload[i + 1] in advType:
                    yield payload[i + 2 : i + payload[i] + 1]
                i += 1 + payload[i]

    def __splitBytes(self, data, chunkSize):
        """
        Private method to split some data into chunks of given size.

        @param data data to be chunked
        @type bytes, bytearray, str
        @param chunkSize size for each chunk
        @type int
        @return list of chunks
        @rtype list of bytes, bytearray, str
        """
        start = 0
        dataChunks = []
        while start < len(data):
            end = start + chunkSize
            dataChunks.append(data[start:end])
            start = end
        return dataChunks

    @property
    def completeName(self):
        """
        Public method to get the complete advertised name, if available.

        @return advertised name
        @rtype str
        """
        for n in self.__decodeField(ADV_TYPE_COMPLETE_NAME):
            return str(n, "utf-8").replace("\x00", "") if n else ""

        return ""

    @property
    def shortName(self):
        """
        Public method to get the shortened advertised name, if available.

        @return advertised name
        @rtype str
        """
        for n in self.__decodeField(ADV_TYPE_SHORT_NAME):
            return str(n, "utf-8").replace("\x00", "") if n else ""

        return ""

    @property
    def name(self):
        """
        Public method to get the complete or shortened advertised name, if available.

        @return advertised name
        @rtype str
        """
        return self.completeName or self.shortName

    @property
    def rssi(self):
        """
        Public method to get the RSSI value.

        @return RSSI value in dBm
        @rtype int
        """
        return self.__rssi

    @property
    def address(self):
        """
        Public method to get the address string.

        @return address of the device
        @rtype str
        """
        return self.__address

    @property
    def txPower(self):
        """
        Public method to get the advertised power level in dBm.

        @return transmit power of the device (in dBm)
        @rtype int
        """
        for txLevel in self.__decodeField(ADV_TYPE_TX_POWER_LEVEL):
            return struct.unpack("<b", txLevel)[0]

        return 0

    @property
    def services(self):
        """
        Public method to get the service IDs.

        @return list of tuples containing the advertised service ID, the associated
            service name (if available) and a flag indicating a complete ID
        @rtype list of tuple of (str, bool)
        """
        if ServiceIDs is None:
            _loadServiceUUIDs()

        result = []

        for u in self.__decodeField(ADV_TYPE_UUID16_INCOMPLETE):
            for v in self.__splitBytes(u, 2):
                uid = struct.unpack("<H", v)[0]
                result.append((hex(uid), ServiceIDs.get(uid, ""), False))
        for u in self.__decodeField(ADV_TYPE_UUID16_COMPLETE):
            for v in self.__splitBytes(u, 2):
                uid = struct.unpack("<H", v)[0]
                result.append((hex(uid), ServiceIDs.get(uid, ""), False))

        for u in self.__decodeField(ADV_TYPE_UUID32_INCOMPLETE):
            for v in self.__splitBytes(u, 4):
                result.append((hex(struct.unpack("<I", v)), "", False))
        for u in self.__decodeField(ADV_TYPE_UUID32_COMPLETE):
            for v in self.__splitBytes(u, 4):
                result.append((hex(struct.unpack("<I", v)), "", True))

        for u in self.__decodeField(ADV_TYPE_UUID128_INCOMPLETE):
            for v in self.__splitBytes(u, 16):
                uid = uuid.UUID(bytes=bytes(reversed(v)))
                result.append((str(uid), "", False))
        for u in self.__decodeField(ADV_TYPE_UUID128_COMPLETE):
            for v in self.__splitBytes(u, 16):
                uid = uuid.UUID(bytes=bytes(reversed(v)))
                result.append((str(uid), "", True))

        return result

    def manufacturer(self, filterId=None, withName=False):
        """
        Public method to get the manufacturer data.

        @param filterId manufacturer ID to filter on (defaults to None)
        @type int (optional)
        @param withName flag indicating to report the manufacturer name as well
            (if available) (defaults to False)
        @type bool
        @return tuple containing the manufacturer ID, associated data and manufacturer
            name
        @rtype tuple of (int, bytes, str)
        """
        if ManufacturerIDs is None:
            _loadManufacturerIDs()

        result = []
        for u in self.__decodeField(ADV_TYPE_MANUFACTURER):
            if len(u) < 2:
                continue

            m = struct.unpack("<H", u[0:2])[0]
            if filterId is None or m == filterId:
                name = ManufacturerIDs.get(m, "") if withName else None
                result.append((m, u[2:], name))
        return result


#
# eflag: noqa = U200
