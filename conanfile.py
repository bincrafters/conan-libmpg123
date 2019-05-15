# -*- coding: utf-8 -*-

from conans import ConanFile, tools, AutoToolsBuildEnvironment, MSBuild
from conans.model.version import Version
from conans.errors import ConanInvalidConfiguration
import os
import glob


class LibMPG123Conan(ConanFile):
    name = "libmpg123"
    version = "1.25.10"
    description = "mpg123  is the fast and Free (LGPL license) real time MPEG Audio Layer 1, 2 and 3 decoding library and console player"
    topics = ("conan", "mpg123", "libmpg123", "mpeg", "audio", "decoding", "multimedia")
    url = "https://github.com/bincrafters/conan-libmpg123"
    homepage = "https://www.mpg123.de/"
    author = "Bincrafters <bincrafters@gmail.com>"
    license = "LGPL-2.0-only"
    exports = ["LICENSE.md"]
    exports_sources = ["patches/*.patch"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    @property
    def _is_msvc(self):
        return self.settings.compiler == "Visual Studio"

    def configure(self):
        compiler_version = Version(self.settings.compiler.version.value)
        if self.settings.compiler == "Visual Studio" and compiler_version < "14":
            raise ConanInvalidConfiguration("libmpg123 could not be built by Visual Studio < 14")

    def config_options(self):
        if self.settings.os == 'Windows':
            del self.options.fPIC

    def build_requirements(self):
        if tools.os_info.is_windows:
            if "CONAN_BASH_PATH" not in os.environ:
                self.build_requires("msys2_installer/latest@bincrafters/stable")
        if not tools.which("yasm"):
            self.build_requires("yasm_installer/1.3.0@bincrafters/stable")

    def source(self):
        source_url = "https://netcologne.dl.sourceforge.net/project/mpg123/mpg123/{v}/mpg123-{v}.tar.bz2".format(v=self.version)
        tools.get(source_url, sha256="6c1337aee2e4bf993299851c70b7db11faec785303cfca3a5c3eb5f329ba7023")
        os.rename("mpg123-" + self.version, self._source_subfolder)

    def build(self):
        if self._is_msvc:
            self._build_msvc()
        else:
            self._build_configure()

    def _build_msvc(self):
        for filename in glob.glob("patches/*.patch"):
            self.output.info('applying patch "%s"' % filename)
            tools.patch(base_path=self._source_subfolder, patch_file=filename)

        with tools.chdir(os.path.join(self._source_subfolder, "ports", "MSVC++", "2015", "win32", "libmpg123")):
            configuration = str(self.settings.build_type) + "_x86"
            if self.options.shared:
                configuration += "_Dll"
            msbuild = MSBuild(self)
            msbuild.build(project_file="libmpg123.vcxproj", build_type=configuration)

    def _build_configure(self):
        with tools.chdir(self._source_subfolder):
            args = ["--enable-debug=yes" if self.settings.build_type == "Debug" else "--enable-debug=no"]
            if self.options.shared:
                args.extend(["--disable-static", "--enable-shared"])
            else:
                args.extend(["--enable-static", "--disable-shared"])
            if self.settings.os == "Android":
                args.extend(['--disable-buffer', '--with-cpu=generic_fpu'])
            if self.settings.os == "Emscripten":
                args.append("--with-default-audio=dummy")
            env_build = AutoToolsBuildEnvironment(self)
            env_build.configure(args=args)
            env_build.make()
            env_build.install()

    def package(self):
        self.copy(pattern="COPYING", dst="licenses", src=self._source_subfolder)
        if self._is_msvc:
            src_folder = os.path.join(self._source_subfolder, "src", "libmpg123")
            self.copy(pattern="*mpg123.h.in", dst="include", src=src_folder)
            self.copy(pattern="*fmt123.h", dst="include", src=src_folder)
            self.copy(pattern="*config.h", dst="include", src=os.path.join(self._source_subfolder, "ports", "MSVC++"))
            self.copy(pattern="*mpg123.h", dst="include", src=os.path.join(self._source_subfolder, "ports", "MSVC++"))
            self.copy(pattern="*.dll", dst="bin", keep_path=False)
            self.copy(pattern="*.lib", dst="lib", keep_path=False)

    def package_info(self):
        self.cpp_info.libs = ["libmpg123" if self._is_msvc else "mpg123"]
        if self._is_msvc and self.options.shared:
            self.cpp_info.defines.append("LINK_MPG123_DLL")
