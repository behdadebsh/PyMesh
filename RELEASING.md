# Releasing PyMesh

PyMesh publishes the `pymesh2.0` distribution to PyPI from GitHub Actions. The
publish job uses PyPI Trusted Publishing, so no long-lived PyPI token is stored
in the repository.

## One-time setup

1. In the PyPI settings for `pymesh2.0`, add a GitHub Trusted Publisher.
2. Enter the GitHub owner, repository name, and workflow filename `build.yml`.
3. Leave the environment blank, matching the workflow configuration.

If `pymesh2.0` has not been published before, create a pending publisher from
the publishing settings in your PyPI account. The configured GitHub owner must
own the repository from which the release workflow runs.

## Release checklist

1. Update `python/pymesh/version.py` and the `version` and `release` values in
   `docs/conf.py`.
2. Merge the version change into `main` and confirm the build workflow passes.
3. Create and push an annotated tag whose value is the package version prefixed
   with `v`:

       git tag -a v1.0.1 -m "PyMesh 1.0.1"
       git push origin v1.0.1

4. Confirm that all wheel and source-distribution jobs pass and that the
   `Publish to PyPI` job succeeds.
5. Create a GitHub release from the existing tag:

       gh release create v1.0.1 --verify-tag --generate-notes --title "PyMesh 1.0.1"

6. Verify installation in a fresh Python environment:

       python -m pip install pymesh2.0==1.0.1
       python -c "import pymesh; print(pymesh.__version__)"

PyPI does not permit replacing files for an existing version. If any files for
a version have been published, increment the package version before retrying.

## Published artifacts

The workflow publishes manylinux x86-64 wheels for supported CPython versions
3.8 through 3.12 and a source distribution. Other platforms install from the
source distribution and therefore need PyMesh's native build dependencies.
