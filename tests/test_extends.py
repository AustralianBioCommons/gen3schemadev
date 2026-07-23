"""
Tests for `extends`, which merges a declared node onto a packaged preset.

Background: Gen3 ships three nodes that its own microservices depend on -
program, project and core_metadata_collection. Their schemas carry settings the
simplified input language cannot express: which properties the backend manages
rather than the submitter (project's release flags), which combination of fields
must be unique (project's `code` rather than the usual submitter_id), default
values for the project state machine, and ontology term identifiers on the Data
Use consent codes.

Previously a repository that wanted to add one field to `project` had to declare
the whole node, and the generator would rebuild it from generic defaults -
quietly dropping all of the above and breaking project release and consent
handling. `extends` fixes that: declare only what you are adding, inherit
everything else.

The guarantee these tests protect is narrow and absolute: extending a preset
must never remove or alter anything the preset defined.
"""

import pytest
import yaml

from gen3schemadev.schema.gen3_template import (
    generate_project_template,
    generate_core_metadata_template,
)


EXTENDS_PROJECT_INPUT = """version: 0.1.0
url: https://example.biocommons.org.au
nodes:
  - name: project
    extends: project
    properties:
      - name: institute_name
        description: "Institution leading the study."
        type: string
      - name: ethics_approval_id
        description: "Ethics approval identifier covering these samples."
        type: string
  - name: subject
    category: clinical
    description: "An individual organism."
    properties:
      - name: submitter_subject_id
        description: "Submitter-assigned subject identifier."
        type: string
links:
  - parent: project
    multiplicity: one_to_many
    child: subject
"""


@pytest.fixture
def extended_project(run_cli, tmp_path):
    """Generate a dictionary whose project node extends the packaged preset."""
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(EXTENDS_PROJECT_INPUT)
    out = tmp_path / "dictionary"
    out.mkdir()
    code, printed = run_cli("generate", "-i", str(input_file), "-o", str(out))
    assert code == 0, printed
    return yaml.safe_load((out / "project.yaml").read_text()), printed


def test_extends_project_preserves_system_properties_and_unique_keys(extended_project):
    """
    Input: a project node that extends the preset and adds two properties.

    Expected: systemProperties and uniqueKeys are exactly the preset's.

    Why it matters: project's systemProperties include the flags Gen3 uses to
    release a project, and its uniqueKeys are keyed on `code` rather than the
    submitter_id used by ordinary nodes. Rebuilding the node from generic
    defaults replaces both, which breaks project release and lets duplicate
    project codes through. This is the single most important thing extends
    protects.
    """
    project, _ = extended_project
    preset = generate_project_template()

    assert project["systemProperties"] == preset["systemProperties"]
    assert project["uniqueKeys"] == preset["uniqueKeys"]


def test_extends_project_preserves_every_preset_property(extended_project):
    """
    Input: the same extended project node.

    Expected: every property the preset defined is still present and unchanged.

    Why it matters: the preset's consent_codes property carries Data Use
    Ontology term identifiers, and several properties carry default values and
    format annotations that the input language has no way to express. If any of
    them were dropped or rewritten during the merge, the loss would be silent -
    the generated file would still be valid, just wrong.
    """
    project, _ = extended_project
    preset = generate_project_template()

    for name, definition in preset["properties"].items():
        assert name in project["properties"], f"preset property '{name}' was lost"
        assert project["properties"][name] == definition, f"'{name}' was altered"


def test_extends_adds_the_declared_properties(extended_project):
    """
    Input: a project node declaring institute_name and ethics_approval_id.

    Expected: both appear in the generated schema alongside the preset's own.

    Why it matters: preserving the preset is only half the job. The reason to
    extend at all is to add fields, so the addition has to actually happen.
    """
    project, _ = extended_project

    assert project["properties"]["institute_name"]["type"] == "string"
    assert "ethics_approval_id" in project["properties"]


def test_extends_reports_what_it_merged(extended_project):
    """
    Input: the same extended project node.

    Expected: the output names the preset, and lists the added properties.

    Why it matters: a merge nobody can see is a merge nobody can trust. Someone
    reviewing a change to a Gen3-critical node needs to know at a glance what
    was inherited and what was replaced, without diffing the result against a
    template buried inside an installed package.
    """
    _, printed = extended_project

    assert "extends the packaged 'project' preset" in printed
    assert "institute_name" in printed
    assert "inherited" in printed


def test_declared_core_metadata_collection_is_no_longer_silently_discarded(
    run_cli, tmp_path
):
    """
    Input: a core_metadata_collection node that extends its preset and adds
    submitter_cmc_id.

    Expected: submitter_cmc_id is present in the generated schema.

    Why it matters: this is a regression test for a real bug. program and
    project were only written from their templates when the user had not
    declared them, but core_metadata_collection was written unconditionally,
    after the user's version had already been generated. The result was that a
    declared core_metadata_collection was built and then immediately overwritten
    - one production dictionary declared submitter_cmc_id for months while the
    generated dictionary never contained it, and nothing reported a problem.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: core_metadata_collection\n"
        "    extends: core_metadata_collection\n"
        "    properties:\n"
        "      - name: submitter_cmc_id\n"
        "        description: \"Submitter-assigned identifier.\"\n"
        "        type: string\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    properties: []\n"
        "links:\n"
        "  - parent: project\n"
        "    multiplicity: one_to_many\n"
        "    child: subject\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    code, _ = run_cli("generate", "-i", str(input_file), "-o", str(out))
    cmc = yaml.safe_load((out / "core_metadata_collection.yaml").read_text())

    assert code == 0
    assert "submitter_cmc_id" in cmc["properties"]
    # and the preset's own properties are still intact
    preset = generate_core_metadata_template()
    for name in preset["properties"]:
        assert name in cmc["properties"]


def test_a_preset_named_node_merges_even_without_extends(run_cli, tmp_path):
    """
    Input: a core_metadata_collection node declared with a category and one
    extra property, but WITHOUT saying `extends`.

    Expected: the preset's own properties all survive, the extra property is
    added, and the output explains that the node was merged rather than
    replaced.

    Why it matters: this is the most dangerous case, and a real repository is in
    it. Declaring a node that happens to share a preset's name reads like
    "add this field", not "replace the entire node", but building it from
    generic defaults drops all fourteen of the preset's properties. The
    resulting file is still valid YAML and still passes validation, so the loss
    is completely silent. Merging by default is the safe reading of the author's
    intent, and the message tells them how to make it explicit.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: core_metadata_collection\n"
        "    category: administrative\n"
        "    description: \"Core metadata for this commons.\"\n"
        "    properties:\n"
        "      - name: submitter_cmc_id\n"
        "        description: \"Submitter-assigned identifier.\"\n"
        "        type: string\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    properties: []\n"
        "links:\n"
        "  - parent: project\n"
        "    multiplicity: one_to_many\n"
        "    child: subject\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    code, printed = run_cli("generate", "-i", str(input_file), "-o", str(out))
    cmc = yaml.safe_load((out / "core_metadata_collection.yaml").read_text())

    assert code == 0
    for name in generate_core_metadata_template()["properties"]:
        assert name in cmc["properties"], f"preset property '{name}' was lost"
    assert "submitter_cmc_id" in cmc["properties"]
    assert "shares the name of a packaged preset" in printed


def test_a_declared_category_is_written_as_a_plain_string(run_cli, tmp_path):
    """
    Input: a preset-named node that declares `category: administrative`.

    Expected: generation succeeds and the category is the string
    "administrative".

    Why it matters: the category is validated into an enum member, and an enum
    member cannot be serialised to YAML. Passing it through the merge unchanged
    made generation fail at the final write with a representer error naming an
    internal Python type - an error that gives the author no clue that their
    perfectly reasonable `category:` line was responsible.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: project\n"
        "    extends: project\n"
        "    category: administrative\n"
        "    properties: []\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    properties: []\n"
        "links:\n"
        "  - parent: project\n"
        "    multiplicity: one_to_many\n"
        "    child: subject\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    code, _ = run_cli("generate", "-i", str(input_file), "-o", str(out))
    project = yaml.safe_load((out / "project.yaml").read_text())

    assert code == 0
    assert project["category"] == "administrative"
    assert isinstance(project["category"], str)


def test_extends_allows_an_explicit_override(run_cli, tmp_path):
    """
    Input: a project node that extends the preset but sets submittable: false.

    Expected: the generated schema uses false, not the preset's true.

    Why it matters: inheriting by default only works if deliberate overrides are
    still possible. The rule is that anything written in the input wins and
    anything omitted is inherited, so an author is never stuck with a preset
    value they need to change.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: project\n"
        "    extends: project\n"
        "    submittable: false\n"
        "    properties: []\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    properties: []\n"
        "links:\n"
        "  - parent: project\n"
        "    multiplicity: one_to_many\n"
        "    child: subject\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    code, printed = run_cli("generate", "-i", str(input_file), "-o", str(out))
    project = yaml.safe_load((out / "project.yaml").read_text())

    assert code == 0
    assert generate_project_template()["submittable"] is True
    assert project["submittable"] is False
    assert "overrode" in printed
