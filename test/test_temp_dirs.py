import gc
import os
import sqlite3
import tempfile
from pathlib import Path

import pytest

from acd.api import ImportProjectFromFile, load_acd
from acd.l5x.elements import ControllerBuilder
from acd.l5x.export_l5x import ExportL5x

ACD = os.path.join("..", "resources", "CuteLogix.ACD")


def test_import_project_from_file_leaves_no_temp_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    ImportProjectFromFile(Path(ACD)).import_project()

    assert list(tmp_path.iterdir()) == []


def test_export_l5x_leaves_no_temp_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))

    export = ExportL5x(ACD)
    export.project
    assert len(list(tmp_path.glob("acd-build-*"))) == 1

    del export
    gc.collect()

    assert list(tmp_path.iterdir()) == []


def _fail(*args, **kwargs):
    raise RuntimeError("conversion failed")


def _track_connections(monkeypatch):
    connections = []
    connect = sqlite3.connect

    def tracking_connect(*args, **kwargs):
        connections.append(connect(*args, **kwargs))
        return connections[-1]

    monkeypatch.setattr(sqlite3, "connect", tracking_connect)
    return connections


def _assert_closed(connection):
    with pytest.raises(sqlite3.ProgrammingError):
        connection.execute("SELECT 1")


@pytest.mark.parametrize("failing", ["populate_region_map", "controller"])
def test_load_acd_error_closes_database_and_removes_temp_dir(tmp_path, monkeypatch, failing):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    connections = _track_connections(monkeypatch)
    if failing == "controller":
        monkeypatch.setattr(ControllerBuilder, "build", _fail)
    else:
        monkeypatch.setattr(ExportL5x, failing, _fail)

    with pytest.raises(RuntimeError):
        load_acd(ACD)

    assert len(connections) == 1
    _assert_closed(connections[0])
    assert list(tmp_path.iterdir()) == []


def test_export_l5x_error_closes_database_and_removes_temp_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    connections = _track_connections(monkeypatch)
    monkeypatch.setattr(ExportL5x, "populate_region_map", _fail)

    with pytest.raises(RuntimeError):
        ExportL5x(ACD)
    gc.collect()

    assert len(connections) == 1
    _assert_closed(connections[0])
    assert list(tmp_path.iterdir()) == []


def test_unused_export_l5x_closes_database_before_removing_temp_dir(tmp_path, monkeypatch):
    # On Windows an open connection keeps acd.db locked, so the directory can
    # only be removed after the connection is closed.
    import shutil

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    connections = _track_connections(monkeypatch)
    rmtree = shutil.rmtree
    open_at_removal = []

    def checking_rmtree(path, *args, **kwargs):
        try:
            connections[0].execute("SELECT 1")
            open_at_removal.append(True)
        except sqlite3.ProgrammingError:
            open_at_removal.append(False)
        return rmtree(path, *args, **kwargs)

    monkeypatch.setattr(shutil, "rmtree", checking_rmtree)

    export = ExportL5x(ACD)
    del export
    gc.collect()

    assert open_at_removal == [False]
    assert list(tmp_path.iterdir()) == []
