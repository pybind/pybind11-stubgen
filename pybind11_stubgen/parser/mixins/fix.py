from __future__ import annotations

import builtins
import importlib
import inspect
import re
import sys
import types
from logging import getLogger
from typing import Any, Sequence

from pybind11_stubgen.parser.errors import (
    InvalidExpressionError,
    NameResolutionError,
    ParserError,
)
from pybind11_stubgen.parser.interface import IParser
from pybind11_stubgen.structs import (
    Alias,
    Argument,
    Attribute,
    Class,
    Docstring,
    Field,
    Function,
    Identifier,
    Import,
    InvalidExpression,
    Method,
    Module,
    Property,
    QualifiedName,
    ResolvedType,
    TypeVar_,
    Value,
)
from pybind11_stubgen.typing_ext import DynamicSize, FixedSize

logger = getLogger("pybind11_stubgen")


class RemoveSelfAnnotation(IParser):

    __any_t_name = QualifiedName.from_str("Any")
    __typing_any_t_name = QualifiedName.from_str("typing.Any")

    def handle_method(self, path: QualifiedName, method: Any) -> list[Method]:
        methods = super().handle_method(path, method)
        for method in methods:
            self._remove_self_arg_annotation(path, method.function)
        return methods

    def handle_property(self, path: QualifiedName, prop: Any) -> Property | None:
        prop = super().handle_property(path, prop)
        if prop is not None:
            if prop.getter is not None:
                self._remove_self_arg_annotation(path, prop.getter)
            if prop.setter is not None:
                self._remove_self_arg_annotation(path, prop.setter)

        return prop

    def _remove_self_arg_annotation(self, path: QualifiedName, func: Function) -> None:
        if len(func.args) == 0:
            return
        fully_qualified_class_name = QualifiedName(path[:-1])  # remove the method name
        first_arg = func.args[0]
        if (
            first_arg.name == "self"
            and isinstance(first_arg.annotation, ResolvedType)
            and not first_arg.annotation.parameters
            and (
                first_arg.annotation.name
                in {
                    self.__any_t_name,
                    self.__typing_any_t_name,
                    fully_qualified_class_name,
                    fully_qualified_class_name[-len(first_arg.annotation.name) :],
                }
            )
        ):
            first_arg.annotation = None


class FixMissingImports(IParser):
    def __init__(self):
        super().__init__()
        self.__extra_imports: set[Import] = set()
        self.__current_module: types.ModuleType | None = None
        self.__current_class: type | None = None

    def handle_alias(self, path: QualifiedName, origin: Any) -> Alias | None:
        result = super().handle_alias(path, origin)
        if result is None:
            return None
        self._add_import(result.origin)
        return result

    def handle_attribute(self, path: QualifiedName, attr: Any) -> Attribute | None:
        result = super().handle_attribute(path, attr)
        if result is None:
            return None
        if isinstance(result.annotation, ResolvedType):
            self._add_import(result.annotation.name)
        return result

    def handle_class(self, path: QualifiedName, class_: type) -> Class | None:
        old_class = self.__current_class
        self.__current_class = class_
        result = super().handle_class(path, class_)
        self.__current_class = old_class
        return result

    def handle_import(self, path: QualifiedName, origin: Any) -> Import | None:
        result = super().handle_import(path, origin)
        if result is None:
            return None
        self.__extra_imports.add(result)
        return result

    def handle_module(
        self, path: QualifiedName, module: types.ModuleType
    ) -> Module | None:
        old_imports = self.__extra_imports
        old_module = self.__current_module
        self.__extra_imports = set()
        self.__current_module = module
        result = super().handle_module(path, module)
        if result is not None:
            result.imports |= self.__extra_imports
        self.__extra_imports = old_imports
        self.__current_module = old_module
        return result

    def handle_type(self, type_: type) -> QualifiedName:
        result = super().handle_type(type_)
        if not inspect.ismodule(type_):
            self._add_import(result)
        return result

    def handle_value(self, value: Any) -> Value:
        result = super().handle_value(value)
        if inspect.isroutine(value) and result.is_print_safe:
            self._add_import(QualifiedName.from_str(result.repr))
        return result

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        result = super().parse_annotation_str(annotation_str)
        if isinstance(result, ResolvedType):
            self._add_import(result.name)
        return result

    def _add_import(self, name: QualifiedName) -> None:
        if len(name) == 0:
            return
        if len(name) == 1 and len(name[0]) == 0:
            return
        if hasattr(builtins, name[0]):
            return
        if self.__current_class is not None and hasattr(self.__current_class, name[0]):
            return
        if self.__current_module is not None and hasattr(
            self.__current_module, name[0]
        ):
            return
        module_name = self._get_parent_module(name)
        if module_name is None:
            self.report_error(NameResolutionError(name))
            return
        self.__extra_imports.add(Import(name=None, origin=module_name))

    def _get_parent_module(self, name: QualifiedName) -> QualifiedName | None:
        parent = name.parent
        while len(parent) != 0:
            if self._is_module(parent):
                if not self._is_accessible(name, from_module=parent):
                    return None
                return parent
            parent = parent.parent
        return None

    def _is_module(self, name: QualifiedName):
        try:
            return importlib.import_module(str(name)) is not None
        except ModuleNotFoundError:
            return False

    def _is_accessible(self, name: QualifiedName, from_module: QualifiedName) -> bool:
        try:
            parent = importlib.import_module(str(from_module))
        except ModuleNotFoundError:
            return False
        relative_path = name[len(from_module) :]
        for part in relative_path:
            if not hasattr(parent, part):
                return False
            parent = getattr(parent, part)
        return True


class FixMissing__future__AnnotationsImport(IParser):
    def handle_module(
        self, path: QualifiedName, module: types.ModuleType
    ) -> Module | None:
        result = super().handle_module(path, module)
        if result is None:
            return None
        result.imports.add(self._future(Identifier("annotations")))
        return result

    def _future(self, feature: Identifier) -> Import:
        return Import(
            name=feature, origin=QualifiedName((Identifier("__future__"), feature))
        )


class FixMissing__all__Attribute(IParser):
    def handle_module(
        self, path: QualifiedName, module: types.ModuleType
    ) -> Module | None:
        result = super().handle_module(path, module)
        if result is None:
            return None

        # don't override __all__
        for attr in result.attributes:
            if attr.name == Identifier("__all__"):
                return result

        all_names: list[str] = sorted(
            set(
                filter(
                    lambda name: not name.startswith("_"),
                    map(
                        str,
                        (
                            *(class_.name for class_ in result.classes),
                            *(attr.name for attr in result.attributes),
                            *(func.name for func in result.functions),
                            *(alias.name for alias in result.aliases),
                            *(
                                import_.name
                                for import_ in result.imports
                                if import_.name is not None
                            ),
                            *(sub_module.name for sub_module in result.sub_modules),
                        ),
                    ),
                )
            )
        )

        result.attributes.append(
            Attribute(
                name=Identifier("__all__"),
                value=self.handle_value(all_names),
                annotation=ResolvedType(name=QualifiedName.from_str("list[str]")),
            )
        )

        return result


class FixBuiltinTypes(IParser):
    _any_type = QualifiedName.from_str("typing.Any")

    def handle_type(self, type_: type) -> QualifiedName:
        if type_.__qualname__ == "PyCapsule" and type_.__module__ == "builtins":
            return self._any_type

        result = super().handle_type(type_)

        if result[0] == "builtins":
            if result[1] == "NoneType":
                return QualifiedName((Identifier("None"),))
            if result[1] in ("function", "builtin_function_or_method"):
                callable_t = self.parse_annotation_str("typing.Callable")
                assert isinstance(callable_t, ResolvedType)
                return callable_t.name
            return QualifiedName(result[1:])

        return result

    def report_error(self, error: ParserError):
        if isinstance(error, NameResolutionError):
            if error.name[0] in ["PyCapsule"]:
                return
        super().report_error(error)


class FixRedundantBuiltinsAnnotation(IParser):
    def handle_attribute(self, path: QualifiedName, attr: Any) -> Attribute | None:
        result = super().handle_attribute(path, attr)
        if result is None:
            return None
        if attr is None or inspect.ismodule(attr):
            result.annotation = None
        return result


class FixMissingNoneHashFieldAnnotation(IParser):
    def handle_field(self, path: QualifiedName, field: Any) -> Field | None:
        result = super().handle_field(path, field)
        if result is None:
            return None
        if field is None and path[-1] == "__hash__":
            result.attribute.annotation = self.parse_annotation_str(
                "typing.ClassVar[None]"
            )
        return result


class FixPEP585CollectionNames(IParser):
    __typing_collection_names: set[Identifier] = set(
        Identifier(name)
        for name in (
            "Dict",
            "List",
            "Set",
            "Tuple",
            "FrozenSet",
            "Type",
        )
    )

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        result = super().parse_annotation_str(annotation_str)
        if (
            not isinstance(result, ResolvedType)
            or len(result.name) != 2
            or result.name[0] != "typing"
        ):
            return result

        word = result.name[1]
        if word in self.__typing_collection_names:
            result.name = QualifiedName.from_str(f"{word.lower()}")

        return result


class FixTypingTypeNames(IParser):
    __typing_names: set[Identifier] = set(
        Identifier(name)
        for name in (
            "Annotated",
            "Any",
            "Buffer",
            "Callable",
            "Dict",
            "ItemsView",
            "Iterable",
            "Iterator",
            "KeysView",
            "List",
            "Literal",
            "Optional",
            "Sequence",
            "Set",
            "Tuple",
            "Union",
            "ValuesView",
            # Old pybind11 annotations were not capitalized
            "buffer",
            "iterable",
            "iterator",
            "sequence",
        )
    )
    __typing_extensions_names: set[Identifier] = set(
        Identifier(name)
        for name in (
            "buffer",
            "Buffer",
        )
    )

    def __init__(self):
        super().__init__()
        if sys.version_info < (3, 9):
            self.__typing_extensions_names.add(Identifier("Annotated"))
        if sys.version_info < (3, 8):
            self.__typing_extensions_names.add(Identifier("Literal"))

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        result = super().parse_annotation_str(annotation_str)
        return self._parse_annotation_str(result)

    def _parse_annotation_str(
        self, result: ResolvedType | InvalidExpression | Value
    ) -> ResolvedType | InvalidExpression | Value:
        if not isinstance(result, ResolvedType):
            return result

        result.parameters = (
            [self._parse_annotation_str(p) for p in result.parameters]
            if result.parameters is not None
            else None
        )

        if len(result.name) != 1:
            return result

        word = result.name[0]
        if word in self.__typing_names:
            package = "typing"
            if word in self.__typing_extensions_names:
                package = "typing_extensions"
            result.name = QualifiedName.from_str(
                f"{package}.{word[0].upper()}{word[1:]}"
            )
        if word == "function" and result.parameters is None:
            result.name = QualifiedName.from_str("typing.Callable")
        if word in ("object", "handle") and result.parameters is None:
            result.name = QualifiedName.from_str("typing.Any")

        return result


class FixCurrentModulePrefixInTypeNames(IParser):
    def __init__(self):
        super().__init__()
        self.__current_module: QualifiedName = QualifiedName()

    def handle_alias(self, path: QualifiedName, origin: Any) -> Alias | None:
        result = super().handle_alias(path, origin)
        if result is None:
            return None
        result.origin = self._strip_current_module(result.origin)
        return result

    def handle_attribute(self, path: QualifiedName, attr: Any) -> Attribute | None:
        result = super().handle_attribute(path, attr)
        if result is None:
            return None
        if isinstance(result.annotation, ResolvedType):
            result.annotation.name = self._strip_current_module(result.annotation.name)
        return result

    def handle_module(
        self, path: QualifiedName, module: types.ModuleType
    ) -> Module | None:
        tmp = self.__current_module
        self.__current_module = path
        result = super().handle_module(path, module)
        self.__current_module = tmp
        return result

    def handle_type(self, type_: type) -> QualifiedName:
        result = super().handle_type(type_)
        return self._strip_current_module(result)

    def handle_value(self, value: Any) -> Value:
        result = super().handle_value(value)
        if inspect.isroutine(value):
            result.repr = str(
                self._strip_current_module(QualifiedName.from_str(result.repr))
            )
        return result

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        result = super().parse_annotation_str(annotation_str)
        if isinstance(result, ResolvedType):
            result.name = self._strip_current_module(result.name)
        return result

    def _strip_current_module(self, name: QualifiedName) -> QualifiedName:
        if name[: len(self.__current_module)] == self.__current_module:
            return QualifiedName(name[len(self.__current_module) :])
        return name


class FixValueReprRandomAddress(IParser):
    """
    repr examples:
        <capsule object NULL at 0x7fdfdf8b5f20> # PyCapsule
        <foo.bar.Baz object at 0x7fdfdf8b5f20>
    """

    _pattern = re.compile(
        r"<(?P<name>[\w.]+) object "
        r"(?P<capsule>\w+\s)*at "
        r"(?P<address>0x[a-fA-F0-9]+)>"
    )

    def handle_value(self, value: Any) -> Value:
        result = super().handle_value(value)
        result.repr = self._pattern.sub(r"<\g<name> object>", result.repr)
        return result


class FixNumpyArrayDimAnnotation(IParser):
    __array_names: set[QualifiedName] = {
        QualifiedName.from_str("numpy.ndarray"),
        *(
            QualifiedName.from_str(f"scipy.sparse.{storage}_{arr}")
            for storage in ["bsr", "coo", "csr", "csc", "dia", "dok", "lil"]
            for arr in ["array", "matrix"]
        ),
    }
    # NB: Not using full name due to ambiguity `typing.Annotated` vs
    #     `typing_extension.Annotated` in different python versions
    #     Rely on later fix by `FixTypingTypeNames`
    __annotated_name = QualifiedName.from_str("Annotated")
    numpy_primitive_types: set[QualifiedName] = set(
        map(
            QualifiedName.from_str,
            (
                "bool",
                *map(
                    lambda name: f"numpy.{name}",
                    (
                        "uint8",
                        "int8",
                        "uint16",
                        "int16",
                        "uint32",
                        "int32",
                        "uint64",
                        "int64",
                        "float16",
                        "float32",
                        "float64",
                        "complex32",
                        "complex64",
                        "longcomplex",
                    ),
                ),
            ),
        )
    )

    __DIM_VARS = ["n", "m"]

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        # Affects types of the following pattern:
        #       ARRAY_T[PRIMITIVE_TYPE[*DIMS], *FLAGS]
        # Replace with:
        #       Annotated[ARRAY_T, PRIMITIVE_TYPE, FixedSize/DynamicSize[*DIMS], *FLAGS]

        result = super().parse_annotation_str(annotation_str)
        if (
            not isinstance(result, ResolvedType)
            or result.name not in self.__array_names
            or result.parameters is None
            or len(result.parameters) == 0
        ):
            return result

        scalar_with_dims = result.parameters[0]  # e.g. numpy.float64[32, 32]
        flags = result.parameters[1:]

        if (
            not isinstance(scalar_with_dims, ResolvedType)
            or scalar_with_dims.name not in self.numpy_primitive_types
        ):
            return result

        result = ResolvedType(
            name=self.__annotated_name,
            parameters=[
                self.parse_annotation_str(str(result.name)),
                ResolvedType(scalar_with_dims.name),
            ],
        )

        assert result.parameters is not None
        if (
            scalar_with_dims.parameters is not None
            and len(scalar_with_dims.parameters) >= 0
        ):
            dims = self.__to_dims(scalar_with_dims.parameters)
            if dims is not None and len(dims) > 0:
                result.parameters += [
                    self.handle_value(self.__wrap_with_size_helper(dims))
                ]

        result.parameters += flags

        return result

    def __wrap_with_size_helper(self, dims: list[int | str]) -> FixedSize | DynamicSize:
        if all(isinstance(d, int) for d in dims):
            return_t = FixedSize
        else:
            return_t = DynamicSize

        # TRICK: Use `self.handle_type` to make `FixedSize`/`DynamicSize`
        #        properly added to the list of imports
        self.handle_type(return_t)
        return return_t(*dims)  # type: ignore[arg-type]

    def __to_dims(
        self, dimensions: Sequence[ResolvedType | Value | InvalidExpression]
    ) -> list[int | str] | None:
        result = []
        for dim_param in dimensions:
            if isinstance(dim_param, Value):
                try:
                    dim = int(dim_param.repr)
                except ValueError:
                    return None
            elif isinstance(dim_param, ResolvedType):
                dim = str(dim_param)
                if dim not in self.__DIM_VARS:
                    return None
            else:
                return None
            result.append(dim)
        return result

    def report_error(self, error: ParserError) -> None:
        if (
            isinstance(error, NameResolutionError)
            and len(error.name) == 1
            and len(error.name[0]) == 1
            and error.name[0] in self.__DIM_VARS
        ):
            # Ignores all unknown 'm' and 'n' regardless of the context
            return
        super().report_error(error)


class FixNumpyArrayDimTypeVar(IParser):
    __array_names: set[QualifiedName] = {QualifiedName.from_str("numpy.ndarray")}
    numpy_primitive_types = FixNumpyArrayDimAnnotation.numpy_primitive_types

    __DIM_VARS: set[str] = set()

    def handle_module(
        self, path: QualifiedName, module: types.ModuleType
    ) -> Module | None:
        result = super().handle_module(path, module)
        if result is None:
            return None

        if self.__DIM_VARS:
            # the TypeVar_'s generated code will reference `typing`
            result.imports.add(
                Import(name=None, origin=QualifiedName.from_str("typing"))
            )

            for name in self.__DIM_VARS:
                result.type_vars.append(
                    TypeVar_(
                        name=Identifier(name),
                        bound=self.parse_annotation_str("int"),
                    ),
                )

        self.__DIM_VARS.clear()

        return result

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        # Affects types of the following pattern:
        #       numpy.ndarray[PRIMITIVE_TYPE[*DIMS], *FLAGS]
        # Replace with:
        #       numpy.ndarray[tuple[M, Literal[1]], numpy.dtype[numpy.float32]]

        result = super().parse_annotation_str(annotation_str)

        if not isinstance(result, ResolvedType):
            return result

        # handle unqualified, single-letter annotation as a TypeVar
        if len(result.name) == 1 and len(result.name[0]) == 1:
            result.name = QualifiedName.from_str(result.name[0].upper())
            self.__DIM_VARS.add(result.name[0])

        if result.name not in self.__array_names:
            return result

        # ndarray is generic and should have 2 type arguments
        if result.parameters is None or len(result.parameters) == 0:
            result.parameters = [
                self.parse_annotation_str("Any"),
                ResolvedType(
                    name=QualifiedName.from_str("numpy.dtype"),
                    parameters=[self.parse_annotation_str("Any")],
                ),
            ]
            return result

        scalar_with_dims = result.parameters[0]  # e.g. numpy.float64[32, 32]

        if (
            not isinstance(scalar_with_dims, ResolvedType)
            or scalar_with_dims.name not in self.numpy_primitive_types
        ):
            return result

        name = scalar_with_dims.name
        # Pybind annotates a bool Python type, which cannot be used with
        # numpy.dtype because it does not inherit from numpy.generic.
        # Only numpy.bool_ works reliably with both NumPy 1.x and 2.x.
        if str(name) == "bool":
            name = QualifiedName.from_str("numpy.bool_")
        dtype = ResolvedType(
            name=QualifiedName.from_str("numpy.dtype"),
            parameters=[ResolvedType(name=name)],
        )

        shape = self.parse_annotation_str("Any")
        if (
            scalar_with_dims.parameters is not None
            and len(scalar_with_dims.parameters) > 0
        ):
            dims = self.__to_dims(scalar_with_dims.parameters)
            if dims is not None:
                shape = self.parse_annotation_str("Tuple")
                assert isinstance(shape, ResolvedType)
                shape.parameters = []
                for dim in dims:
                    if isinstance(dim, int):
                        # self.parse_annotation_str will qualify Literal with either
                        # typing or typing_extensions and add the import to the module
                        literal_dim = self.parse_annotation_str("Literal")
                        assert isinstance(literal_dim, ResolvedType)
                        literal_dim.parameters = [Value(repr=str(dim))]
                        shape.parameters.append(literal_dim)
                    else:
                        shape.parameters.append(
                            ResolvedType(name=QualifiedName.from_str(dim))
                        )

        result.parameters = [shape, dtype]
        return result

    def __to_dims(
        self, dimensions: Sequence[ResolvedType | Value | InvalidExpression]
    ) -> list[int | str] | None:
        result: list[int | str] = []
        for dim_param in dimensions:
            if isinstance(dim_param, Value):
                try:
                    dim = int(dim_param.repr)
                except ValueError:
                    return None
            elif isinstance(dim_param, ResolvedType):
                dim = str(dim_param)
            else:
                return None
            result.append(dim)
        return result

    def report_error(self, error: ParserError) -> None:
        if (
            isinstance(error, NameResolutionError)
            and len(error.name) == 1
            and error.name[0] in self.__DIM_VARS
        ):
            # allow type variables, which are manually resolved in `handle_module`
            return
        super().report_error(error)


class FixNumpyArrayRemoveParameters(IParser):
    __ndarray_name = QualifiedName.from_str("numpy.ndarray")

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        result = super().parse_annotation_str(annotation_str)
        if isinstance(result, ResolvedType) and result.name == self.__ndarray_name:
            result.parameters = None
        return result


class FixScipyTypeArguments(IParser):
    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        result = super().parse_annotation_str(annotation_str)

        if not isinstance(result, ResolvedType):
            return result

        # scipy.sparse arrays/matrices are not currently generic and do not accept type
        # arguments
        if result.name[:2] == ("scipy", "sparse"):
            result.parameters = None

        return result


class FixNumpyDtype(IParser):
    __numpy_dtype = QualifiedName.from_str("numpy.dtype")

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        result = super().parse_annotation_str(annotation_str)

        if not isinstance(result, ResolvedType) or result.parameters:
            return result

        # numpy.dtype is generic and should have a type argument
        if result.name[:1] == ("dtype",) or result.name[:2] == ("numpy", "dtype"):
            result.name = self.__numpy_dtype
            result.parameters = [self.parse_annotation_str("Any")]

        return result


class FixNumpyArrayFlags(IParser):
    __ndarray_name = QualifiedName.from_str("numpy.ndarray")
    __flags: set[QualifiedName] = {
        QualifiedName.from_str("flags.writeable"),
        QualifiedName.from_str("flags.c_contiguous"),
        QualifiedName.from_str("flags.f_contiguous"),
    }

    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        result = super().parse_annotation_str(annotation_str)
        if isinstance(result, ResolvedType) and result.name == self.__ndarray_name:
            if result.parameters is not None:
                for param in result.parameters:
                    if isinstance(param, ResolvedType) and param.name in self.__flags:
                        param.name = QualifiedName.from_str(
                            f"numpy.ndarray.{param.name}"
                        )

        return result

    def report_error(self, error: ParserError) -> None:
        if isinstance(error, NameResolutionError) and error.name in self.__flags:
            return
        super().report_error(error)


class FixRedundantMethodsFromBuiltinObject(IParser):
    def handle_method(self, path: QualifiedName, method: Any) -> list[Method]:
        result = super().handle_method(path, method)
        return [
            m
            for m in result
            if not (
                m.function.name == "__init__"
                and m.function.doc == object.__init__.__doc__
            )
        ]


class ReplaceReadWritePropertyWithField(IParser):
    def handle_class_member(
        self, path: QualifiedName, class_: type, obj: Any
    ) -> Docstring | Alias | Class | list[Method] | Field | Property | None:
        result = super().handle_class_member(path, class_, obj)
        if isinstance(result, Property):
            if (
                result.doc is None
                and result.getter is not None
                and result.setter is not None
                and len(result.getter.args) == 1
                and len(result.setter.args) == 2
                and result.getter.doc is None
                and result.setter.doc is None
                and result.getter.returns == result.setter.args[1].annotation
            ):
                return Field(
                    attribute=Attribute(
                        name=result.name, annotation=result.getter.returns, value=None
                    ),
                    modifier=None,
                )
        return result


class FixMissingFixedSizeImport(IParser):
    def parse_annotation_str(
        self, annotation_str: str
    ) -> ResolvedType | InvalidExpression | Value:
        # Accommodate to
        # https://github.com/pybind/pybind11/pull/4679
        result = super().parse_annotation_str(annotation_str)
        if (
            isinstance(result, Value)
            and result.repr.startswith("FixedSize(")
            and result.repr.endswith(")")
        ):
            try:
                dimensions = map(
                    int,
                    result.repr[len("FixedSize(") : -len(")")].split(","),
                )
            except ValueError:
                pass
            else:
                # call `handle_type` to trigger implicit import
                self.handle_type(FixedSize)
                return self.handle_value(FixedSize(*dimensions))
        return result


class FixMissingEnumMembersAnnotation(IParser):
    __class_var_dict = ResolvedType(
        name=QualifiedName.from_str("typing.ClassVar"),
        parameters=[ResolvedType(name=QualifiedName.from_str("dict"))],
    )

    def handle_field(self, path: QualifiedName, field: Any) -> Field | None:
        result = super().handle_field(path, field)
        if result is None:
            return None
        if (
            path[-1] == "__members__"
            and isinstance(field, dict)
            and result.attribute.annotation == self.__class_var_dict
        ):
            assert isinstance(result.attribute.annotation, ResolvedType)
            dict_type = self._guess_dict_type(field)
            if dict_type is not None:
                result.attribute.annotation.parameters = [dict_type]
        return result

    def _guess_dict_type(self, d: dict) -> ResolvedType | None:
        if len(d) == 0:
            return None
        key_types = set()
        value_types = set()
        for key, value in d.items():
            key_types.add(self.handle_type(type(key)))
            value_types.add(self.handle_type(type(value)))
        if len(key_types) == 1:
            key_type = [ResolvedType(name=t) for t in key_types][0]
        else:
            union_t = self.parse_annotation_str("typing.Union")
            assert isinstance(union_t, ResolvedType)
            key_type = ResolvedType(
                name=union_t.name, parameters=[ResolvedType(name=t) for t in key_types]
            )
        if len(value_types) == 1:
            value_type = [ResolvedType(name=t) for t in value_types][0]
        else:
            union_t = self.parse_annotation_str("typing.Union")
            assert isinstance(union_t, ResolvedType)
            value_type = ResolvedType(
                name=union_t.name,
                parameters=[ResolvedType(name=t) for t in value_types],
            )
        dict_t = self.parse_annotation_str("typing.Dict")
        assert isinstance(dict_t, ResolvedType)
        return ResolvedType(
            name=dict_t.name,
            parameters=[key_type, value_type],
        )


class FixPybind11EnumStrDoc(IParser):
    def handle_class_member(
        self, path: QualifiedName, class_: type, obj: Any
    ) -> Docstring | Alias | Class | list[Method] | Field | Property | None:
        result = super().handle_class_member(path, class_, obj)
        if not isinstance(result, list) or not hasattr(  # list[Method]
            class_, "__members__"
        ):  # class is enum
            return result
        for method in result:
            assert isinstance(method, Method)
            if (
                method.function.name != "__str__"
                or method.function.doc != "name(self: handle) -> str\n"
            ):
                continue
            method.function.args = [
                Argument(
                    name=Identifier("self"),
                    # annotation=ResolvedType(self.handle_type(class_)),
                )
            ]
            method.function.returns = ResolvedType(name=QualifiedName.from_str("str"))
            # Note: Wrong function name in __str.__.__doc__ triggered
            #       generic (*args, **kwargs) signature which in turn
            #       recognized as a static method signature
            method.modifier = None
            method.function.doc = None
        return result


class OverridePrintSafeValues(IParser):
    _print_safe_values: re.Pattern | None

    def __init__(self):
        super().__init__()
        self._print_safe_values = None

    def set_print_safe_value_pattern(self, pattern: re.Pattern):
        self._print_safe_values = pattern

    def parse_value_str(self, value: str) -> Value | InvalidExpression:
        result = super().parse_value_str(value)
        if (
            self._print_safe_values is not None
            and isinstance(result, Value)
            and not result.is_print_safe
            and self._print_safe_values.match(result.repr) is not None
        ):
            result.is_print_safe = True
        return result


class RewritePybind11EnumValueRepr(IParser):
    _pybind11_enum_pattern = re.compile(r"<(?P<enum>\w+(\.\w+)+): (?P<value>-?\d+)>")
    # _pybind11_enum_pattern = re.compile(r"<(?P<enum>\w+(\.\w+)+): (?P<value>\d+)>")
    _unknown_enum_classes: set[str] = set()

    def __init__(self):
        super().__init__()
        self._pybind11_enum_locations: dict[re.Pattern, str] = {}

    def set_pybind11_enum_locations(self, locations: dict[re.Pattern, str]):
        self._pybind11_enum_locations = locations

    def parse_value_str(self, value: str) -> Value | InvalidExpression:
        value = value.strip()
        match = self._pybind11_enum_pattern.match(value)
        if match is not None:
            enum_qual_name = match.group("enum")
            enum_class_str, entry = enum_qual_name.rsplit(".", maxsplit=1)
            for pattern, prefix in self._pybind11_enum_locations.items():
                if pattern.match(enum_class_str) is None:
                    continue
                enum_class = self.parse_annotation_str(f"{prefix}.{enum_class_str}")
                if isinstance(enum_class, ResolvedType):
                    return Value(repr=f"{enum_class.name}.{entry}", is_print_safe=True)
        return super().parse_value_str(value)

    def report_error(self, error: ParserError) -> None:
        if isinstance(error, InvalidExpressionError):
            match = self._pybind11_enum_pattern.match(error.expression)
            if match is not None:
                enum_qual_name = match.group("enum")
                enum_class_str, entry = enum_qual_name.rsplit(".", maxsplit=1)
                self._unknown_enum_classes.add(enum_class_str)
        super().report_error(error)

    def finalize(self):
        if self._unknown_enum_classes:
            logger.warning(
                "Enum-like str representations were found with no "
                "matching mapping to the enum class location.\n"
                "Use `--enum-class-locations` to specify "
                "full path to the following enum(s):\n"
                + "\n".join(f" - {c}" for c in self._unknown_enum_classes)
            )
        super().finalize()
