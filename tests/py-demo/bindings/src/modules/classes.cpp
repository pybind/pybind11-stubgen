#include "modules.h"

#include <demo/Foo.h>
#include <demo/Inheritance.h>
#include <demo/NestedClasses.h>

void bind_classes_module(py::module&&m) {

    {
        auto pyOuter = py::class_<demo::Outer>(m, "Outer");
        auto pyInner = py::class_<demo::Outer::Inner>(pyOuter, "Inner");

        py::enum_<demo::Outer::Inner::NestedEnum>(pyInner, "NestedEnum")
            .value("ONE", demo::Outer::Inner::NestedEnum::ONE)
            .value("TWO", demo::Outer::Inner::NestedEnum::TWO);

        pyInner.def_readwrite("value", &demo::Outer::Inner::value);
        pyOuter.def_readwrite("inner", &demo::Outer::inner);
    }

    {
        py::class_<demo::MyBase> pyMyBase(m, "MyBase");

        pyMyBase.def_readwrite("name", &demo::MyBase::name);

        py::class_<demo::MyBase::Inner>(pyMyBase, "Inner");

        py::class_<demo::Derived, demo::MyBase>(m, "Derived")
            .def_readwrite("count", &demo::Derived::count);

    }
    {
        auto pyFoo = py::class_<demo::Foo>(m, "Foo");
        pyFoo.def(py::init<>()).def("f", &demo::Foo::f);

        py::class_<demo::Foo::Child>(pyFoo, "FooChild")
            .def(py::init<>())
            .def("g", &demo::Foo::Child::g);
    }

    {
        py::register_exception<demo::CppException>(m, "CppException");
    }
}
