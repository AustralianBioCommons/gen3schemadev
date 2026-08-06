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


# ---------------------------------------------------------------------------
# Dangling reference detection
#
# The resolver this tool ships raises a bare KeyError naming only the missing
# key - 'file_format' - with no indication of which file or which property
# asked for it. On a dictionary with ninety definitions that is a grep, not a
# diagnosis. find_dangling_refs names all three up front.
# ---------------------------------------------------------------------------

from gen3schemadev.refs import find_dangling_refs


def test_find_dangling_refs_names_the_file_the_path_and_the_ref():
    """
    Input: a bundle whose _definitions.yaml points a term at a key that
    _terms.yaml does not contain.

    Expected: one hit giving the source file, the dotted path to the offending
    property, and the reference itself.

    Why it matters: this is exactly the defect in the dictionary Gen3
    publishes. The reader needs to know where to go, and the resolver's own
    error tells them only what was missing, not where it was asked for.
    """
    bundle = {
        '_definitions.yaml': {
            'file_format': {'type': 'string', 'term': {'$ref': '_terms.yaml#/file_format'}},
        },
        '_terms.yaml': {'data_format': {'description': 'A real term.'}},
    }

    assert find_dangling_refs(bundle) == [
        ('_definitions.yaml', 'file_format.term', '_terms.yaml#/file_format'),
    ]


def test_find_dangling_refs_resolves_bare_refs_against_their_own_schema():
    """
    Input: a bundle whose _definitions.yaml uses a bare '#/UUID' reference to
    a definition that exists in that same file.

    Expected: nothing reported.

    Why it matters: a bare ref points inside the schema that carries it, not
    at another file in the bundle. Treating it as a cross-file lookup would
    report a false dangling reference on essentially every healthy dictionary,
    since Gen3's shared definitions reference each other this way constantly.
    """
    bundle = {
        '_definitions.yaml': {
            'UUID': {'type': 'string'},
            'id': {'$ref': '#/UUID'},
        },
    }

    assert find_dangling_refs(bundle) == []


def test_find_dangling_refs_is_quiet_on_a_healthy_bundle():
    """
    Input: a bundle in which every reference resolves.

    Expected: an empty list.

    Why it matters: this diagnostic runs on every validate. If it reported
    false positives, the warning it produces would be noise and people would
    learn to scroll past it.
    """
    bundle = {
        '_definitions.yaml': {'state': {'type': 'string'}},
        '_terms.yaml': {'sample': {'description': 'A term.'}},
        'sample.yaml': {'id': 'sample', 'properties': {'state': {'$ref': '_definitions.yaml#/state'}}},
    }

    assert find_dangling_refs(bundle) == []
