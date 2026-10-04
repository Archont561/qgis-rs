# The native manager's C++ test target.
#
# Built and run by `pixi run xtask test-cpp`, which turbo reaches through
# @qgis/rust's `test` script, so `pixi run ci` covers this suite like every
# other (D10: the automation is an xtask subcommand, not a shell file).
#
# It compiles the QGIS-free half of the manager — `conversions.cpp` — and
# nothing else. No QGIS, no QApplication, no display: the suite is headless
# because there is nothing in it that could want a screen. The QGIS-linked
# half is covered by the Rust integration tests in `crates/qgis-sys/tests`.

cmake_minimum_required(VERSION 3.25)

project(qgis_sys_cpp_tests LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)
set(CMAKE_CXX_EXTENSIONS OFF)

find_package(Qt5 REQUIRED COMPONENTS Core)
find_package(GTest REQUIRED)
find_package(rapidcheck REQUIRED)

enable_testing()

set(SHIM_DIR "${CMAKE_CURRENT_SOURCE_DIR}/../..")

add_executable(conversions_test
  conversions_test.cpp
  "${SHIM_DIR}/src/native_manager/conversions.cpp"
)

target_include_directories(conversions_test PRIVATE "${SHIM_DIR}/include")

# The same warnings-as-errors contract build.rs compiles the shim under, so a
# warning cannot be introduced here and discovered by the Rust build instead.
target_compile_options(conversions_test PRIVATE -Wall -Wextra -Werror)

target_link_libraries(conversions_test PRIVATE
  Qt5::Core
  GTest::gtest
  GTest::gtest_main
  rapidcheck
)

add_test(NAME conversions COMMAND conversions_test)
