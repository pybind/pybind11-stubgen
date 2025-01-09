#pragma once
#include <string>

namespace demo
{
    // note: class stubs must not be sorted
    // https://github.com/sizmailov/pybind11-stubgen/issues/231

    struct MyBase {
      struct Inner{};
      std::string name;
    };

    struct Derived : MyBase {
      int count;
    };
}
