gen3schemadev is an object mapper for a gen3 schema to allow programmatical generation.

## Current Workflow for editing CAD Project Dictionary

### Local deployment (compose-services)

1. Make schema edits to the `Harmonised Variables - v1 google sheet`
2. All schema objects in the google sheet need to have a template schema in the `schema` folder (to be phased out when all info can be generated)
3. Run `schema2yaml.py` which automatically reads the google sheets and parses the required information, writing the parsed schemas to the folder `schema_out` 
4. Copy `schema_out/*.yaml` to `path/to/umccr-dictionary/dictionary/cad/gdcdictionary/schema`, compile, test, validate. If test or validate fails, go back to 1 above.
5. Simulate data with the new schema, `make simulate dd=cad`, adjust the number of samples and name of project as required.
   1. Replace random simulated values with plausible ones using `plausible-data-gen` script
6. Switch the old gen3 dictionary with the new one
   1. upload the compiled json schema to the configured s3 bucket@`DICTIONARY_URL`
   2. ?? delete psql volume (?) (only in development phase so doesn't matter if data is lost)
   3. disable indexing services (kibana, guppy, tube)
   4. restart services, re-configure auth
   5. upload the simulated data against the new dictionary
   6. re-enable and restart indexing services and re-run etl index (`guppy_setup.sh`)

## Todo:
- make link generation work
- implement reference mangling
- add unit tests

