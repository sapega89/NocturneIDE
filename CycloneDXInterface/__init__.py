# -*- coding: utf-8 -*-

# Copyright (c) 2022 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Package implementing the interface to the CycloneDX tool for the generation
of Software Bill of Materials files.
"""

from .CycloneDXUtilities import createCycloneDXFile

__all__ = [createCycloneDXFile]
