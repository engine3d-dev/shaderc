import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd, stdcpp_library
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualBuildEnv
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rmdir
from conan.tools.microsoft import is_msvc, is_msvc_static_runtime
from conan.tools.apple import fix_apple_shared_install_name

required_conan_version = ">=1.53.0"


class ShadercConan(ConanFile):
    name = "shaderc"
    version = "1.0"
    description = "A collection of tools, libraries and tests for shader compilation."
    license = "Apache-2.0"
    homepage = "https://github.com/engine3d-dev/shaderc"
    topics = ("glsl", "hlsl", "msl", "spirv", "spir-v", "glslc")
    export_sources = "CMakeLists.txt", "libshaderc/CMakeLists.txt", "libshaderc/include/shaderc/*.h", "libshaderc/src/*.cc", "libshaderc/src/*.c", "cmake/*.cmake", "./libshaderc_util/CMakeLists.txt", "./libshaderc_util/include/libshaderc_util/*.h", "./libshaderc_util/src/*.cc"

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    # def layout(self):
    #     cmake_layout(self, src_folder="src")
    def layout(self):
        cmake_layout(self)

    @property
    def _spirv_version(self):
        # return self.conan_data.get("siprv_mapping")[self.version]
        return "1.3.261.1"

    def requirements(self):
        # transitive_headers=True is not required for any of the dependencies
        self.requires(f"glslang/{self._spirv_version}")
        self.requires(f"spirv-tools/{self._spirv_version}")
        self.requires(f"spirv-headers/{self._spirv_version}")

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def build_requirements(self):
        self.tool_requires("cmake/[>=3.17.2 <4]")

    # def source(self):
    #     get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        venv = VirtualBuildEnv(self)
        venv.generate()

        tc = CMakeToolchain(self, "Unix Makefiles")
        tc.cache_variables["SHADERC_SKIP_INSTALL"] = False
        tc.cache_variables["SHADERC_SKIP_EXAMPLES"] = True
        tc.cache_variables["SHADERC_SKIP_TESTS"] = True
        tc.cache_variables["ENABLE_CODE_COVERAGE"] = False
        tc.cache_variables["SHADERC_ENABLE_WERROR_COMPILE"] = False
        if is_msvc(self):
            tc.cache_variables["SHADERC_ENABLE_SHARED_CRT"] = not is_msvc_static_runtime(self)
        tc.generate()

        self.dependencies["glslang"].cpp_info.components["glslang-core"].includedirs.append(
            os.path.join(self.dependencies["glslang"].package_folder, "include", "glslang")
        )

        deps = CMakeDeps(self)
        deps.set_property("glslang::glslang-core", "cmake_target_name", "glslang")
        deps.set_property("glslang::osdependent", "cmake_target_name", "OSDependent")
        deps.set_property("glslang::oglcompiler", "cmake_target_name", "OGLCompiler")
        deps.set_property("glslang::hlsl", "cmake_target_name", "HLSL")
        deps.set_property("glslang::spirv", "cmake_target_name", "SPIRV")
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # Copying *.h and *.cpp to a conan/imgui<hash>/p/imgui -> *.h
        copy(self, "LICENSE", dst=os.path.join(self.package_folder, "licenses"), src=self.source_folder)
        copy(self, pattern="*.h", src=os.path.join(self.source_folder, "./libshaderc/include/shaderc"), dst=os.path.join(self.package_folder, "shaderc"))
        copy(self, pattern="*.hpp", src=os.path.join(self.source_folder, "./libshaderc/include/shaderc"), dst=os.path.join(self.package_folder, "shaderc"))
        copy(self, pattern="*.h", src=os.path.join(self.source_folder, "./libshaderc_util/include/libshaderc_util"), dst=os.path.join(self.package_folder, "shaderc"))
        # copy(self, pattern="*.cpp", src=os.path.join(self.source_folder, "."), dst=os.path.join(self.package_folder, "imgui"))
        # copy(self, pattern="*.h", src=os.path.join(self.source_folder, "./backends/"), dst=os.path.join(self.package_folder, "imgui/backends"))
        # copy(self, pattern="*.cpp", src=os.path.join(self.source_folder, "./backends/"), dst=os.path.join(self.package_folder, "imgui/backends"))
        # copy(self, pattern="backends/imgui_impl_glfw.h", src=os.path.join(self.source_folder, "./backends/"), dst=os.path.join(self.package_folder, "imgui/backends"))
        # copy(self, pattern="backends/imgui_impl_glfw.cpp", src=os.path.join(self.source_folder, "./backends/"), dst=os.path.join(self.package_folder, "imgui/backends"))
        copy(self, pattern="*.a", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, pattern="*.so", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, pattern="*.lib", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        copy(self, pattern="*.dll", src=self.build_folder, dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, pattern="*.dylib", src=self.build_folder, dst=os.path.join(self.package_folder, "lib"), keep_path=False)
        cmake = CMake(self)
        cmake.install()
        fix_apple_shared_install_name(self)
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        if self.options.shared:
            self.cpp_info.set_property("pkg_config_name", "shaderc")
            self.cpp_info.libs = ["shaderc_shared"]
            self.cpp_info.defines.append("SHADERC_SHAREDLIB")
        else:
            self.cpp_info.set_property("pkg_config_name", "shaderc_static")
            self.cpp_info.libs = ["shaderc", "shaderc_util"]
            if stdcpp_library(self):
                self.cpp_info.system_libs.append(stdcpp_library(self))

        if self.settings.os in ["Linux", "FreeBSD"]:
            self.cpp_info.system_libs.append("pthread")

        self.cpp_info.requires = [
            "glslang::glslang-core",
            "glslang::osdependent",
            "glslang::oglcompiler",
            "glslang::hlsl",
            "glslang::spirv",
            "spirv-tools::spirv-tools-core",
            "spirv-tools::spirv-tools-opt",
            "spirv-headers::spirv-headers"
        ]

        # TODO: to remove in conan v2
        # bin_path = os.path.join(self.package_folder, "bin")
        # self.env_info.PATH.append(bin_path)
