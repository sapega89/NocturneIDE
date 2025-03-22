# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some utility functions for setup.cfg creation.
"""

#
# http://setuptools.readthedocs.io/en/latest/setuptools.html#specifying-values
#
# str - simple string
# list-comma - dangling list or string of comma-separated values
# list-semi - dangling list or string of semicolon-separated values
# bool - True is 1, yes, true
# dict - list-comma where keys are separated from values by =
#


def _bool2string(value):
    """
    Function to convert a bool value to a setup.cfg string.

    @param value bool value to be converted
    @type bool
    @return setup.cfg string
    @rtype str
    """
    return "True" if value else "False"


def _list2string(value):
    """
    Function to convert a list value to a setup.cfg string.

    @param value list value to be converted
    @type list
    @return setup.cfg string
    @rtype str
    """
    if value:
        return "\n{0}".format("\n".join(sorted(filter(None, value))))

    return ""


def _dict2list(value):
    """
    Function to convert a dict value to a setup.cfg list string.

    @param value dict value to be converted
    @type dict
    @yield setup.cfg string
    @ytype str
    """
    for k, v in value.items():
        yield "{0} = {1}".format(k, v)


def _dict2string(value):
    """
    Function to convert a dict value to a setup.cfg string.

    @param value dict value to be converted
    @type dict
    @return setup.cfg string
    @rtype str
    """
    return _list2string(list(_dict2list(value)))


def toString(value):
    """
    Function to convert a value to a setup.cfg string.

    @param value value to be converted
    @type bool, list, set, tuple or dict
    @return setup.cfg string
    @rtype str
    """
    if isinstance(value, bool):
        return _bool2string(value)
    if isinstance(value, (list, set, tuple)):
        return _list2string(value)
    if isinstance(value, dict):
        return _dict2string(value)
    return str(value).rstrip()
