import argparse
from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission
import os
import json


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True, type=str,
                        help="The outer folder where simulated data lives, usually "
                             "s/path/to/umccr-dictionary/data/<NAME OF DICT>")
    parser.add_argument("--projects", nargs="*", default=["AusDiab", "FIELD", "BioHEART-CT"],
                        help="The names of the specific projects, space-delimited, which are sub-folders of the "
                             "--folder provided")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()
    for project in args.projects:
        print("Processing project: {}".format(project))
        with open("{}/{}/edited_jsons/sample.json".format(args.folder, project), "r") as f:
            sample_json = json.load(f)

        with open("{}/{}/edited_jsons/core_metadata_collection.json".format(args.folder, project), "r") as f:
            cmc_json = json.load(f)

        with open("{}/{}/edited_jsons/sequencing_file.json".format(args.folder, project), "r") as f:
            seq_file_json = json.load(f)

        with open("{}/{}/edited_jsons/lipidomics_file.json".format(args.folder, project), "r") as f:
            lip_file_json = json.load(f)

        sample_ids = [x['submitter_id'] for x in sample_json]

        cmc_ids = [x['submitter_id'] for x in cmc_json]

        for index in range(len(sample_ids)):
            seq_file_json[index]['samples'] = {'submitter_id': sample_ids[index]}
            seq_file_json[index]['core_metadata_collections'] = {'submitter_id': cmc_ids[index]}
            lip_file_json[index]['samples'] = {'submitter_id': sample_ids[index]}
            lip_file_json[index]['core_metadata_collections'] = {'submitter_id': cmc_ids[index]}

        with open("{}/{}/edited_jsons/sequencing_file.json".format(args.folder, project), "w+") as f:
            json.dump(seq_file_json, f, indent=4, sort_keys=True)

        with open("{}/{}/edited_jsons/lipidomics_file.json".format(args.folder, project), "w+") as f:
            json.dump(seq_file_json, f, indent=4, sort_keys=True)

        folder = args.folder
        endpoint = "https://gen3.biocommons.org.au"
        auth = Gen3Auth(endpoint=endpoint, refresh_file="_local/credentials.json")
        sub = Gen3Submission(endpoint=endpoint, auth_provider=auth)

        sub.create_program({
            "dbgap_accession_number": "prg123",
            "name": "program1",
            "type": "program"
        })

        proj = json.load(open(os.path.join(folder, project, "edited_jsons", "project.json")))
        sub.create_project("program1", proj)

        for line in open(os.path.join(folder, project, "DataImportOrder.txt"), "r"):
            line = line.strip()
            if line != "program" and line != "project":
                print(f"uploading {line}")
                jsn = json.load(open(os.path.join(folder, project, "edited_jsons", f"{line}.json")))
                sub.submit_record("program1", proj["code"], jsn)
