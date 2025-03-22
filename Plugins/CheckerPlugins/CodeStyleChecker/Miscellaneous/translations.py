# -*- coding: utf-8 -*-

# Copyright (c) 2020 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#


"""
Module implementing message translations for the code style plugin messages
(miscellaneous part).
"""

from PyQt6.QtCore import QCoreApplication

_miscellaneousMessages = {
    ## Coding line
    "M101": QCoreApplication.translate(
        "MiscellaneousChecker",
        "coding magic comment not found",
    ),
    "M102": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unknown encoding ({0}) found in coding magic comment",
    ),
    ## Copyright
    "M111": QCoreApplication.translate(
        "MiscellaneousChecker",
        "copyright notice not present",
    ),
    "M112": QCoreApplication.translate(
        "MiscellaneousChecker",
        "copyright notice contains invalid author",
    ),
    ## Shadowed Builtins
    "M131": QCoreApplication.translate(
        "MiscellaneousChecker",
        '"{0}" is a Python builtin and is being shadowed; '
        "consider renaming the variable",
    ),
    "M132": QCoreApplication.translate(
        "MiscellaneousChecker",
        '"{0}" is used as an argument and thus shadows a '
        "Python builtin; consider renaming the argument",
    ),
    ## Comprehensions
    "M180": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary generator - rewrite as a list comprehension",
    ),
    "M181": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary generator - rewrite as a set comprehension",
    ),
    "M182": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary generator - rewrite as a dict comprehension",
    ),
    "M183": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary list comprehension - rewrite as a set comprehension",
    ),
    "M184": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary list comprehension - rewrite as a dict comprehension",
    ),
    "M185": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} literal - rewrite as a {1} literal",
    ),
    "M186": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} literal - rewrite as a {1} literal",
    ),
    "M188": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} call - rewrite as a literal",
    ),
    "M189a": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} passed to tuple() - remove the outer call to {1}()",
    ),
    "M189b": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} passed to tuple() - rewrite as a {1} literal",
    ),
    "M190a": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} passed to list() - remove the outer call to {1}()",
    ),
    "M190b": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} passed to list() - rewrite as a {1} literal",
    ),
    "M191": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary list call - remove the outer call to list()",
    ),
    "M193a": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} call around {1}() - toggle reverse argument to sorted()",
    ),
    "M193b": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} call around {1}() - use sorted(..., reverse={2!r})",
    ),
    "M193c": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} call around {1}()",
    ),
    "M194": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} call within {1}()",
    ),
    "M195": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary subscript reversal of iterable within {0}()",
    ),
    "M196": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} comprehension - rewrite using {0}()",
    ),
    "M197": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary use of map - use a {0} instead",
    ),
    "M198": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} passed to dict() - remove the outer call to dict()",
    ),
    "M199": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary list comprehension passed to {0}() prevents short-circuiting"
        " - rewrite as a generator",
    ),
    "M200": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unnecessary {0} comprehension - rewrite using dict.fromkeys()",
    ),
    ## Dictionaries with sorted keys
    "M251": QCoreApplication.translate(
        "MiscellaneousChecker",
        "sort keys - '{0}' should be before '{1}'",
    ),
    ## Property
    "M260": QCoreApplication.translate(
        "MiscellaneousChecker",
        "the number of arguments for property getter method is wrong"
        " (should be 1 instead of {0})",
    ),
    "M261": QCoreApplication.translate(
        "MiscellaneousChecker",
        "the number of arguments for property setter method is wrong"
        " (should be 2 instead of {0})",
    ),
    "M262": QCoreApplication.translate(
        "MiscellaneousChecker",
        "the number of arguments for property deleter method is wrong"
        " (should be 1 instead of {0})",
    ),
    "M263": QCoreApplication.translate(
        "MiscellaneousChecker",
        "the name of the setter method is wrong (should be '{0}' instead of '{1}')",
    ),
    "M264": QCoreApplication.translate(
        "MiscellaneousChecker",
        "the name of the deleter method is wrong (should be '{0}' instead of '{1}')",
    ),
    "M265": QCoreApplication.translate(
        "MiscellaneousChecker",
        "the name of the setter decorator is wrong (should be '{0}' instead of '{1}')",
    ),
    "M266": QCoreApplication.translate(
        "MiscellaneousChecker",
        "the name of the deleter decorator is wrong (should be '{0}' instead of '{1}')",
    ),
    "M267": QCoreApplication.translate(
        "MiscellaneousChecker",
        "multiple decorators were used to declare property '{0}'",
    ),
    ## Naive datetime usage
    "M301": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.datetime()' without 'tzinfo' argument should be avoided",
    ),
    "M302": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.datetime.today()' should be avoided.\n"
        "Use 'datetime.datetime.now(tz=)' instead.",
    ),
    "M303": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.datetime.utcnow()' should be avoided.\n"
        "Use 'datetime.datetime.now(tz=datetime.timezone.utc)' instead.",
    ),
    "M304": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.datetime.utcfromtimestamp()' should be avoided.\n"
        "Use 'datetime.datetime.fromtimestamp(..., tz=datetime.timezone.utc)' instead.",
    ),
    "M305": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.datetime.now()' without 'tz' argument should be avoided",
    ),
    "M306": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.datetime.fromtimestamp()' without 'tz' argument"
        " should be avoided",
    ),
    "M307": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.datetime.strptime()' should be followed by"
        " '.replace(tzinfo=)'",
    ),
    "M308": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.datetime.fromordinal()' should be avoided",
    ),
    "M311": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.date()' should be avoided.\n"
        "Use 'datetime.datetime(, tzinfo=).date()' instead.",
    ),
    "M312": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.date.today()' should be avoided.\n"
        "Use 'datetime.datetime.now(tz=).date()' instead.",
    ),
    "M313": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.date.fromtimestamp()' should be avoided.\n"
        "Use 'datetime.datetime.fromtimestamp(tz=).date()' instead.",
    ),
    "M314": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.date.fromordinal()' should be avoided",
    ),
    "M315": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.date.fromisoformat()' should be avoided",
    ),
    "M321": QCoreApplication.translate(
        "MiscellaneousChecker",
        "use of 'datetime.time()' without 'tzinfo' argument should be avoided",
    ),
    ## sys.version and sys.version_info usage
    "M401": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'sys.version[:3]' referenced (Python 3.10), use 'sys.version_info'",
    ),
    "M402": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'sys.version[2]' referenced (Python 3.10), use 'sys.version_info'",
    ),
    "M403": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'sys.version' compared to string (Python 3.10), use 'sys.version_info'",
    ),
    "M411": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'sys.version_info[0] == 3' referenced (Python 4), use '>='",
    ),
    "M412": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'six.PY3' referenced (Python 4), use 'not six.PY2'",
    ),
    "M413": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'sys.version_info[1]' compared to integer (Python 4),"
        " compare 'sys.version_info' to tuple",
    ),
    "M414": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'sys.version_info.minor' compared to integer (Python 4),"
        " compare 'sys.version_info' to tuple",
    ),
    "M421": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'sys.version[0]' referenced (Python 10), use 'sys.version_info'",
    ),
    "M422": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'sys.version' compared to string (Python 10), use 'sys.version_info'",
    ),
    "M423": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'sys.version[:1]' referenced (Python 10), use 'sys.version_info'",
    ),
    ## Bugbear
    "M501": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Do not use bare 'except:', it also catches unexpected events like memory"
        " errors, interrupts, system exit, and so on. Prefer excepting specific"
        " exceptions. If you're sure what you're doing, be explicit and write"
        " 'except BaseException:'.",
    ),
    "M502": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Python does not support the unary prefix increment",
    ),
    "M503": QCoreApplication.translate(
        "MiscellaneousChecker",
        "assigning to 'os.environ' does not clear the environment -"
        " use 'os.environ.clear()'",
    ),
    "M504": QCoreApplication.translate(
        "MiscellaneousChecker",
        """using 'hasattr(x, "__call__")' to test if 'x' is callable is"""
        """ unreliable. Use 'callable(x)' for consistent results.""",
    ),
    "M505": QCoreApplication.translate(
        "MiscellaneousChecker",
        "using .strip() with multi-character strings is misleading. Use .replace(),"
        " .removeprefix(), .removesuffix(), or regular expressions to remove string"
        " fragments.",
    ),
    "M506": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Do not use mutable data structures for argument defaults. They are created"
        " during function definition time. All calls to the function reuse this one"
        " instance of that data structure, persisting changes between them.",
    ),
    "M507": QCoreApplication.translate(
        "MiscellaneousChecker",
        "loop control variable {0} not used within the loop body -"
        " start the name with an underscore",
    ),
    "M508": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Do not perform function calls in argument defaults. The call is performed"
        " only once at function definition time. All calls to your function will reuse"
        " the result of that definition-time function call.  If this is intended,"
        " assign the function call to a module-level variable and use that variable as"
        " a default value.",
    ),
    "M509": QCoreApplication.translate(
        "MiscellaneousChecker",
        "do not call getattr with a constant attribute value",
    ),
    "M510": QCoreApplication.translate(
        "MiscellaneousChecker",
        "do not call setattr with a constant attribute value",
    ),
    "M511": QCoreApplication.translate(
        "MiscellaneousChecker",
        "do not call assert False since python -O removes these calls",
    ),
    "M512": QCoreApplication.translate(
        "MiscellaneousChecker",
        "return/continue/break inside finally blocks cause exceptions to be silenced."
        " Exceptions should be silenced in except blocks. Control statements can be"
        " moved outside the finally block.",
    ),
    "M513": QCoreApplication.translate(
        "MiscellaneousChecker",
        "A length-one tuple literal is redundant. Write 'except {0}:' instead of"
        " 'except ({0},):'.",
    ),
    "M514": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Redundant exception types in 'except ({0}){1}:'. Write 'except {2}{1}:',"
        " which catches exactly the same exceptions.",
    ),
    "M515": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Result of comparison is not used. This line doesn't do anything. Did you"
        " intend to prepend it with assert?",
    ),
    "M516": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Cannot raise a literal. Did you intend to return it or raise an Exception?",
    ),
    "M517": QCoreApplication.translate(
        "MiscellaneousChecker",
        "'assertRaises(Exception)' and 'pytest.raises(Exception)' should "
        "be considered evil. They can lead to your test passing even if the "
        "code being tested is never executed due to a typo. Assert for a more "
        "specific exception (builtin or custom), or use 'assertRaisesRegex' "
        "(if using 'assertRaises'), or add the 'match' keyword argument (if "
        "using 'pytest.raises'), or use the context manager form with a target.",
    ),
    "M518": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Found useless {0} expression. Consider either assigning it to a variable or"
        " removing it.",
    ),
    "M519": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Use of 'functools.lru_cache' or 'functools.cache' on methods can lead to"
        " memory leaks. The cache may retain instance references, preventing garbage"
        " collection.",
    ),
    "M520": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Found for loop that reassigns the iterable it is iterating with each"
        " iterable value.",
    ),
    "M521": QCoreApplication.translate(
        "MiscellaneousChecker",
        "f-string used as docstring. This will be interpreted by python as a joined"
        " string rather than a docstring.",
    ),
    "M522": QCoreApplication.translate(
        "MiscellaneousChecker",
        "No arguments passed to 'contextlib.suppress'. No exceptions will be"
        " suppressed and therefore this context manager is redundant.",
    ),
    "M523": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Function definition does not bind loop variable '{0}'.",
    ),
    "M524": QCoreApplication.translate(
        "MiscellaneousChecker",
        "{0} is an abstract base class, but none of the methods it defines are"
        " abstract. This is not necessarily an error, but you might have forgotten to"
        " add the @abstractmethod decorator, potentially in conjunction with"
        " @classmethod, @property and/or @staticmethod.",
    ),
    "M525": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Exception '{0}' has been caught multiple times. Only the first except will be"
        " considered and all other except catches can be safely removed.",
    ),
    "M526": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Star-arg unpacking after a keyword argument is strongly discouraged,"
        " because it only works when the keyword parameter is declared after all"
        " parameters supplied by the unpacked sequence, and this change of ordering can"
        " surprise and mislead readers.",
    ),
    "M527": QCoreApplication.translate(
        "MiscellaneousChecker",
        "{0} is an empty method in an abstract base class, but has no abstract"
        " decorator. Consider adding @abstractmethod.",
    ),
    "M528": QCoreApplication.translate(
        "MiscellaneousChecker",
        "No explicit stacklevel argument found. The warn method from the"
        " warnings module uses a stacklevel of 1 by default. This will only show a"
        " stack trace for the line on which the warn method is called."
        " It is therefore recommended to use a stacklevel of 2 or"
        " greater to provide more information to the user.",
    ),
    "M529": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Using 'except ():' with an empty tuple does not handle/catch "
        "anything. Add exceptions to handle.",
    ),
    "M530": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Except handlers should only be names of exception classes",
    ),
    "M531": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Using the generator returned from 'itertools.groupby()' more than once"
        " will do nothing on the second usage. Save the result to a list, if the"
        " result is needed multiple times.",
    ),
    "M532": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Possible unintentional type annotation (using ':'). Did you mean to"
        " assign (using '=')?",
    ),
    "M533": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Set should not contain duplicate item '{0}'. Duplicate items will be replaced"
        " with a single item at runtime.",
    ),
    "M534": QCoreApplication.translate(
        "MiscellaneousChecker",
        "re.{0} should get '{1}' and 'flags' passed as keyword arguments to avoid"
        " confusion due to unintuitive argument positions.",
    ),
    "M535": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Static key in dict comprehension: {0!r}.",
    ),
    "M536": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Don't except 'BaseException' unless you plan to re-raise it.",
    ),
    "M537": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Class '__init__' methods must not return or yield and any values.",
    ),
    "M539": QCoreApplication.translate(
        "MiscellaneousChecker",
        "ContextVar with mutable literal or function call as default. This is only"
        " evaluated once, and all subsequent calls to `.get()` will return the same"
        " instance of the default.",
    ),
    "M540": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Exception with added note not used. Did you forget to raise it?",
    ),
    ## Bugbear, opininonated
    "M569": QCoreApplication.translate(
        "MiscellaneousChecker",
        "Editing a loop's mutable iterable often leads to unexpected results/bugs.",
    ),
    ## Bugbear++
    "M581": QCoreApplication.translate(
        "MiscellaneousChecker",
        "unncessary f-string",
    ),
    "M582": QCoreApplication.translate(
        "MiscellaneousChecker",
        "cannot use 'self.__class__' as first argument of 'super()' call",
    ),
    ## Format Strings
    "M601": QCoreApplication.translate(
        "MiscellaneousChecker",
        "found {0} formatter",
    ),
    "M611": QCoreApplication.translate(
        "MiscellaneousChecker",
        "format string does contain unindexed parameters",
    ),
    "M612": QCoreApplication.translate(
        "MiscellaneousChecker",
        "docstring does contain unindexed parameters",
    ),
    "M613": QCoreApplication.translate(
        "MiscellaneousChecker",
        "other string does contain unindexed parameters",
    ),
    "M621": QCoreApplication.translate(
        "MiscellaneousChecker",
        "format call uses too large index ({0})",
    ),
    "M622": QCoreApplication.translate(
        "MiscellaneousChecker",
        "format call uses missing keyword ({0})",
    ),
    "M623": QCoreApplication.translate(
        "MiscellaneousChecker",
        "format call uses keyword arguments but no named entries",
    ),
    "M624": QCoreApplication.translate(
        "MiscellaneousChecker",
        "format call uses variable arguments but no numbered entries",
    ),
    "M625": QCoreApplication.translate(
        "MiscellaneousChecker",
        "format call uses implicit and explicit indexes together",
    ),
    "M631": QCoreApplication.translate(
        "MiscellaneousChecker",
        "format call provides unused index ({0})",
    ),
    "M632": QCoreApplication.translate(
        "MiscellaneousChecker",
        "format call provides unused keyword ({0})",
    ),
    ## Future statements
    "M701": QCoreApplication.translate(
        "MiscellaneousChecker",
        "expected these __future__ imports: {0}; but only got: {1}",
    ),
    "M702": QCoreApplication.translate(
        "MiscellaneousChecker",
        "expected these __future__ imports: {0}; but got none",
    ),
    ## Gettext
    "M711": QCoreApplication.translate(
        "MiscellaneousChecker",
        "gettext import with alias _ found: {0}",
    ),
    ##~ print() statements
    "M801": QCoreApplication.translate(
        "MiscellaneousChecker",
        "print statement found",
    ),
    ## one element tuple
    "M811": QCoreApplication.translate(
        "MiscellaneousChecker",
        "one element tuple found",
    ),
    ## Mutable Defaults
    "M821": QCoreApplication.translate(
        "MiscellaneousChecker",
        "mutable default argument of type {0}",
    ),
    "M822": QCoreApplication.translate(
        "MiscellaneousChecker",
        "mutable default argument of type {0}",
    ),
    "M823": QCoreApplication.translate(
        "MiscellaneousChecker",
        "mutable default argument of function call '{0}'",
    ),
    ##~ return statements
    "M831": QCoreApplication.translate(
        "MiscellaneousChecker",
        "None should not be added at any return if function has no return"
        " value except None",
    ),
    "M832": QCoreApplication.translate(
        "MiscellaneousChecker",
        "an explicit value at every return should be added if function has"
        " a return value except None",
    ),
    "M833": QCoreApplication.translate(
        "MiscellaneousChecker",
        "an explicit return at the end of the function should be added if"
        " it has a return value except None",
    ),
    "M834": QCoreApplication.translate(
        "MiscellaneousChecker",
        "a value should not be assigned to a variable if it will be used as a"
        " return value only",
    ),
    ## line continuation
    "M841": QCoreApplication.translate(
        "MiscellaneousChecker",
        "prefer implied line continuation inside parentheses, "
        "brackets and braces as opposed to a backslash",
    ),
    ## implicitly concatenated strings
    "M851": QCoreApplication.translate(
        "MiscellaneousChecker",
        "implicitly concatenated string or bytes literals on one line",
    ),
    "M852": QCoreApplication.translate(
        "MiscellaneousChecker",
        "implicitly concatenated string or bytes literals over continuation line",
    ),
    "M853": QCoreApplication.translate(
        "MiscellaneousChecker",
        "explicitly concatenated string or bytes should be implicitly concatenated",
    ),
    ## commented code
    "M891": QCoreApplication.translate(
        "MiscellaneousChecker",
        "commented code lines should be removed",
    ),
}

_miscellaneousMessagesSampleArgs = {
    ## Coding line
    "M102": ["enc42"],
    ## Shadowed Builtins
    "M131": ["list"],
    "M132": ["list"],
    ## Comprehensions
    "M185": ["list", "set"],
    "M186": ["list", "dict"],
    "M188": ["list"],
    "M189a": ["tuple", "tuple"],
    "M189b": ["list", "tuple"],
    "M190a": ["list", "list"],
    "M190b": ["tuple", "list"],
    "M193a": ["reversed", "sorted"],
    "M193b": ["reversed", "sorted", "True"],
    "M193c": ["list", "sorted"],
    "M194": ["list", "sorted"],
    "M195": ["sorted"],
    "M196": ["list"],
    "M197": ["list"],
    "M198": ["dict comprehension"],
    "M199": ["any"],
    "M200": ["dict"],
    ## Dictionaries with sorted keys
    "M251": ["bar", "foo"],
    ## Property
    "M260": [2],
    "M261": [1],
    "M262": [2],
    "M263": ["foo", "bar"],
    "M264": ["foo", "bar"],
    "M265": ["foo", "bar"],
    "M266": ["foo", "bar"],
    "M267": ["foo"],
    ## Bugbear
    "M507": ["x"],
    "M513": ["Exception"],
    "M514": ["OSError, IOError", " as err", "OSError"],
    "M518": ["List"],
    "M523": ["x"],
    "M524": ["foobar"],
    "M525": ["OSError"],
    "M527": ["foo"],
    "M533": ["foo"],
    "M534": ["split", "maxsplit"],
    "M535": ["foo"],
    ## Format Strings
    "M601": ["%s"],
    "M621": [5],
    "M622": ["foo"],
    "M631": [5],
    "M632": ["foo"],
    ## Future statements
    "M701": ["print_function, unicode_literals", "print_function"],
    "M702": ["print_function, unicode_literals"],
    ## Gettext
    "M711": ["lgettext"],
    ## Mutable Defaults
    "M821": ["Dict"],
    "M822": ["Call"],
    "M823": ["dict"],
}
