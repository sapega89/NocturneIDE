# -*- coding: utf-8 -*-

# Copyright (c) 2023 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing variants of some 'circup' functions suitable for 'eric-ide'
integration.
"""

#
# Copyright of the original sources:
# Copyright (c) 2019 Adafruit Industries
#

import os
import shutil

import circup
import circup.command_utils
import circup.module
import circup.shared
import requests

from PyQt6.QtCore import QCoreApplication

from eric7.EricWidgets import EricMessageBox


def find_modules(device_path, bundles_list):
    """
    Function to extract metadata from the connected device and available bundles and
    returns this as a list of Module instances representing the modules on the device.

    @param device_path path to the connected board or a disk backend object
    @type str or circup.DiskBackend
    @param bundles_list list of supported bundles
    @type list of circup.Bundle
    @return list of Module instances describing the current state of the
        modules on the connected device
    @rtype list of circup.module.Module
    """
    backend = (
        circup.DiskBackend(device_path, circup.logger)
        if isinstance(device_path, str)
        else device_path
    )
    result = []
    try:
        device_modules = backend.get_device_versions()
        bundle_modules = circup.get_bundle_versions(bundles_list)
        for key, device_metadata in device_modules.items():
            if key in bundle_modules:
                path = device_metadata["path"]
                bundle_metadata = bundle_modules[key]
                repo = bundle_metadata.get("__repo__")
                bundle = bundle_metadata.get("bundle")
                device_version = device_metadata.get("__version__")
                bundle_version = bundle_metadata.get("__version__")
                mpy = device_metadata["mpy"]
                compatibility = device_metadata.get("compatibility", (None, None))
                module_name = (
                    path.split(os.sep)[-1]
                    if not path.endswith(os.sep)
                    else path[:-1].split(os.sep)[-1] + os.sep
                )
                result.append(
                    circup.module.Module(
                        module_name,
                        backend,
                        repo,
                        device_version,
                        bundle_version,
                        mpy,
                        bundle,
                        compatibility,
                    )
                )
    except Exception as ex:
        # If it's not possible to get the device and bundle metadata, bail out
        # with a friendly message and indication of what's gone wrong.
        EricMessageBox.critical(
            None,
            QCoreApplication.translate("CircupFunctions", "Find Modules"),
            QCoreApplication.translate(
                "CircupFunctions", """<p>There was an error: {0}</p>"""
            ).format(str(ex)),
        )

    return result


def ensure_latest_bundle(bundle):
    """
    Function to ensure that there's a copy of the latest library bundle available so
    circup can check the metadata contained therein.

    @param bundle reference to the target Bundle object.
    @type circup.Bundle
    """
    tag = bundle.latest_tag
    do_update = False
    if tag == bundle.current_tag:
        for platform in circup.shared.PLATFORMS:
            # missing directories (new platform added on an existing install
            # or side effect of pytest or network errors)
            do_update = do_update or not os.path.isdir(bundle.lib_dir(platform))
    else:
        do_update = True

    if do_update:
        try:
            circup.get_bundle(bundle, tag)
            circup.command_utils.tags_data_save_tag(bundle.key, tag)
        except requests.exceptions.HTTPError as ex:
            EricMessageBox.critical(
                None,
                QCoreApplication.translate("CircupFunctions", "Download Bundle"),
                QCoreApplication.translate(
                    "CircupFunctions",
                    """<p>There was a problem downloading the bundle. Please try"""
                    """ again in a moment.</p><p>Error: {0}</p>""",
                ).format(str(ex)),
            )


def get_circuitpython_version(device_path):
    """
    Function to return the version number of CircuitPython running on the board
    connected via ``device_path``, along with the board ID.

    This is obtained from the 'boot_out.txt' file on the device, whose first line
    will start with something like this:

        Adafruit CircuitPython 4.1.0 on 2019-08-02;

    While the second line is:

        Board ID:raspberry_pi_pico

    @param device_path path to the connected board.
    @type str
    @return tuple with the version string for CircuitPython and the board ID string
    @rtype tuple of (str, str)
    """
    try:
        with open(os.path.join(device_path, "boot_out.txt")) as boot:
            version_line = boot.readline()
            circuit_python = version_line.split(";")[0].split(" ")[-3]
            board_line = boot.readline()
            board_id = (
                board_line[9:].strip() if board_line.startswith("Board ID:") else ""
            )
    except FileNotFoundError:
        EricMessageBox.critical(
            None,
            QCoreApplication.translate("CircupFunctions", "Download Bundle"),
            QCoreApplication.translate(
                "CircupFunctions",
                """<p>Missing file <b>boot_out.txt</b> on the device: wrong path or"""
                """ drive corrupted.</p>""",
            ),
        )
        circuit_python, board_id = "", ""

    return (circuit_python, board_id)


def install_module(device_path, device_modules, name, py, mod_names):
    """
    Function to find a connected device and install a given module name.

    Installation is done if it is available in the current module bundle and is not
    already installed on the device.

    @param device_path path to the connected board
    @type str
    @param device_modules list of module metadata from the device
    @type list of dict
    @param name name of the module to be installed
    @type str
    @param py flag indicating if the module should be installed from source or
        from a pre-compiled module
    @type bool
    @param mod_names dictionary containing metadata from modules that can be generated
        with circup.get_bundle_versions()
    @type dict
    @return flag indicating success
    @rtype bool
    """
    if not name:
        return False
    elif name in mod_names:
        library_path = os.path.join(device_path, "lib")
        if not os.path.exists(library_path):  # pragma: no cover
            os.makedirs(library_path)
        metadata = mod_names[name]
        bundle = metadata["bundle"]
        # Grab device modules to check if module already installed
        if name in device_modules:
            # ignore silently
            return False
        if py:
            # Use Python source for module.
            source_path = metadata["path"]  # Path to Python source version.
            if os.path.isdir(source_path):
                target = os.path.basename(os.path.dirname(source_path))
                target_path = os.path.join(library_path, target)
                # Copy the directory.
                shutil.copytree(source_path, target_path)
                return True
            else:
                target = os.path.basename(source_path)
                target_path = os.path.join(library_path, target)
                # Copy file.
                shutil.copyfile(source_path, target_path)
                return True
        else:
            # Use pre-compiled mpy modules.
            module_name = os.path.basename(metadata["path"]).replace(".py", ".mpy")
            if not module_name:
                # Must be a directory based module.
                module_name = os.path.basename(os.path.dirname(metadata["path"]))
            major_version = circup.CPY_VERSION.split(".")[0]
            bundle_platform = "{0}mpy".format(major_version)
            bundle_path = os.path.join(bundle.lib_dir(bundle_platform), module_name)
            if os.path.isdir(bundle_path):
                target_path = os.path.join(library_path, module_name)
                # Copy the directory.
                shutil.copytree(bundle_path, target_path)
                return True
            elif os.path.isfile(bundle_path):
                target = os.path.basename(bundle_path)
                target_path = os.path.join(library_path, target)
                # Copy file.
                shutil.copyfile(bundle_path, target_path)
                return True
            else:
                EricMessageBox.critical(
                    None,
                    QCoreApplication.translate("CircupFunctions", "Install Modules"),
                    QCoreApplication.translate(
                        "CircupFunctions",
                        """<p>The compiled version of module <b>{0}</b> cannot be"""
                        """ found.</p>""",
                    ).format(name),
                )
                return False
    else:
        EricMessageBox.critical(
            None,
            QCoreApplication.translate("CircupFunctions", "Install Modules"),
            QCoreApplication.translate(
                "CircupFunctions", """<p>The module name <b>{0}</b> is not known.</p>"""
            ).format(name),
        )
        return False


def patch_circup():
    """
    Function to patch 'circup' to use our functions adapted to the use within the
    eric-ide.
    """
    circup.ensure_latest_bundle = ensure_latest_bundle
    circup.find_modules = find_modules
    circup.get_circuitpython_version = get_circuitpython_version
    circup.install_module = install_module
