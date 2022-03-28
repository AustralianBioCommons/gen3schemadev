### this script will go through the current dictionary and fix up the links...
import json

with open("../edited_jsons/sample.json", "r") as f:
    sample_json = json.load(f)

with open("../edited_jsons/core_metadata_collection.json", "r") as f:
    cmc_json = json.load(f)

with open("../edited_jsons/sequencing_file.json", "r") as f:
    seq_file_json = json.load(f)

with open("../edited_jsons/lipidomics_file.json", "r") as f:
    lip_file_json = json.load(f)

sample_ids = [x['submitter_id'] for x in sample_json]

cmc_ids = [x['submitter_id'] for x in cmc_json]

for index in range(len(sample_ids)):
    seq_file_json[index]['samples'] = {'submitter_id': sample_ids[index]}
    seq_file_json[index]['core_metadata_collections'] = {'submitter_id': cmc_ids[index]}
    lip_file_json[index]['samples'] = {'submitter_id': sample_ids[index]}
    lip_file_json[index]['core_metadata_collections'] = {'submitter_id': cmc_ids[index]}


with open("../edited_jsons/sequencing_file.json", "w+") as f:
    json.dump(seq_file_json, f, indent=4, sort_keys=True)

with open("../edited_jsons/lipidomics_file.json", "w+") as f:
    json.dump(seq_file_json, f, indent=4, sort_keys=True)