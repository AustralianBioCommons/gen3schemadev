"""
Tests for the guiding messages the CLI prints when it stops or warns.

Background: this tool refuses to do things. A refusal that does not explain
itself is worse than no refusal, because the user is blocked and has nowhere to
go except the source code. The messages are therefore treated as behaviour and
asserted like any other output - if one regresses, someone loses a morning.

Every message follows the same shape: what happened, which files are affected,
why the tool stopped, and the concrete ways forward with destructive ones marked
as such. The last test in this module enforces the link between code and
documentation by checking that every doc path a message prints actually exists.
"""

import os
import re

import pytest

from gen3schemadev import messages


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_refusal_names_every_file_it_would_overwrite():
    """
    Input: a refusal covering three named files.

    Expected: all three appear in the message.

    Why it matters: "some files would be overwritten" gives the reader nothing
    to act on. Knowing exactly which files are at stake is what lets someone
    decide in seconds whether they care - and if one of them is the file they
    spent yesterday hand-editing, they need to see its name.
    """
    message = messages.overwrite_refusal(
        "dictionary/", ["subject.yaml", "biospecimen.yaml", "project.yaml"], [], "input_dd.yaml"
    )

    assert "subject.yaml" in message
    assert "biospecimen.yaml" in message
    assert "project.yaml" in message


def test_refusal_states_the_count_honestly_when_truncating():
    """
    Input: a refusal covering twenty files, more than the message lists inline.

    Expected: the message reports twenty, and says how many were not shown.

    Why it matters: a truncated list is fine, but a truncated list that hides
    the true scale is not. Someone about to type --force is making a decision
    about all twenty files, so the number has to be visible even when the names
    are not.
    """
    names = [f"node_{i:02d}.yaml" for i in range(20)]

    message = messages.overwrite_refusal("dictionary/", names, [], "input_dd.yaml")

    assert "20 existing files" in message
    assert "more)" in message


def test_refusal_offers_every_route_forward():
    """
    Input: any refusal.

    Expected: the message names --input-driven, --only, --force, and the option
    of deleting the input file to work schema-first.

    Why it matters: the refusal is the one place many users will ever learn that
    these workflows exist. Leaving one out would strand whichever group of users
    needed it - most importantly the people who bootstrapped from an input file
    and now want to edit the YAMLs directly, who otherwise have no idea that is
    a supported way to work.
    """
    message = messages.overwrite_refusal(
        "dictionary/", ["subject.yaml"], [], "input_dd.yaml"
    )

    assert "--input-driven" in message
    assert "--only" in message
    assert "--force" in message
    assert "Delete the input file" in message


def test_refusal_marks_force_as_destructive():
    """
    Input: any refusal.

    Expected: the --force option is described as discarding hand edits.

    Why it matters: --force is the only irreversible choice on offer. It sits in
    a list beside three safe ones, so it has to be visibly different - a reader
    skimming for the command that makes the error go away should not be able to
    miss that this one destroys work.
    """
    message = messages.overwrite_refusal(
        "dictionary/", ["subject.yaml"], [], "input_dd.yaml"
    )

    assert "DISCARDS ANY HAND EDITS" in message


def test_orphan_warning_states_the_consequence_not_just_the_observation():
    """
    Input: an orphan report for one file.

    Expected: the message explains that the file still ships in the bundle and
    reaches Gen3.

    Why it matters: "orphan file found" sounds like untidiness and gets ignored.
    The fact that matters is that an unreproducible file is still bundled and
    still deployed, so it is part of the live data model while being invisible
    to anyone reading the input. Stating the consequence is what turns the
    warning into something people act on.
    """
    message = messages.orphan_report("dictionary/", ["legacy_study.yaml"], as_error=False)

    assert "legacy_study.yaml" in message
    assert "bundle" in message
    assert "deployed" in message


def test_orphan_message_differs_between_warning_and_error():
    """
    Input: the same orphan, reported as a warning and as an error.

    Expected: only the error mentions --input-driven and calls it an error.

    Why it matters: an orphan is normal in a hand-edited repository and a
    failure in one that claims its input is complete. The same words for both
    would either alarm the first group or under-sell the problem to the second.
    """
    warning = messages.orphan_report("dictionary/", ["x.yaml"], as_error=False)
    error = messages.orphan_report("dictionary/", ["x.yaml"], as_error=True)

    assert "--input-driven" in error
    assert "error" in error
    assert "--input-driven" not in warning


def test_drift_report_separates_the_three_kinds_of_disagreement():
    """
    Input: a drift report with one changed, one missing and one orphaned file.

    Expected: each is listed under its own heading and named.

    Why it matters: the three mean different things and have different fixes -
    regenerate, regenerate, and decide-then-delete respectively. Collapsing them
    into "these files differ" would leave the reader to work out which is which.
    """
    message = messages.drift_report(
        "dictionary/", ["subject.yaml"], ["biospecimen.yaml"], ["legacy.yaml"],
        input_path="input_dd.yaml",
    )

    assert "Changed" in message and "subject.yaml" in message
    assert "Missing" in message and "biospecimen.yaml" in message
    assert "Orphaned" in message and "legacy.yaml" in message


def test_unknown_only_node_suggests_a_near_match():
    """
    Input: --only naming "subjcet" when "subject" exists.

    Expected: the message suggests "subject" and confirms nothing was written.

    Why it matters: this error is almost always a typo. Suggesting the near
    match turns a dead end into a one-second fix, and confirming that nothing
    was written removes the worry that the tool did something partial before
    giving up.
    """
    message = messages.only_unknown_nodes({"subjcet"}, ["subject", "biospecimen"])

    assert "did you mean" in message
    assert "subject" in message
    assert "Nothing was written" in message


def test_unparseable_input_reports_the_position_and_the_usual_cause():
    """
    Input: a YAML error carrying a problem mark at line 1030.

    Expected: the message reports line 1031 (marks are zero-based) and explains
    the missing-colon cause.

    Why it matters: this reproduces a real incident. A repository committed a
    node written as '- name_workflow' instead of '- name: alignment_workflow',
    which made the input unparseable, and it went unnoticed for weeks. The raw
    parser error - "mapping values are not allowed here" - explains nothing to
    someone who has not seen it before, so the message names the likely cause
    directly.
    """
    class FakeMark:
        line = 1030
        column = 10

    class FakeError(Exception):
        problem_mark = FakeMark()
        problem = "mapping values are not allowed here"

    message = messages.unparseable_input("input_dd.yaml", FakeError())

    assert "line 1031" in message
    assert "missing colon" in message
    assert "Nothing was written" in message


@pytest.mark.parametrize("doc_path", [
    messages.DOCS_DICTIONARY_REPO,
    messages.DOCS_TROUBLESHOOTING,
])
def test_every_message_doc_pointer_resolves_to_a_real_file(doc_path):
    """
    Input: each documentation path referenced by a message.

    Expected: the file exists in the repository.

    Why it matters: every message ends by pointing at documentation, which is
    what keeps the messages short. If a pointer goes nowhere, the message has
    quietly become a dead end at exactly the moment the reader needed help. This
    test also runs in the other direction: it means documentation cannot be
    renamed or deleted without someone noticing that a message depended on it.
    """
    assert os.path.exists(os.path.join(REPO_ROOT, doc_path)), (
        f"{doc_path} is referenced by a CLI message but does not exist"
    )


def test_no_message_references_an_undeclared_doc_path():
    """
    Input: the source of the messages module.

    Expected: every 'docs/...' path it mentions is one of the declared DOCS_
    constants, which the test above proves exist.

    Why it matters: the check above only covers paths routed through the
    constants. Someone adding a message with a hardcoded doc path would slip
    past it, so this closes the gap by reading the source directly.
    """
    source = open(os.path.join(REPO_ROOT, "src/gen3schemadev/messages.py")).read()
    declared = {messages.DOCS_DICTIONARY_REPO, messages.DOCS_TROUBLESHOOTING}

    referenced = set(re.findall(r"docs/[\w/]+\.md", source))

    assert referenced <= declared, (
        f"hardcoded doc paths found: {sorted(referenced - declared)}"
    )
