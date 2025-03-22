# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing message translations for the code style plugin messages
(simplify part).
"""

from PyQt6.QtCore import QCoreApplication

_simplifyMessages = {
    # Python-specifics
    "Y101": QCoreApplication.translate(
        "SimplifyChecker",
        """Multiple "isinstance()" calls which can be merged into a single """
        '''call for variable "{0}"''',
    ),
    "Y102": QCoreApplication.translate(
        "SimplifyChecker",
        """Use a single if-statement instead of nested if-statements""",
    ),
    "Y103": QCoreApplication.translate(
        "SimplifyChecker", """Return the condition "{0}" directly"""
    ),
    "Y104": QCoreApplication.translate("SimplifyChecker", '''Use "yield from {0}"'''),
    "Y105": QCoreApplication.translate(
        "SimplifyChecker", '''Use "with contextlib.suppress({0}):"'''
    ),
    "Y106": QCoreApplication.translate(
        "SimplifyChecker", """Handle error-cases first"""
    ),
    "Y107": QCoreApplication.translate(
        "SimplifyChecker", """Don't use return in try/except and finally"""
    ),
    "Y108": QCoreApplication.translate(
        "SimplifyChecker",
        """Use ternary operator "{0} = {1} if {2} else {3}" """
        """instead of if-else-block""",
    ),
    "Y109": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0} in {1}" instead of "{2}"'''
    ),
    "Y110": QCoreApplication.translate(
        "SimplifyChecker", '''Use "any({0} for {1} in {2})"'''
    ),
    "Y111": QCoreApplication.translate(
        "SimplifyChecker", '''Use "all({0} for {1} in {2})"'''
    ),
    "Y112": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0}" instead of "{1}"'''
    ),
    "Y113": QCoreApplication.translate(
        "SimplifyChecker", '''Use enumerate instead of "{0}"'''
    ),
    "Y114": QCoreApplication.translate(
        "SimplifyChecker", """Use logical or ("({0}) or ({1})") and a single body"""
    ),
    "Y115": QCoreApplication.translate(
        "SimplifyChecker", """Use context handler for opening files"""
    ),
    "Y116": QCoreApplication.translate(
        "SimplifyChecker",
        """Use a dictionary lookup instead of 3+ if/elif-statements: """
        """return {0}""",
    ),
    "Y117": QCoreApplication.translate(
        "SimplifyChecker", """Use "{0}" instead of multiple with statements"""
    ),
    "Y118": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0} in {1}" instead of "{0} in {1}.keys()"'''
    ),
    "Y119": QCoreApplication.translate(
        "SimplifyChecker", '''Use a dataclass for "class {0}"'''
    ),
    "Y120": QCoreApplication.translate(
        "SimplifyChecker", '''Use "class {0}:" instead of "class {0}(object):"'''
    ),
    "Y121": QCoreApplication.translate(
        "SimplifyChecker",
        '''Use "class {0}({1}):" instead of "class {0}({1}, object):"''',
    ),
    "Y122": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0}.get({1})" instead of "if {1} in {0}: {0}[{1}]"'''
    ),
    "Y123": QCoreApplication.translate(
        "SimplifyChecker", """Use "{0} = {1}.get({2}, {3})" instead of an if-block"""
    ),
    # Python-specifics not part of flake8-simplify
    "Y181": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0}" instead of "{1}"'''
    ),
    "Y182": QCoreApplication.translate(
        "SimplifyChecker", '''Use "super()" instead of "{0}"'''
    ),
    # Comparations
    "Y201": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0} != {1}" instead of "not {0} == {1}"'''
    ),
    "Y202": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0} == {1}" instead of "not {0} != {1}"'''
    ),
    "Y203": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0} not in {1}" instead of "not {0} in {1}"'''
    ),
    "Y204": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0} >= {1}" instead of "not ({0} < {1})"'''
    ),
    "Y205": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0} > {1}" instead of "not ({0} <= {1})"'''
    ),
    "Y206": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0} <= {1}" instead of "not ({0} > {1})"'''
    ),
    "Y207": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0} < {1}" instead of "not ({0} >= {1})"'''
    ),
    "Y208": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0}" instead of "not (not {0})"'''
    ),
    "Y211": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{1}" instead of "True if {0} else False"'''
    ),
    "Y212": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{1}" instead of "False if {0} else True"'''
    ),
    "Y213": QCoreApplication.translate(
        "SimplifyChecker",
        '''Use "{0} if {0} else {1}" instead of "{1} if not {0} else {0}"''',
    ),
    "Y221": QCoreApplication.translate(
        "SimplifyChecker", '''Use "False" instead of "{0} and not {0}"'''
    ),
    "Y222": QCoreApplication.translate(
        "SimplifyChecker", '''Use "True" instead of "{0} or not {0}"'''
    ),
    "Y223": QCoreApplication.translate(
        "SimplifyChecker", '''Use "True" instead of "... or True"'''
    ),
    "Y224": QCoreApplication.translate(
        "SimplifyChecker", '''Use "False" instead of "... and False"'''
    ),
    # Opinionated
    "Y301": QCoreApplication.translate(
        "SimplifyChecker",
        """Use "{1} == {0}" instead of "{0} == {1}" (Yoda-condition)""",
    ),
    # General Code Style
    "Y401": QCoreApplication.translate(
        "SimplifyChecker", """Use keyword-argument instead of magic boolean"""
    ),
    "Y402": QCoreApplication.translate(
        "SimplifyChecker", """Use keyword-argument instead of magic number"""
    ),
    "Y901": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0}" instead of "{1}"'''
    ),
    "Y904": QCoreApplication.translate(
        "SimplifyChecker", """Initialize dictionary "{0}" directly"""
    ),
    "Y905": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0}" instead of "{1}"'''
    ),
    "Y906": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0}" instead of "{1}"'''
    ),
    "Y907": QCoreApplication.translate(
        "SimplifyChecker", '''Use "Optional[{0}]" instead of "{1}"'''
    ),
    "Y909": QCoreApplication.translate(
        "SimplifyChecker", '''Remove reflexive assignment "{0}"'''
    ),
    "Y910": QCoreApplication.translate(
        "SimplifyChecker", '''Use "{0}" instead of "{1}"'''
    ),
    "Y911": QCoreApplication.translate(
        "SimplifyChecker",
        '''Use "{0}.items()" instead of "zip({0}.keys(), {0}.values())"''',
    ),
}

_simplifyMessagesSampleArgs = {
    # Python-specifics
    "Y101": ["foo"],
    "Y103": ["foo != bar"],
    "Y104": ["iterable"],
    "Y105": ["Exception"],
    "Y108": ["foo", "bar", "condition", "baz"],
    "Y109": ["foo", "[1, 42]", "foo == 1 or foo == 42"],
    "Y110": ["check", "foo", "iterable"],
    "Y111": ["check", "foo", "iterable"],
    "Y112": ["FOO", "foo"],
    "Y113": ["foo"],
    "Y114": ["foo > 42", "bar < 42"],
    "Y116": ["bar_dict.get(foo, 42)"],
    "Y117": ["with Foo() as foo, Bar() as bar:"],
    "Y118": ["foo", "bar_dict"],
    "Y119": ["Foo"],
    "Y120": ["Foo"],
    "Y121": ["FooBar", "Foo"],
    "Y122": ["bar_dict", "'foo'"],
    "Y123": ["foo", "fooDict", "bar", "default"],
    "Y124": ["foo", "bar"],
    # Python-specifics not part of flake8-simplify
    "Y181": ["foo += 42", "foo = foo + 42"],
    "Y182": ["super()"],
    # Comparations
    "Y201": ["foo", "bar"],
    "Y202": ["foo", "bar"],
    "Y203": ["foo", "bar"],
    "Y204": ["foo", "bar"],
    "Y205": ["foo", "bar"],
    "Y206": ["foo", "bar"],
    "Y207": ["foo", "bar"],
    "Y208": ["foo"],
    "Y211": ["foo", "bool(foo)"],
    "Y212": ["foo", "not foo"],
    "Y213": ["foo", "bar"],
    "Y221": ["foo"],
    "Y222": ["foo"],
    # Opinionated
    "Y301": ["42", "foo"],
    # General Code Style
    # Additional checks
    "Y901": ["foo == bar", "bool(foo == bar)"],
    "Y904": ["foo"],
    "Y905": [
        """["de", "com", "net", "org"]""",
        """domains = "de com net org".split()""",
    ],
    "Y906": ["os.path.join(a, b, c)", "os.path.join(a,os.path.join(b,c))"],
    "Y907": ["int", "Union[int, None]"],
    "Y909": ["foo = foo"],
    "Y911": ["foo"],
}
