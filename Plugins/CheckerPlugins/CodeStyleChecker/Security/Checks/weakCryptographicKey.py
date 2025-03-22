# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing checks for weak cryptographic key use.
"""

#
# This is a modified version of the one found in the bandit package.
#
# Original Copyright 2014 Hewlett-Packard Development Company, L.P.
#
# SPDX-License-Identifier: Apache-2.0
#

from Security.SecurityDefaults import SecurityDefaults


def getChecks():
    """
    Public method to get a dictionary with checks handled by this module.

    @return dictionary containing checker lists containing checker function and
        list of codes
    @rtype dict
    """
    return {
        "Call": [
            (checkWeakCryptographicKey, ("S505",)),
        ],
    }


def _classifyKeySize(reportError, config, keyType, keySize, node):
    """
    Function to classify a key and report an error if insufficient.

    @param reportError function to be used to report errors
    @type func
    @param config dictionary with configuration data
    @type dict
    @param keyType type of key to be classified ('DSA', 'RSA', 'EC')
    @type str
    @param keySize size of the key to be classified
    @type int
    @param node node the key was extracted from (needed for reporting)
    @type ast.Call
    @return flag indicating an error was reported
    @rtype bool
    """
    if isinstance(keySize, str):
        # try to convert to an integer
        try:
            keySize = int(keySize)
        except ValueError:
            # size provided via a variable - can't process it at the moment
            return False

    conf = {}
    conf.update(SecurityDefaults)
    if config:
        conf.update(config)

    keySizes = {
        "DSA": [
            (conf["weak_key_size_dsa_high"], "H"),
            (conf["weak_key_size_dsa_medium"], "M"),
        ],
        "RSA": [
            (conf["weak_key_size_rsa_high"], "H"),
            (conf["weak_key_size_rsa_medium"], "M"),
        ],
        "EC": [
            (conf["weak_key_size_ec_high"], "H"),
            (conf["weak_key_size_ec_medium"], "M"),
        ],
    }

    for size, level in keySizes[keyType]:
        if keySize < size:
            reportError(
                node.lineno - 1, node.col_offset, "S505", level, "H", keyType, size
            )
            return True

    return False


def _weakCryptoKeySizeCryptography(reportError, context, config):
    """
    Function to check 'cryptography.hazmat' for weak key use.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    @return flag indicating an error was reported
    @rtype bool
    """
    funcKeyType = {
        "cryptography.hazmat.primitives.asymmetric.dsa.generate_private_key": "DSA",
        "cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key": "RSA",
        "cryptography.hazmat.primitives.asymmetric.ec.generate_private_key": "EC",
    }
    argPosition = {
        "DSA": 0,
        "RSA": 1,
        "EC": 0,
    }
    keyType = funcKeyType.get(context.callFunctionNameQual)
    if keyType in ["DSA", "RSA"]:
        keySize = (
            context.getCallArgValue("key_size")
            or context.getCallArgAtPosition(argPosition[keyType])
            or 2048
        )
        return _classifyKeySize(reportError, config, keyType, keySize, context.node)

    elif keyType == "EC":
        curveKeySizes = {
            "SECT571K1": 571,
            "SECT571R1": 570,
            "SECP521R1": 521,
            "BrainpoolP512R1": 512,
            "SECT409K1": 409,
            "SECT409R1": 409,
            "BrainpoolP384R1": 384,
            "SECP384R1": 384,
            "SECT283K1": 283,
            "SECT283R1": 283,
            "BrainpoolP256R1": 256,
            "SECP256K1": 256,
            "SECP256R1": 256,
            "SECT233K1": 233,
            "SECT233R1": 233,
            "SECP224R1": 224,
            "SECP192R1": 192,
            "SECT163K1": 163,
            "SECT163R2": 163,
        }
        curve = context.getCallArgValue("curve") or (
            len(context.callArgs) > argPosition[keyType]
            and context.callArgs[argPosition[keyType]]
        )
        keySize = curveKeySizes[curve] if curve in curveKeySizes else 224
        return _classifyKeySize(reportError, config, keyType, keySize, context.node)

    else:
        return False


def _weakCryptoKeySizePycrypto(reportError, context, config):
    """
    Function to check 'pycrypto' for weak key use.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    @return flag indicating an error was reported
    @rtype bool
    """
    funcKeyType = {
        "Crypto.PublicKey.DSA.generate": "DSA",
        "Crypto.PublicKey.RSA.generate": "RSA",
        "Cryptodome.PublicKey.DSA.generate": "DSA",
        "Cryptodome.PublicKey.RSA.generate": "RSA",
    }
    keyType = funcKeyType.get(context.callFunctionNameQual)
    if keyType:
        keySize = (
            context.getCallArgValue("bits") or context.getCallArgAtPosition(0) or 2048
        )
        return _classifyKeySize(reportError, config, keyType, keySize, context.node)

    return False


def checkWeakCryptographicKey(reportError, context, config):
    """
    Function to check for weak cryptographic key use.

    @param reportError function to be used to report errors
    @type func
    @param context security context object
    @type SecurityContext
    @param config dictionary with configuration data
    @type dict
    """
    (
        _weakCryptoKeySizeCryptography(reportError, context, config)
        or _weakCryptoKeySizePycrypto(reportError, context, config)
    )
