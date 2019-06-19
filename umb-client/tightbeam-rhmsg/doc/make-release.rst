Make a new release
==================

Make new builds in Brew
-----------------------

1. Bump version

   1. Bump version in ``setup.py``
   2. Ensure all changes since last release have been recorded in file
      ``CHANGELOG.rst``.
   3. Commit and tag the new release, e.g.

      ::

            git tag -m "v0.1-1" v0.1-1

2. Make source distribution tarball.

   ::

        python setup.py sdist

3. Upload tarball to dist-git for preparing making RPMs.

   ::

        rhpkg new-sources path/to/tarball

4. Checkout to branch ``eng-rhel-6``, then bump version and release in SPEC.

   ::

        rpmdev-bumpspec -n $new_version python-rhmsg.spec

5. Update SPEC and commit changes, e.g.

   ::

        rhpkg commit -m "0.1 Release"

6. Checkout to branch ``eng-rhel-7``, ``eng-fedora-25`` and ``eng-fedora-26``,
   and merge from ``eng-rhel-6``.

   ::

        for b in eng-rhel-7 eng-fedora-25 eng-fedora-26; do
            rhpkg switch-branch $b
            git merge eng-rhel-6
        done

6. Start to build RPMs. New RPMs must be built from both ``eng-rhel-6``,
   ``eng-rhel-7``, ``eng-fedora-25`` and ``eng-fedora-26``.

   ::

        for b in eng-rhel-6 eng-rhel-7 eng-fedora-25 eng-fedora-26; do
            rhpkg switch-branch $b
            rhpkg scratch-build --srpm --nowait
        done

7. If there is any error in scratch build, fix them and repeat
   build. Otherwise, push and begin to build normal build in Brew.

   ::

        for b in eng-rhel-6 eng-rhel-7 eng-fedora-25 eng-fedora-26; do
            rhpkg switch-branch $b
            rhpkg push
            rhpkg build --nowait
        done

8. Finally, tag the build.

   ::

        for tag in eng-rhel-6 eng-rhel-7 eng-fedora-25 eng-fedora-26; do
            nvr="$(brew --quiet latest-build ${tag}-candidate python-rhmsg | cut -d' ' -f1)"
            brew tag-build $tag $nvr
        done

Announcement
------------

Sending announcement email to mailing lists

- rcm-tools@redhat.com
- pnt-devops@redhat.com
