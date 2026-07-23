"""
Tests for the widened input model: node-level settings and property annotations.

Background: the input language originally described a property with five fields
and a node with four. Anything Gen3 supported beyond that - a default value, a
format annotation, the list of properties the backend manages - could only be
obtained by hand-editing the generated file afterwards, which put the repository
back in the position of not being able to regenerate.

These tests cover what the input can now express, and the two rules that keep
the widening safe: omitting a field inherits the template default rather than
writing a null over it, and an unrecognised key is an error rather than a
silently ignored typo.
"""

import pytest
import yaml
from pydantic import ValidationError

from gen3schemadev.schema.input_schema import DataModel, node, Property


def _model(nodes_yaml):
    """Validate a small data model containing the given nodes block."""
    return DataModel.model_validate(yaml.safe_load(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        f"nodes:\n{nodes_yaml}"
        "links:\n"
        "  - parent: project\n"
        "    multiplicity: one_to_many\n"
        "    child: subject\n"
    ))


def test_property_default_and_format_reach_the_output(run_cli, tmp_path):
    """
    Input: a property declaring both a default value and a format annotation.

    Expected: both appear verbatim in the generated schema.

    Why it matters: Gen3's own project node relies on defaults for its state
    machine and on a date-time format for its release date. Until the input
    could express these, any repository needing them had to edit the generated
    file by hand and then never regenerate.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    properties:\n"
        "      - name: release_state\n"
        "        description: \"Whether the record has been released.\"\n"
        "        type: string\n"
        "        default: unreleased\n"
        "      - name: released_at\n"
        "        description: \"When the record was released.\"\n"
        "        type: string\n"
        "        format: date-time\n"
        "links: []\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    code, _ = run_cli("generate", "-i", str(input_file), "-o", str(out))
    subject = yaml.safe_load((out / "subject.yaml").read_text())

    assert code == 0
    assert subject["properties"]["release_state"]["default"] == "unreleased"
    assert subject["properties"]["released_at"]["format"] == "date-time"


def test_unset_annotations_are_absent_rather_than_null(run_cli, tmp_path):
    """
    Input: a plain string property declaring none of the optional annotations.

    Expected: the generated property has no 'default', 'format' or 'pattern'
    keys at all.

    Why it matters: the model now offers half a dozen optional annotations. If
    every unset one were emitted as null, each property in every schema would
    carry a row of meaningless nulls, and the Gen3 metaschema rejects a null
    where it expects a string. Absent and null are not the same thing here.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    properties:\n"
        "      - name: plain_field\n"
        "        description: \"Nothing special.\"\n"
        "        type: string\n"
        "links: []\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    run_cli("generate", "-i", str(input_file), "-o", str(out))
    prop = yaml.safe_load((out / "subject.yaml").read_text())["properties"]["plain_field"]

    assert prop == {"type": "string", "description": "Nothing special."}


def test_node_level_settings_accept_both_spellings():
    """
    Input: one node using snake_case 'system_properties' and another using the
    Gen3 spelling 'systemProperties'.

    Expected: both validate and carry the same value.

    Why it matters: the rest of the input file is snake_case, but the generated
    Gen3 schema is camelCase, and people copy fragments from existing schemas
    when authoring. Accepting either spelling avoids a class of error whose
    message would otherwise be an unhelpful "unknown field".
    """
    model = _model(
        "  - name: subject\n"
        "    category: clinical\n"
        "    system_properties: [id, state]\n"
        "    properties: []\n"
        "  - name: biospecimen\n"
        "    category: biospecimen\n"
        "    systemProperties: [id, state]\n"
        "    properties: []\n"
    )

    assert model.nodes[0].system_properties == ["id", "state"]
    assert model.nodes[1].system_properties == ["id", "state"]


def test_unset_node_fields_do_not_overwrite_template_defaults(run_cli, tmp_path):
    """
    Input: a node that declares no systemProperties or uniqueKeys.

    Expected: the generated schema still carries the standard Gen3 defaults.

    Why it matters: making these fields optional is only safe if leaving one out
    means "inherit". If an unset field were written through as null, every node
    in every existing dictionary would lose its systemProperties on the next
    regeneration - a silent, catastrophic change that still produces a file that
    looks plausible.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    properties: []\n"
        "links: []\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    run_cli("generate", "-i", str(input_file), "-o", str(out))
    subject = yaml.safe_load((out / "subject.yaml").read_text())

    assert subject["systemProperties"] == [
        "id", "project_id", "state", "created_datetime", "updated_datetime"
    ]
    assert subject["uniqueKeys"] == [["id"], ["project_id", "submitter_id"]]


def test_node_level_required_takes_precedence_over_property_flags(run_cli, tmp_path):
    """
    Input: a node declaring `required: [alpha]` while a different property,
    beta, carries `required: true`.

    Expected: the generated required list is driven by the node-level
    declaration, and always includes submitter_id and type.

    Why it matters: two ways of saying the same thing need a stated winner,
    otherwise the result depends on implementation order and changes without
    warning. The explicit node-level list is the more specific instruction, so
    it wins.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    required: [alpha]\n"
        "    properties:\n"
        "      - name: alpha\n"
        "        description: \"First field.\"\n"
        "        type: string\n"
        "      - name: beta\n"
        "        description: \"Second field.\"\n"
        "        type: string\n"
        "        required: true\n"
        "links: []\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    run_cli("generate", "-i", str(input_file), "-o", str(out))
    subject = yaml.safe_load((out / "subject.yaml").read_text())

    assert subject["required"] == ["alpha", "submitter_id", "type"]


def test_unknown_key_in_input_is_rejected(run_cli, tmp_path):
    """
    Input: a property using the misspelling 'descriptoin'.

    Expected: generation fails, names the offending location, and writes nothing.

    Why it matters: unknown keys used to be dropped in silence, so a typo in a
    field name produced a schema quietly missing that field. Since a description
    is mandatory in Gen3, the failure would surface much later as a metaschema
    error against a file nobody remembered editing.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    properties:\n"
        "      - name: species\n"
        "        descriptoin: \"Typo above.\"\n"
        "        type: string\n"
        "links: []\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    code, printed = run_cli("generate", "-i", str(input_file), "-o", str(out))

    assert code == 1
    assert "descriptoin" in printed or "description" in printed
    assert list(out.iterdir()) == []


def test_category_is_required_unless_the_node_extends_a_preset():
    """
    Input: one node with neither category nor extends, and one with extends but
    no category.

    Expected: the first is rejected; the second is accepted.

    Why it matters: category was mandatory, and it must stay mandatory for
    ordinary nodes because it drives how the node is generated. A node that
    extends a preset is the one legitimate exception, since it inherits the
    preset's category - requiring it there would force authors to restate a
    value they are not choosing.
    """
    with pytest.raises(ValidationError):
        _model(
            "  - name: subject\n"
            "    properties: []\n"
        )

    model = _model(
        "  - name: project\n"
        "    extends: project\n"
        "    properties: []\n"
    )
    assert model.nodes[0].category is None
    assert model.nodes[0].extends == "project"


def test_extra_definitions_are_merged_into_the_generated_definitions(run_cli, tmp_path):
    """
    Input: a top-level `definitions` block contributing a custom enum.

    Expected: the custom enum appears in the generated _definitions.yaml, and
    the packaged definitions are still present.

    Why it matters: _definitions.yaml is rewritten from a packaged template on
    every run, so any shared enum a repository added by hand was destroyed the
    next time anyone regenerated. One repository maintained a bespoke script
    purely to re-inject its enums after every generation; declaring them in the
    input removes the need for that entirely.
    """
    input_file = tmp_path / "input_dd.yaml"
    input_file.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "definitions:\n"
        "  enum_sample_state:\n"
        "    description: \"Whether a sample is available.\"\n"
        "    enum: [available, exhausted]\n"
        "nodes:\n"
        "  - name: subject\n"
        "    category: clinical\n"
        "    description: \"An individual organism.\"\n"
        "    properties: []\n"
        "links: []\n"
    )
    out = tmp_path / "dictionary"
    out.mkdir()

    code, _ = run_cli("generate", "-i", str(input_file), "-o", str(out))
    definitions = yaml.safe_load((out / "_definitions.yaml").read_text())

    assert code == 0
    assert definitions["enum_sample_state"]["enum"] == ["available", "exhausted"]
    # the packaged definitions survive the merge
    assert "ubiquitous_properties" in definitions
    assert "datetime" in definitions
