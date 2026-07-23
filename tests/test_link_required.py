"""
Tests for declaring whether a link is required, per link.

Background: in Gen3, every link on a node carries a `required` flag saying
whether an instance of the child must be attached to a parent of that type.
Until now the input language could not express it — a link was declared as a
plain parent/multiplicity/child triple and the generator stamped
`required: true` on every one.

That is not a cosmetic gap. Across the four dictionaries built with this tool,
41 of 113 declared links are `required: false`, and the same triple shape appears
with both values: in one repository `subject -> site` is required while
`subject -> demographic_measurements`, an identical one_to_one triple, is
optional. No rule derived from the triple could produce both, so those values had
been hand-edited into the generated files and were destroyed on regeneration.

A node with several links matters here too. Where a node has two or three
parents the generator emits them as one subgroup, and each member needs its own
answer — typically a real parent that is required alongside an optional
attachment. These tests pin that each link keeps its own value rather than the
node getting a single blanket setting.
"""

import textwrap

import pytest
import yaml

from gen3schemadev.converter import convert_node_links, get_node_links, populate_template
from gen3schemadev.schema.gen3_template import generate_gen3_template, get_metaschema
from gen3schemadev.schema.input_schema import DataModel


def build(input_yaml):
    """Validate an input document and return (model, node template)."""
    model = DataModel.model_validate(yaml.safe_load(textwrap.dedent(input_yaml)))
    return model, generate_gen3_template(get_metaschema())


def links_of(schema):
    """Return a node's links, flattening the subgroup wrapper if present."""
    links = schema.get('links') or []
    if links and 'subgroup' in links[0]:
        return links[0]['subgroup']
    return links


def required_by_name(schema):
    """Map link name -> required flag, for readable assertions."""
    return {link['name']: link['required'] for link in links_of(schema)}


BASE = """
    version: 0.1.0
    url: https://example.biocommons.org.au
    nodes:
      - name: subject
        category: clinical
        description: "An individual organism."
        properties: []
      - name: site
        category: clinical
        description: "A collection site."
        properties: []
      - name: measurement
        category: clinical
        description: "A measurement taken from a subject."
        properties: []
    links:
      - parent: project
        multiplicity: one_to_many
        child: subject
      - parent: subject
        multiplicity: one_to_many
        child: measurement
"""


def test_link_is_required_by_default():
    """
    Input: a link that says nothing about `required`.

    Expected: the generated link is `required: true`.

    Why it matters: this is what makes the feature additive. Every dictionary
    written before `required` was declarable must regenerate byte-identically,
    so the default has to match the value the generator used to hardcode. A
    different default would silently flip every link in four production models.
    """
    model, template = build(BASE)

    schema = populate_template('measurement', model, template)

    assert required_by_name(schema) == {'subjects': True}


def test_link_can_be_declared_optional():
    """
    Input: the same link, declared `required: false`.

    Expected: the generated link is `required: false`.

    Why it matters: this is the whole point. One repository has eight links that
    are optional in its committed dictionary and could not be expressed at all,
    so regenerating would have quietly made eight parent relationships mandatory
    and broken submissions that omit them.
    """
    model, template = build(BASE.replace(
        "      - parent: subject\n        multiplicity: one_to_many\n        child: measurement\n",
        "      - parent: subject\n        multiplicity: one_to_many\n        child: measurement\n        required: false\n",
    ))

    schema = populate_template('measurement', model, template)

    assert required_by_name(schema) == {'subjects': False}


def test_each_link_in_a_subgroup_keeps_its_own_required():
    """
    Input: a node with three parents — the first required, the second optional,
    the third required.

    Expected: the generated subgroup carries true, false, true respectively.

    Why it matters: this is the headline case. A node with several parents is
    emitted as one subgroup, and previously every member got the same flag. Real
    dictionaries need to mix them — a file node genuinely belongs to its assay
    but only optionally to a collection site — so the second and third links must
    be able to disagree with the first.
    """
    model, template = build("""
        version: 0.1.0
        url: https://example.biocommons.org.au
        nodes:
          - name: subject
            category: clinical
            description: "An individual organism."
            properties: []
          - name: site
            category: clinical
            description: "A collection site."
            properties: []
          - name: assay
            category: biospecimen
            description: "An assay."
            properties: []
          - name: measurement
            category: clinical
            description: "A measurement."
            properties: []
        links:
          - parent: project
            multiplicity: one_to_many
            child: subject
          - parent: subject
            multiplicity: one_to_many
            child: measurement
            required: true
          - parent: site
            multiplicity: one_to_many
            child: measurement
            required: false
          - parent: assay
            multiplicity: one_to_many
            child: measurement
            required: true
    """)

    schema = populate_template('measurement', model, template)

    assert required_by_name(schema) == {
        'subjects': True,
        'sites': False,
        'assays': True,
    }
    # The subgroup wrapper itself is unchanged - "at least one of these".
    assert schema['links'][0]['exclusive'] is False
    assert schema['links'][0]['required'] is True


def test_single_link_node_keeps_its_required():
    """
    Input: a node with exactly one parent, declared optional.

    Expected: the flat, non-subgroup link form is `required: false`.

    Why it matters: a node with one link is emitted as a bare list rather than a
    subgroup, which is a separate code path. The eight links that motivated this
    feature are all of this shape, so if only the subgroup path honoured the
    flag the feature would miss its own use case.
    """
    model, template = build(BASE.replace(
        "      - parent: subject\n        multiplicity: one_to_many\n        child: measurement\n",
        "      - parent: subject\n        multiplicity: one_to_many\n        child: measurement\n        required: false\n",
    ))

    schema = populate_template('measurement', model, template)

    assert 'subgroup' not in schema['links'][0]
    assert schema['links'][0]['required'] is False


def test_injected_core_metadata_link_stays_optional():
    """
    Input: a data_file node whose declared link is marked required.

    Expected: the declared link is required, and the automatically injected
    core_metadata_collection link is still optional.

    Why it matters: the core metadata link is added by the generator, not the
    author, and Gen3 treats it as optional. Reading `required` per link must not
    leak the neighbouring link's value onto it.
    """
    model, template = build("""
        version: 0.1.0
        url: https://example.biocommons.org.au
        nodes:
          - name: assay
            category: biospecimen
            description: "An assay."
            properties: []
          - name: result_file
            category: data_file
            description: "A results file."
            properties: []
        links:
          - parent: project
            multiplicity: one_to_many
            child: assay
          - parent: assay
            multiplicity: one_to_many
            child: result_file
            required: true
    """)

    schema = populate_template('result_file', model, template)

    assert required_by_name(schema) == {
        'assays': True,
        'core_metadata_collections': False,
    }


def test_data_file_node_without_declared_links_still_gets_core_metadata():
    """
    Input: a data_file node that declares no links at all.

    Expected: it still receives the core_metadata_collection link.

    Why it matters: this is a regression test for a bug found while adding the
    feature. The injection was conditional on the node already having links, so
    a link-less data_file node emitted `links: []` while still receiving the
    matching core_metadata_collections property — producing a schema that failed
    this tool's own data_file validation rule. The tool should not be able to
    generate something its validator rejects.
    """
    model, template = build("""
        version: 0.1.0
        url: https://example.biocommons.org.au
        nodes:
          - name: orphan_file
            category: data_file
            description: "A file with no declared parent."
            properties: []
        links: []
    """)

    schema = populate_template('orphan_file', model, template)

    assert required_by_name(schema) == {'core_metadata_collections': False}


def test_convert_node_links_falls_back_for_raw_dicts():
    """
    Input: raw link dicts with no `required` key, passed straight to
    convert_node_links with the parameter set to False.

    Expected: both emitted links are `required: false`.

    Why it matters: convert_node_links is a public helper with a `required`
    parameter that predates this feature. Callers passing hand-built dicts must
    keep working, so a link's own value wins and the parameter remains the
    fallback rather than being ignored.
    """
    raw = [
        {'parent': 'subject', 'multiplicity': 'one_to_many', 'child': 'measurement'},
        {'parent': 'site', 'multiplicity': 'one_to_many', 'child': 'measurement'},
    ]

    converted = convert_node_links(raw, required=False)

    assert [link['required'] for link in converted] == [False, False]


def test_declared_required_wins_over_the_parameter():
    """
    Input: raw link dicts that declare `required: true`, with the fallback
    parameter set to False.

    Expected: the declared value wins.

    Why it matters: pins the precedence explicitly. Without it, a future change
    could reverse the two and every dictionary would silently flip.
    """
    raw = [{'parent': 'subject', 'multiplicity': 'one_to_many',
            'child': 'measurement', 'required': True}]

    converted = convert_node_links(raw, required=False)

    assert converted[0]['required'] is True


def test_a_meaningless_required_value_is_rejected():
    """
    Input: a link declaring `required: maybe`.

    Expected: validation fails.

    Why it matters: the Gen3 metaschema types this key as a boolean, so a bad
    value would otherwise surface as a metaschema failure on a generated file,
    far from the line at fault. Failing during input validation names the link
    instead. Note that the ordinary boolean spellings YAML and pydantic accept -
    true/false, yes/no, 1/0 - are coerced rather than rejected, consistent with
    every other boolean field in the input model.
    """
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        build(BASE.replace(
            "        child: measurement\n",
            "        child: measurement\n        required: maybe\n",
        ))
