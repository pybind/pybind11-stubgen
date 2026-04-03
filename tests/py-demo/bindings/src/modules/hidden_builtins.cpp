#include "modules.h"

#include <pybind11/pytypes.h>

void bind_hidden_builtins_module(py::module&& m) {
  py::dict readonly_dict{};

  auto types_m = py::module::import("types");
  auto mappingproxy_t = types_m.attr("MappingProxyType");
  auto none_t = types_m.attr("NoneType");

  m.attr("mapping_proxy") = mappingproxy_t(readonly_dict);
  m.attr("none") = none_t();
}
