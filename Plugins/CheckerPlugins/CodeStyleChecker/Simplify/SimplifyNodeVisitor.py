# -*- coding: utf-8 -*-

# Copyright (c) 2021 - 2025 Detlev Offenbach <detlev@die-offenbachs.de>
#

"""
Module implementing a node visitor checking for code that could be simplified.
"""

import ast
import collections
import copy
import itertools
import json

try:
    from ast import unparse
except ImportError:
    # Python < 3.9
    from ast_unparse import unparse

import AstUtilities

###############################################################################
## adapted from: flake8-simplify v0.21.0
##
## Original License:
##
## MIT License
##
## Copyright (c) 2020 Martin Thoma
##
## Permission is hereby granted, free of charge, to any person obtaining a copy
## of this software and associated documentation files (the "Software"), to
## deal in the Software without restriction, including without limitation the
## rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
## sell copies of the Software, and to permit persons to whom the Software is
## furnished to do so, subject to the following conditions:
##
## The above copyright notice and this permission notice shall be included in
## all copies or substantial portions of the Software.
##
## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
## IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
## FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
## AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
## LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
## FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
## IN THE SOFTWARE.
###############################################################################


class SimplifyNodeVisitor(ast.NodeVisitor):
    """
    Class to traverse the AST node tree and check for code that can be
    simplified.
    """

    def __init__(self, errorCallback):
        """
        Constructor

        @param errorCallback callback function to register an error
        @type func
        """
        super().__init__()

        self.__error = errorCallback

        self.__classDefinitionStack = []

    def visit_Expr(self, node):
        """
        Public method to process an Expr node.

        @param node reference to the Expr node
        @type ast.Expr
        """
        self.__check112(node)

        self.generic_visit(node)

    def visit_Assign(self, node):
        """
        Public method to process an Assign node.

        @param node reference to the Assign node
        @type ast.Assign
        """
        self.__check181(node)
        self.__check904(node)
        self.__check909(node)

        self.generic_visit(node)

    def visit_BoolOp(self, node):
        """
        Public method to process a BoolOp node.

        @param node reference to the BoolOp node
        @type ast.BoolOp
        """
        self.__check101(node)
        self.__check109(node)
        self.__check221(node)
        self.__check222(node)
        self.__check223(node)
        self.__check224(node)

        self.generic_visit(node)

    def visit_If(self, node):
        """
        Public method to process an If node.

        @param node reference to the If node
        @type ast.If
        """
        self.__check102(node)
        self.__check103(node)
        self.__check106(node)
        self.__check108(node)
        self.__check114(node)
        self.__check116(node)
        self.__check122(node)
        self.__check123(node)

        self.generic_visit(node)

    def visit_IfExp(self, node):
        """
        Public method to process an IfExp node.

        @param node reference to the IfExp node
        @type ast.IfExp
        """
        self.__check211(node)
        self.__check212(node)
        self.__check213(node)

        self.generic_visit(node)

    def visit_For(self, node):
        """
        Public method to process a For node.

        @param node reference to the For node
        @type ast.For
        """
        self.__check104(node)
        self.__check110_111(node)
        self.__check113(node)
        self.__check118(node)

        self.generic_visit(node)

    def visit_Try(self, node):
        """
        Public method to process a Try node.

        @param node reference to the Try node
        @type ast.Try
        """
        self.__check105(node)
        self.__check107(node)

        self.generic_visit(node)

    def visit_Call(self, node):
        """
        Public method to process a Call node.

        @param node reference to the Call node
        @type ast.Call
        """
        self.__check115(node)
        self.__check182(node)
        self.__check401(node)
        self.__check402(node)
        self.__check901(node)
        self.__check905(node)
        self.__check906(node)
        self.__check910(node)
        self.__check911(node)

        self.generic_visit(node)

    def visit_With(self, node):
        """
        Public method to process a With node.

        @param node reference to the With node
        @type ast.With
        """
        self.__check117(node)

        self.generic_visit(node)

    def visit_Compare(self, node):
        """
        Public method to process a Compare node.

        @param node reference to the Compare node
        @type ast.Compare
        """
        self.__check118(node)
        self.__check301(node)

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        """
        Public method to process a ClassDef node.

        @param node reference to the ClassDef node
        @type ast.ClassDef
        """
        # register the name of the class being defined
        self.__classDefinitionStack.append(node.name)

        self.__check119(node)
        self.__check120_121(node)

        self.generic_visit(node)

        self.__classDefinitionStack.pop()

    def visit_UnaryOp(self, node):
        """
        Public method to process a UnaryOp node.

        @param node reference to the UnaryOp node
        @type ast.UnaryOp
        """
        self.__check201(node)
        self.__check202(node)
        self.__check203(node)
        self.__check204(node)
        self.__check205(node)
        self.__check206(node)
        self.__check207(node)
        self.__check208(node)

        self.generic_visit(node)

    def visit_Subscript(self, node):
        """
        Public method to process a Subscript node.

        @param node reference to the Subscript node
        @type ast.Subscript
        """
        self.__check907(node)

        self.generic_visit(node)

    #############################################################
    ## Helper methods for the various checkers below
    #############################################################

    def __getDuplicatedIsinstanceCall(self, node):
        """
        Private method to get a list of isinstance arguments which could
        be combined.

        @param node reference to the AST node to be inspected
        @type ast.BoolOp
        @return list of variable names of duplicated isinstance calls
        @rtype list of str
        """
        counter = collections.defaultdict(int)

        for call in node.values:
            # Ensure this is a call of the built-in isinstance() function.
            if not isinstance(call, ast.Call) or len(call.args) != 2:
                continue
            functionName = unparse(call.func)
            if functionName != "isinstance":
                continue

            arg0Name = unparse(call.args[0])
            counter[arg0Name] += 1

        return [name for name, count in counter.items() if count > 1]

    def __isConstantIncrease(self, expr):
        """
        Private method to check an expression for being a constant increase.

        @param expr reference to the node to be checked
        @type ast.AugAssign
        @return flag indicating a constant increase
        @rtype bool
        """
        return isinstance(expr.op, ast.Add) and (
            (isinstance(expr.value, ast.Constant) and expr.value.value == 1)
        )

    def __getIfBodyPairs(self, node):
        """
        Private method to extract a list of pairs of test and body for an
        If node.

        @param node reference to the If node to be processed
        @type ast.If
        @return list of pairs of test and body
        @rtype list of tuples of (ast.expr, [ast.stmt])
        """
        pairs = [(node.test, node.body)]
        orelse = node.orelse
        while (
            isinstance(orelse, list)
            and len(orelse) == 1
            and isinstance(orelse[0], ast.If)
        ):
            pairs.append((orelse[0].test, orelse[0].body))
            orelse = orelse[0].orelse
        return pairs

    def __isSameBody(self, body1, body2):
        """
        Private method check, if the given bodies are equivalent.

        @param body1 list of statements of the first body
        @type list of ast.stmt
        @param body2 list of statements of the second body
        @type list of ast.stmt
        @return flag indicating identical bodies
        @rtype bool
        """
        if len(body1) != len(body2):
            return False
        for a, b in zip(body1, body2):
            try:
                statementEqual = self.__isStatementEqual(a, b)
            except RecursionError:  # maximum recursion depth
                statementEqual = False
            if not statementEqual:
                return False

        return True

    def __isSameExpression(self, a, b):
        """
        Private method to check, if two expressions are equal.

        @param a first expression to be checked
        @type ast.expr
        @param b second expression to be checked
        @type ast.expr
        @return flag indicating equal expressions
        @rtype bool
        """
        if isinstance(a, ast.Name) and isinstance(b, ast.Name):
            return a.id == b.id
        else:
            return False

    def __isStatementEqual(self, a, b):
        """
        Private method to check, if two statements are equal.

        @param a reference to the first statement
        @type ast.stmt
        @param b reference to the second statement
        @type ast.stmt
        @return flag indicating if the two statements are equal
        @rtype bool
        """
        if type(a) is not type(b):
            return False

        if isinstance(a, ast.AST):
            for k, v in vars(a).items():
                if k in ("lineno", "col_offset", "ctx", "end_lineno", "parent"):
                    continue
                if not self.__isStatementEqual(v, getattr(b, k)):
                    return False
            return True
        elif isinstance(a, list):
            return all(itertools.starmap(self.__isStatementEqual, zip(a, b)))
        else:
            return a == b

    def __isExceptionCheck(self, node):
        """
        Private method to check, if the node is checking an exception.

        @param node reference to the node to be checked
        @type ast.If
        @return flag indicating an exception check
        @rtype bool
        """
        return len(node.body) == 1 and isinstance(node.body[0], ast.Raise)

    def __negateTest(self, node):
        """
        Private method negate the given Compare node.

        @param node reference to the node to be negated
        @type ast.Compare
        @return node with negated logic
        @rtype ast.Compare
        """
        newNode = copy.deepcopy(node)
        op = newNode.ops[0]
        if isinstance(op, ast.Eq):
            op = ast.NotEq()
        elif isinstance(op, ast.NotEq):
            op = ast.Eq()
        elif isinstance(op, ast.Lt):
            op = ast.GtE()
        elif isinstance(op, ast.LtE):
            op = ast.Gt()
        elif isinstance(op, ast.Gt):
            op = ast.LtE()
        elif isinstance(op, ast.GtE):
            op = ast.Lt()
        elif isinstance(op, ast.Is):
            op = ast.IsNot()
        elif isinstance(op, ast.IsNot):
            op = ast.Is()
        elif isinstance(op, ast.In):
            op = ast.NotIn()
        elif isinstance(op, ast.NotIn):
            op = ast.In()
        newNode.ops = [op]
        return newNode

    def __expressionUsesVariable(self, expr, var):
        """
        Private method to check, if a variable is used by an expression.

        @param expr expression node to be checked
        @type ast.expr
        @param var variable name to be checked for
        @type str
        @return flag indicating the expression uses the variable
        @rtype bool
        """
        return var in unparse(expr)
        # This is WAY too broad, but it's better to have false-negatives than
        # false-positives.

    def __bodyContainsContinue(self, stmts):
        """
        Private method to check, if a list of statements contain a 'continue' statement.

        @param stmts list of statements
        @type list of ast.stmt
        @return flag indicating a continue statement
        @rtype bool
        """
        return any(
            isinstance(stmt, ast.Continue)
            or (isinstance(stmt, ast.If) and self.__bodyContainsContinue(stmt.body))
            for stmt in stmts
        )

    #############################################################
    ## Methods to check for possible code simplifications below
    #############################################################

    def __check101(self, node):
        """
        Private method to check for duplicate isinstance() calls.

        @param node reference to the AST node to be checked
        @type ast.BoolOp
        """
        if isinstance(node.op, ast.Or):
            for variable in self.__getDuplicatedIsinstanceCall(node):
                self.__error(node.lineno - 1, node.col_offset, "Y101", variable)

    def __check102(self, node):
        """
        Private method to check for nested if statements without else blocks.

        @param node reference to the AST node to be checked
        @type ast.If
        """
        # Don't treat 'if __name__ == "__main__":' as an issue.
        if (
            isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and node.test.left.id == "__name__"
            and isinstance(node.test.ops[0], ast.Eq)
            and isinstance(node.test.comparators[0], ast.Constant)
            and node.test.comparators[0].value == "__main__"
        ):
            return

        # ## Pattern 1
        # if a: <---
        #     if b: <---
        #         c
        isPattern1 = (
            node.orelse == []
            and len(node.body) == 1
            and isinstance(node.body[0], ast.If)
            and node.body[0].orelse == []
        )
        # ## Pattern 2
        # if a: < irrelevant for here
        #     pass
        # elif b:  <--- this is treated like a nested block
        #     if c: <---
        #         d
        if isPattern1:
            self.__error(node.lineno - 1, node.col_offset, "Y102")

    def __check103(self, node):
        """
        Private method to check for calls that wrap a condition to return
        a bool.

        @param node reference to the AST node to be checked
        @type ast.If
        """
        # if cond:
        #     return True
        # else:
        #     return False
        if not (
            len(node.body) != 1
            or not isinstance(node.body[0], ast.Return)
            or not isinstance(node.body[0].value, ast.Constant)
            or not (
                node.body[0].value.value is True or node.body[0].value.value is False
            )
            or len(node.orelse) != 1
            or not isinstance(node.orelse[0], ast.Return)
            or not isinstance(node.orelse[0].value, ast.Constant)
            or not (
                node.orelse[0].value.value is True
                or node.orelse[0].value.value is False
            )
        ):
            condition = unparse(node.test)
            self.__error(node.lineno - 1, node.col_offset, "Y103", condition)

    def __check104(self, node):
        """
        Private method to check for "iterate and yield" patterns.

        @param node reference to the AST node to be checked
        @type ast.For
        """
        # for item in iterable:
        #     yield item
        if not (
            len(node.body) != 1
            or not isinstance(node.body[0], ast.Expr)
            or not isinstance(node.body[0].value, ast.Yield)
            or not isinstance(node.target, ast.Name)
            or not isinstance(node.body[0].value.value, ast.Name)
            or node.target.id != node.body[0].value.value.id
            or node.orelse != []
        ):
            parent = getattr(node, "parent", None)
            while (
                parent
                and hasattr(parent, "parent")
                and parent.parent is not parent
                and not isinstance(parent, ast.AsyncFunctionDef)
            ):
                parent = getattr(parent, "parent", None)

            if not isinstance(parent, ast.AsyncFunctionDef):
                iterable = unparse(node.iter)
                self.__error(node.lineno - 1, node.col_offset, "Y104", iterable)

    def __check105(self, node):
        """
        Private method to check for "try-except-pass" patterns.

        @param node reference to the AST node to be checked
        @type ast.Try
        """
        # try:
        #     foo()
        # except ValueError:
        #     pass
        if not (
            len(node.handlers) != 1
            or not isinstance(node.handlers[0], ast.ExceptHandler)
            or len(node.handlers[0].body) != 1
            or not isinstance(node.handlers[0].body[0], ast.Pass)
            or node.orelse != []
        ):
            if node.handlers[0].type is None:
                exception = "Exception"
            elif isinstance(node.handlers[0].type, ast.Tuple):
                exception = ", ".join([unparse(n) for n in node.handlers[0].type.elts])
            else:
                exception = unparse(node.handlers[0].type)
            self.__error(node.lineno - 1, node.col_offset, "Y105", exception)

    def __check106(self, node):
        """
        Private method to check for calls where an exception is raised in else.

        @param node reference to the AST node to be checked
        @type ast.If
        """
        # if cond:
        #     return True
        # else:
        #     raise Exception
        just_one = (
            len(node.body) == 1
            and len(node.orelse) >= 1
            and isinstance(node.orelse[-1], ast.Raise)
            and not isinstance(node.body[-1], ast.Raise)
        )
        many = (
            len(node.body) > 2 * len(node.orelse)
            and len(node.orelse) >= 1
            and isinstance(node.orelse[-1], ast.Raise)
            and not isinstance(node.body[-1], ast.Raise)
        )
        if just_one or many:
            self.__error(node.lineno - 1, node.col_offset, "Y106")

    def __check107(self, node):
        """
        Private method to check for calls where try/except and finally have
        'return'.

        @param node reference to the AST node to be checked
        @type ast.Try
        """
        # def foo():
        #     try:
        #         1 / 0
        #         return "1"
        #     except:
        #         return "2"
        #     finally:
        #         return "3"
        tryHasReturn = False
        for stmt in node.body:
            if isinstance(stmt, ast.Return):
                tryHasReturn = True
                break

        exceptHasReturn = False
        for stmt2 in node.handlers:
            if isinstance(stmt2, ast.Return):
                exceptHasReturn = True
                break

        finallyHasReturn = False
        finallyReturn = None
        for stmt in node.finalbody:
            if isinstance(stmt, ast.Return):
                finallyHasReturn = True
                finallyReturn = stmt
                break

        if (tryHasReturn or exceptHasReturn) and finallyHasReturn:
            self.__error(finallyReturn.lineno - 1, finallyReturn.col_offset, "Y107")

    def __check108(self, node):
        """
        Private method to check for if-elses which could be a ternary
        operator assignment.

        @param node reference to the AST node to be checked
        @type ast.If
        """
        # if a:
        #     b = c
        # else:
        #     b = d
        #
        # but not:
        # if a:
        #     b = c
        # elif c:
        #     b = e
        # else:
        #     b = d
        if (
            len(node.body) == 1
            and len(node.orelse) == 1
            and isinstance(node.body[0], ast.Assign)
            and isinstance(node.orelse[0], ast.Assign)
            and len(node.body[0].targets) == 1
            and len(node.orelse[0].targets) == 1
            and isinstance(node.body[0].targets[0], ast.Name)
            and isinstance(node.orelse[0].targets[0], ast.Name)
            and node.body[0].targets[0].id == node.orelse[0].targets[0].id
            and not isinstance(node.parent, ast.If)
        ):
            targetVar = node.body[0].targets[0]
            assign = unparse(targetVar)

            # It's part of a bigger if-elseif block:
            if isinstance(node.parent, ast.If):
                for n in node.parent.body:
                    if (
                        isinstance(n, ast.Assign)
                        and isinstance(n.targets[0], ast.Name)
                        and n.targets[0].id == targetVar.id
                    ):
                        return

            body = unparse(node.body[0].value)
            cond = unparse(node.test)
            orelse = unparse(node.orelse[0].value)

            self.__error(
                node.lineno - 1, node.col_offset, "Y108", assign, body, cond, orelse
            )

    def __check109(self, node):
        """
        Private method to check for multiple equalities with the same value
        are combined via "or".

        @param node reference to the AST node to be checked
        @type ast.BoolOp
        """
        # if a == b or a == c:
        #     d
        if isinstance(node.op, ast.Or):
            equalities = [
                value
                for value in node.values
                if isinstance(value, ast.Compare)
                and len(value.ops) == 1
                and isinstance(value.ops[0], ast.Eq)
            ]
            ids = []  # (name, compared_to)
            for eq in equalities:
                if isinstance(eq.left, ast.Name):
                    ids.append((eq.left, eq.comparators[0]))
                if len(eq.comparators) == 1 and isinstance(eq.comparators[0], ast.Name):
                    ids.append((eq.comparators[0], eq.left))

            id2count = {}
            for identifier, comparedTo in ids:
                if identifier.id not in id2count:
                    id2count[identifier.id] = []
                id2count[identifier.id].append(comparedTo)
            for value, values in id2count.items():
                if len(values) == 1:
                    continue

                self.__error(
                    node.lineno - 1,
                    node.col_offset,
                    "Y109",
                    value,
                    unparse(ast.Tuple(elts=values)),
                    unparse(node),
                )

    def __check110_111(self, node):
        """
        Private method to check if any / all could be used.

        @param node reference to the AST node to be checked
        @type ast.For
        """
        # for x in iterable:
        #     if check(x):
        #         return True
        # return False
        #
        # for x in iterable:
        #     if check(x):
        #         return False
        # return True
        if (
            len(node.body) == 1
            and isinstance(node.body[0], ast.If)
            and len(node.body[0].body) == 1
            and isinstance(node.body[0].body[0], ast.Return)
            and isinstance(node.body[0].body[0].value, ast.Constant)
            and hasattr(node.body[0].body[0].value, "value")
            and isinstance(node.next_sibling, ast.Return)
        ):
            check = unparse(node.body[0].test)
            target = unparse(node.target)
            iterable = unparse(node.iter)
            if node.body[0].body[0].value.value is True:
                self.__error(
                    node.lineno - 1, node.col_offset, "Y110", check, target, iterable
                )
            elif node.body[0].body[0].value.value is False:
                isCompoundExpression = " and " in check or " or " in check

                if isCompoundExpression:
                    check = f"not ({check})"
                else:
                    if check.startswith("not "):
                        check = check[len("not ") :]
                    else:
                        check = f"not {check}"
                self.__error(
                    node.lineno - 1, node.col_offset, "Y111", check, target, iterable
                )

    def __check112(self, node):
        """
        Private method to check for non-capitalized calls to environment
        variables.

        @param node reference to the AST node to be checked
        @type ast.Expr
        """
        # os.environ["foo"]
        # os.environ.get("bar")
        isIndexCall = (
            isinstance(node.value, ast.Subscript)
            and isinstance(node.value.value, ast.Attribute)
            and isinstance(node.value.value.value, ast.Name)
            and node.value.value.value.id == "os"
            and node.value.value.attr == "environ"
            and (
                (
                    isinstance(node.value.slice, ast.Index)
                    and isinstance(node.value.slice.value, ast.Constant)
                )
                or isinstance(node.value.slice, ast.Constant)
            )
        )
        if isIndexCall:
            subscript = node.value
            slice_ = subscript.slice
            if isinstance(slice_, ast.Index):
                # Python < 3.9
                stringPart = slice_.value  # type: ignore
                envName = stringPart.value
            elif isinstance(slice_, ast.Constant):
                # Python 3.9
                envName = slice_.value

            # Check if this has a change
            hasChange = envName != envName.upper()

        isGetCall = (
            isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and isinstance(node.value.func.value, ast.Attribute)
            and isinstance(node.value.func.value.value, ast.Name)
            and node.value.func.value.value.id == "os"
            and node.value.func.value.attr == "environ"
            and node.value.func.attr == "get"
            and len(node.value.args) in [1, 2]
            and isinstance(node.value.args[0], ast.Constant)
        )
        if isGetCall:
            call = node.value
            stringPart = call.args[0]
            envName = stringPart.value
            # Check if this has a change
            hasChange = envName != envName.upper()
        if not (isIndexCall or isGetCall) or not hasChange:
            return
        if isIndexCall:
            original = unparse(node)
            expected = f"os.environ['{envName.upper()}']"
        elif isGetCall:
            original = unparse(node)
            if len(node.value.args) == 1:
                expected = f"os.environ.get('{envName.upper()}')"
            else:
                defaultValue = unparse(node.value.args[1])
                expected = f"os.environ.get('{envName.upper()}', '{defaultValue}')"
        else:
            return

        self.__error(node.lineno - 1, node.col_offset, "Y112", expected, original)

    def __check113(self, node):
        """
        Private method to check for loops in which "enumerate" should be
        used.

        @param node reference to the AST node to be checked
        @type ast.For
        """
        # idx = 0
        # for el in iterable:
        #     ...
        #     idx += 1
        if not self.__bodyContainsContinue(node.body):
            # Find variables that might just count the iteration of the current loop
            variableCandidates = []
            for expression in node.body:
                if (
                    isinstance(expression, ast.AugAssign)
                    and self.__isConstantIncrease(expression)
                    and isinstance(expression.target, ast.Name)
                ):
                    variableCandidates.append(expression.target)
            strCandidates = [unparse(x) for x in variableCandidates]

            olderSiblings = []
            for olderSibling in node.parent.body:
                if olderSibling is node:
                    break
                olderSiblings.append(olderSibling)

            matches = [
                n.targets[0]
                for n in olderSiblings
                if isinstance(n, ast.Assign)
                and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and unparse(n.targets[0]) in strCandidates
            ]
            if len(matches) == 0:
                return

            sibling = node.previous_sibling
            while sibling is not None:
                sibling = sibling.previous_sibling

            for match in matches:
                variable = unparse(match)
                self.__error(match.lineno - 1, match.col_offset, "Y113", variable)

    def __check114(self, node):
        """
        Private method to check for alternative if clauses with identical
        bodies.

        @param node reference to the AST node to be checked
        @type ast.If
        """
        # if a:
        #     b
        # elif c:
        #     b
        ifBodyPairs = self.__getIfBodyPairs(node)
        errorPairs = []
        for i in range(len(ifBodyPairs) - 1):
            # It's not all combinations because of this:
            ifbody1 = ifBodyPairs[i]
            ifbody2 = ifBodyPairs[i + 1]
            if self.__isSameBody(ifbody1[1], ifbody2[1]):
                errorPairs.append((ifbody1, ifbody2))
        for ifbody1, ifbody2 in errorPairs:
            self.__error(
                ifbody1[0].lineno - 1,
                ifbody1[0].col_offset,
                "Y114",
                unparse(ifbody1[0]),
                unparse(ifbody2[0]),
            )

    def __check115(self, node):
        """
        Private method to to check for places where open() is called without
        a context handler.

        @param node reference to the AST node to be checked
        @type ast.Call
        """
        # f = open(...)
        # . ..  # (do something with f)
        # f.close()
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "open"
            and not isinstance(node.parent, ast.withitem)
        ):
            self.__error(node.lineno - 1, node.col_offset, "Y115")

    def __check116(self, node):
        """
        Private method to check for places with 3 or more consecutive
        if-statements with direct returns.

        * Each if-statement must be a check for equality with the
          same variable
        * Each if-statement must just have a "return"
        * Else must also just have a return

        @param node reference to the AST node to be checked
        @type ast.If
        """
        # if a == "foo":
        #     return "bar"
        # elif a == "bar":
        #     return "baz"
        # elif a == "boo":
        #     return "ooh"
        # else:
        #    return 42
        if (
            isinstance(node.test, ast.Compare)
            and isinstance(node.test.left, ast.Name)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.Eq)
            and len(node.test.comparators) == 1
            and isinstance(node.test.comparators[0], ast.Constant)
            and len(node.body) == 1
            and isinstance(node.body[0], ast.Return)
            and len(node.orelse) == 1
            and isinstance(node.orelse[0], ast.If)
        ):
            variable = node.test.left
            child = node.orelse[0]
            elseValue = None
            if node.body[0].value is not None:
                bodyValueStr = unparse(node.body[0].value).strip("'")
            else:
                bodyValueStr = "None"
            if AstUtilities.isString(node.test.comparators[0]):
                value = (
                    bodyValueStr
                    if bodyValueStr[0] == '"' and bodyValueStr[-1] == '"'
                    else bodyValueStr[1:-1]
                )
                keyValuePairs = {node.test.comparators[0].s: value}
            else:
                keyValuePairs = {node.test.comparators[0].value: bodyValueStr}
            while child:
                if not (
                    isinstance(child.test, ast.Compare)
                    and isinstance(child.test.left, ast.Name)
                    and child.test.left.id == variable.id
                    and len(child.test.ops) == 1
                    and isinstance(child.test.ops[0], ast.Eq)
                    and len(child.test.comparators) == 1
                    and isinstance(child.test.comparators[0], ast.Constant)
                    and len(child.body) == 1
                    and isinstance(child.body[0], ast.Return)
                    and len(child.orelse) <= 1
                ):
                    return

                returnCall = child.body[0]
                if isinstance(returnCall.value, ast.Call):
                    return

                key = child.test.comparators[0].value

                value = unparse(child.body[0].value)
                if value[0] == '"' and value[-1] == '"':
                    value = value[1:-1]
                keyValuePairs[key] = value

                if len(child.orelse) == 1:
                    if isinstance(child.orelse[0], ast.If):
                        child = child.orelse[0]
                    elif isinstance(child.orelse[0], ast.Return):
                        elseValue = unparse(child.orelse[0].value)
                        child = None
                    else:
                        return
                else:
                    child = None

            if len(keyValuePairs) < 3:
                return

            if elseValue:
                ret = f"{keyValuePairs}.get({variable.id}, {elseValue})"
            else:
                ret = f"{keyValuePairs}.get({variable.id})"

            self.__error(node.lineno - 1, node.col_offset, "Y116", ret)

    def __check117(self, node):
        """
        Private method to check for multiple with-statements with same scope.

        @param node reference to the AST node to be checked
        @type ast.With
        """
        # with A() as a:
        #     with B() as b:
        #         print("hello")
        if len(node.body) == 1 and isinstance(node.body[0], ast.With):
            withItems = []
            for withitem in node.items + node.body[0].items:
                withItems.append(f"{unparse(withitem)}")
            mergedWith = f"with {', '.join(withItems)}:"
            self.__error(node.lineno - 1, node.col_offset, "Y117", mergedWith)

    def __check118(self, node):
        """
        Private method to check for usages of "key in dict.keys()".

        @param node reference to the AST node to be checked
        @type ast.Compare or ast.For
        """
        # Pattern 1:
        #
        # if key in dict.keys():
        #     # do something
        #
        # Pattern 2:
        #
        # for key in dict.keys():
        #     # do something
        if (
            isinstance(node, ast.Compare)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.In)
            and len(node.comparators) == 1
        ):
            callNode = node.comparators[0]
        elif isinstance(node, ast.For):
            callNode = node.iter
        else:
            callNode = None

        if not isinstance(callNode, ast.Call):
            return

        attrNode = callNode.func
        if (
            isinstance(callNode.func, ast.Attribute)
            and callNode.func.attr == "keys"
            and isinstance(callNode.func.ctx, ast.Load)
        ):
            if isinstance(node, ast.Compare):
                keyStr = unparse(node.left)
            else:
                keyStr = unparse(node.target)
            dictStr = unparse(attrNode.value)
            self.__error(node.lineno - 1, node.col_offset, "Y118", keyStr, dictStr)

    def __check119(self, node):
        """
        Private method to check for classes that should be "dataclasses".

        @param node reference to the AST node to be checked
        @type ast.ClassDef
        """
        if len(node.decorator_list) == 0 and len(node.bases) == 0:
            dataclassFunctions = [
                "__init__",
                "__eq__",
                "__hash__",
                "__repr__",
                "__str__",
            ]
            hasOnlyConstructorMethod = True
            for bodyElement in node.body:
                if (
                    isinstance(bodyElement, ast.FunctionDef)
                    and bodyElement.name not in dataclassFunctions
                ):
                    hasOnlyConstructorMethod = False
                    break

            if (
                hasOnlyConstructorMethod
                and sum(1 for el in node.body if isinstance(el, ast.FunctionDef)) > 0
            ):
                self.__error(node.lineno - 1, node.col_offset, "Y119", node.name)

    def __check120_121(self, node):
        """
        Private method to check for classes that inherit from object.

        @param node reference to the AST node to be checked
        @type ast.ClassDef
        """
        # class FooBar(object):
        #     ...
        if (
            len(node.bases) == 1
            and isinstance(node.bases[0], ast.Name)
            and node.bases[0].id == "object"
        ):
            self.__error(node.lineno - 1, node.col_offset, "Y120", node.name)

        elif (
            len(node.bases) > 1
            and isinstance(node.bases[-1], ast.Name)
            and node.bases[-1].id == "object"
        ):
            self.__error(
                node.lineno - 1,
                node.col_offset,
                "Y121",
                node.name,
                ", ".join(b.id for b in node.bases[:-1]),
            )

    def __check122(self, node):
        """
        Private method to check for all if-blocks which only check if a key
        is in a dictionary.

        @param node reference to the AST node to be checked
        @type ast.If
        """
        if (
            isinstance(node.test, ast.Compare)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.In)
            and len(node.body) == 1
            and len(node.orelse) == 0
        ) and (
            # We might still be left with a check if a value is in a list or
            # in the body the developer might remove the element from the list.
            # We need to have a look at the body.
            isinstance(node.body[0], ast.Assign)
            and isinstance(node.body[0].value, ast.Subscript)
            and len(node.body[0].targets) == 1
            and isinstance(node.body[0].targets[0], ast.Name)
            and isinstance(node.body[0].value.value, ast.Name)
            and isinstance(node.test.comparators[0], ast.Name)
            and node.body[0].value.value.id == node.test.comparators[0].id
        ):
            key = unparse(node.test.left)
            dictname = unparse(node.test.comparators[0])
            self.__error(node.lineno - 1, node.col_offset, "Y122", dictname, key)

    def __check123(self, node):
        """
        Private method to check for complicated dictionary access with default value.

        @param node reference to the AST node to be checked
        @type ast.If
        """
        isPattern1 = (
            len(node.body) == 1
            and isinstance(node.body[0], ast.Assign)
            and len(node.body[0].targets) == 1
            and isinstance(node.body[0].value, ast.Subscript)
            and len(node.orelse) == 1
            and isinstance(node.orelse[0], ast.Assign)
            and len(node.orelse[0].targets) == 1
            and isinstance(node.test, ast.Compare)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.In)
        )

        # just like pattern_1, but using NotIn and reversing if/else
        isPattern2 = (
            len(node.body) == 1
            and isinstance(node.body[0], ast.Assign)
            and len(node.orelse) == 1
            and isinstance(node.orelse[0], ast.Assign)
            and isinstance(node.orelse[0].value, ast.Subscript)
            and isinstance(node.test, ast.Compare)
            and len(node.test.ops) == 1
            and isinstance(node.test.ops[0], ast.NotIn)
        )

        if isPattern1:
            key = node.test.left
            if unparse(key) != unparse(node.body[0].value.slice):
                return
            assignToIfBody = node.body[0].targets[0]
            assignToElse = node.orelse[0].targets[0]
            if unparse(assignToIfBody) != unparse(assignToElse):
                return
            dictName = node.test.comparators[0]
            defaultValue = node.orelse[0].value
            valueNode = node.body[0].targets[0]
            keyStr = unparse(key)
            dictStr = unparse(dictName)
            defaultStr = unparse(defaultValue)
            valueStr = unparse(valueNode)
        elif isPattern2:
            key = node.test.left
            if unparse(key) != unparse(node.orelse[0].value.slice):
                return
            dictName = node.test.comparators[0]
            defaultValue = node.body[0].value
            valueNode = node.body[0].targets[0]
            keyStr = unparse(key)
            dictStr = unparse(dictName)
            defaultStr = unparse(defaultValue)
            valueStr = unparse(valueNode)
        else:
            return
        self.__error(
            node.lineno - 1,
            node.col_offset,
            "Y123",
            valueStr,
            dictStr,
            keyStr,
            defaultStr,
        )

    def __check181(self, node):
        """
        Private method to check for assignments that could be converted into
        an augmented assignment.

        @param node reference to the AST node to be checked
        @type ast.Assign
        """
        # a = a - b
        if (
            len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.BinOp)
            and isinstance(node.value.left, ast.Name)
            and node.value.left.id == node.targets[0].id
            and not isinstance(node.value.right, ast.Tuple)
        ):
            newNode = ast.AugAssign(node.targets[0], node.value.op, node.value.right)
            self.__error(
                node.lineno - 1,
                node.col_offset,
                "Y181",
                unparse(newNode),
                unparse(node),
            )

    def __check182(self, node):
        """
        Private method to check for calls of type 'super()' that could
        be shortened to 'super()'.

        @param node reference to the AST node to be checked
        @type ast.Call
        """
        # super()
        if (
            self.__classDefinitionStack
            and isinstance(node.func, ast.Name)
            and node.func.id == "super"
            and len(node.args) == 2
            and all(isinstance(arg, ast.Name) for arg in node.args)
            and node.args[0].id == self.__classDefinitionStack[-1]
            and node.args[1].id == "self"
        ):
            self.__error(node.lineno - 1, node.col_offset, "Y182", unparse(node))

    def __check201(self, node):
        """
        Private method to check for calls where an unary 'not' is used for
        an unequality.

        @param node reference to the UnaryOp node
        @type ast.UnaryOp
        """
        # not a == b
        if not (
            (
                not isinstance(node.op, ast.Not)
                or not isinstance(node.operand, ast.Compare)
                or len(node.operand.ops) != 1
                or not isinstance(node.operand.ops[0], ast.Eq)
            )
            or isinstance(node.parent, ast.If)
            and self.__isExceptionCheck(node.parent)
        ):
            comparison = node.operand
            left = unparse(comparison.left)
            right = unparse(comparison.comparators[0])
            self.__error(node.lineno - 1, node.col_offset, "Y201", left, right)

    def __check202(self, node):
        """
        Private method to check for calls where an unary 'not' is used for
        an equality.

        @param node reference to the UnaryOp node
        @type ast.UnaryOp
        """
        # not a != b
        if not (
            (
                not isinstance(node.op, ast.Not)
                or not isinstance(node.operand, ast.Compare)
                or len(node.operand.ops) != 1
                or not isinstance(node.operand.ops[0], ast.NotEq)
            )
            or isinstance(node.parent, ast.If)
            and self.__isExceptionCheck(node.parent)
        ):
            comparison = node.operand
            left = unparse(comparison.left)
            right = unparse(comparison.comparators[0])
            self.__error(node.lineno - 1, node.col_offset, "Y202", left, right)

    def __check203(self, node):
        """
        Private method to check for calls where an unary 'not' is used for
        an in-check.

        @param node reference to the UnaryOp node
        @type ast.UnaryOp
        """
        # not a in b
        if not (
            (
                not isinstance(node.op, ast.Not)
                or not isinstance(node.operand, ast.Compare)
                or len(node.operand.ops) != 1
                or not isinstance(node.operand.ops[0], ast.In)
            )
            or isinstance(node.parent, ast.If)
            and self.__isExceptionCheck(node.parent)
        ):
            comparison = node.operand
            left = unparse(comparison.left)
            right = unparse(comparison.comparators[0])
            self.__error(node.lineno - 1, node.col_offset, "Y203", left, right)

    def __check204(self, node):
        """
        Private method to check for calls of the type "not (a < b)".

        @param node reference to the UnaryOp node
        @type ast.UnaryOp
        """
        # not a < b
        if not (
            (
                not isinstance(node.op, ast.Not)
                or not isinstance(node.operand, ast.Compare)
                or len(node.operand.ops) != 1
                or not isinstance(node.operand.ops[0], ast.Lt)
            )
            or isinstance(node.parent, ast.If)
            and self.__isExceptionCheck(node.parent)
        ):
            comparison = node.operand
            left = unparse(comparison.left)
            right = unparse(comparison.comparators[0])
            self.__error(node.lineno - 1, node.col_offset, "Y204", left, right)

    def __check205(self, node):
        """
        Private method to check for calls of the type "not (a <= b)".

        @param node reference to the UnaryOp node
        @type ast.UnaryOp
        """
        # not a <= b
        if not (
            (
                not isinstance(node.op, ast.Not)
                or not isinstance(node.operand, ast.Compare)
                or len(node.operand.ops) != 1
                or not isinstance(node.operand.ops[0], ast.LtE)
            )
            or isinstance(node.parent, ast.If)
            and self.__isExceptionCheck(node.parent)
        ):
            comparison = node.operand
            left = unparse(comparison.left)
            right = unparse(comparison.comparators[0])
            self.__error(node.lineno - 1, node.col_offset, "Y205", left, right)

    def __check206(self, node):
        """
        Private method to check for calls of the type "not (a > b)".

        @param node reference to the UnaryOp node
        @type ast.UnaryOp
        """
        # not a > b
        if not (
            (
                not isinstance(node.op, ast.Not)
                or not isinstance(node.operand, ast.Compare)
                or len(node.operand.ops) != 1
                or not isinstance(node.operand.ops[0], ast.Gt)
            )
            or isinstance(node.parent, ast.If)
            and self.__isExceptionCheck(node.parent)
        ):
            comparison = node.operand
            left = unparse(comparison.left)
            right = unparse(comparison.comparators[0])
            self.__error(node.lineno - 1, node.col_offset, "Y206", left, right)

    def __check207(self, node):
        """
        Private method to check for calls of the type "not (a >= b)".

        @param node reference to the UnaryOp node
        @type ast.UnaryOp
        """
        # not a >= b
        if not (
            (
                not isinstance(node.op, ast.Not)
                or not isinstance(node.operand, ast.Compare)
                or len(node.operand.ops) != 1
                or not isinstance(node.operand.ops[0], ast.GtE)
            )
            or isinstance(node.parent, ast.If)
            and self.__isExceptionCheck(node.parent)
        ):
            comparison = node.operand
            left = unparse(comparison.left)
            right = unparse(comparison.comparators[0])
            self.__error(node.lineno - 1, node.col_offset, "Y207", left, right)

    def __check208(self, node):
        """
        Private method to check for calls of the type "not (not a)".

        @param node reference to the UnaryOp node
        @type ast.UnaryOp
        """
        # not (not a)
        if (
            isinstance(node.op, ast.Not)
            and isinstance(node.operand, ast.UnaryOp)
            and isinstance(node.operand.op, ast.Not)
        ):
            var = unparse(node.operand.operand)
            self.__error(node.lineno - 1, node.col_offset, "Y208", var)

    def __check211(self, node):
        """
        Private method to check for calls of the type "True if a else False".

        @param node reference to the AST node to be checked
        @type ast.IfExp
        """
        # True if a else False
        if (
            isinstance(node.body, ast.Constant)
            and node.body.value is True
            and isinstance(node.orelse, ast.Constant)
            and node.orelse.value is False
        ):
            cond = unparse(node.test)
            if isinstance(node.test, ast.Name):
                newCond = "bool({0})".format(cond)
            else:
                newCond = cond
            self.__error(node.lineno - 1, node.col_offset, "Y211", cond, newCond)

    def __check212(self, node):
        """
        Private method to check for calls of the type "False if a else True".

        @param node reference to the AST node to be checked
        @type ast.IfExp
        """
        # False if a else True
        if (
            isinstance(node.body, ast.Constant)
            and node.body.value is False
            and isinstance(node.orelse, ast.Constant)
            and node.orelse.value is True
        ):
            cond = unparse(node.test)
            if isinstance(node.test, ast.Name):
                newCond = "not {0}".format(cond)
            else:
                if len(node.test.ops) == 1:
                    newCond = unparse(self.__negateTest(node.test))
                else:
                    newCond = "not ({0})".format(cond)
            self.__error(node.lineno - 1, node.col_offset, "Y212", cond, newCond)

    def __check213(self, node):
        """
        Private method to check for calls of the type "b if not a else a".

        @param node reference to the AST node to be checked
        @type ast.IfExp
        """
        # b if not a else a
        if (
            isinstance(node.test, ast.UnaryOp)
            and isinstance(node.test.op, ast.Not)
            and self.__isSameExpression(node.test.operand, node.orelse)
        ):
            a = unparse(node.test.operand)
            b = unparse(node.body)
            self.__error(node.lineno - 1, node.col_offset, "Y213", a, b)

    def __check221(self, node):
        """
        Private method to check for calls of the type "a and not a".

        @param node reference to the AST node to be checked
        @type ast.BoolOp
        """
        # a and not a
        if isinstance(node.op, ast.And) and len(node.values) >= 2:
            # We have a boolean And. Let's make sure there is two times the
            # same expression, but once with a "not"
            negatedExpressions = []
            nonNegatedExpressions = []
            for exp in node.values:
                if isinstance(exp, ast.UnaryOp) and isinstance(exp.op, ast.Not):
                    negatedExpressions.append(exp.operand)
                else:
                    nonNegatedExpressions.append(exp)
            for negatedExpression in negatedExpressions:
                for nonNegatedExpression in nonNegatedExpressions:
                    if self.__isSameExpression(negatedExpression, nonNegatedExpression):
                        negExp = unparse(negatedExpression)
                        self.__error(node.lineno - 1, node.col_offset, "Y221", negExp)

    def __check222(self, node):
        """
        Private method to check for calls of the type "a or not a".

        @param node reference to the AST node to be checked
        @type ast.BoolOp
        """
        # a or not a
        if isinstance(node.op, ast.Or) and len(node.values) >= 2:
            # We have a boolean And. Let's make sure there is two times the
            # same expression, but once with a "not"
            negatedExpressions = []
            nonNegatedExpressions = []
            for exp in node.values:
                if isinstance(exp, ast.UnaryOp) and isinstance(exp.op, ast.Not):
                    negatedExpressions.append(exp.operand)
                else:
                    nonNegatedExpressions.append(exp)
            for negatedExpression in negatedExpressions:
                for nonNegatedExpression in nonNegatedExpressions:
                    if self.__isSameExpression(negatedExpression, nonNegatedExpression):
                        negExp = unparse(negatedExpression)
                        self.__error(node.lineno - 1, node.col_offset, "Y222", negExp)

    def __check223(self, node):
        """
        Private method to check for calls of the type "... or True".

        @param node reference to the AST node to be checked
        @type ast.BoolOp
        """
        # a or True
        if isinstance(node.op, ast.Or):
            for exp in node.values:
                if isinstance(exp, ast.Constant) and exp.value is True:
                    self.__error(node.lineno - 1, node.col_offset, "Y223")

    def __check224(self, node):
        """
        Private method to check for calls of the type "... and False".

        @param node reference to the AST node to be checked
        @type ast.BoolOp
        """
        # a and False
        if isinstance(node.op, ast.And):
            for exp in node.values:
                if isinstance(exp, ast.Constant) and exp.value is False:
                    self.__error(node.lineno - 1, node.col_offset, "Y224")

    def __check301(self, node):
        """
        Private method to check for Yoda conditions.

        @param node reference to the AST node to be checked
        @type ast.Compare
        """
        # 42 == age
        if (
            isinstance(node.left, ast.Constant)
            and len(node.ops) == 1
            and isinstance(node.ops[0], ast.Eq)
        ):
            left = unparse(node.left)
            isStr = isinstance(node.left, ast.Constant) and isinstance(
                node.left.value, str
            )
            if isStr:
                left = f"'{left}'"
            right = unparse(node.comparators[0])
            self.__error(node.lineno - 1, node.col_offset, "Y301", left, right)

    def __check401(self, node):
        """
        Private method to check for bare boolean function arguments.

        @param node reference to the AST node to be checked
        @type ast.Call
        """
        # foo(a, b, True)
        hasBareBool = any(
            isinstance(callArg, ast.Constant)
            and (callArg.value is True or callArg.value is False)
            for callArg in node.args
        )

        isException = isinstance(node.func, ast.Attribute) and node.func.attr in ["get"]

        if hasBareBool and not isException:
            self.__error(node.lineno - 1, node.col_offset, "Y401")

    def __check402(self, node):
        """
        Private method to check for bare numeric function arguments.

        @param node reference to the AST node to be checked
        @type ast.Call
        """
        # foo(a, b, 123123)
        hasBareNumeric = any(
            isinstance(callArg, ast.Constant) and type(callArg.value) in (float, int)
            for callArg in node.args
        )

        isException = isinstance(node.func, ast.Name) and node.func.id == "range"
        isException = isException or (
            isinstance(node.func, ast.Attribute) and node.func.attr in ("get", "insert")
        )

        if hasBareNumeric and not isException:
            self.__error(node.lineno - 1, node.col_offset, "Y402")

    def __check901(self, node):
        """
        Private method to check for unnecessary bool conversion.

        @param node reference to the AST node to be checked
        @type ast.Call
        """
        if (
            isinstance(node.func, ast.Name)
            and node.func.id == "bool"
            and len(node.args) == 1
            and isinstance(node.args[0], ast.Compare)
        ):
            actual = unparse(node)
            expected = unparse(node.args[0])
            self.__error(node.lineno - 1, node.col_offset, "Y901", expected, actual)

    def __check904(self, node):
        """
        Private method to check for dictionary initialization.

        @param node reference to the AST node to be checked
        @type ast.Assign
        """
        # a = {}; a['b'] = 'c'
        n2 = node.next_sibling
        if (
            isinstance(node.value, ast.Dict)
            and isinstance(n2, ast.Assign)
            and len(n2.targets) == 1
            and len(node.targets) == 1
            and isinstance(n2.targets[0], ast.Subscript)
            and isinstance(n2.targets[0].value, ast.Name)
            and isinstance(node.targets[0], ast.Name)
            and n2.targets[0].value.id == node.targets[0].id
        ):
            dictName = unparse(node.targets[0])
            if not self.__expressionUsesVariable(n2.value, dictName):
                self.__error(node.lineno - 1, node.col_offset, "Y904", dictName)

    def __check905(self, node):
        """
        Private method to check for list initialization by splitting a string.

        @param node reference to the AST node to be checked
        @type ast.Call
        """
        if (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "split"
            and isinstance(node.func.value, ast.Constant)
        ):
            value = node.func.value.value

            expected = json.dumps(value.split())
            actual = unparse(node.func.value) + ".split()"
            self.__error(node.lineno - 1, node.col_offset, "Y905", expected, actual)

    def __check906(self, node):
        """
        Private method to check for unnecessary nesting of os.path.join().

        @param node reference to the AST node to be checked
        @type ast.Call
        """  # __IGNORE_WARNING_D234r__

        def getOsPathJoinArgs(node):
            names = []
            for arg in node.args:
                if (
                    isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Attribute)
                    and isinstance(arg.func.value, ast.Attribute)
                    and isinstance(arg.func.value.value, ast.Name)
                    and arg.func.value.value.id == "os"
                    and arg.func.value.attr == "path"
                    and arg.func.attr == "join"
                ):
                    names += getOsPathJoinArgs(arg)
                elif isinstance(arg, ast.Name):
                    names.append(arg.id)
                elif AstUtilities.isString(arg):
                    names.append(f"'{arg.value}'")
            return names

        if (
            isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Attribute)
            and isinstance(node.func.value.value, ast.Name)
            and node.func.value.value.id == "os"
            and node.func.value.attr == "path"
            and node.func.attr == "join"
            and len(node.args) == 2
            and any(
                (
                    isinstance(arg, ast.Call)
                    and isinstance(arg.func, ast.Attribute)
                    and isinstance(arg.func.value, ast.Attribute)
                    and isinstance(arg.func.value.value, ast.Name)
                    and arg.func.value.value.id == "os"
                    and arg.func.value.attr == "path"
                    and arg.func.attr == "join"
                )
                for arg in node.args
            )
        ):
            names = getOsPathJoinArgs(node)

            actual = unparse(node)
            expected = "os.path.join({0})".format(", ".join(names))
            self.__error(node.lineno - 1, node.col_offset, "Y906", expected, actual)

    def __check907(self, node):
        """
        Private method to check for Union type annotation with None.

        @param node reference to the AST node to be checked
        @type ast.Subscript
        """
        if isinstance(node.value, ast.Name) and node.value.id == "Union":
            if isinstance(node.slice, ast.Index) and isinstance(
                node.slice.value, ast.Tuple
            ):
                # Python 3.8
                tupleVar = node.slice.value
            elif isinstance(node.slice, ast.Tuple):
                # Python 3.9+
                tupleVar = node.slice
            else:
                return

            hasNone = False
            others = []
            for elt in tupleVar.elts:
                if isinstance(elt, ast.Constant) and elt.value is None:
                    hasNone = True
                else:
                    others.append(elt)

            if len(others) == 1 and hasNone:
                type_ = unparse(others[0])
                self.__error(
                    node.lineno - 1, node.col_offset, "Y907", type_, unparse(node)
                )

    def __check909(self, node):
        """
        Private method to check for reflexive assignments.

        @param node reference to the AST node to be checked
        @type ast.Assign
        """
        names = []
        if isinstance(node.value, (ast.Name, ast.Subscript, ast.Tuple)):
            names.append(unparse(node.value))
        for target in node.targets:
            names.append(unparse(target))

        if len(names) != len(set(names)) and not isinstance(node.parent, ast.ClassDef):
            srccode = unparse(node)
            self.__error(node.lineno - 1, node.col_offset, "Y909", srccode)

    def __check910(self, node):
        """
        Private method to check for uses of 'dict.get(key, None)'.

        @param node reference to the AST node to be checked
        @type ast.Call
        """
        if not (
            isinstance(node.func, ast.Attribute)
            and node.func.attr == "get"
            and isinstance(node.func.ctx, ast.Load)
        ):
            return

        # check the argument value
        if not (
            len(node.args) == 2
            and isinstance(node.args[1], ast.Constant)
            and node.args[1].value is None
        ):
            return

        actual = unparse(node)
        func = unparse(node.func)
        key = unparse(node.args[0])
        expected = f"{func}({key})"
        self.__error(node.lineno - 1, node.col_offset, "Y910", expected, actual)

    def __check911(self, node):
        """
        Private method to check for the expression "zip(_.keys(), _.values())".

        @param node reference to the AST node to be checked
        @type ast.Call
        """
        if isinstance(node, ast.Call) and (
            isinstance(node.func, ast.Name)
            and node.func.id == "zip"
            and len(node.args) == 2
        ):
            firstArg, secondArg = node.args
            if (
                isinstance(firstArg, ast.Call)
                and isinstance(firstArg.func, ast.Attribute)
                and isinstance(firstArg.func.value, ast.Name)
                and firstArg.func.attr == "keys"
                and isinstance(secondArg, ast.Call)
                and isinstance(secondArg.func, ast.Attribute)
                and isinstance(secondArg.func.value, ast.Name)
                and secondArg.func.attr == "values"
                and firstArg.func.value.id == secondArg.func.value.id
            ):
                self.__error(
                    node.lineno - 1, node.col_offset, "Y911", firstArg.func.value.id
                )


#
# eflag: noqa = M891
