"""
Tests for the warning shown when input properties duplicate a shared definition.

Background: every generated node points at
`_definitions.yaml#/ubiquitous_properties` (or `#/data_file_properties` for a
data_file node) and the node's own properties are written beside it. Both
survive into the file on disk, so someone reading the YAML sees an apparent
duplicate with no indication of which one wins. It resolves only when the
dictionary is resolved, and the node's own definition is the one that takes
effect.

This used to be a hard error at validate time, which was wrong: it rejected the
dictionary Gen3 itself publishes, where 27 of 28 nodes declare a literal `type`.
It is now a warning at generate time, where the person who wrote the property is
the one reading the output.
"""

import os

import yaml

from gen3schemadev.generation import find_shadowed_properties
from gen3schemadev.schema.input_schema import DataModel


def _model(nodes_yaml):
    """Build a validated input model from the nodes described in YAML."""
    return DataModel.model_validate(yaml.safe_load(f"""
version: 0.1.0
url: https://example.biocommons.org.au
nodes:
{nodes_yaml}
links:
  - parent: project
    multiplicity: one_to_many
    child: subject
"""))


def test_declaring_type_on_a_node_is_reported():
    """
    Input: a subject node declaring a property called `type`.

    Expected: one entry naming the node, the ubiquitous_properties block and
    the property.

    Why it matters: `type` is supplied to every node already. Declaring it is
    legal and sometimes deliberate, but silently replacing a Gen3-supplied
    definition is the kind of thing someone should find out at the moment they
    do it, not when a submission behaves strangely months later.
    """
    model = _model("""
  - name: subject
    category: clinical
    description: "A subject."
    properties:
      - name: type
        description: "A custom type."
        type: string
      - name: subject_id
        description: "An identifier."
        type: string
""")

    assert find_shadowed_properties(model) == [
        {'node': 'subject', 'block': 'ubiquitous_properties', 'properties': ['type']},
    ]


def test_data_file_node_is_checked_against_the_data_file_block():
    """
    Input: a data_file node declaring `file_name`.

    Expected: reported against data_file_properties, not ubiquitous_properties.

    Why it matters: data_file nodes get a different shared block, which adds
    file_name, md5sum and friends on top of the ubiquitous names. Checking
    every node against the same set would miss these entirely.
    """
    model = _model("""
  - name: subject
    category: clinical
    description: "A subject."
    properties:
      - name: subject_id
        description: "An identifier."
        type: string
  - name: my_file
    category: data_file
    description: "A file."
    properties:
      - name: file_name
        description: "A custom file name."
        type: string
""")

    assert find_shadowed_properties(model) == [
        {'node': 'my_file', 'block': 'data_file_properties', 'properties': ['file_name']},
    ]


def test_a_node_that_shadows_nothing_is_not_reported():
    """
    Input: a node whose properties are all its own.

    Expected: nothing reported.

    Why it matters: this is the common case. A warning that fired on ordinary
    input would be noise, and noisy warnings get filtered out mentally along
    with the ones that matter.
    """
    model = _model("""
  - name: subject
    category: clinical
    description: "A subject."
    properties:
      - name: subject_id
        description: "An identifier."
        type: string
""")

    assert find_shadowed_properties(model) == []


def test_preset_nodes_are_not_reported():
    """
    Input: a `project` node declaring `project_id`.

    Expected: nothing reported.

    Why it matters: project.yaml and program.yaml are packaged presets that
    list their properties literally with no shared $ref, so there is nothing to
    shadow - and merge_onto_preset already reports what a declaring node added
    or overrode. This is not hypothetical: tests/input_example.yml and two
    other fixtures declare project_id on project, so getting this wrong would
    fire the warning on the repository's own examples.
    """
    model = _model("""
  - name: project
    category: administrative
    description: "A project."
    properties:
      - name: project_id
        description: "A project identifier."
        type: string
  - name: subject
    category: clinical
    description: "A subject."
    properties:
      - name: subject_id
        description: "An identifier."
        type: string
""")

    assert find_shadowed_properties(model) == []


def test_a_declared_property_overrides_the_shared_ref_definition():
    """
    Input: a node carrying both `$ref: ubiquitous_properties` and its own
    `type` property, put through the resolver gen3schemadev ships.

    Expected: the node's own definition survives; a property it does not
    declare keeps the shared definition.

    Why it matters: the warning tells users their definition is the one that
    takes effect. That is true of this resolver - it spreads sibling keys over
    the referenced block - and was verified by hand against the real library.
    If an upgrade to gen3-validator ever flipped that precedence, the warning
    would quietly become false. This test is what catches that.
    """
    from gen3_validator.resolve_schema import ResolveSchema

    resolver = ResolveSchema.__new__(ResolveSchema)
    definitions = {
        'ubiquitous_properties': {
            'type': {'type': 'string'},
            'submitter_id': {'type': 'string', 'description': 'The shared one.'},
        },
    }
    node = {
        'properties': {
            '$ref': '_definitions.yaml#/ubiquitous_properties',
            'type': {'enum': ['my_custom_type'], 'description': 'The declared one.'},
        },
    }

    resolved = resolver.resolve_references(node, definitions)['properties']

    assert resolved['type'] == {'enum': ['my_custom_type'], 'description': 'The declared one.'}
    assert resolved['submitter_id']['description'] == 'The shared one.'


# ---------------------------------------------------------------------------
# Through the CLI
# ---------------------------------------------------------------------------

SHADOWING_INPUT = """version: 0.1.0
url: https://example.biocommons.org.au
nodes:
  - name: subject
    category: clinical
    description: "A subject."
    properties:
      - name: type
        description: "A custom type."
        type: string
      - name: subject_id
        description: "An identifier."
        type: string
links:
  - parent: project
    multiplicity: one_to_many
    child: subject
"""


def test_generate_warns_and_still_writes_the_dictionary(run_cli, tmp_path):
    """
    Input: `generate` with an input file declaring a property called `type`.

    Expected: exit 0, the warning names the node and property, and the files
    are written.

    Why it matters: this is a warning, not a gate. Declaring a shared property
    is legal Gen3 - the dictionary Gen3 publishes does it on nearly every node -
    so blocking generation would repeat the mistake this change exists to undo.
    If this ever starts failing, the warning has quietly become a rule again.
    """
    input_path = tmp_path / "input_dd.yaml"
    input_path.write_text(SHADOWING_INPUT)
    output_dir = tmp_path / "dictionary"

    code, out = run_cli("generate", "-i", str(input_path), "-o", str(output_dir))

    assert code == 0
    assert "subject" in out
    assert "type" in out
    assert "ubiquitous_properties" in out
    assert (output_dir / "subject.yaml").exists()


def test_generate_is_quiet_for_the_shipped_example(run_cli, tmp_path):
    """
    Input: `generate` with the example input file that `init` writes.

    Expected: exit 0 with no shadowing warning.

    Why it matters: a warning that fires on our own starter file teaches every
    new user, on their first run, that warnings from this tool can be ignored.
    """
    example = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "examples", "input_example.yaml",
    )

    code, out = run_cli("generate", "-i", example, "-o", str(tmp_path / "dictionary"))

    assert code == 0
    assert "already supplies" not in out
