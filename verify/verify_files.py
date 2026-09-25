#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 Ashforde OÜ
"""Every file here is one SHA256SUMS names, and nothing else is here.

These are the public records of Ashforde OÜ (osaühing, an Estonian private
limited company), and the question this script answers is which files they
are.

`shasum -a 256 -c SHA256SUMS` reads the list and checks every file on it.
It cannot see a file nobody listed, because it walks the list and never the
directory: a file added to a clone of these records -- a script, a note,
anything at all -- leaves that check, and the workflow that runs it, green.
Deleting a listed file is caught, and changing one byte of a listed file is
caught; adding one is not, and that was the hole.

This script walks the directory instead. It reports every file here that
SHA256SUMS does not name, and every name SHA256SUMS holds that is not here.
It hashes nothing: `shasum -a 256 -c SHA256SUMS` does that, and the two
together are the whole statement -- these files, with these contents, and
no others.

  python3 verify/verify_files.py .

The repository's own .git is not part of the published set and is skipped
at the top level, where a clone keeps it. One further down is a repository
somebody nested inside these records, and every file in it is a file
nobody published, so it is reported like any other.

Nothing is installed and nothing is fetched: Python's standard library and
the files in front of you.

Exit 0 when the two agree, 1 on a finding, 2 when it cannot run.
"""

import io
import os
import sys

SUMS = "SHA256SUMS"
#: What a clone keeps beside the set at its root, and which the set does
#: not publish.
CLONE_METADATA = (".git",)


class Unreadable(Exception):
    """The check could not run at all, which is not a finding about files."""


def listed(root):
    """The paths SHA256SUMS names, in the format `shasum -a 256 -c` reads:
    a digest, two spaces, the path."""
    path = os.path.join(root, SUMS)
    try:
        with io.open(path, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        raise Unreadable("%s: %s" % (path, exc.strerror or exc))
    out = set()
    for number, line in enumerate(text.splitlines(), 1):
        if not line.strip():
            continue
        digest, sep, name = line.partition("  ")
        if not sep or len(digest) != 64:
            raise Unreadable("%s line %d is not a digest and a path: %r"
                             % (SUMS, number, line))
        out.add(name)
    if not out:
        raise Unreadable("%s names no file, so there is nothing to compare "
                         "the directory with" % SUMS)
    return out


def present(root):
    """Every file in the copy, the clone's own .git at the root aside."""
    out = set()
    for where, directories, names in os.walk(root):
        if where == root:
            directories[:] = [d for d in directories
                              if d not in CLONE_METADATA]
        directories.sort()
        for name in sorted(names):
            full = os.path.join(where, name)
            out.add(os.path.relpath(full, root).replace(os.sep, "/"))
    return out


def findings(root):
    """Every disagreement between the list and the directory."""
    names, here = listed(root), present(root)
    names.add(SUMS)
    out = ["%s is here and %s does not name it: a file in the published set "
           "that nothing published is a file nobody holds to anything"
           % (name, SUMS) for name in sorted(here - names)]
    out += ["%s names %s and it is not here" % (SUMS, name)
            for name in sorted(names - here)]
    return out


def main(argv):
    if len(argv) != 2:
        print("usage: verify_files.py <directory>")
        print("  the directory holding SHA256SUMS: for a clone of these "
              "records, .")
        return 2
    root = argv[1]
    try:
        found = findings(root)
    except Unreadable as exc:
        print("FAIL verify-files: could not run: %s" % exc)
        return 2
    if found:
        for one in found:
            print("FAIL verify-files: %s" % one)
        return 1
    print("PASS verify-files: %d file(s), and %s names every one of them "
          "and nothing else." % (len(present(root)), SUMS))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
