from conans import ConanFile, tools, CMake
from conans.tools import Version
from conans.errors import ConanInvalidConfiguration
import os


class LibMPG123Conan(ConanFile):
    name = "libmpg123"
    description = "mpg123 is the fast and Free (LGPL license) real time MPEG Audio Layer 1, 2 and 3 decoding library and console player"
    topics = ("conan", "mpg123", "libmpg123", "mpeg", "audio", "decoding", "multimedia")
    url = "https://github.com/bincrafters/conan-libmpg123"
    homepage = "https://www.mpg123.de"
    license = "LGPL-2.0-only"
    exports_sources = ["CMakeLists.txt", "patches/*"]
    generators = "cmake"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"
    _cmake = None

    @property
    def _is_msvc(self):
        return self.settings.compiler == "Visual Studio"

    def configure(self):
        del self.settings.compiler.libcxx
        del self.settings.compiler.cppstd

        compiler_version = Version(self.settings.compiler.version.value)
        if self.settings.compiler == "Visual Studio" and compiler_version < "14":
            raise ConanInvalidConfiguration("libmpg123 could not be built by Visual Studio < 14")

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def build_requirements(self):
        if not tools.which("yasm"):
            self.build_requires("yasm/1.3.0")

    def source(self):
        tools.get(**self.conan_data["sources"][self.version])
        extracted_dir = "mpg123-" + self.version
        os.rename(extracted_dir, self._source_subfolder)

    def _configure_cmake(self):
        if not self._cmake:
            self._cmake = CMake(self)
            self._cmake.configure(build_folder=self._build_subfolder)
        return self._cmake

    def build(self):
        for patch in self.conan_data.get("patches", {}).get(self.version, []):
            tools.patch(**patch)
        cmake = self._configure_cmake()
        cmake.build()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        cmake = self._configure_cmake()
        cmake.install()
        src_folder = os.path.join(self._source_subfolder, "src", "libmpg123")
        self.copy(pattern="*fmt123.h", dst="include", src=src_folder)
        if self._is_msvc:
            self.copy(pattern="*mpg123.h.in", dst="include", src=src_folder)
            self.copy(pattern="*config.h", dst="include", src=os.path.join(self._source_subfolder, "ports", "MSVC++"))
            self.copy(pattern="*mpg123.h", dst="include", src=os.path.join(self._source_subfolder, "ports", "MSVC++"))

        tools.rmdir(os.path.join(self.package_folder, "share"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "cmake"))
        tools.rmdir(os.path.join(self.package_folder, "lib", "pkgconfig"))
    
    def package_info(self):
        self.cpp_info.libs = ["mpg123"]
        self.cpp_info.names["cmake_find_package"] = "mpg123"
        self.cpp_info.names["cmake_find_package_multi"] = "mpg123"
        self.cpp_info.names["pkg_config"] = "libmpg123"
        if self._is_msvc and self.options.shared:
            self.cpp_info.defines.append("LINK_MPG123_DLL")
        if self.settings.os == "Windows":
            self.cpp_info.system_libs.append("shlwapi")
        elif self.settings.os == "Linux":
            self.cpp_info.system_libs.extend(["dl", "m"])
