# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a dataclass containing the metadata of a virtual environment.
"""

from dataclasses import asdict, dataclass


@dataclass
class VirtualenvMetaData:
    """
    Class implementing a container for the metadata of a virtual environment.
    """

    name: str  # name of the virtual environment
    path: str = ""  # directory of the virtual environment (empty for a global one)
    interpreter: str = ""  # path of the Python interpreter
    is_global: bool = False  # flag indicating a global environment
    is_conda: bool = False  # flag indicating an Anaconda environment
    is_remote: bool = False  # flag indicating a remotely accessed environment
    exec_path: str = ""  # string to be prefixed to the PATH environment setting
    description: str = ""  # description of the environment
    is_eric_server: bool = False  # flag indicating an eric-ide server environment
    eric_server: str = ""  # server name the environment belongs to

    def as_dict(self):
        """
        Public method to convert the metadata into a dictionary.

        @return dictionary containing the metadata
        @rtype dict
        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        """
        Class method to create a metadata object from the given dictionary.

        @param data dictionary containing the metadata
        @type dict
        @return created metadata object
        @rtype VirtualenvMetaData
        """
        return cls(
            name=data["name"],
            path=data.get("path", ""),
            interpreter=data.get("interpreter", ""),
            is_global=data.get("is_global", False),
            is_conda=data.get("is_conda", False),
            is_remote=data.get("is_remote", False),
            exec_path=data.get("exec_path", ""),
            description=data.get("description", ""),
            is_eric_server=data.get("is_eric_server", False),
            eric_server=data.get("eric_server", ""),
        )
