import argparse
from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission
import os
import json
import sys


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True, type=str,
                        help="The outer folder where simulated data lives, usually "
                             "s/path/to/umccr-dictionary/data/<NAME OF DICT>")
    parser.add_argument("--projects", nargs="*", default=["AusDiab", "FIELD", "BioHEART-CT"],
                        help="The names of the specific projects, space-delimited, which are sub-folders of the "
                             "--folder provided")
    parser.add_argument("--delete_all_metadata", action="store_true",
                        help="If specified, will delete all node metadata below the project level in order.")
    return parser.parse_args()


def delete_metadata(project_name, folder_path):
    with open(os.path.join(folder_path, project, "DataImportOrder.txt"), "r") as f:
        import_order = [line.rstrip() for line in f]
        import_order.remove("project")
        import_order.remove("program")
    import_order.reverse()
    endpoint = "https://data.acdc.ozheart.org"
    auth = Gen3Auth(endpoint=endpoint, refresh_file="_local/credentials.json")
    sub = Gen3Submission(endpoint=endpoint, auth_provider=auth)
    for node in import_order:
        sub.delete_node("program1", project_name, node)


if __name__ == "__main__":
    args = parse_arguments()
    if args.delete_all_metadata:
        proceed = input(f"Are you sure you want to delete all exising metadata for the projects: {args.projects}? y/n\n")
        if proceed.lower() == "y":
            "Ok, now proceeding to delete..."
            for project in args.projects:
                delete_metadata(project, args.folder)
            print("Deletion completed, now exiting.")
            sys.exit()
        else:
            print("ok, now exiting. Please remove --delete_all_metadata flag and rerun script")
            sys.exit()

    for project in args.projects:
        print("Processing project: {}".format(project))

        folder = args.folder
        endpoint = "https://data.acdc.ozheart.org"
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
