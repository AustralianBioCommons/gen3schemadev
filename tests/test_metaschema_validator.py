import pytest
import os
import logging
import re
from unittest.mock import patch, MagicMock

from gen3schemadev.schema.gen3_template import get_metaschema, resolve_schema
from gen3schemadev.validators.metaschema_validator import validate_schema_with_metaschema


def _get_demographic_schema(schema_filename: str) -> dict:
    """Helper to load and parse a specific schema from a test data file."""
    file_loc = os.path.dirname(os.path.abspath(__file__))
    schema_file = os.path.join(file_loc, schema_filename)
    resolved_schema_dict = resolve_schema(schema_path=schema_file)

    for schema in resolved_schema_dict.values():
        if isinstance(schema, dict) and schema.get('id') == 'demographic':
            demographic_schema = schema
            break

    if not demographic_schema:
        pytest.fail(f"Test setup error: Schema 'demographic' not found in {schema_filename}")
    return demographic_schema


# --- Fixtures ---
@pytest.fixture
def fixture_metaschema() -> dict:
    """Provides the Gen3 metaschema."""
    return get_metaschema()

@pytest.fixture
def fixture_gen3_schema_pass() -> dict:
    """Provides a valid Gen3 schema."""
    return _get_demographic_schema('gen3_schema/testing/schema_dev_pass.json')

@pytest.fixture
def fixture_gen3_schema_fail() -> dict:
    """Provides an invalid Gen3 schema."""
    return _get_demographic_schema('gen3_schema/testing/schema_dev_fail.json')


# --- Test Cases ---

@patch('gen3schemadev.validators.metaschema_validator.subprocess.run')
def test_successful_validation(mock_run, fixture_metaschema, fixture_gen3_schema_pass, caplog):
    """
    Tests the happy path: a valid schema should pass without errors.
    """
    mock_run.return_value = MagicMock(returncode=0)
    with caplog.at_level(logging.INFO):
        validate_schema_with_metaschema(fixture_gen3_schema_pass, fixture_metaschema)
    assert "successfully validated" in caplog.text

@patch('gen3schemadev.validators.metaschema_validator.subprocess.run')
def test_validation_failure_logs_specific_errors(mock_run, fixture_metaschema, fixture_gen3_schema_fail, caplog):
    """
    Tests the failure path by 'grepping' the log output for specific
    validation errors, ignoring the exact temporary file path.
    """
    # Realistic stdout from the check-jsonschema tool.
    mock_stdout_from_tool = """
    [/var/folders/h1/smw4rryj4zs361v4bw9qqc0c0000gn/T/tmp2ipbzydn.json]::$.properties.year_birth.type: 'date-time' is not valid under any of the given schemas
    [/var/folders/h1/smw4rryj4zs361v4bw9qqc0c0000gn/T/tmp_other.json]::$.category: 'a_random_category' is not one of ['administrative', 'analysis', 'biospecimen', 'clinical', 'data']
    [/var/folders/h1/smw4rryj4zs361v4bw9qqc0c0000gn/T/another_tmp.json]::$.links[0]: Additional properties are not allowed ('names' was unexpected)
    """
    mock_run.return_value = MagicMock(returncode=1, stdout=mock_stdout_from_tool, stderr="")

    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="check-jsonschema validation failed"):
            validate_schema_with_metaschema(fixture_gen3_schema_fail, fixture_metaschema)

    # Grep the logs for key error messages, using a wildcard for the file path.
    log_text = caplog.text
    expected_errors = [
        # Match "::$.properties.year_birth.type: 'date-time' is not valid", ignoring the file path.
        r"::\$\.properties\.year_birth\.type: 'date-time' is not valid",
        # Match "::$.category: 'a_random_category' is not one of", ignoring the file path.
        r"::\$\.category: 'a_random_category' is not one of",
        # Match "::$.links[0]: Additional properties are not allowed ('names' was unexpected)", ignoring the file path.
        r"::\$\.links\[0\]: Additional properties are not allowed \('names' was unexpected\)",
    ]

    for error_pattern in expected_errors:
        assert re.search(error_pattern, log_text), f"Expected error pattern not found in logs: '{error_pattern}'"

@patch('gen3schemadev.validators.metaschema_validator.subprocess.run')
def test_tool_not_found(mock_run, fixture_metaschema, fixture_gen3_schema_pass, caplog):
    """
    Tests resilience if the check-jsonschema tool is not installed.
    """
    mock_run.side_effect = FileNotFoundError
    with caplog.at_level(logging.ERROR):
        with pytest.raises(RuntimeError, match="check-jsonschema tool not found"):
            validate_schema_with_metaschema(fixture_gen3_schema_pass, fixture_metaschema)
    assert "tool was not found" in caplog.text

@pytest.mark.parametrize("bad_input", ["not_a_dict", 123, None, []])
def test_invalid_input_types(bad_input, fixture_metaschema):
    """
    Tests input validation: ensures a ValueError for non-dictionary inputs.
    """
    with pytest.raises(ValueError, match="must be a dictionary"):
        validate_schema_with_metaschema(schema=bad_input, metaschema=fixture_metaschema)
    with pytest.raises(ValueError, match="must be a dictionary"):
        validate_schema_with_metaschema(schema=fixture_metaschema, metaschema=bad_input)


# ---------------------------------------------------------------------------
# Nested link subgroups
#
# Gen3 allows a link subgroup to contain another subgroup - `submitted_copy_number`
# in the official dictionary is shaped that way. The packaged metaschema only
# allowed plain links inside a subgroup, so it rejected a dictionary Gen3 itself
# publishes.
# ---------------------------------------------------------------------------

import jsonschema


def _node_with_links(links):
    """A metaschema-complete node, so a test only varies the links."""
    return {
        "id": "nested_node",
        "title": "Nested Node",
        "type": "object",
        "category": "clinical",
        "description": "A node whose links nest.",
        "program": "*",
        "project": "*",
        "submittable": True,
        "validators": None,
        "systemProperties": ["id"],
        "uniqueKeys": [["id"]],
        "required": ["submitter_id", "type"],
        "links": links,
        "properties": {"type": {"type": "string"}},
    }


def _complete_link(name, target):
    return {
        "name": name,
        "backref": f"{name}_backref",
        "label": "derived_from",
        "target_type": target,
        "multiplicity": "one_to_one",
        "required": False,
    }


def test_a_nested_link_subgroup_passes_the_metaschema(fixture_metaschema):
    """
    Input: a node whose link subgroup contains another subgroup.

    Expected: no metaschema errors.

    Why it matters: this is the shape of `submitted_copy_number` in the
    dictionary Gen3 publishes. The metaschema previously allowed only plain
    links inside a subgroup, so that node failed - the last thing standing
    between the reference dictionary and a clean validate.
    """
    schema = _node_with_links([{
        "exclusive": False,
        "required": True,
        "subgroup": [
            _complete_link("core_metadata_collections", "core_metadata_collection"),
            {
                "exclusive": True,
                "required": False,
                "subgroup": [
                    _complete_link("aliquots", "aliquot"),
                    _complete_link("read_groups", "read_group"),
                ],
            },
        ],
    }])

    errors = list(jsonschema.Draft4Validator(fixture_metaschema).iter_errors(schema))

    assert errors == []


def test_a_malformed_link_inside_a_nested_subgroup_is_still_rejected(fixture_metaschema):
    """
    Input: the same nested shape, but a link in the inner subgroup has no
    `backref`.

    Expected: the metaschema still reports an error.

    Why it matters: the recursion was added so nested links are checked
    properly, not so they stop being checked. Without this, a change that
    accepted anything inside a subgroup would look identical to the fix.
    """
    incomplete = _complete_link("aliquots", "aliquot")
    del incomplete["backref"]
    schema = _node_with_links([{
        "exclusive": False,
        "required": True,
        "subgroup": [
            _complete_link("core_metadata_collections", "core_metadata_collection"),
            {"exclusive": True, "required": False, "subgroup": [incomplete]},
        ],
    }])

    errors = list(jsonschema.Draft4Validator(fixture_metaschema).iter_errors(schema))

    assert errors != []
