# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing message translations for the code style plugin messages
(pathlib part).
"""

from PyQt6.QtCore import QCoreApplication

_pathlibMessages = {
    "P101": QCoreApplication.translate(
        "PathlibChecker",
        "os.chmod('foo', 0o444) should be replaced by foo_path.chmod(0o444)",
    ),
    "P102": QCoreApplication.translate(
        "PathlibChecker", "os.mkdir('foo') should be replaced by foo_path.mkdir()"
    ),
    "P103": QCoreApplication.translate(
        "PathlibChecker",
        "os.makedirs('foo/bar') should be replaced by bar_path.mkdir(parents=True)",
    ),
    "P104": QCoreApplication.translate(
        "PathlibChecker",
        "os.rename('foo', 'bar') should be replaced by foo_path.rename(Path('bar'))",
    ),
    "P105": QCoreApplication.translate(
        "PathlibChecker",
        "os.replace('foo', 'bar') should be replaced by "
        "foo_path.replace(Path('bar'))",
    ),
    "P106": QCoreApplication.translate(
        "PathlibChecker", "os.rmdir('foo') should be replaced by foo_path.rmdir()"
    ),
    "P107": QCoreApplication.translate(
        "PathlibChecker", "os.remove('foo') should be replaced by foo_path.unlink()"
    ),
    "P108": QCoreApplication.translate(
        "PathlibChecker", "os.unlink('foo'') should be replaced by foo_path.unlink()"
    ),
    "P109": QCoreApplication.translate(
        "PathlibChecker", "os.getcwd() should be replaced by Path.cwd()"
    ),
    "P110": QCoreApplication.translate(
        "PathlibChecker", "os.readlink('foo') should be replaced by foo_path.readlink()"
    ),
    "P111": QCoreApplication.translate(
        "PathlibChecker",
        "os.stat('foo') should be replaced by foo_path.stat() or "
        "foo_path.owner() or foo_path.group()",
    ),
    "P112": QCoreApplication.translate(
        "PathlibChecker",
        "os.listdir(path='foo') should be replaced by foo_path.iterdir()",
    ),
    "P113": QCoreApplication.translate(
        "PathlibChecker",
        "os.link('bar', 'foo') should be replaced by foo_path.hardlink_to('bar')",
    ),
    "P114": QCoreApplication.translate(
        "PathlibChecker",
        "os.symlink('bar', 'foo') should be replaced by foo_path.symlink_to('bar')",
    ),
    "P201": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.abspath('foo') should be replaced by foo_path.resolve()",
    ),
    "P202": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.exists('foo') should be replaced by foo_path.exists()",
    ),
    "P203": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.expanduser('~/foo') should be replaced by foo_path.expanduser()",
    ),
    "P204": QCoreApplication.translate(
        "PathlibChecker", "os.path.isdir('foo') should be replaced by foo_path.is_dir()"
    ),
    "P205": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.isfile('foo') should be replaced by foo_path.is_file()",
    ),
    "P206": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.islink('foo') should be replaced by foo_path.is_symlink()",
    ),
    "P207": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.isabs('foo') should be replaced by foo_path.is_absolute()",
    ),
    "P208": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.join('foo', 'bar') should be replaced by foo_path / 'bar'",
    ),
    "P209": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.basename('foo/bar') should be replaced by bar_path.name",
    ),
    "P210": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.dirname('foo/bar') should be replaced by bar_path.parent",
    ),
    "P211": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.samefile('foo', 'bar') should be replaced by "
        "foo_path.samefile(bar_path)",
    ),
    "P212": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.splitext('foo.bar') should be replaced by foo_path.suffix",
    ),
    "P213": QCoreApplication.translate(
        "PathlibChecker",
        "os.path.relpath('/bar/foo', start='bar') should be replaced by "
        "foo_path.relative_to('/bar')",
    ),
    "P301": QCoreApplication.translate(
        "PathlibChecker", "open('foo') should be replaced by Path('foo').open()"
    ),
    "P401": QCoreApplication.translate(
        "PathlibChecker", "py.path.local is in maintenance mode, use pathlib instead"
    ),
}
