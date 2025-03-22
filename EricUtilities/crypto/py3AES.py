# -*- coding: utf-8 -*-

#
# aes.py: implements AES - Advanced Encryption Standard
# from the SlowAES project, http://code.google.com/p/slowaes/
#
# Copyright (c) 2008    Josh Davis ( http://www.josh-davis.org ),
#           Alex Martelli ( http://www.aleax.it )
#
# Ported from C code written by Laurent Haan
# ( http://www.progressive-coding.com )
#
# Licensed under the Apache License, Version 2.0
# http://www.apache.org/licenses/
#

#
# Ported to Python3
#
# Copyright (c) 2011 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing classes for encryption according
Advanced Encryption Standard.
"""

import math
import os


def append_PKCS7_padding(b):
    """
    Function to pad the given data to a multiple of 16-bytes by PKCS7 padding.

    @param b data to be padded
    @type bytes
    @return padded data
    @rtype bytes
    """
    numpads = 16 - (len(b) % 16)
    return b + numpads * bytes(chr(numpads), encoding="ascii")


def strip_PKCS7_padding(b):
    """
    Function to strip off PKCS7 padding.

    @param b data to be stripped
    @type bytes
    @return stripped data
    @rtype bytes
    @exception ValueError data padding is invalid
    """
    if len(b) % 16 or not b:
        raise ValueError("Data of len {0} can't be PCKS7-padded".format(len(b)))
    numpads = b[-1]
    if numpads > 16:
        raise ValueError("Data ending with {0} can't be PCKS7-padded".format(b[-1]))
    return b[:-numpads]


class AES:
    """
    Class implementing the Advanced Encryption Standard algorithm.
    """

    # valid key sizes
    KeySize = {
        "SIZE_128": 16,
        "SIZE_192": 24,
        "SIZE_256": 32,
    }

    # Rijndael S-box
    sbox = [
        0x63,
        0x7C,
        0x77,
        0x7B,
        0xF2,
        0x6B,
        0x6F,
        0xC5,
        0x30,
        0x01,
        0x67,
        0x2B,
        0xFE,
        0xD7,
        0xAB,
        0x76,
        0xCA,
        0x82,
        0xC9,
        0x7D,
        0xFA,
        0x59,
        0x47,
        0xF0,
        0xAD,
        0xD4,
        0xA2,
        0xAF,
        0x9C,
        0xA4,
        0x72,
        0xC0,
        0xB7,
        0xFD,
        0x93,
        0x26,
        0x36,
        0x3F,
        0xF7,
        0xCC,
        0x34,
        0xA5,
        0xE5,
        0xF1,
        0x71,
        0xD8,
        0x31,
        0x15,
        0x04,
        0xC7,
        0x23,
        0xC3,
        0x18,
        0x96,
        0x05,
        0x9A,
        0x07,
        0x12,
        0x80,
        0xE2,
        0xEB,
        0x27,
        0xB2,
        0x75,
        0x09,
        0x83,
        0x2C,
        0x1A,
        0x1B,
        0x6E,
        0x5A,
        0xA0,
        0x52,
        0x3B,
        0xD6,
        0xB3,
        0x29,
        0xE3,
        0x2F,
        0x84,
        0x53,
        0xD1,
        0x00,
        0xED,
        0x20,
        0xFC,
        0xB1,
        0x5B,
        0x6A,
        0xCB,
        0xBE,
        0x39,
        0x4A,
        0x4C,
        0x58,
        0xCF,
        0xD0,
        0xEF,
        0xAA,
        0xFB,
        0x43,
        0x4D,
        0x33,
        0x85,
        0x45,
        0xF9,
        0x02,
        0x7F,
        0x50,
        0x3C,
        0x9F,
        0xA8,
        0x51,
        0xA3,
        0x40,
        0x8F,
        0x92,
        0x9D,
        0x38,
        0xF5,
        0xBC,
        0xB6,
        0xDA,
        0x21,
        0x10,
        0xFF,
        0xF3,
        0xD2,
        0xCD,
        0x0C,
        0x13,
        0xEC,
        0x5F,
        0x97,
        0x44,
        0x17,
        0xC4,
        0xA7,
        0x7E,
        0x3D,
        0x64,
        0x5D,
        0x19,
        0x73,
        0x60,
        0x81,
        0x4F,
        0xDC,
        0x22,
        0x2A,
        0x90,
        0x88,
        0x46,
        0xEE,
        0xB8,
        0x14,
        0xDE,
        0x5E,
        0x0B,
        0xDB,
        0xE0,
        0x32,
        0x3A,
        0x0A,
        0x49,
        0x06,
        0x24,
        0x5C,
        0xC2,
        0xD3,
        0xAC,
        0x62,
        0x91,
        0x95,
        0xE4,
        0x79,
        0xE7,
        0xC8,
        0x37,
        0x6D,
        0x8D,
        0xD5,
        0x4E,
        0xA9,
        0x6C,
        0x56,
        0xF4,
        0xEA,
        0x65,
        0x7A,
        0xAE,
        0x08,
        0xBA,
        0x78,
        0x25,
        0x2E,
        0x1C,
        0xA6,
        0xB4,
        0xC6,
        0xE8,
        0xDD,
        0x74,
        0x1F,
        0x4B,
        0xBD,
        0x8B,
        0x8A,
        0x70,
        0x3E,
        0xB5,
        0x66,
        0x48,
        0x03,
        0xF6,
        0x0E,
        0x61,
        0x35,
        0x57,
        0xB9,
        0x86,
        0xC1,
        0x1D,
        0x9E,
        0xE1,
        0xF8,
        0x98,
        0x11,
        0x69,
        0xD9,
        0x8E,
        0x94,
        0x9B,
        0x1E,
        0x87,
        0xE9,
        0xCE,
        0x55,
        0x28,
        0xDF,
        0x8C,
        0xA1,
        0x89,
        0x0D,
        0xBF,
        0xE6,
        0x42,
        0x68,
        0x41,
        0x99,
        0x2D,
        0x0F,
        0xB0,
        0x54,
        0xBB,
        0x16,
    ]

    # Rijndael Inverted S-box
    rsbox = [
        0x52,
        0x09,
        0x6A,
        0xD5,
        0x30,
        0x36,
        0xA5,
        0x38,
        0xBF,
        0x40,
        0xA3,
        0x9E,
        0x81,
        0xF3,
        0xD7,
        0xFB,
        0x7C,
        0xE3,
        0x39,
        0x82,
        0x9B,
        0x2F,
        0xFF,
        0x87,
        0x34,
        0x8E,
        0x43,
        0x44,
        0xC4,
        0xDE,
        0xE9,
        0xCB,
        0x54,
        0x7B,
        0x94,
        0x32,
        0xA6,
        0xC2,
        0x23,
        0x3D,
        0xEE,
        0x4C,
        0x95,
        0x0B,
        0x42,
        0xFA,
        0xC3,
        0x4E,
        0x08,
        0x2E,
        0xA1,
        0x66,
        0x28,
        0xD9,
        0x24,
        0xB2,
        0x76,
        0x5B,
        0xA2,
        0x49,
        0x6D,
        0x8B,
        0xD1,
        0x25,
        0x72,
        0xF8,
        0xF6,
        0x64,
        0x86,
        0x68,
        0x98,
        0x16,
        0xD4,
        0xA4,
        0x5C,
        0xCC,
        0x5D,
        0x65,
        0xB6,
        0x92,
        0x6C,
        0x70,
        0x48,
        0x50,
        0xFD,
        0xED,
        0xB9,
        0xDA,
        0x5E,
        0x15,
        0x46,
        0x57,
        0xA7,
        0x8D,
        0x9D,
        0x84,
        0x90,
        0xD8,
        0xAB,
        0x00,
        0x8C,
        0xBC,
        0xD3,
        0x0A,
        0xF7,
        0xE4,
        0x58,
        0x05,
        0xB8,
        0xB3,
        0x45,
        0x06,
        0xD0,
        0x2C,
        0x1E,
        0x8F,
        0xCA,
        0x3F,
        0x0F,
        0x02,
        0xC1,
        0xAF,
        0xBD,
        0x03,
        0x01,
        0x13,
        0x8A,
        0x6B,
        0x3A,
        0x91,
        0x11,
        0x41,
        0x4F,
        0x67,
        0xDC,
        0xEA,
        0x97,
        0xF2,
        0xCF,
        0xCE,
        0xF0,
        0xB4,
        0xE6,
        0x73,
        0x96,
        0xAC,
        0x74,
        0x22,
        0xE7,
        0xAD,
        0x35,
        0x85,
        0xE2,
        0xF9,
        0x37,
        0xE8,
        0x1C,
        0x75,
        0xDF,
        0x6E,
        0x47,
        0xF1,
        0x1A,
        0x71,
        0x1D,
        0x29,
        0xC5,
        0x89,
        0x6F,
        0xB7,
        0x62,
        0x0E,
        0xAA,
        0x18,
        0xBE,
        0x1B,
        0xFC,
        0x56,
        0x3E,
        0x4B,
        0xC6,
        0xD2,
        0x79,
        0x20,
        0x9A,
        0xDB,
        0xC0,
        0xFE,
        0x78,
        0xCD,
        0x5A,
        0xF4,
        0x1F,
        0xDD,
        0xA8,
        0x33,
        0x88,
        0x07,
        0xC7,
        0x31,
        0xB1,
        0x12,
        0x10,
        0x59,
        0x27,
        0x80,
        0xEC,
        0x5F,
        0x60,
        0x51,
        0x7F,
        0xA9,
        0x19,
        0xB5,
        0x4A,
        0x0D,
        0x2D,
        0xE5,
        0x7A,
        0x9F,
        0x93,
        0xC9,
        0x9C,
        0xEF,
        0xA0,
        0xE0,
        0x3B,
        0x4D,
        0xAE,
        0x2A,
        0xF5,
        0xB0,
        0xC8,
        0xEB,
        0xBB,
        0x3C,
        0x83,
        0x53,
        0x99,
        0x61,
        0x17,
        0x2B,
        0x04,
        0x7E,
        0xBA,
        0x77,
        0xD6,
        0x26,
        0xE1,
        0x69,
        0x14,
        0x63,
        0x55,
        0x21,
        0x0C,
        0x7D,
    ]

    # Rijndael Rcon
    Rcon = [
        0x8D,
        0x01,
        0x02,
        0x04,
        0x08,
        0x10,
        0x20,
        0x40,
        0x80,
        0x1B,
        0x36,
        0x6C,
        0xD8,
        0xAB,
        0x4D,
        0x9A,
        0x2F,
        0x5E,
        0xBC,
        0x63,
        0xC6,
        0x97,
        0x35,
        0x6A,
        0xD4,
        0xB3,
        0x7D,
        0xFA,
        0xEF,
        0xC5,
        0x91,
        0x39,
        0x72,
        0xE4,
        0xD3,
        0xBD,
        0x61,
        0xC2,
        0x9F,
        0x25,
        0x4A,
        0x94,
        0x33,
        0x66,
        0xCC,
        0x83,
        0x1D,
        0x3A,
        0x74,
        0xE8,
        0xCB,
        0x8D,
        0x01,
        0x02,
        0x04,
        0x08,
        0x10,
        0x20,
        0x40,
        0x80,
        0x1B,
        0x36,
        0x6C,
        0xD8,
        0xAB,
        0x4D,
        0x9A,
        0x2F,
        0x5E,
        0xBC,
        0x63,
        0xC6,
        0x97,
        0x35,
        0x6A,
        0xD4,
        0xB3,
        0x7D,
        0xFA,
        0xEF,
        0xC5,
        0x91,
        0x39,
        0x72,
        0xE4,
        0xD3,
        0xBD,
        0x61,
        0xC2,
        0x9F,
        0x25,
        0x4A,
        0x94,
        0x33,
        0x66,
        0xCC,
        0x83,
        0x1D,
        0x3A,
        0x74,
        0xE8,
        0xCB,
        0x8D,
        0x01,
        0x02,
        0x04,
        0x08,
        0x10,
        0x20,
        0x40,
        0x80,
        0x1B,
        0x36,
        0x6C,
        0xD8,
        0xAB,
        0x4D,
        0x9A,
        0x2F,
        0x5E,
        0xBC,
        0x63,
        0xC6,
        0x97,
        0x35,
        0x6A,
        0xD4,
        0xB3,
        0x7D,
        0xFA,
        0xEF,
        0xC5,
        0x91,
        0x39,
        0x72,
        0xE4,
        0xD3,
        0xBD,
        0x61,
        0xC2,
        0x9F,
        0x25,
        0x4A,
        0x94,
        0x33,
        0x66,
        0xCC,
        0x83,
        0x1D,
        0x3A,
        0x74,
        0xE8,
        0xCB,
        0x8D,
        0x01,
        0x02,
        0x04,
        0x08,
        0x10,
        0x20,
        0x40,
        0x80,
        0x1B,
        0x36,
        0x6C,
        0xD8,
        0xAB,
        0x4D,
        0x9A,
        0x2F,
        0x5E,
        0xBC,
        0x63,
        0xC6,
        0x97,
        0x35,
        0x6A,
        0xD4,
        0xB3,
        0x7D,
        0xFA,
        0xEF,
        0xC5,
        0x91,
        0x39,
        0x72,
        0xE4,
        0xD3,
        0xBD,
        0x61,
        0xC2,
        0x9F,
        0x25,
        0x4A,
        0x94,
        0x33,
        0x66,
        0xCC,
        0x83,
        0x1D,
        0x3A,
        0x74,
        0xE8,
        0xCB,
        0x8D,
        0x01,
        0x02,
        0x04,
        0x08,
        0x10,
        0x20,
        0x40,
        0x80,
        0x1B,
        0x36,
        0x6C,
        0xD8,
        0xAB,
        0x4D,
        0x9A,
        0x2F,
        0x5E,
        0xBC,
        0x63,
        0xC6,
        0x97,
        0x35,
        0x6A,
        0xD4,
        0xB3,
        0x7D,
        0xFA,
        0xEF,
        0xC5,
        0x91,
        0x39,
        0x72,
        0xE4,
        0xD3,
        0xBD,
        0x61,
        0xC2,
        0x9F,
        0x25,
        0x4A,
        0x94,
        0x33,
        0x66,
        0xCC,
        0x83,
        0x1D,
        0x3A,
        0x74,
        0xE8,
        0xCB,
    ]

    def __getSBoxValue(self, num):
        """
        Private method to retrieve a given S-Box value.

        @param num position of the value
        @type int
        @return value of the S-Box
        @rtype int
        """
        return self.sbox[num]

    def __getSBoxInvert(self, num):
        """
        Private method to retrieve a given Inverted S-Box value.

        @param num position of the value
        @type int
        @return value of the Inverted S-Box
        @rtype int
        """
        return self.rsbox[num]

    def __rotate(self, data):
        """
        Private method performing Rijndael's key schedule rotate operation.

        Rotate the data word eight bits to the left: eg,
        rotate(1d2c3a4f) == 2c3a4f1d.

        @param data data of size 4
        @type bytearray
        @return rotated data
        @rtype bytearray
        """
        return data[1:] + data[:1]

    def __getRconValue(self, num):
        """
        Private method to retrieve a given Rcon value.

        @param num position of the value
        @type int
        @return Rcon value
        @rtype int
        """
        return self.Rcon[num]

    def __core(self, data, iteration):
        """
        Private method performing the key schedule core operation.

        @param data data to operate on
        @type bytearray
        @param iteration iteration counter
        @type int
        @return modified data
        @rtype bytearray
        """
        # rotate the 32-bit word 8 bits to the left
        data = self.__rotate(data)
        # apply S-Box substitution on all 4 parts of the 32-bit word
        for i in range(4):
            data[i] = self.__getSBoxValue(data[i])
        # XOR the output of the rcon operation with i to the first part
        # (leftmost) only
        data[0] = data[0] ^ self.__getRconValue(iteration)
        return data

    def __expandKey(self, key, size, expandedKeySize):
        """
        Private method performing Rijndael's key expansion.

        Expands a 128, 192 or 256 bit key into a 176, 208 or 240 bit key.

        @param key key to be expanded
        @type bytes or bytearray
        @param size size of the key in bytes (16, 24 or 32)
        @type int
        @param expandedKeySize size of the expanded key
        @type int
        @return expanded key
        @rtype bytearray
        """
        # current expanded keySize, in bytes
        currentSize = 0
        rconIteration = 1
        expandedKey = bytearray(expandedKeySize)

        # set the 16, 24, 32 bytes of the expanded key to the input key
        for j in range(size):
            expandedKey[j] = key[j]
        currentSize += size

        while currentSize < expandedKeySize:
            # assign the previous 4 bytes to the temporary value t
            t = expandedKey[currentSize - 4 : currentSize]

            # every 16, 24, 32 bytes we apply the core schedule to t
            # and increment rconIteration afterwards
            if currentSize % size == 0:
                t = self.__core(t, rconIteration)
                rconIteration += 1
            # For 256-bit keys, we add an extra sbox to the calculation
            if size == self.KeySize["SIZE_256"] and ((currentSize % size) == 16):
                for ll in range(4):
                    t[ll] = self.__getSBoxValue(t[ll])

            # We XOR t with the four-byte block 16, 24, 32 bytes before the new
            # expanded key. This becomes the next four bytes in the expanded
            # key.
            for m in range(4):
                expandedKey[currentSize] = expandedKey[currentSize - size] ^ t[m]
                currentSize += 1  # noqa: Y113

        return expandedKey

    def __addRoundKey(self, state, roundKey):
        """
        Private method to add (XORs) the round key to the state.

        @param state state to be changed
        @type bytearray
        @param roundKey key to be used for the modification
        @type bytearray
        @return modified state
        @rtype bytearray
        """
        buf = state[:]
        for i in range(16):
            buf[i] ^= roundKey[i]
        return buf

    def __createRoundKey(self, expandedKey, roundKeyPointer):
        """
        Private method to create a round key.

        @param expandedKey expanded key to be used
        @type bytearray
        @param roundKeyPointer position within the expanded key
        @type int
        @return round key
        @rtype bytearray
        """
        roundKey = bytearray(16)
        for i in range(4):
            for j in range(4):
                roundKey[j * 4 + i] = expandedKey[roundKeyPointer + i * 4 + j]
        return roundKey

    def __galois_multiplication(self, a, b):
        """
        Private method to perform a Galois multiplication of 8 bit characters
        a and b.

        @param a first factor
        @type bytes
        @param b second factor
        @type bytes
        @return result
        @rtype bytes
        """
        p = 0
        for _counter in range(8):
            if b & 1:
                p ^= a
            hi_bit_set = a & 0x80
            a <<= 1
            # keep a 8 bit
            a &= 0xFF
            if hi_bit_set:
                a ^= 0x1B
            b >>= 1
        return p

    def __subBytes(self, state, isInv):
        """
        Private method to substitute all the values from the state with the
        value in the SBox using the state value as index for the SBox.

        @param state state to be worked on
        @type bytearray
        @param isInv flag indicating an inverse operation
        @type bool
        @return modified state
        @rtype bytearray
        """
        state = state[:]
        getter = self.__getSBoxInvert if isInv else self.__getSBoxValue
        for i in range(16):
            state[i] = getter(state[i])
        return state

    def __shiftRows(self, state, isInv):
        """
        Private method to iterate over the 4 rows and call __shiftRow() with
        that row.

        @param state state to be worked on
        @type bytearray
        @param isInv flag indicating an inverse operation
        @type bool
        @return modified state
        @rtype bytearray
        """
        state = state[:]
        for i in range(4):
            state = self.__shiftRow(state, i * 4, i, isInv)
        return state

    def __shiftRow(self, state, statePointer, nbr, isInv):
        """
        Private method to shift the bytes of a row to the left.

        @param state state to be worked on
        @type bytearray
        @param statePointer index into the state
        @type int
        @param nbr number of positions to shift
        @type int
        @param isInv flag indicating an inverse operation
        @type bool
        @return modified state
        @rtype bytearray
        """
        state = state[:]
        for _ in range(nbr):
            if isInv:
                state[statePointer : statePointer + 4] = (
                    state[statePointer + 3 : statePointer + 4]
                    + state[statePointer : statePointer + 3]
                )
            else:
                state[statePointer : statePointer + 4] = (
                    state[statePointer + 1 : statePointer + 4]
                    + state[statePointer : statePointer + 1]
                )
        return state

    def __mixColumns(self, state, isInv):
        """
        Private method to perform a galois multiplication of the 4x4 matrix.

        @param state state to be worked on
        @type bytearray
        @param isInv flag indicating an inverse operation
        @type bool
        @return modified state
        @rtype bytearray
        """
        state = state[:]
        # iterate over the 4 columns
        for i in range(4):
            # construct one column by slicing over the 4 rows
            column = state[i : i + 16 : 4]
            # apply the __mixColumn on one column
            column = self.__mixColumn(column, isInv)
            # put the values back into the state
            state[i : i + 16 : 4] = column

        return state

    # galois multiplication of 1 column of the 4x4 matrix
    def __mixColumn(self, column, isInv):
        """
        Private method to perform a galois multiplication of 1 column the
        4x4 matrix.

        @param column column to be worked on
        @type bytearray
        @param isInv flag indicating an inverse operation
        @type bool
        @return modified column
        @rtype bytearray
        """
        column = column[:]
        mult = [14, 9, 13, 11] if isInv else [2, 1, 1, 3]
        cpy = column[:]
        g = self.__galois_multiplication

        column[0] = (
            g(cpy[0], mult[0])
            ^ g(cpy[3], mult[1])
            ^ g(cpy[2], mult[2])
            ^ g(cpy[1], mult[3])
        )
        column[1] = (
            g(cpy[1], mult[0])
            ^ g(cpy[0], mult[1])
            ^ g(cpy[3], mult[2])
            ^ g(cpy[2], mult[3])
        )
        column[2] = (
            g(cpy[2], mult[0])
            ^ g(cpy[1], mult[1])
            ^ g(cpy[0], mult[2])
            ^ g(cpy[3], mult[3])
        )
        column[3] = (
            g(cpy[3], mult[0])
            ^ g(cpy[2], mult[1])
            ^ g(cpy[1], mult[2])
            ^ g(cpy[0], mult[3])
        )
        return column

    def __aes_round(self, state, roundKey):
        """
        Private method to apply the 4 operations of the forward round in
        sequence.

        @param state state to be worked on
        @type bytearray
        @param roundKey round key to be used
        @type bytearray
        @return modified state
        @rtype bytearray
        """
        state = self.__subBytes(state, False)
        state = self.__shiftRows(state, False)
        state = self.__mixColumns(state, False)
        state = self.__addRoundKey(state, roundKey)
        return state

    def __aes_invRound(self, state, roundKey):
        """
        Private method to apply the 4 operations of the inverse round in
        sequence.

        @param state state to be worked on
        @type bytearray
        @param roundKey round key to be used
        @type bytearray
        @return modified state
        @rtype bytearray
        """
        state = self.__shiftRows(state, True)
        state = self.__subBytes(state, True)
        state = self.__addRoundKey(state, roundKey)
        state = self.__mixColumns(state, True)
        return state

    def __aes_main(self, state, expandedKey, nbrRounds):
        """
        Private method to do the AES encryption for one round.

        Perform the initial operations, the standard round, and the
        final operations of the forward AES, creating a round key for
        each round.

        @param state state to be worked on
        @type bytearray
        @param expandedKey expanded key to be used
        @type bytearray
        @param nbrRounds number of rounds to be done
        @type int
        @return modified state
        @rtype bytearray
        """
        state = self.__addRoundKey(state, self.__createRoundKey(expandedKey, 0))
        i = 1
        while i < nbrRounds:
            state = self.__aes_round(state, self.__createRoundKey(expandedKey, 16 * i))
            i += 1
        state = self.__subBytes(state, False)
        state = self.__shiftRows(state, False)
        state = self.__addRoundKey(
            state, self.__createRoundKey(expandedKey, 16 * nbrRounds)
        )
        return state

    def __aes_invMain(self, state, expandedKey, nbrRounds):
        """
        Private method to do the inverse AES encryption for one round.

        Perform the initial operations, the standard round, and the
        final operations of the inverse AES, creating a round key for
        each round.

        @param state state to be worked on
        @type bytearray
        @param expandedKey expanded key to be used
        @type bytearray
        @param nbrRounds number of rounds to be done
        @type int
        @return modified state
        @rtype bytearray
        """
        state = self.__addRoundKey(
            state, self.__createRoundKey(expandedKey, 16 * nbrRounds)
        )
        i = nbrRounds - 1
        while i > 0:
            state = self.__aes_invRound(
                state, self.__createRoundKey(expandedKey, 16 * i)
            )
            i -= 1
        state = self.__shiftRows(state, True)
        state = self.__subBytes(state, True)
        state = self.__addRoundKey(state, self.__createRoundKey(expandedKey, 0))
        return state

    def encrypt(self, iput, key, size):
        """
        Public method to encrypt a 128 bit input block against the given key
        of size specified.

        @param iput input data
        @type bytearray
        @param key key to be used
        @type bytes or bytearray
        @param size key size (16, 24 or 32)
        @type int
        @return encrypted data
        @rtype bytes
        @exception ValueError key size is invalid
        """
        if size not in self.KeySize.values():
            raise ValueError("Wrong key size given ({0}).".format(size))

        output = bytearray(16)
        # the number of rounds
        nbrRounds = 0
        # the 128 bit block to encode
        block = bytearray(16)
        # set the number of rounds
        if size == self.KeySize["SIZE_128"]:
            nbrRounds = 10
        elif size == self.KeySize["SIZE_192"]:
            nbrRounds = 12
        else:
            nbrRounds = 14

        # the expanded keySize
        expandedKeySize = 16 * (nbrRounds + 1)

        # Set the block values, for the block:
        # a0,0 a0,1 a0,2 a0,3
        # a1,0 a1,1 a1,2 a1,3
        # a2,0 a2,1 a2,2 a2,3
        # a3,0 a3,1 a3,2 a3,3
        # the mapping order is a0,0 a1,0 a2,0 a3,0 a0,1 a1,1 ... a2,3 a3,3
        #
        # iterate over the columns
        for i in range(4):
            # iterate over the rows
            for j in range(4):
                block[i + j * 4] = iput[i * 4 + j]

        # expand the key into an 176, 208, 240 bytes key
        # the expanded key
        expandedKey = self.__expandKey(key, size, expandedKeySize)

        # encrypt the block using the expandedKey
        block = self.__aes_main(block, expandedKey, nbrRounds)

        # unmap the block again into the output
        for kk in range(4):
            # iterate over the rows
            for ll in range(4):
                output[kk * 4 + ll] = block[kk + ll * 4]
        return bytes(output)

    # decrypts a 128 bit input block against the given key of size specified
    def decrypt(self, iput, key, size):
        """
        Public method to decrypt a 128 bit input block against the given key
        of size specified.

        @param iput input data
        @type bytearray
        @param key key to be used
        @type bytes or bytearray
        @param size key size (16, 24 or 32)
        @type int
        @return decrypted data
        @rtype bytes
        @exception ValueError key size is invalid
        """
        if size not in self.KeySize.values():
            raise ValueError("Wrong key size given ({0}).".format(size))

        output = bytearray(16)
        # the number of rounds
        nbrRounds = 0
        # the 128 bit block to decode
        block = bytearray(16)
        # set the number of rounds

        if size == self.KeySize["SIZE_128"]:
            nbrRounds = 10
        elif size == self.KeySize["SIZE_192"]:
            nbrRounds = 12
        else:
            nbrRounds = 14

        # the expanded keySize
        expandedKeySize = 16 * (nbrRounds + 1)

        # Set the block values, for the block:
        # a0,0 a0,1 a0,2 a0,3
        # a1,0 a1,1 a1,2 a1,3
        # a2,0 a2,1 a2,2 a2,3
        # a3,0 a3,1 a3,2 a3,3
        # the mapping order is a0,0 a1,0 a2,0 a3,0 a0,1 a1,1 ... a2,3 a3,3

        # iterate over the columns
        for i in range(4):
            # iterate over the rows
            for j in range(4):
                block[i + j * 4] = iput[i * 4 + j]
        # expand the key into an 176, 208, 240 bytes key
        expandedKey = self.__expandKey(key, size, expandedKeySize)
        # decrypt the block using the expandedKey
        block = self.__aes_invMain(block, expandedKey, nbrRounds)
        # unmap the block again into the output
        for kk in range(4):
            # iterate over the rows
            for ll in range(4):
                output[kk * 4 + ll] = block[kk + ll * 4]
        return output


class AESModeOfOperation:
    """
    Class implementing the different AES mode of operations.
    """

    aes = AES()

    # structure of supported modes of operation
    ModeOfOperation = {
        "OFB": 0,
        "CFB": 1,
        "CBC": 2,
    }

    def __extractBytes(self, inputData, start, end, mode):
        """
        Private method to extract a range of bytes from the input.

        @param inputData input data
        @type bytes
        @param start start index
        @type int
        @param end end index
        @type int
        @param mode mode of operation (0, 1, 2)
        @type int
        @return extracted bytes
        @rtype bytearray
        """
        if end - start > 16:
            end = start + 16
        ar = bytearray(16) if mode == self.ModeOfOperation["CBC"] else bytearray()

        i = start
        j = 0
        while len(ar) < end - start:
            ar.append(0)
        while i < end:
            ar[j] = inputData[i]
            j += 1
            i += 1
        return ar

    def encrypt(self, inputData, mode, key, size, IV):
        """
        Public method to perform the encryption operation.

        @param inputData data to be encrypted
        @type bytes
        @param mode mode of operation (0, 1 or 2)
        @type int
        @param key key to be used
        @type bytes
        @param size length of the key (16, 24 or 32)
        @type int
        @param IV initialisation vector
        @type bytearray
        @return tuple with mode of operation, length of the input data and
            the encrypted data
        @rtype tuple of (int, int, bytes)
        @exception ValueError key size is invalid or decrypted data is invalid
        """
        if len(key) % size:
            raise ValueError("Illegal size ({0}) for key '{1}'.".format(size, key))
        if len(IV) % 16:
            raise ValueError("IV is not a multiple of 16.")
        # the AES input/output
        iput = bytearray(16)
        output = bytearray()
        ciphertext = bytearray(16)
        # the output cipher string
        cipherOut = bytearray()
        # char firstRound
        firstRound = True
        if inputData:
            for j in range(int(math.ceil(float(len(inputData)) / 16))):
                start = j * 16
                end = j * 16 + 16
                if end > len(inputData):
                    end = len(inputData)
                plaintext = self.__extractBytes(inputData, start, end, mode)
                if mode == self.ModeOfOperation["CFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(plaintext) - 1 < i:
                            ciphertext[i] = 0 ^ output[i]
                        elif len(output) - 1 < i:
                            ciphertext[i] = plaintext[i] ^ 0
                        elif len(plaintext) - 1 < i and len(output) < i:
                            ciphertext[i] = 0 ^ 0
                        else:
                            ciphertext[i] = plaintext[i] ^ output[i]
                    for k in range(end - start):
                        cipherOut.append(ciphertext[k])
                    iput = ciphertext
                elif mode == self.ModeOfOperation["OFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(plaintext) - 1 < i:
                            ciphertext[i] = 0 ^ output[i]
                        elif len(output) - 1 < i:
                            ciphertext[i] = plaintext[i] ^ 0
                        elif len(plaintext) - 1 < i and len(output) < i:
                            ciphertext[i] = 0 ^ 0
                        else:
                            ciphertext[i] = plaintext[i] ^ output[i]
                    for k in range(end - start):
                        cipherOut.append(ciphertext[k])
                    iput = output
                elif mode == self.ModeOfOperation["CBC"]:
                    for i in range(16):
                        if firstRound:
                            iput[i] = plaintext[i] ^ IV[i]
                        else:
                            iput[i] = plaintext[i] ^ ciphertext[i]
                    firstRound = False
                    ciphertext = self.aes.encrypt(iput, key, size)
                    # always 16 bytes because of the padding for CBC
                    for k in range(16):
                        cipherOut.append(ciphertext[k])
        return mode, len(inputData), bytes(cipherOut)

    # Mode of Operation Decryption
    # cipherIn - Encrypted String
    # originalsize - The unencrypted string length - required for CBC
    # mode - mode of type modeOfOperation
    # key - a number array of the bit length size
    # size - the bit length of the key
    # IV - the 128 bit number array Initilization Vector
    def decrypt(self, cipherIn, originalsize, mode, key, size, IV):
        """
        Public method to perform the decryption operation.

        @param cipherIn data to be decrypted
        @type bytes
        @param originalsize unencrypted string length (required for CBC)
        @type int
        @param mode mode of operation (0, 1 or 2)
        @type int
        @param key key to be used
        @type bytes
        @param size length of the key (16, 24 or 32)
        @type int
        @param IV initialisation vector
        @type bytearray
        @return decrypted data
        @rtype bytes
        @exception ValueError key size is invalid or decrypted data is invalid
        """
        if len(key) % size:
            raise ValueError("Illegal size ({0}) for key '{1}'.".format(size, key))
        if len(IV) % 16:
            raise ValueError("IV is not a multiple of 16.")
        # the AES input/output
        ciphertext = bytearray()
        iput = bytearray()
        output = bytearray()
        plaintext = bytearray(16)
        # the output bytes
        bytesOut = bytearray()
        # char firstRound
        firstRound = True
        if cipherIn is not None:
            for j in range(int(math.ceil(float(len(cipherIn)) / 16))):
                start = j * 16
                end = j * 16 + 16
                if j * 16 + 16 > len(cipherIn):
                    end = len(cipherIn)
                ciphertext = cipherIn[start:end]
                if mode == self.ModeOfOperation["CFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(output) - 1 < i:
                            plaintext[i] = 0 ^ ciphertext[i]
                        elif len(ciphertext) - 1 < i:
                            plaintext[i] = output[i] ^ 0
                        elif len(output) - 1 < i and len(ciphertext) < i:
                            plaintext[i] = 0 ^ 0
                        else:
                            plaintext[i] = output[i] ^ ciphertext[i]
                    for k in range(end - start):
                        bytesOut.append(plaintext[k])
                    iput = ciphertext
                elif mode == self.ModeOfOperation["OFB"]:
                    if firstRound:
                        output = self.aes.encrypt(IV, key, size)
                        firstRound = False
                    else:
                        output = self.aes.encrypt(iput, key, size)
                    for i in range(16):
                        if len(output) - 1 < i:
                            plaintext[i] = 0 ^ ciphertext[i]
                        elif len(ciphertext) - 1 < i:
                            plaintext[i] = output[i] ^ 0
                        elif len(output) - 1 < i and len(ciphertext) < i:
                            plaintext[i] = 0 ^ 0
                        else:
                            plaintext[i] = output[i] ^ ciphertext[i]
                    for k in range(end - start):
                        bytesOut.append(plaintext[k])
                    iput = output
                elif mode == self.ModeOfOperation["CBC"]:
                    output = self.aes.decrypt(ciphertext, key, size)
                    for i in range(16):
                        if firstRound:
                            plaintext[i] = IV[i] ^ output[i]
                        else:
                            plaintext[i] = iput[i] ^ output[i]
                    firstRound = False
                    if originalsize is not None and originalsize < end:
                        for k in range(originalsize - start):
                            bytesOut.append(plaintext[k])
                    else:
                        for k in range(end - start):
                            bytesOut.append(plaintext[k])
                    iput = ciphertext
        return bytes(bytesOut)


def encryptData(key, data, mode=AESModeOfOperation.ModeOfOperation["CBC"]):
    """
    Module function to encrypt the given data with the given key.

    @param key key to be used for encryption
    @type bytes
    @param data data to be encrypted
    @type bytes
    @param mode mode of operations (0, 1 or 2)
    @type int
    @return encrypted data prepended with the initialization vector
    @rtype bytes
    @exception ValueError raised to indicate an invalid key size
    """
    key = bytearray(key)
    if mode == AESModeOfOperation.ModeOfOperation["CBC"]:
        data = append_PKCS7_padding(data)
    keysize = len(key)
    if keysize not in AES.KeySize.values():
        raise ValueError("invalid key size: {0}".format(keysize))
    # create a new iv using random data
    iv = bytearray(list(os.urandom(16)))
    moo = AESModeOfOperation()
    _mode, _length, ciph = moo.encrypt(data, mode, key, keysize, iv)
    # With padding, the original length does not need to be known. It's a bad
    # idea to store the original message length.
    # prepend the iv.
    return bytes(iv) + bytes(ciph)


def decryptData(key, data, mode=AESModeOfOperation.ModeOfOperation["CBC"]):
    """
    Module function to decrypt the given data with the given key.

    @param key key to be used for decryption
    @type bytes
    @param data data to be decrypted (with initialization vector prepended)
    @type bytes
    @param mode mode of operations (0, 1 or 2)
    @type int
    @return decrypted data
    @rtype bytes
    @exception ValueError raised to indicate an invalid key size
    """
    key = bytearray(key)
    keysize = len(key)
    if keysize not in AES.KeySize.values():
        raise ValueError("invalid key size: {0}".format(keysize))
    # iv is first 16 bytes
    iv = bytearray(data[:16])
    data = bytearray(data[16:])
    moo = AESModeOfOperation()
    decr = moo.decrypt(data, None, mode, key, keysize, iv)
    if mode == AESModeOfOperation.ModeOfOperation["CBC"]:
        decr = strip_PKCS7_padding(decr)
    return bytes(decr)
