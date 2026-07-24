#!/usr/bin/env python

""" Build and install third party dependencies for PyMesh.
"""

import argparse
import subprocess
import os
import os.path
import tempfile
import shutil
import shlex
import sys

def get_third_party_dependencies():
    return ["cgal", "cork", "eigen",
        "tetgen", "triangle", "qhull", "clipper", "draco",
        "tbb", "mmg", "json"]

def parse_args():
    parser = argparse.ArgumentParser(__doc__);
    parser.add_argument("--cleanup", action="store_true",
            help="Clean up the build folder after done.");
    parser.add_argument("package",
            choices=["all"] + get_third_party_dependencies());
    return parser.parse_args();

def get_pymesh_dir():
    return os.path.join(sys.path[0], "..");

def build_generic(libname, build_flags="", cleanup=True):
    pymesh_dir = get_pymesh_dir();
    build_dir = os.path.join(pymesh_dir, "third_party", "build", libname);
    if not os.path.exists(build_dir):
        os.makedirs(build_dir);

    # Configure cgal
    cmake_args = shlex.split(
            os.environ.get("CMAKE_ARGS", ""),
            posix=os.name != "nt");
    dependency_args = shlex.split(build_flags, posix=os.name != "nt");
    cmd = [
            "cmake",
            os.path.join(pymesh_dir, "third_party", libname),
            "-DBUILD_SHARED_LIBS=Off",
            "-DCMAKE_POSITION_INDEPENDENT_CODE=On",
            "-DCMAKE_BUILD_TYPE=Release",
            "-DCMAKE_POLICY_VERSION_MINIMUM=3.5",
            "-DCMAKE_INSTALL_PREFIX={}".format(
                os.path.join(pymesh_dir, "python", "pymesh", "third_party")),
            ] + dependency_args + cmake_args;
    subprocess.check_call(cmd, cwd=build_dir);

    # Build cgal
    requested_parallel = os.environ.get("NUM_CORES", str(os.cpu_count() or 1));
    # vcpkg's app-local deployment can run for multiple DLL targets during the
    # build.  MSBuild may then try to copy the same runtime DLL concurrently,
    # which intermittently fails with a Windows file-lock error (code 32).
    parallel = "1" if os.name == "nt" else requested_parallel;
    cmd = ["cmake", "--build", build_dir, "--config", "Release",
            "--parallel", parallel];
    subprocess.check_call(cmd);

    cmd = ["cmake", "--build", build_dir, "--config", "Release",
            "--target", "install", "--parallel", parallel];
    subprocess.check_call(cmd);

    # Clean up
    if cleanup:
        shutil.rmtree(build_dir)

def patch_eigen_for_modern_compilers():
    """Backport Eigen 3.4's transposition expression fix.

    Recent Clang and GCC versions validate this template body eagerly and reject
    ``derived()`` on the specialized Transpose type used by the pinned Eigen
    revision. Eigen 3.4 passes the expression itself instead.
    """
    header = os.path.join(
            get_pymesh_dir(), "python", "pymesh", "third_party", "include",
            "eigen3", "Eigen", "src", "Core", "Transpositions.h");
    with open(header, "r", encoding="utf-8") as fin:
        contents = fin.read();
    old = "matrix.derived(), trt.derived());"
    new = "matrix.derived(), trt);"
    if old in contents:
        with open(header, "w", encoding="utf-8") as fout:
            fout.write(contents.replace(old, new));
    elif new not in contents:
        raise RuntimeError("Could not apply the Eigen transposition patch")

def patch_cgal_for_modern_boost():
    """Add the Boost.MPL include no longer supplied transitively by Boost."""
    header = os.path.join(
            get_pymesh_dir(), "python", "pymesh", "third_party", "include",
            "CGAL", "number_utils.h")
    with open(header, "r", encoding="utf-8") as fin:
        contents = fin.read()
    old = "#include <CGAL/Real_embeddable_traits.h>"
    new = old + "\n#include <boost/mpl/if.hpp>"
    if new not in contents and old in contents:
        with open(header, "w", encoding="utf-8") as fout:
            fout.write(contents.replace(old, new, 1))
    elif new not in contents:
        raise RuntimeError("Could not add the required Boost.MPL include to CGAL")

    iterator = os.path.join(
            get_pymesh_dir(), "python", "pymesh", "third_party", "include",
            "CGAL", "boost", "graph", "iterator.h")
    with open(iterator, "r", encoding="utf-8") as fin:
        contents = fin.read()
    old = "return (! (this->base() == nullptr)) ?"
    new = "return (g != nullptr) ?"
    if old in contents:
        if contents.count(old) != 3:
            raise RuntimeError("Unexpected CGAL iterator compatibility sites")
        with open(iterator, "w", encoding="utf-8") as fout:
            fout.write(contents.replace(old, new))
    elif contents.count(new) != 3:
        raise RuntimeError("Could not patch CGAL iterators for modern Boost")

def patch_cork_for_msvc():
    """Adapt the pinned Cork sources to the GMP package available on Windows."""
    if os.name != "nt":
        return

    prelude = os.path.join(
            get_pymesh_dir(), "third_party", "cork", "src", "util",
            "prelude.h")
    with open(prelude, "r", encoding="utf-8") as fin:
        contents = fin.read()
    old = "#pragma once\n\n#include <cmath>"
    new = (
            "#pragma once\n\n"
            "#ifndef _USE_MATH_DEFINES\n"
            "#define _USE_MATH_DEFINES\n"
            "#endif\n\n"
            "#include <cmath>\n\n"
            "#ifndef M_PI\n"
            "#define M_PI 3.14159265358979323846\n"
            "#endif")
    if old in contents:
        with open(prelude, "w", encoding="utf-8") as fout:
            fout.write(contents.replace(old, new, 1))
    elif new not in contents:
        raise RuntimeError("Could not expose math constants in Cork")

    fixint = os.path.join(
            get_pymesh_dir(), "third_party", "cork", "src", "isct",
            "fixint.h")
    with open(fixint, "r", encoding="utf-8") as fin:
        contents = fin.read()
    old = "#ifdef _WIN32\n#include <mpir.h>\n#else\n#include <gmp.h>\n#endif"
    new = "#include <gmp.h>"
    if old in contents:
        with open(fixint, "w", encoding="utf-8") as fout:
            fout.write(contents.replace(old, new, 1))
    elif old not in contents and new not in contents:
        raise RuntimeError("Could not switch Cork from MPIR to GMP")

    gmpext = os.path.join(
            get_pymesh_dir(), "third_party", "cork", "src", "isct",
            "gmpext4.h")
    with open(gmpext, "r", encoding="utf-8") as fin:
        contents = fin.read()
    old = "#include <mpirxx.h>"
    new = "#include <gmpxx.h>"
    if old in contents:
        with open(gmpext, "w", encoding="utf-8") as fout:
            fout.write(contents.replace(old, new, 1))
    elif new not in contents:
        raise RuntimeError("Could not switch Cork C++ bindings from MPIR to GMP")

def build(package, cleanup):
    if package == "all":
        for libname in get_third_party_dependencies():
            build(libname, cleanup);
    elif package == "cgal":
        build_generic("cgal",
                " -DWITH_CGAL_ImageIO=Off -DWITH_CGAL_Qt5=Off",
                cleanup=cleanup);
        patch_cgal_for_modern_boost();
    elif package == "clipper":
        build_generic("Clipper/cpp", cleanup=cleanup);
    elif package == "eigen":
        build_generic("eigen", cleanup=cleanup);
        patch_eigen_for_modern_compilers();
    elif package == "cork":
        patch_cork_for_msvc();
        build_generic("cork", cleanup=cleanup);
    elif package == "tbb":
        build_generic("tbb",
                " -DTBB_BUILD_SHARED=On -DTBB_BUILD_STATIC=Off",
                cleanup=cleanup);
    elif package == "json":
        build_generic("json",
                " -DJSON_BuildTests=Off",
                cleanup=cleanup);
    else:
        build_generic(package, cleanup=cleanup);

def main():
    args = parse_args();
    build(args.package, args.cleanup);

if __name__ == "__main__":
    main();
