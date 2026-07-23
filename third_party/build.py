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
            "-DCMAKE_INSTALL_PREFIX={}".format(
                os.path.join(pymesh_dir, "python", "pymesh", "third_party")),
            ] + dependency_args + cmake_args;
    subprocess.check_call(cmd, cwd=build_dir);

    # Build cgal
    parallel = os.environ.get("NUM_CORES", str(os.cpu_count() or 1));
    cmd = ["cmake", "--build", build_dir, "--config", "Release",
            "--parallel", parallel];
    subprocess.check_call(cmd);

    cmd = ["cmake", "--build", build_dir, "--config", "Release",
            "--target", "install", "--parallel", parallel];
    subprocess.check_call(cmd);

    # Clean up
    if cleanup:
        shutil.rmtree(build_dir)

def build(package, cleanup):
    if package == "all":
        for libname in get_third_party_dependencies():
            build(libname, cleanup);
    elif package == "cgal":
        build_generic("cgal",
                " -DWITH_CGAL_ImageIO=Off -DWITH_CGAL_Qt5=Off",
                cleanup=cleanup);
    elif package == "clipper":
        build_generic("Clipper/cpp", cleanup=cleanup);
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
