"""
Tests for the `init` subcommand.

Background: `init` is the first command a new user runs. It writes a starter
input YAML they can edit into their own data model. Historically it emitted a
hardcoded dictionary that was a stale subset of the documented example in
examples/input_example.yaml (no data_file node, no enum property, no link to
the built-in `project` node), so the first thing a new user saw disagreed with
the docs. `init` now writes the packaged copy of that example verbatim, and
these tests pin the three things that keep it trustworthy: it matches the
example in the repo, the two copies cannot drift apart silently, and the file
it writes is a valid input for `generate`.
"""

import os

import yaml
from pydantic import ValidationError

from gen3schemadev.schema.gen3_template import get_input_example_text
from gen3schemadev.schema.input_schema import DataModel

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXAMPLE_PATH = os.path.join(REPO_ROOT, "examples", "input_example.yaml")


def test_init_writes_the_example_input_yaml(run_cli, tmp_path):
    """
    Input: `gen3schemadev init -o <tmp>/input_example.yaml` in a clean directory.

    Expected: exit code 0, and the written file is byte-for-byte identical to
    examples/input_example.yaml.

    Why it matters: the example file is what the documentation walks new users
    through. If init produced something different - even just reordered keys -
    a new user following the docs would be looking at a file that does not
    match what is on their disk.
    """
    output_path = str(tmp_path / "input_example.yaml")

    code, out = run_cli("init", "-o", output_path)

    assert code == 0
    with open(output_path) as f:
        written = f.read()
    with open(EXAMPLE_PATH) as f:
        example = f.read()
    assert written == example


def test_packaged_template_matches_examples_folder():
    """
    Input: the template shipped inside the package, and the copy committed in
    the examples/ folder.

    Expected: identical text.

    Why it matters: the example must live inside the package so an installed
    wheel can write it without the repo present, which means two copies exist.
    This test is the sync mechanism: edit examples/input_example.yaml without
    updating the packaged copy (or vice versa) and CI fails here, instead of
    users quietly receiving a stale starter file.
    """
    with open(EXAMPLE_PATH) as f:
        example = f.read()
    assert get_input_example_text() == example


def test_init_output_is_a_valid_input_model(run_cli, tmp_path):
    """
    Input: the file written by `init`, parsed and validated as a DataModel.

    Expected: it parses as YAML and passes the same pydantic validation that
    `generate` applies to its input.

    Why it matters: the whole point of init is to hand the user a file that
    `generate` accepts. A starter file that fails validation on first run
    would teach a new user that the tool is broken before they typed anything.
    """
    output_path = str(tmp_path / "input_example.yaml")
    run_cli("init", "-o", output_path)

    with open(output_path) as f:
        data = yaml.safe_load(f)
    try:
        DataModel.model_validate(data)
    except ValidationError as exc:
        raise AssertionError(f"init output failed input validation: {exc}")


def test_init_defaults_to_input_example_yaml_in_cwd(run_cli, tmp_path, monkeypatch):
    """
    Input: `gen3schemadev init` with no -o flag, run from an empty directory.

    Expected: input_example.yaml appears in the current working directory.

    Why it matters: the no-argument form is the one the README quickstart
    uses; it should work from any directory without the user thinking about
    paths.
    """
    monkeypatch.chdir(tmp_path)

    code, out = run_cli("init")

    assert code == 0
    assert (tmp_path / "input_example.yaml").exists()
