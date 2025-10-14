import pytest
import os
from gen3schemadev.cli import get_version

@pytest.fixture
def fixture_toml_version():

    test_file_loc = os.path.abspath(__file__)
    toml_file_loc = os.path.join(os.path.dirname(test_file_loc), "../pyproject.toml")
    with open(toml_file_loc, "r") as f:
        toml = f.read()
    # get version from pyproject.toml
    version = toml.split("version = ")[1].split("\n")[0]
    version = version.strip('"')
    return version

@pytest.fixture
def fixture_cli_version():
    return get_version()

def test_do_versions_match(fixture_toml_version, fixture_cli_version):
    assert fixture_toml_version == fixture_cli_version