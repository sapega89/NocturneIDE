# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing some enums for function type annotations.
"""

#
# adapted from flake8-annotations v2.9.0
#

import enum


class FunctionType(enum.Enum):
    """
    Class representing the various function types.
    """

    PUBLIC = enum.auto()
    PROTECTED = enum.auto()  # Leading single underscore
    PRIVATE = enum.auto()  # Leading double underscore
    SPECIAL = enum.auto()  # Leading & trailing double underscore


class ClassDecoratorType(enum.Enum):
    """
    Class representing the various class method decorators.
    """

    CLASSMETHOD = enum.auto()
    STATICMETHOD = enum.auto()


class AnnotationType(enum.Enum):
    """
    Class representing the kind of missing type annotation.
    """

    POSONLYARGS = enum.auto()
    ARGS = enum.auto()
    VARARG = enum.auto()
    KWONLYARGS = enum.auto()
    KWARG = enum.auto()
    RETURN = enum.auto()
