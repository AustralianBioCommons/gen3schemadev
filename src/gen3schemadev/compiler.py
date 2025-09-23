# Module to compile user input into gen3 schema yamls, also compiles multiple gen3 schema yamls into a single gen3 bundled jsonschemas (.json)
import json
import os
import yaml
from jsonschema import validate

