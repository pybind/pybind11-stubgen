#include "modules.h"

PYBIND11_MODULE(_bindings, m) {
    bind_classes_module(m.def_submodule("classes"));
    bind_eigen_module(m.def_submodule("eigen"));
    bind_enum_module(m.def_submodule("enum"));
    bind_aliases_module(m.def_submodule("aliases"));
    bind_flawed_bindings_module(m.def_submodule("flawed_bindings"));
    bind_functions_module(m.def_submodule("functions"));
    bind_issues_module(m.def_submodule("issues"));
    bind_methods_module(m.def_submodule("methods"));
    bind_numpy_module(m.def_submodule("numpy"));
    bind_properties_module(m.def_submodule("properties"));
    bind_stl_module(m.def_submodule("stl"));
    bind_stl_bind_module(m.def_submodule("stl_bind"));
    bind_typing_module(m.def_submodule("typing"));
    bind_values_module(m.def_submodule("values"));
    bind_hidden_builtins_module(m.def_submodule("hidden_builtins"));
}
