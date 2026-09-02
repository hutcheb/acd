"""Regression test: DumpCompsRecordsToFile works on a FRESH (non-existent)
output directory and lands the record tree + output.log together.

Previously two things broke this (the README-documented
DumpCompsRecordsToFile("My.ACD", "output/").extract() flow):
  1. output.log was opened without creating output_directory -> FileNotFoundError.
  2. the record tree defaulted to ./dump, separate from output_directory.

This test uses a tmp_path (a fresh dir) so it exercises both fixes and does
not depend on the pre-existing ./build dir.
"""
import os

from acd.api import DumpCompsRecordsToFile


def test_dump_to_fresh_dir_lands_together(tmp_path):
    acd = os.path.join("..", "resources", "CuteLogix.ACD")
    out = tmp_path / "out"  # does not exist yet
    assert not out.exists()

    DumpCompsRecordsToFile(acd, str(out)).extract()

    # output.log was written (dir was created).
    log = out / "output.log"
    assert log.exists(), "output.log should be written into the fresh dir"
    assert log.stat().st_size > 0, "output.log should not be empty"

    # The record tree also landed in the same dir (not ./dump): there should be
    # multiple top-level sub-directories created from comp_names.
    subdirs = [p for p in out.iterdir() if p.is_dir()]
    assert len(subdirs) > 0, "record tree should be created inside the output dir"

    # None of the created names contain path-illegal characters (the sanitizer
    # maps comp_names like "x:O:0" to safe components on Windows).
    for p in subdirs:
        for ch in p.name:
            assert ch not in '\\/:*?"<>|', f"unsafe char in dumped dir name: {p.name!r}"
