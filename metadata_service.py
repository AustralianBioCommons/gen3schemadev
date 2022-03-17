import argparse
from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission
from gen3.index import Gen3Index
from gen3.metadata import Gen3Metadata
import requests
import os
import json
import sys
import subprocess

endpoint = "https://data.acdc.ozheart.org"
auth = Gen3Auth(endpoint=endpoint, refresh_file="_local/credentials.json")
metadata = Gen3Metadata(auth)
sub = Gen3Submission(auth)
query = "{ project(first:0) { id, code, name, project_description, consent_codes } }"
projects = sub.query(query)
for project in projects['data']['project']:
    print(project)
    metadata.create(project['id'], project)


