# -*- coding: utf-8 -*-

# Copyright (c) 2009 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a function to compile all user interface files of a
directory or directory tree.
"""

import os

from PyQt6.uic import compileUiDir


def __pyName(py_dir, py_file):
    """
    Local function to create the Python source file name for the compiled
    .ui file.

    @param py_dir suggested name of the directory
    @type str
    @param py_file suggested name for the compiled source file
    @type str
    @return tuple of directory name and source file name
    @rtype tuple of (str, str)
    """
    return py_dir, "Ui_{0}".format(py_file)


def compileUiFiles(directory, recurse=False):
    """
    Module function to compile the .ui files of a directory tree to Python
    sources.

    @param directory name of a directory to scan for .ui files
    @type str
    @param recurse flag indicating to recurse into subdirectories
    @type boolean)
    """
    compileUiDir(directory, recurse=recurse, map=__pyName)


def compileOneUi(ui_path, mapFunc=None, execute=False, indent=4, uiheadername=""):
    """
    Function to compile a single form file to Python code.

    @param ui_path path of the Qt form file
    @type str
    @param mapFunc function to change directory and/or name of the resulting Python file
        (defaults to None)
    @type func (optional)
    @param execute flag indicating to generate code to execute the form in standalone
        mode (defaults to False)
    @type bool (optional)
    @param indent indentation width using spaces (defaults to 4)
    @type int (optional)
    @param uiheadername UI file name to be placed in the header (defaults to "")
    @type str ((optional)
    """
    py_dir, py_file = os.path.split(ui_path[:-3] + ".py")

    # Allow the caller to change the name of the .py file or generate
    # it in a different directory.
    if mapFunc is None:
        py_dir, py_file = __pyName(py_dir, py_file)
    else:
        py_dir, py_file = mapFunc(py_dir, py_file)

    # Make sure the destination directory exists.
    os.makedirs(py_dir, exist_ok=True)

    py_path = os.path.join(py_dir, py_file)

    with open(py_path, "w", encoding="utf-8") as py_file:
        __compileUi(
            ui_path, py_file, execute=execute, indent=indent, uiheadername=uiheadername
        )


################################################################################
## Below is a modified compileUi() of PyQt6
################################################################################


def __compileUi(uifile, pyfile, execute=False, indent=4, uiheadername=""):
    """
    Function to create a Python module from a Qt Designer .ui file.

    @param uifile file name or file-like object containing the .ui file
    @type str or file
    @param pyfile file-like object to which the Python code will be written to
    @type file
    @param execute flag indicating to generate extra Python code that allows the
        code to be run as a standalone application (defaults to False)
    @type bool (optional)
    @param indent indentation width using spaces. If it is 0 then a tab is used.
        (defaults to 4)
    @type int (optional)
    @param uiheadername UI file name to be placed in the header (defaults to "")
    @type str ((optional)
    """
    from PyQt6.QtCore import PYQT_VERSION_STR  # noqa: I102
    from PyQt6.uic.compile_ui import _display_code, _header  # noqa: I102
    from PyQt6.uic.Compiler import compiler, indenter  # noqa: I102

    if uiheadername:
        uifname = uiheadername
    else:
        try:
            uifname = uifile.name
        except AttributeError:
            uifname = uifile

    indenter.indentwidth = indent

    pyfile.write(_header.format(uifname, PYQT_VERSION_STR))

    winfo = compiler.UICompiler().compileUi(uifile, pyfile)

    if execute:
        indenter.write_code(_display_code % winfo)
