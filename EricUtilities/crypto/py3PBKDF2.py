# -*- coding: utf-8 -*-

# Copyright (c) 2002 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing PBKDF2 functions.
"""

import base64
import hashlib
import hmac
import os

Hashes = {
    "sha1": hashlib.sha1,
    "sha224": hashlib.sha224,
    "sha256": hashlib.sha256,
    "sha384": hashlib.sha384,
    "sha512": hashlib.sha512,
    "md5": hashlib.md5,
}

Delimiter = "$"


def pbkdf2(password, salt, iterations, digestMod):
    """
    Module function to hash a password according to the PBKDF2 specification.

    @param password clear text password
    @type bytes
    @param salt salt value
    @type bytes
    @param iterations number of times hash function should be applied
    @type int
    @param digestMod hash function
    @type function
    @return hashed password
    @rtype bytes
    """
    pwHash = password
    for _ in range(iterations):
        pwHash = hmac.new(salt, pwHash, digestMod).digest()
    return pwHash


def hashPasswordTuple(
    password, digestMod=hashlib.sha512, iterations=10000, saltSize=32
):
    """
    Module function to hash a password according to the PBKDF2 specification.

    @param password clear text password
    @type str
    @param digestMod hash function
    @type function
    @param iterations number of times hash function should be applied
    @type int
    @param saltSize size of the salt
    @type int
    @return tuple of digestname, number of iterations, salt and hashed password
    @rtype tuple of (str, int, bytes, bytes)
    """
    salt = os.urandom(saltSize)
    password = password.encode("utf-8")
    pwHash = pbkdf2(password, salt, iterations, digestMod)
    digestname = digestMod.__name__.replace("openssl_", "")
    return digestname, iterations, salt, pwHash


def hashPassword(password, digestMod=hashlib.sha512, iterations=10000, saltSize=32):
    """
    Module function to hash a password according to the PBKDF2 specification.

    @param password clear text password
    @type str
    @param digestMod hash function
    @type function
    @param iterations number of times hash function should be applied
    @type int
    @param saltSize size of the salt
    @type int
    @return hashed password entry according to PBKDF2 specification
    @rtype str
    """
    digestname, iterations, salt, pwHash = hashPasswordTuple(
        password, digestMod, iterations, saltSize
    )
    return Delimiter.join(
        [
            digestname,
            str(iterations),
            base64.b64encode(salt).decode("ascii"),
            base64.b64encode(pwHash).decode("ascii"),
        ]
    )


def verifyPassword(password, pwHash):
    """
    Module function to verify a password against a hash encoded password.

    @param password clear text password
    @type str
    @param pwHash hash encoded password in the form
        'digestmod$iterations$salt$hashed_password' as produced by the
        hashPassword function
    @type str
    @return flag indicating a successfull verification
    @rtype bool
    @exception ValueError the hash is not of the expected format or the
        digest is not one of the known ones
    """
    try:
        digestname, iterations, salt, pwHash = pwHash.split(Delimiter)
    except ValueError:
        raise ValueError(
            "Expected hash encoded password in format "
            "'digestmod{0}iterations{0}salt{0}hashed_password".format(Delimiter)
        )

    if digestname not in Hashes:
        raise ValueError(
            "Unsupported hash algorithm '{0}' for hash encoded password '{1}'.".format(
                digestname, pwHash
            )
        )

    iterations = int(iterations)
    salt = base64.b64decode(salt.encode("ascii"))
    pwHash = base64.b64decode(pwHash.encode("ascii"))
    password = password.encode("utf-8")
    return pwHash == pbkdf2(password, salt, iterations, Hashes[digestname])


def rehashPassword(password, hashParameters):
    """
    Module function to recreate a password hash given the hash parameters.

    @param password clear text password
    @type str
    @param hashParameters hash parameters in the form
        'digestmod$iterations$salt'
    @type str
    @return hashed password
    @rtype bytes
    @exception ValueError the hash parameters string is not of the expected
        format or the digest is not one of the known ones
    """
    try:
        digestname, iterations, salt = hashParameters.split(Delimiter)
    except ValueError:
        raise ValueError(
            "Expected hash parameters string in format "
            "'digestmod{0}iterations{0}salt".format(Delimiter)
        )

    if digestname not in Hashes:
        raise ValueError(
            "Unsupported hash algorithm '{0}' for hash parameters '{1}'.".format(
                digestname, hashParameters
            )
        )

    iterations = int(iterations)
    salt = base64.b64decode(salt.encode("ascii"))
    password = password.encode("utf-8")
    return pbkdf2(password, salt, iterations, Hashes[digestname])
