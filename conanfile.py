from conans import ConanFile, tools, AutoToolsBuildEnvironment, MSBuild
from conans.tools import Version
from conans.errors import ConanInvalidConfiguration
from conans.errors import ConanInvalidConfiguration
import os
import glob
import six


class LibMPG123Conan(ConanFile):
    name = "libmpg123"
    version = "1.25.10"
    description = "mpg123  is the fast and Free (LGPL license) real time MPEG Audio Layer 1, 2 and 3 decoding library and console player"
    topics = ("conan", "mpg123", "libmpg123", "mpeg", "audio", "decoding", "multimedia")
    url = "https://github.com/bincrafters/conan-libmpg123"
    homepage = "https://www.mpg123.de/"
    license = "LGPL-2.0-only"
    exports = ["LICENSE.md"]
    exports_sources = ["patches/*.patch"]
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}
    _source_subfolder = "source_subfolder"
    _build_subfolder = "build_subfolder"

    # copied from conan, need to make expose it
    def _system_registry_key(self, key, subkey, query):
        from six.moves import winreg  # @UnresolvedImport
        try:
            hkey = winreg.OpenKey(key, subkey)
        except (OSError, WindowsError):  # Raised by OpenKey/Ex if the function fails (py3, py2)
            return None
        else:
            try:
                value, _ = winreg.QueryValueEx(hkey, query)
                return value
            except EnvironmentError:
                return None
            finally:
                winreg.CloseKey(hkey)

    def _find_windows_10_sdk(self):
        """finds valid Windows 10 SDK version which can be passed to vcvarsall.bat (vcvars_command)"""
        # uses the same method as VCVarsQueryRegistry.bat
        from six.moves import winreg  # @UnresolvedImport
        hives = [
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE\Wow6432Node'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE\Wow6432Node'),
            (winreg.HKEY_LOCAL_MACHINE, r'SOFTWARE'),
            (winreg.HKEY_CURRENT_USER, r'SOFTWARE')
        ]
        for key, subkey in hives:
            subkey = r'%s\Microsoft\Microsoft SDKs\Windows\v10.0' % subkey
            installation_folder = self._system_registry_key(key, subkey, 'InstallationFolder')
            if installation_folder:
                if os.path.isdir(installation_folder):
                    include_dir = os.path.join(installation_folder, 'include')
                    for sdk_version in os.listdir(include_dir):
                        if (os.path.isdir(os.path.join(include_dir, sdk_version))
                                and sdk_version.startswith('10.')):
                            windows_h = os.path.join(include_dir, sdk_version, 'um', 'Windows.h')
                            if os.path.isfile(windows_h):
                                return sdk_version
        return None

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
                self.build_requires("msys2/20161025")
        if not tools.which("yasm"):
            self.build_requires("yasm/1.3.0")

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
            compiler_version = Version(self.settings.compiler.version.value)
            if compiler_version > "14":
                win10sdk = self._find_windows_10_sdk()
                if not win10sdk:
                    raise ConanInvalidConfiguration("Windows 10 SDK wasn't found")
                tools.replace_in_file("libmpg123.vcxproj",
                                      "<WindowsTargetPlatformVersion>8.1</WindowsTargetPlatformVersion>",
                                      "<WindowsTargetPlatformVersion>%s</WindowsTargetPlatformVersion>" % win10sdk)
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
