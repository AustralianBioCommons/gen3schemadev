"""
Tests that a bundled schema is byte-identical wherever it is built.

Background: `bundle` combines a folder of Gen3 schemas into the single JSON file
that gets deployed. That file is committed alongside the schemas, so any
instability in how it is written shows up as a diff.

The bundle used to be assembled by iterating os.listdir, which returns entries
in filesystem order. That order differs between machines, so bundling an
unchanged dictionary on macOS and on a Linux CI runner produced JSON with the
same content in a different key order - byte-different files describing an
identical model. A downstream repository hit exactly this: its CI compared the
committed bundle against a freshly built one and failed on the first run, for a
reason that had nothing to do with the dictionary.
"""

import json
import os

import pytest

from gen3schemadev.utils import bundle_yamls, write_json


@pytest.fixture
def schema_dir(tmp_path):
    """
    A small dictionary folder whose filenames are deliberately not in
    alphabetical order on disk, so a sorted result cannot happen by accident.
    """
    directory = tmp_path / "dictionary"
    directory.mkdir()
    for name in ["subject", "acknowledgement", "genomic_file", "biospecimen"]:
        (directory / f"{name}.yaml").write_text(
            f"id: {name}\ntitle: {name}\ncategory: clinical\n"
        )
    # A non-YAML file, which must be ignored rather than bundled.
    (directory / "notes.txt").write_text("not a schema")
    return str(directory)


def test_bundle_keys_are_sorted(schema_dir):
    """
    Input: a folder of four schemas created in non-alphabetical order.

    Expected: the bundle's keys come out alphabetically sorted.

    Why it matters: sorting is what makes the output independent of the
    filesystem. Asserting the specific order - rather than just that two runs
    agree - pins the behaviour to something a reader can predict, and means the
    committed bundle is identical no matter who regenerated it.
    """
    bundle = bundle_yamls(schema_dir)

    assert list(bundle) == [
        "acknowledgement.yaml",
        "biospecimen.yaml",
        "genomic_file.yaml",
        "subject.yaml",
    ]


def test_bundle_order_is_independent_of_filesystem_order(schema_dir, monkeypatch):
    """
    Input: the same folder, bundled twice, with os.listdir returning the
    filenames in a different order each time.

    Expected: both bundles have identical key order and serialise to identical
    JSON.

    Why it matters: this reproduces the actual failure. Two machines enumerating
    the same directory differently must still produce the same file, otherwise
    the committed bundle churns whenever a different person regenerates it, and
    any CI check comparing bundles fails for no real reason. Reordering listdir
    is the only practical way to simulate a different filesystem here.
    """
    real_listdir = os.listdir

    def reversed_listdir(path):
        return list(reversed(real_listdir(path)))

    first = bundle_yamls(schema_dir)

    monkeypatch.setattr(os, "listdir", reversed_listdir)
    second = bundle_yamls(schema_dir)

    assert list(first) == list(second)
    assert json.dumps(first) == json.dumps(second)


def test_written_bundle_file_is_byte_identical_across_runs(schema_dir, tmp_path, monkeypatch):
    """
    Input: the same folder bundled and written to disk twice, with the
    filesystem enumeration order reversed in between.

    Expected: the two JSON files are byte-for-byte identical.

    Why it matters: the previous tests cover the in-memory dictionary, but what
    gets committed and deployed is the file. This asserts the property that
    actually matters to a repository - regenerating without changing anything
    leaves the working tree clean.
    """
    real_listdir = os.listdir
    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"

    write_json(bundle_yamls(schema_dir), str(first_path))

    monkeypatch.setattr(os, "listdir", lambda p: list(reversed(real_listdir(p))))
    write_json(bundle_yamls(schema_dir), str(second_path))

    assert first_path.read_bytes() == second_path.read_bytes()


def test_property_order_within_a_schema_is_preserved(tmp_path):
    """
    Input: a schema whose properties are authored in a deliberate, non-
    alphabetical order.

    Expected: the bundle keeps that order.

    Why it matters: only the top level is sorted. Property order comes from the
    YAML document and carries intent - it is the order a submitter sees in the
    portal - so sorting it would silently rearrange every node in every
    dictionary. This test is the guard against "fixing" determinism too
    enthusiastically.
    """
    directory = tmp_path / "dictionary"
    directory.mkdir()
    (directory / "subject.yaml").write_text(
        "id: subject\n"
        "properties:\n"
        "  zeta: {type: string}\n"
        "  alpha: {type: string}\n"
        "  middle: {type: string}\n"
    )

    bundle = bundle_yamls(str(directory))

    assert list(bundle["subject.yaml"]["properties"]) == ["zeta", "alpha", "middle"]
