"""
Tests for gen3schemadev.refs — diagnostics for ``$ref`` usage in Gen3
data dictionaries.

Background: Gen3's resolver merges a property's sibling keys over the
referenced definition, so ``{description: ..., $ref: ...}`` is the normal,
working form. The real hazard is a ``description: null`` placeholder in a
shared definition (commonly the enum definitions in ``_definitions.yaml``):
the Gen3 metaschema requires ``description`` to be a string, and the null
shows up as "No Description" in the data-dictionary viewer and fails
metaschema validation on a resolved NODE schema — far from the definition
that carries it, aborting on the first hit. The helpers tested here report
every offender by path up front, and detect refs whether they sit at the
top level of a property or inside an allOf/anyOf/oneOf combinator (a shape
some dictionaries in the wild carry).
"""

import pytest

from gen3schemadev.cli import print_null_description_warning
from gen3schemadev.refs import find_null_descriptions, has_ref


def test_has_ref_top_level():
    """
    The everyday Gen3 form: a property with a top-level $ref (with or
    without sibling annotations) is a reference. Validators use this to
    skip type/enum checks — the type comes from the referenced definition.
    """
    assert has_ref({"$ref": "_definitions.yaml#/to_one"}) is True
    assert has_ref({"description": "x", "$ref": "_definitions.yaml#/enum_yes_no"}) is True


@pytest.mark.parametrize("combinator", ["allOf", "anyOf", "oneOf"])
def test_has_ref_inside_combinator(combinator):
    """
    Some dictionaries in the wild carry refs wrapped inside combinator
    lists, e.g. {description, allOf: [{$ref: ...}]}. These are valid JSON
    Schema and must also count as references so validation stays tolerant
    of that shape.
    """
    prop = {"description": "x", combinator: [{"$ref": "_definitions.yaml#/enum_yes_no"}]}
    assert has_ref(prop) is True


def test_has_ref_negative_cases():
    """
    Plain properties, empty combinator lists, and non-dict input are not
    references — has_ref must not produce false positives, or validators
    would silently skip real type/enum checks.
    """
    assert has_ref({"type": "string", "description": "notes"}) is False
    assert has_ref({"allOf": [{"minimum": 0}]}) is False
    assert has_ref("not a dict") is False


def test_find_null_descriptions_in_shared_definition():
    """
    Input: a _definitions.yaml-style mapping where one enum carries the
    'description: null' placeholder and another has a real description.
    Expected: exactly the null one is reported, as a dotted path that names
    the offending definition (so the user knows what to fix without
    reverse-engineering a metaschema traceback).
    """
    definitions = {
        "enum_yes_no": {"description": None, "enum": ["yes", "no"]},
        "enum_sex": {"description": "Sex at birth.", "enum": ["male", "female"]},
    }
    assert find_null_descriptions(definitions) == ["enum_yes_no.description"]


def test_find_null_descriptions_inside_list_items():
    """
    Nulls can hide inside combinator lists (anyOf/allOf items). The path
    must show the list index so the offender is still locatable, e.g.
    'properties.status.anyOf[0].description'.
    """
    schema = {
        "properties": {
            "status": {
                "anyOf": [
                    {"description": None, "enum": ["a", "b"]},
                    {"type": "string"},
                ]
            }
        }
    }
    assert find_null_descriptions(schema) == ["properties.status.anyOf[0].description"]


def test_find_null_descriptions_top_level_and_clean_schema():
    """
    A null description at the very top of a schema is reported with the
    bare key as its path; a schema whose descriptions are all real strings
    reports nothing; non-dict input (e.g. a YAML file that parsed to a
    scalar) is handled gracefully with an empty result.
    """
    assert find_null_descriptions({"description": None}) == ["description"]
    clean = {"description": "A node.", "properties": {"x": {"description": "X."}}}
    assert find_null_descriptions(clean) == []
    assert find_null_descriptions("not a schema") == []


def test_print_null_description_warning_lists_offenders(capsys):
    """
    The warning block used by `gen3schemadev validate` must name every
    offender it is given ("file: dotted.path" lines) so a user can fix all
    placeholders in one pass instead of replaying validate after each fix.
    """
    print_null_description_warning([
        "_definitions.yaml: enum_yes_no.description",
        "_definitions.yaml: enum_smoking.description",
    ])
    output = capsys.readouterr().out
    assert "WARNING" in output
    assert "_definitions.yaml: enum_yes_no.description" in output
    assert "_definitions.yaml: enum_smoking.description" in output


def test_print_null_description_warning_silent_when_clean(capsys):
    """
    With no offenders the warning must print nothing at all, so warnings
    remain a trustworthy signal in validate output.
    """
    print_null_description_warning([])
    assert capsys.readouterr().out == ""
