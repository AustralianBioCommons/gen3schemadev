"""
Tests for drift detection (`generate --check`) and orphan reporting.

Background: a dictionary repository commits both its input file and the Gen3
YAML files generated from it. Nothing forced those two to agree, so they drifted:
one repository committed an input file that had stopped parsing altogether and
carried on for weeks, because the generated files were still present and looked
fine. Another carried a node YAML that no input could produce, which continued
to be bundled and deployed long after the input stopped describing it.

`--check` regenerates in memory and compares, so continuous integration can fail
a pull request the moment the two disagree. Orphan reporting covers the second
case: a file nothing can regenerate, which still ships.
"""

import os
import shutil

from tests.conftest import snapshot


def test_check_passes_when_output_matches_input(run_cli, input_file, generated):
    """
    Input: a dictionary freshly generated from its input, checked immediately.

    Expected: exit code 0 and nothing reported.

    Why it matters: this is the state continuous integration should see on a
    healthy pull request. If a clean dictionary reported drift, the check would
    be noise and people would rightly turn it off.
    """
    code, out = run_cli("generate", "-i", input_file, "-o", generated, "--check")

    assert code == 0
    assert "OK" in out


def test_check_writes_nothing(run_cli, input_file, generated):
    """
    Input: a dictionary with a hand-edited file, run through --check.

    Expected: the files on disk are untouched.

    Why it matters: --check is meant to be safe to run anywhere, including
    against a production dictionary and inside CI. If it repaired what it found,
    it would be a generate with a confusing name, and running it would become a
    decision rather than a reflex.
    """
    with open(f"{generated}/subject.yaml", "a") as handle:
        handle.write("\n# hand edit\n")
    before = snapshot(generated)

    run_cli("generate", "-i", input_file, "-o", generated, "--check")

    assert snapshot(generated) == before


def test_check_detects_hand_edited_node(run_cli, input_file, generated):
    """
    Input: a generated dictionary where one node YAML has been edited by hand.

    Expected: exit code 1, and subject.yaml named as changed.

    Why it matters: a hand edit in a repository that believes it is
    input-driven is the moment the two sources of truth part company. Catching
    it in CI is the difference between a one-line fix now and an archaeology
    exercise in six months.
    """
    with open(f"{generated}/subject.yaml", "a") as handle:
        handle.write("\n# hand edit\n")

    code, out = run_cli("generate", "-i", input_file, "-o", generated, "--check")

    assert code == 1
    assert "subject.yaml" in out
    assert "Changed" in out


def test_check_detects_missing_file(run_cli, input_file, generated):
    """
    Input: a generated dictionary with one node YAML deleted.

    Expected: exit code 1, and the deleted file reported as missing.

    Why it matters: a node the input describes but the dictionary lacks will not
    be deployed, so a submission referencing it fails at the far end of the
    pipeline. Naming it as missing points at the fix - regenerate - rather than
    leaving someone to compare two directory listings.
    """
    os.remove(f"{generated}/biospecimen.yaml")

    code, out = run_cli("generate", "-i", input_file, "-o", generated, "--check")

    assert code == 1
    assert "biospecimen.yaml" in out
    assert "Missing" in out


def test_check_detects_orphan_not_produced_by_input(run_cli, input_file, generated):
    """
    Input: a dictionary containing legacy_study.yaml, a node YAML that the input
    does not describe.

    Expected: exit code 1, and the file reported as orphaned.

    Why it matters: this is a real incident reproduced as a test. A repository
    carried exactly such a file for months. It could not be regenerated, so it
    was invisible to anyone reading the input, yet it was bundled and deployed
    like any other node. An orphan is not untidiness - it is a part of the
    deployed model that no source describes.
    """
    shutil.copy(f"{generated}/subject.yaml", f"{generated}/legacy_study.yaml")

    code, out = run_cli("generate", "-i", input_file, "-o", generated, "--check")

    assert code == 1
    assert "legacy_study.yaml" in out
    assert "Orphaned" in out


def test_orphan_is_only_a_warning_by_default(run_cli, input_file, generated):
    """
    Input: a dictionary containing an orphan, regenerated with --force.

    Expected: the command succeeds, but the orphan is reported.

    Why it matters: hand-written nodes alongside generated ones are a valid way
    to work. The tool should say what it sees without refusing to run, because
    for these repositories the orphan is the point, not a mistake.
    """
    shutil.copy(f"{generated}/subject.yaml", f"{generated}/hand_written.yaml")

    code, out = run_cli("generate", "-i", input_file, "-o", generated, "--force")

    assert code == 0
    assert "hand_written.yaml" in out


def test_orphan_is_an_error_under_input_driven(run_cli, input_file, generated):
    """
    Input: the same orphan, but regenerated with --input-driven.

    Expected: the command fails and nothing is written.

    Why it matters: --input-driven is a repository stating that its input file
    describes the whole dictionary. A file that contradicts that claim is a
    failure by definition, and this is what makes the declaration meaningful
    rather than decorative.
    """
    shutil.copy(f"{generated}/subject.yaml", f"{generated}/hand_written.yaml")

    code, out = run_cli("generate", "-i", input_file, "-o", generated, "--input-driven")

    assert code == 1
    assert "hand_written.yaml" in out


def test_framework_files_are_never_orphans(run_cli, input_file, generated):
    """
    Input: a normally generated dictionary, checked as-is.

    Expected: _definitions.yaml, _settings.yaml and _terms.yaml are not
    reported as orphans.

    Why it matters: those three come from packaged templates rather than from
    the user's nodes. Flagging them would produce a warning on every healthy
    repository, and a warning that is always present is one nobody reads.
    """
    code, out = run_cli("generate", "-i", input_file, "-o", generated, "--check")

    assert code == 0
    for framework_file in ("_definitions.yaml", "_settings.yaml", "_terms.yaml"):
        assert os.path.exists(f"{generated}/{framework_file}")
        assert f"Orphaned" not in out
