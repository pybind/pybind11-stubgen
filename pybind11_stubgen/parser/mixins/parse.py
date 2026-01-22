from __future__ import annotations

import ast
import inspect
import re
import types
from typing import Any

from pybind11_stubgen.parser.errors import (
    InvalidExpressionError,
    InvalidIdentifierError,
    NameResolutionError,
    ParserError,
)
from pybind11_stubgen.parser.interface import IParser
from pybind11_stubgen.structs import (
    Alias,
    Argument,
    Attribute,
    Class,
    Decorator,
    Docstring,
    Field,
    Function,
    Identifier,
    Import,
    InvalidExpression,
    Method,
    Modifier,
    Module,
    Property,
    QualifiedName,
    ResolvedType,
    TypeVar_,
    Value,
)

_generic_args = [
    Argument(name=Identifier("args"), variadic=True),
    Argument(name=Identifier("kwargs"), kw_variadic=True),
]


class ParserDispatchMixin(IParser):
    def handle_class(self, path: QualifiedName, class_: type) -> Class | None:
        base_classes = class_.__bases__
        result = Class(name=path[-1], bases=self.handle_bases(path, base_classes))
        for name, member in inspect.getmembers(class_):
            obj = self.handle_class_member(
                QualifiedName([*path, Identifier(name)]), class_, member
            )
            if isinstance(obj, Docstring):
                result.doc = obj
            elif isinstance(obj, Alias):
                result.aliases.append(obj)
            elif isinstance(obj, Field):
                result.fields.append(obj)
            elif isinstance(obj, Class):
                result.classes.append(obj)
            elif isinstance(obj, list):  # list[Method]
                result.methods.extend(obj)
            elif isinstance(obj, Property):
                result.properties.append(obj)
            elif obj is None:
                pass
            else:
                raise AssertionError()
        return result

    def handle_class_member(
        self, path: QualifiedName, class_: type, member: Any
    ) -> Docstring | Alias | Class | list[Method] | Field | Property | None:
        if inspect.isroutine(member):
            return self.handle_method(path, member)
        if self._is_alias(path, member):
            return self.handle_alias(path, member)
        if inspect.isclass(member):
            return self.handle_class(path, member)
        if self._is_descriptor(member):
            return self.handle_property(path, member)
        if path[-1] == "__doc__":
            return self.handle_docstring(path, member)
        return self.handle_field(path, member)

    def handle_module(
        self, path: QualifiedName, module: types.ModuleType
    ) -> Module | None:
        result = Module(name=path[-1])
        for name, member in inspect.getmembers(module):
            obj = self.handle_module_member(
                QualifiedName([*path, Identifier(name)]), module, member
            )
            if isinstance(obj, Docstring):
                result.doc = obj
            elif isinstance(obj, Import):
                result.imports.add(obj)
            elif isinstance(obj, Alias):
                result.aliases.append(obj)
            elif isinstance(obj, Class):
                result.classes.append(obj)
            elif isinstance(obj, list):  # list[Function]
                result.functions.extend(obj)
            elif isinstance(obj, Module):
                result.sub_modules.append(obj)
            elif isinstance(obj, Attribute):
                result.attributes.append(obj)
            elif isinstance(obj, TypeVar_):
                result.type_vars.append(obj)
            elif obj is None:
                if name == "__path__":
                    result.is_package = True
            else:
                raise AssertionError()

        return result

    def handle_module_member(
        self, path: QualifiedName, module: types.ModuleType, member: Any
    ) -> (
        Docstring | Import | Alias | Class | list[Function] | Attribute | Module | None
    ):
        member_module = self._get_value_parent_module_name(member)
        if (
            member_module is not None
            and member_module != module.__name__
            or path[-1] == "annotations"
        ):
            return self.handle_import(path, member)
        if self._is_alias(path, member):
            return self.handle_alias(path, member)
        if inspect.isroutine(member):
            return self.handle_function(path, member)
        if inspect.isclass(member):
            return self.handle_class(path, member)
        if inspect.ismodule(member):
            return self.handle_module(path, member)
        if path[-1] == "__doc__":
            return self.handle_docstring(path, member)
        return self.handle_attribute(path, member)

    def _get_value_parent_module_name(self, obj: Any) -> str | None:
        if inspect.ismodule(obj):
            return obj.__name__.rsplit(".", 1)[0]
        if inspect.isclass(obj) or inspect.isroutine(obj):
            return getattr(obj, "__module__", None)
        return None

    def _is_alias(self, path: QualifiedName, member: Any):
        if (inspect.isroutine(member) or inspect.isclass(member)) and path[
            -1
        ] != member.__name__:
            return True
        if inspect.ismodule(member) and member.__name__ != str(path):
            return True
        return False

    def _is_descriptor(self, member: Any) -> bool:
        # https://docs.python.org/3/glossary.html#term-descriptor
        # Ignore `__delete__`-only descriptors
        return hasattr(member, "__get__") or hasattr(member, "__set__")


class BaseParser(IParser):
    def handle_alias(self, path: QualifiedName, origin: Any) -> Alias | None:
        full_name = self._get_full_name(path, origin)
        if full_name is None:
            return None

        return Alias(
            name=path[-1],
            origin=full_name,
        )

    def handle_attribute(self, path: QualifiedName, value: Any) -> Attribute | None:
        return Attribute(
            name=path[-1],
            value=self.handle_value(value),
            annotation=ResolvedType(name=self.handle_type(type(value))),
        )

    def handle_bases(
        self, path: QualifiedName, bases: tuple[type, ...]
    ) -> list[QualifiedName]:
        return [self.handle_type(type_) for type_ in bases if type_ is not object]

    def handle_docstring(self, path: QualifiedName, value: Any) -> Docstring | None:
        if isinstance(value, str):
            return Docstring(value)
        return None

    def handle_field(self, path: QualifiedName, value: Any) -> Field | None:
        attr = self.handle_attribute(path, value)
        if attr is None:
            return None
        result = Field(
            attribute=Attribute(
                name=attr.name,
                value=attr.value,
            ),
            modifier="static",
        )
        if attr.annotation is not None:
            class_var = self.parse_annotation_str("typing.ClassVar")
            assert isinstance(class_var, ResolvedType)
            result.attribute.annotation = ResolvedType(
                name=class_var.name,
                parameters=[attr.annotation],
            )
        return result

    def handle_function(self, path: QualifiedName, func: Any) -> list[Function]:
        doc: Docstring | None = (
            Docstring(func.__doc__)
            if getattr(func, "__doc__", None) is not None
            else None
        )
        func_name = Identifier(path[-1])

        try:
            (
                args,
                var_args,
                var_kw,
                defaults,
                kw_only_args,
                kw_only_defaults,
                annotations,
            ) = inspect.getfullargspec(func)

            func_args: dict[str, Argument] = {
                arg_name: Argument(name=Identifier(arg_name)) for arg_name in args
            }
            func_args["return"] = Argument(
                name=Identifier(),
            )
            if var_args is not None:
                func_args[var_args] = Argument(name=Identifier(var_args), variadic=True)
            for arg_name in kw_only_args:
                func_args[arg_name] = Argument(name=Identifier(arg_name), kw_only=True)
            if var_kw is not None:
                func_args[var_kw] = Argument(name=Identifier(var_kw), kw_variadic=True)
            if defaults is not None:
                for i, default in enumerate(defaults):
                    arg_name = args[len(args) - len(defaults) + i]
                    func_args[arg_name].default = self.handle_value(default)
            if kw_only_defaults is not None:
                for arg_name, default in kw_only_defaults.items():
                    func_args[arg_name].default = self.handle_value(default)
            for arg_name, annotation in annotations.items():
                if isinstance(annotation, str):
                    func_args[arg_name].annotation = self.parse_annotation_str(
                        annotation
                    )
                elif not isinstance(annotation, type):
                    func_args[arg_name].annotation = self.handle_value(annotation)
                elif self._is_generic_alias(annotation):
                    func_args[arg_name].annotation = self.parse_annotation_str(
                        str(annotation)
                    )
                else:
                    func_args[arg_name].annotation = ResolvedType(
                        name=self.handle_type(annotation),
                    )
            if "return" in func_args:
                returns = func_args["return"].annotation
            else:
                returns = None
            return [
                Function(
                    name=func_name,
                    args=[
                        arg
                        for arg_name, arg in func_args.items()
                        if arg_name != "return"
                    ],
                    returns=returns,
                    doc=doc,
                )
            ]

        except TypeError:
            # generic signature `f(*args, *kwargs)`
            return [
                Function(
                    name=func_name,
                    args=_generic_args,
                    doc=doc,
                )
            ]

    def _is_generic_alias(self, annotation: type) -> bool:
        generic_alias_t: type | None = getattr(types, "GenericAlias", None)
        if generic_alias_t is None:
            return False
        return isinstance(annotation, generic_alias_t)

    def handle_import(self, path: QualifiedName, origin: Any) -> Import | None:
        full_name = self._get_full_name(path, origin)
        if full_name is None:
            return None

        return Import(
            path[-1],
            full_name,
        )

    def handle_method(self, path: QualifiedName, method: Any) -> list[Method]:
        return [
            Method(function=func, modifier=self._get_method_modifier(func.args))
            for func in self.handle_function(path, method)
        ]

    def handle_value(self, value: Any) -> Value:
        value_type = type(value)
        # Use exact type match, not `isinstance()` that allows inherited types pass
        if value is None or value_type in (bool, int, str):
            return Value(repr=repr(value), is_print_safe=True)
        if value_type in (float, complex):
            try:
                # checks for NaN, +inf, -inf
                repr_str = repr(value)
                eval(repr_str)
                return Value(repr=repr_str, is_print_safe=True)
            except (SyntaxError, NameError):
                pass
        if value_type in (list, tuple, set):
            assert isinstance(value, (list, tuple, set))
            if len(value) == 0:
                return Value(repr=f"{value_type.__name__}()", is_print_safe=True)
            elements: list[Value] = [self.handle_value(el) for el in value]
            is_print_safe = all(el.is_print_safe for el in elements)
            left, right = {
                list: "[]",
                tuple: "()",
                set: "{}",
            }[value_type]
            return Value(
                repr="".join([left, ", ".join(el.repr for el in elements), right]),
                is_print_safe=is_print_safe,
            )
        if value_type is dict:
            assert isinstance(value, dict)
            parts = []
            is_print_safe = True
            for k, v in value.items():
                k_value = self.handle_value(k)
                v_value = self.handle_value(v)
                parts.append(f"{k_value.repr}: {v_value.repr}")
                is_print_safe = (
                    is_print_safe and k_value.is_print_safe and v_value.is_print_safe
                )

            return Value(
                repr="".join(["{", ", ".join(parts), "}"]), is_print_safe=is_print_safe
            )
        if inspect.isroutine(value):
            module_name = getattr(value, "__module__", None)
            qual_name = getattr(value, "__qualname__", None)
            if (
                module_name is not None
                and "<" not in module_name
                and qual_name is not None
                and "<" not in qual_name
            ):
                if module_name == "builtins":
                    repr_str = qual_name
                else:
                    repr_str = f"{module_name}.{qual_name}"
                return Value(repr=repr_str, is_print_safe=True)
        if inspect.isclass(value):
            return Value(repr=str(self.handle_type(value)), is_print_safe=True)
        if inspect.ismodule(value):
            return Value(repr=value.__name__, is_print_safe=True)
        return Value(repr=repr(value), is_print_safe=False)

    def handle_type(self, type_: type) -> QualifiedName:
        return QualifiedName(
            (
                Identifier(part)
                for part in (
                    *type_.__module__.split("."),
                    *type_.__qualname__.split("."),
                )
            )
        )

    def parse_value_str(self, value: str) -> Value | InvalidExpression:
        return self._parse_expression_str(value)

    def report_error(self, error: ParserError):
        if isinstance(error, NameResolutionError):
            if error.name[0] == "module":
                return
        super().report_error(error)

    def _get_method_modifier(self, args: list[Argument]) -> Modifier:
        if len(args) == 0:
            return "static"
        name = args[0].name
        if name == Identifier("self"):
            return None
        elif name == Identifier("cls"):
            return "class"
        else:
            return "static"

    def _get_full_name(self, path: QualifiedName, origin: Any) -> QualifiedName | None:
        if inspect.ismodule(origin):
            origin_full_name = origin.__name__
        else:
            module_name = getattr(origin, "__module__", None)
            if module_name == "__future__":
                return None
            if module_name is None:
                self.report_error(NameResolutionError(path))
                return None
            qual_name = getattr(origin, "__qualname__", None)
            if qual_name is None:
                self.report_error(NameResolutionError(path))
                return None
            # Note: __qualname__ prefix is an artefact of pybind11
            # `PyCapsule.` in pybind11 2
            # pybind11_detail_function_record_* in 3
            match = re.match(
                r"(PyCapsule|pybind11_detail_function_record_[_a-zA-Z0-9]+)\.",
                qual_name,
            )
            if match:
                qual_name = qual_name[match.end() :]
            origin_full_name = f"{module_name}.{qual_name}"

        origin_name = QualifiedName.from_str(origin_full_name)

        for part in origin_name:
            if not part.isidentifier():
                self.report_error(InvalidIdentifierError(part, path))
                return None
        return origin_name

    def _parse_expression_str(self, expr_str: str) -> Value | InvalidExpression:
        strip_expr = expr_str.strip()
        try:
            ast.parse(strip_expr)
            print_safe = False
            try:
                ast.literal_eval(strip_expr)
                print_safe = True
            except (ValueError, TypeError, SyntaxError, MemoryError, RecursionError):
                pass
            return Value(strip_expr, is_print_safe=print_safe)
        except SyntaxError:
            self.report_error(InvalidExpressionError(strip_expr))
            return InvalidExpression(strip_expr)


class ExtractSignaturesFromPybind11Docstrings(IParser):
    _arg_star_name_regex = re.compile(
        r"^\s*(?P<stars>\*{1,2})?" r"\s*(?P<name>\w+)\s*$"
    )

    def handle_function(self, path: QualifiedName, func: Any) -> list[Function]:
        result = super().handle_function(path, func)
        if len(result) == 1 and result[0].args == _generic_args:
            doc: str | None = func.__doc__
            func_name = Identifier(path[-1])

            if doc is not None:
                parsed_funcs = self.parse_function_docstring(
                    func_name, doc.splitlines()
                )

                if len(parsed_funcs) > 0:
                    return parsed_funcs
        return result

    def handle_property(self, path: QualifiedName, prop: Any) -> Property | None:
        result = Property(name=path[-1], modifier=None)

        # Note: pybind *usually* does not include function name
        #       in getter/setter signatures, e.g.:
        #           (arg0: demo._bindings.enum.ConsoleForegroundColor) -> int
        #
        fake_path = QualifiedName((*path, Identifier("")))

        if hasattr(prop, "fget") and prop.fget is not None:
            for func_path in [fake_path, path]:
                result.getter = self._fixup_parsed_getters_or_setters(
                    self.handle_function(func_path, prop.fget)
                )
                if result.getter is not None and result.getter.args != _generic_args:
                    break

        if hasattr(prop, "fset") and prop.fset is not None:
            for func_path in [fake_path, path]:
                result.setter = self._fixup_parsed_getters_or_setters(
                    self.handle_function(func_path, prop.fset)
                )
                if result.setter is not None and result.setter.args != _generic_args:
                    break
        if result.getter is None and result.setter is None:
            return None

        prop_doc = getattr(prop, "__doc__", None)
        if prop_doc is not None:
            result.doc = self._strip_empty_lines(prop_doc.splitlines())

        if (
            result.doc is not None
            and result.getter is not None
            and (
                result.doc == result.getter.doc
                or result.doc
                == self._strip_empty_lines(
                    (getattr(prop.fget, "__doc__", "") or "").splitlines()
                )
            )
        ):
            result.doc = None

        return result

    def parse_args_str(self, args_str: str) -> list[Argument]:
        split_args = self._split_args_str(args_str)
        if split_args is None:
            return _generic_args

        result: list[Argument] = []
        kw_only = False
        for arg_str, annotation_str, default_str in split_args:
            if arg_str.strip() == "/":
                for arg in result:
                    arg.pos_only = True
                continue
            if arg_str.strip() == "*":
                kw_only = True
                continue
            match = self._arg_star_name_regex.match(arg_str)
            if match is None:
                return _generic_args
            name = Identifier(match.group("name"))

            variadic = False
            kw_variadic = False

            stars = match.group("stars")
            if stars == "*":
                variadic = True
            elif stars == "**":
                kw_variadic = True

            if annotation_str is not None:
                annotation = self.parse_annotation_str(annotation_str)
            else:
                annotation = None

            if default_str is not None:
                default = self.parse_value_str(default_str)
            else:
                default = None

            result.append(
                Argument(
                    name=name,
                    default=default,
                    annotation=annotation,
                    variadic=variadic,
                    kw_variadic=kw_variadic,
                    kw_only=kw_only,
                )
            )
        return result

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        variants = self._split_type_union_str(annotation_str)
        if variants is None or len(variants) == 0:
            self.report_error(InvalidExpressionError(annotation_str))
            return InvalidExpression(annotation_str)
        if len(variants) == 1:
            return self.parse_type_str(variants[0])
        union_t = self.parse_annotation_str("typing.Union")
        assert isinstance(union_t, ResolvedType)
        return ResolvedType(
            name=union_t.name,
            parameters=[self.parse_annotation_str(variant) for variant in variants],
        )

    def parse_type_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        qname_regex = re.compile(
            r"^\s*(?P<qual_name>([_A-Za-z]\w*)?(\s*\.\s*[_A-Za-z]\w*)*)"
        )
        annotation_str = annotation_str.strip()
        match = qname_regex.match(annotation_str)
        if match is None:
            return self.parse_value_str(annotation_str)
        qual_name = QualifiedName(
            Identifier(part)
            for part in match.group("qual_name").replace(" ", "").split(".")
        )
        parameters_str = annotation_str[match.end("qual_name") :].strip()

        if len(parameters_str) == 0:
            parameters = None
        else:
            if parameters_str[0] != "[" or parameters_str[-1] != "]":
                return self.parse_value_str(annotation_str)

            split_parameters = self._split_parameters_str(parameters_str[1:-1])
            if split_parameters is None:
                return self.parse_value_str(annotation_str)

            parameters = [
                self.parse_annotation_str(param_str) for param_str in split_parameters
            ]
        return ResolvedType(name=qual_name, parameters=parameters)

    def parse_function_docstring(
        self, func_name: Identifier, doc_lines: list[str]
    ) -> list[Function]:
        if len(doc_lines) == 0:
            return []

        top_signature_regex = re.compile(
            rf"^{func_name}\((?P<args>.*)\)\s*(->\s*(?P<returns>.+))?$"
        )

        match = top_signature_regex.match(doc_lines[0])
        if match is None:
            return []

        if len(doc_lines) < 2 or doc_lines[1] != "Overloaded function.":
            returns_str = match.group("returns")
            if returns_str is not None:
                returns = self.parse_annotation_str(returns_str)
            else:
                returns = None

            return [
                Function(
                    name=func_name,
                    args=self.parse_args_str(match.group("args")),
                    doc=self._strip_empty_lines(doc_lines[1:]),
                    returns=returns,
                )
            ]

        overload_signature_regex = re.compile(
            rf"^(\s*(?P<overload_number>\d+).\s*)"
            rf"{func_name}\((?P<args>.*)\)\s*->\s*(?P<returns>.+)$"
        )

        doc_start = 0
        _dummy = Function(Identifier(""))
        overloads = [_dummy]

        for i in range(2, len(doc_lines)):
            match = overload_signature_regex.match(doc_lines[i])
            if match:
                if match.group("overload_number") != f"{len(overloads)}":
                    continue
                overloads[-1].doc = self._strip_empty_lines(doc_lines[doc_start:i])
                doc_start = i + 1
                overloads.append(
                    Function(
                        name=func_name,
                        args=self.parse_args_str(match.group("args")),
                        returns=self.parse_annotation_str(match.group("returns")),
                        doc=None,
                        decorators=[
                            # use `parse_annotation_str()` to trigger typing import
                            Decorator(str(self.parse_annotation_str("typing.overload")))
                        ],
                    )
                )

        overloads[-1].doc = self._strip_empty_lines(doc_lines[doc_start:])

        return overloads[1:]

    def _fixup_parsed_getters_or_setters(
        self, funcs: list[Function]
    ) -> Function | None:
        if len(funcs) == 0:
            return None
        if len(funcs) > 1:
            raise RuntimeError(
                "Multiple overloads in property's getters/setters are not supported"
            )

        func = funcs[0]

        if (
            len(func.args) > 0
            and not func.args[0].variadic
            and not func.args[0].kw_variadic
            and func.args[0].default is None
        ):
            func.args[0].name = Identifier("self")
            func.args[0].annotation = None
        else:
            pass
            # TODO: produce warning
        return func

    def _split_args_str(
        self, args_str: str
    ) -> list[tuple[str, str | None, str | None]] | None:
        result = []

        closing = {"(": ")", "{": "}", "[": "]"}
        stack = []
        i = 0
        arg_begin = 0
        semicolon_pos: int | None = None
        eq_sign_pos: int | None = None

        def add_arg():
            nonlocal semicolon_pos
            nonlocal eq_sign_pos
            annotation = None
            default = None

            arg_end = i

            if eq_sign_pos is not None:
                arg_end = eq_sign_pos
                default = args_str[eq_sign_pos + 1 : i]

            if semicolon_pos is not None:
                annotation = args_str[semicolon_pos + 1 : arg_end]
                arg_end = semicolon_pos

            name = args_str[arg_begin:arg_end]
            result.append((name, annotation, default))
            semicolon_pos = None
            eq_sign_pos = None

        while i < len(args_str):
            c = args_str[i]
            if c in "\"'":
                # TODO: handle triple-quoted strings too
                str_end = self._find_str_end(args_str, i)
                if str_end is None:
                    return None
                i = str_end
            elif c in closing:
                stack.append(closing[c])
            elif len(stack) == 0:
                if c == ",":
                    add_arg()
                    arg_begin = i + 1
                elif c == ":" and semicolon_pos is None:
                    semicolon_pos = i
                elif c == "=" and args_str[i : i + 2] != "==":
                    eq_sign_pos = i
            elif stack[-1] == c:
                stack.pop()

            i += 1

        if len(stack) != 0:
            return None

        if len(args_str[arg_begin:i].strip()) != 0:
            add_arg()

        return result

    def _split_type_union_str(self, type_str: str) -> list[str] | None:
        return self._split_str(type_str, delim="|")

    def _split_parameters_str(self, param_str: str) -> list[str] | None:
        return self._split_str(param_str, delim=",")

    def _split_str(self, param_str: str, delim: str):
        result = []
        closing = {"(": ")", "{": "}", "[": "]"}
        stack = []
        i = 0
        arg_begin = 0

        def add_arg():
            arg_end = i
            param = param_str[arg_begin:arg_end]
            result.append(param)

        while i < len(param_str):
            c = param_str[i]
            if c in "\"'":
                # TODO: handle triple-quoted strings too
                str_end = self._find_str_end(param_str, i)
                if str_end is None:
                    return None
                i = str_end
            elif c in closing:
                stack.append(closing[c])
            elif len(stack) == 0:
                if c == delim:
                    add_arg()
                    arg_begin = i + 1
            elif stack[-1] == c:
                stack.pop()

            i += 1
        if len(stack) != 0:
            return None
        if param_str[arg_begin:i].strip() != 0:
            add_arg()
        return result

    def _find_str_end(self, s, start) -> int | None:
        for i in range(start + 1, len(s)):
            c = s[i]
            if c == "\\":  # skip escaped chars
                continue
            if c == s[start]:
                return i
        return None

    def _strip_empty_lines(self, doc_lines: list[str]) -> Docstring | None:
        assert isinstance(doc_lines, list)
        start = 0
        for start in range(0, len(doc_lines)):
            if len(doc_lines[start].strip()) > 0:
                break
        end = len(doc_lines) - 1
        for end in range(len(doc_lines) - 1, 0, -1):
            if len(doc_lines[end].strip()) > 0:
                break
        result = "\n".join(doc_lines[start : end + 1])
        if len(result) == 0:
            return None
        return Docstring(result)

    def report_error(self, error: ParserError) -> None:
        if isinstance(error, NameResolutionError):
            if error.name[0] == "pybind11_builtins":
                return
        if isinstance(error, InvalidIdentifierError):
            name = error.name
            if (
                name.startswith("ItemsView[")
                and name.endswith("]")
                or name.startswith("KeysView[")
                and name.endswith("]")
                or name.startswith("ValuesView[")
                and name.endswith("]")
            ):
                return

        super().report_error(error)

    def handle_bases(
        self, path: QualifiedName, bases: tuple[type, ...]
    ) -> list[QualifiedName]:
        result = []
        for base in super().handle_bases(path, bases):
            if base[0] == "pybind11_builtins":
                break
            result.append(base)
        return result
