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

    // Cross-reference / "cyclic" test case (issue #231, PR #275):
    // Binding registration order here is ParIterBase, then ParticleContainer,
    // then ParIter.
    // ParticleContainer.Iterator is an alias to ParIter (cross-ref).
    // ParIter inherits ParIterBase and takes ParticleContainer in __init__.
    // The topological sort must put ParIterBase before ParIter;
    // from __future__ import annotations handles the annotation back-refs.
    {
        auto pyParIterBase = py::class_<demo::ParIterBase>(m, "ParIterBase");
        pyParIterBase.def_readwrite("level", &demo::ParIterBase::level);

        auto pyParticleContainer = py::class_<demo::ParticleContainer>(m, "ParticleContainer");
        pyParticleContainer.def_readwrite("name", &demo::ParticleContainer::name);

        auto pyParIter = py::class_<demo::ParIter, demo::ParIterBase>(m, "ParIter");
        pyParIter.def(py::init<demo::ParticleContainer&, int>(),
                      py::arg("particle_container"), py::arg("level"));

        // Bind after ParIter is registered so pybind11 resolves the Python type
        pyParticleContainer.def("process", &demo::ParticleContainer::process);

        // Alias: ParticleContainer.Iterator = ParIter
        pyParticleContainer.attr("Iterator") = pyParIter;
    }

    {
        py::register_exception<demo::CppException>(m, "CppException");
    }
}
