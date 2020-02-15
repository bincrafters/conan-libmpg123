cmake_minimum_required(VERSION 2.8.12)
project(cmake_wrapper)

if(EXISTS "${CMAKE_BINARY_DIR}/conanbuildinfo.cmake")
  include("${CMAKE_BINARY_DIR}/conanbuildinfo.cmake")
else()
  include(conanbuildinfo.cmake)
endif()
conan_basic_setup()

if(MSVC)
  add_compile_definitions("strcasecmp=_strcmpi")
  add_compile_definitions("strncasecmp=_strnicmp")
endif()


add_subdirectory("source_subfolder/ports/cmake")
