"""
Tests for the `validate` command, end to end.

Background: validate had three habits that made it untrustworthy on real
dictionaries.

It stopped at the first rule violation, so a dictionary with six problems took
six runs to diagnose. It printed "SUCCESS" per node for the nodes that happened
to resolve and said nothing whatsoever about the ones that did not - on the
dictionary Gen3 publishes, that meant reporting success for 10 nodes while 19
went unmentioned. And a single reference to a documentation term that did not
exist killed the whole command with a bare KeyError traceback naming only the
missing key, not the file or property that asked for it.

These tests drive the real CLI, because the exit code is what continuous
integration acts on and it is part of the contract.
"""

import json
import os

import pytest

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OFFICIAL_DICTIONARY = os.path.join(
    REPO_ROOT, "tests/gen3_schema/examples/json", "gen3_develop_schema.json"
)
ACDC_DICTIONARY = "/Users/harrijh/projects/acdc-schema-json/dictionary/prod_dict/acdc_schema.json"


def _link(name, target):
    """Build a complete Gen3 link, so tests only state what they care about."""
    return {
        "name": name,
        "backref": f"{name}_backref",
        "label": "derived_from",
        "target_type": target,
        "multiplicity": "one_to_one",
        "required": False,
    }


@pytest.fixture
def bundle(tmp_path):
    """
    Return a helper that writes a bundle to disk and gives back its path.

    validate takes a file, so every test here needs one; keeping the plumbing
    in a fixture leaves the test bodies to describe the defect being tested.
    """
    def _write(contents, name="bundle.json"):
        path = tmp_path / name
        path.write_text(json.dumps(contents))
        return str(path)
    return _write


def _healthy_bundle():
    """A small bundle in which every rule passes and every reference resolves."""
    return {
        "_definitions.yaml": {"state": {"type": "string"}},
        "_terms.yaml": {"subject": {"description": "A subject."}},
        "subject.yaml": {
            "id": "subject",
            "title": "Subject",
            "type": "object",
            "category": "clinical",
            "description": "A subject.",
            "program": "*",
            "project": "*",
            "submittable": True,
            "validators": None,
            "systemProperties": ["id"],
            "uniqueKeys": [["id"]],
            "required": ["submitter_id", "type"],
            "links": [],
            "properties": {"type": {"type": "string"}, "state": {"type": "string"}},
        },
    }


def test_the_official_gen3_dictionary_validates_end_to_end(run_cli):
    """
    Input: the dictionary Gen3 publishes, run through `validate --bundled`.

    Expected: exit 0. The dangling documentation term is reported as a warning,
    and none of the old failure text appears.

    Why it matters: this is the whole point of the change, asserted through the
    real entry point rather than by calling internals. Before it, the command
    died on the first node with a traceback about a "reserved system property
    name" - the tool rejecting the reference dictionary it exists to work with.
    """
    code, out = run_cli("validate", "-b", OFFICIAL_DICTIONARY)

    assert code == 0
    assert "_terms.yaml#/file_format" in out
    assert "reserved system property name" not in out
    assert "property for link 'None'" not in out
    assert "Traceback" not in out


def test_a_clean_dictionary_is_summarised_rather_than_narrated(run_cli, bundle):
    """
    Input: a small dictionary in which every rule passes.

    Expected: exit 0 and a single line stating how many schemas were checked.

    Why it matters: validate used to print one SUCCESS line per node for rule
    validation. On a real dictionary that is 27 lines of noise, and the one
    line that matters is buried in it.
    """
    code, out = run_cli("validate", "-b", bundle(_healthy_bundle()))

    assert code == 0
    assert "SUCCESS: rule validation passed for 1 schemas." in out


def test_validate_names_every_broken_node_before_exiting(run_cli, bundle):
    """
    Input: a dictionary with two separately broken nodes - one data_file
    missing its core metadata link, one node whose link has no property.

    Expected: exit 1, and both nodes named in a single report.

    Why it matters: stopping at the first failure meant the reader fixed one
    node, re-ran, and discovered the next. Reporting everything at once turns
    six runs into one.
    """
    contents = _healthy_bundle()
    contents["broken_file.yaml"] = {
        "id": "broken_file",
        "category": "data_file",
        "links": [],
        "properties": {"file_name": {"type": "string"}},
    }
    contents["broken_link.yaml"] = {
        "id": "broken_link",
        "category": "clinical",
        "links": [_link("samples", "sample")],
        "properties": {"other": {"type": "string"}},
    }

    code, out = run_cli("validate", "-b", bundle(contents))

    assert code == 1
    assert "broken_file" in out
    assert "broken_link" in out
    assert "this is the complete list" in out


def test_a_dangling_term_is_a_warning_not_a_failure(run_cli, bundle):
    """
    Input: a dictionary whose property points a `term` at a key _terms.yaml
    does not contain.

    Expected: exit 0, with the reference named and explained.

    Why it matters: a term is documentation, so a missing one does not change
    what the data may contain. The dictionary Gen3 publishes carries exactly
    one of these; treating it as fatal would mean the reference dictionary can
    never pass.
    """
    contents = _healthy_bundle()
    contents["subject.yaml"]["properties"]["state"] = {
        "type": "string",
        "term": {"$ref": "_terms.yaml#/nonexistent_term"},
    }

    code, out = run_cli("validate", "-b", bundle(contents))

    assert code == 0
    assert "_terms.yaml#/nonexistent_term" in out
    assert "documentation" in out


def test_a_dangling_schema_reference_is_reported_without_a_traceback(run_cli, bundle):
    """
    Input: a dictionary whose property references a definition that does not
    exist, outside any `term` block.

    Expected: exit 1, naming the reference and the file that makes it, with no
    Python traceback anywhere in the output.

    Why it matters: this used to surface as `KeyError: 'file_format'` on top of
    a twenty-line traceback. The key alone does not tell you which of ninety
    definitions asked for it, and a traceback tells the reader the tool broke
    rather than that their dictionary has a gap.
    """
    contents = _healthy_bundle()
    contents["subject.yaml"]["properties"]["state"] = {
        "$ref": "_definitions.yaml#/nonexistent_definition"
    }

    code, out = run_cli("validate", "-b", bundle(contents))

    assert code == 1
    assert "_definitions.yaml#/nonexistent_definition" in out
    assert "subject.yaml" in out
    assert "Traceback" not in out
    assert "KeyError" not in out


def test_a_node_that_cannot_be_resolved_is_named_rather_than_skipped(run_cli, bundle):
    """
    Input: a dictionary containing a node schema with no `id`, which resolution
    cannot key and therefore drops.

    Expected: exit 1, with the dropped node named.

    Why it matters: validate previously reported success for whatever survived
    resolution and said nothing about the rest, so a dictionary could pass with
    most of it never checked. Silence about unchecked work is the worst
    possible outcome for a validator.
    """
    contents = _healthy_bundle()
    contents["nameless.yaml"] = {
        "category": "clinical",
        "links": [],
        "properties": {"something": {"type": "string"}},
    }

    code, out = run_cli("validate", "-b", bundle(contents))

    assert code == 1
    assert "nameless" in out
    assert "not checked" in out.lower()


@pytest.mark.skipif(
    not os.path.exists(ACDC_DICTIONARY),
    reason="ACDC production dictionary is not available on this machine",
)
def test_the_acdc_production_dictionary_still_validates(run_cli):
    """
    Input: the ACDC production dictionary, if present on this machine.

    Expected: exit 0, exactly as before this change.

    Why it matters: this change loosened four separate checks, and the risk of
    loosening a validator is that something which used to be caught now slips
    through, or that a working dictionary starts failing. This is a real
    production dictionary, so it is the honest regression check. It skips in CI
    because it lives in another repository.
    """
    code, out = run_cli("validate", "-b", ACDC_DICTIONARY)

    assert code == 0
    assert "Validation process complete." in out
