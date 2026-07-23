"""
Shared fixtures for the CLI-level tests.

The repository historically had no conftest.py and each test module declared its
own fixtures. The CLI tests all need the same two things - a small valid input
file, and a way to invoke the command-line entry point and inspect what it
printed and returned - so they live here rather than being copied five times.
"""

import hashlib
import os
import sys
from unittest.mock import patch

import pytest

from gen3schemadev.cli import main


# A deliberately small dictionary: two nodes and one link. Small enough that a
# failure message is readable, complete enough to exercise links, enums and
# required properties.
MINIMAL_INPUT = """version: 0.1.0
url: https://example.biocommons.org.au
nodes:
  - name: subject
    category: clinical
    description: "An individual organism taking part in the study."
    properties:
      - name: submitter_subject_id
        description: "Submitter-assigned subject identifier."
        type: string
        required: true
      - name: species
        description: "Common name of the species."
        type: enum
        enums:
          - "Human"
          - "Mouse"
  - name: biospecimen
    category: biospecimen
    description: "A sample taken from a subject."
    properties:
      - name: sample_type
        description: "The kind of material sampled."
        type: string
links:
  - parent: project
    multiplicity: one_to_many
    child: subject
  - parent: subject
    multiplicity: one_to_many
    child: biospecimen
"""


@pytest.fixture
def input_file(tmp_path):
    """Write the minimal input dictionary and return its path."""
    path = tmp_path / "input_dd.yaml"
    path.write_text(MINIMAL_INPUT)
    return str(path)


@pytest.fixture
def output_dir(tmp_path):
    """An empty directory to generate into."""
    path = tmp_path / "dictionary"
    path.mkdir()
    return str(path)


@pytest.fixture
def run_cli(capsys):
    """
    Invoke the CLI as a user would and return (exit_code, stdout).

    argparse and sys.exit are what the real entry point uses, so the tests drive
    those rather than calling internals directly - the exit code is part of the
    contract for anyone running this in CI.
    """
    def _run(*args):
        with patch.object(sys, "argv", ["gen3schemadev", *args]):
            code = 0
            try:
                main()
            except SystemExit as exc:
                code = exc.code if exc.code is not None else 0
        return code, capsys.readouterr().out
    return _run


@pytest.fixture
def generated(run_cli, input_file, output_dir):
    """
    A dictionary that has already been generated once.

    Most safety behaviour only becomes observable on the *second* run, so nearly
    every test starts from here rather than from an empty directory.
    """
    code, _ = run_cli("generate", "-i", input_file, "-o", output_dir)
    assert code == 0, "fixture setup: first generate should succeed"
    return output_dir


def snapshot(directory):
    """
    Hash every file in a directory.

    Returns a {filename: sha256} mapping, so a test can assert that nothing on
    disk moved - which is a stronger and more useful claim than asserting a
    command merely exited non-zero.
    """
    result = {}
    for name in sorted(os.listdir(directory)):
        path = os.path.join(directory, name)
        if os.path.isfile(path):
            with open(path, "rb") as handle:
                result[name] = hashlib.sha256(handle.read()).hexdigest()
    return result
