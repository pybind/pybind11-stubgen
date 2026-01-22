#include "modules.h"

#if PYBIND11_VERSION_AT_LEAST(2, 12)

#include <pybind11/typing.h>

#endif

#include <pybind11/stl.h>
#include <pybind11/functional.h>

#include <variant>
#include <list>

#include <demo/sublibA/add.h>

namespace {
    void generic(const py::args &args, const py::kwargs &kwargs) {}

    class Foo {
        int x;
    public:
        explicit Foo(int x) : x(x) {}
    };
}; // namespace

void bind_functions_module(py::module &&m) {
    m.def("add", demo::sublibA::add);
    {

        m.def(
                "mul",
                [](int x, int y) { return x * y; },
                "Multiply x and y (int)",
                py::arg("x"),
                py::arg("y"));
        m.def(
                "mul",
                [](double p, double q) { return p * q; },
                "Multiply p and q (double)",
                py::arg("p"),
                py::arg("q"));
    }

    m.def("func_w_anon_args", [](int x, int y, int z) {});

#if PYBIND11_VERSION_AT_LEAST(2, 6)
    m.def(
            "func_w_named_pos_args",
            [](int x, int y, int z) {},
            py::arg("x"),
            py::arg("y"),
            py::arg("z"),
            py::pos_only());

    m.def(
            "pos_kw_only_mix",
            [](int i, int j, int k) { return py::make_tuple(i, j, k); },
            py::arg("i"),
            py::pos_only(),
            py::arg("j"),
            py::kw_only(),
            py::arg("k"));
    m.def("generic", &generic);

    m.def(
            "pos_kw_only_variadic_mix",
            [](int i, int j, py::args &, int k, py::kwargs &) { return py::make_tuple(i, j, k); },
            py::arg("i"),
            py::pos_only(),
            py::arg("j"),
            py::kw_only(),
            py::arg("k"));
#endif
    m.def("accept_callable", [](py::function &callable) { return callable(); });
    m.def("accept_py_object", [](py::object &object) { return py::str(object); });
    m.def("accept_py_handle", [](py::handle &handle) { return py::str(handle); });

#if PYBIND11_VERSION_AT_LEAST(2, 12)
    m.def("accept_annotated_callable",
          [](py::typing::Callable<int(int, int)> &callable) { return callable(13, 42); });
#endif

#if PYBIND11_VERSION_AT_LEAST(2, 10)
    m.def("accept_frozenset", [](const py::frozenset &) {});
#endif
    m.def("accept_set", [](const py::set &) {});

    m.def("default_int_arg", [](int n) {}, py::arg("n") = 5);
    m.def("default_optional_arg", [](std::optional<int> n) {}, py::arg("n") = py::none());
    {
        auto default_value = py::list();
        default_value.append(py::int_(1));
        default_value.append(py::int_(2));
        default_value.append(py::int_(6));
        default_value.append(py::int_(18));
        m.def("default_list_arg", [](py::list &l) {}, py::arg("l") = default_value);
    }
    py::class_<Foo> pyFoo(m, "Foo");
    pyFoo.def(py::init<int>());
    m.def("default_custom_arg", [](Foo &foo) {}, py::arg_v("foo", Foo(5), "Foo(5)"));
    m.def("pass_callback", [](std::function<Foo(Foo &)> &callback) { return Foo(13); });
    m.def("nested_types", [](std::variant<std::list<Foo>, Foo> arg){ return arg; });
}
