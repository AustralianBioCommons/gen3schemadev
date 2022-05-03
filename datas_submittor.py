import argparse
from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission
from gen3.index import Gen3Index
import requests
import os
import json
import sys
import subprocess


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--folder", required=True, type=str,
                        help="The outer folder where simulated data lives, usually "
                             "s/path/to/umccr-dictionary/data/<NAME OF DICT>")
    parser.add_argument("--projects", nargs="*", default=["AusDiab", "FIELD", "BioHEART-CT"],
                        help="The names of the specific projects, space-delimited, which are sub-folders of the "
                             "--folder provided")
    parser.add_argument("--delete-all-metadata", action="store_true",
                        help="If specified, will delete all node metadata below the project level in order.")
    parser.add_argument("--profile", action="store",
                        help="The name of your gen3-client profile, required for uploading data files to the portal.")
    parser.add_argument("--numparallel", action="store", default=2,
                        help="how many cores to use for uploading in parallel")
    parser.add_argument("--add-subjects", action="store_true", default=False,
                        help="If specified, will skip program and project creation and will add nodes from subjects "
                             "onwards")
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
    sub.delete_nodes("program1", project_name, import_order)


if __name__ == "__main__":
    args = parse_arguments()
    if args.delete_all_metadata:
        proceed = input(f"Are you sure you want to delete all existing metadata for the projects: {args.projects}? y/n\n")
        if proceed.lower() == "y":
            "Ok, now proceeding to delete..."
            for project in args.projects:
                delete_metadata(project, args.folder)
            print("Deletion completed, now exiting.")
            sys.exit()
        else:
            print("ok, now exiting. Please remove --delete_all_metadata flag and rerun script.")
            sys.exit()

    for project in args.projects:
        print(f"Processing project: {project}")
        folder = args.folder

        if args.profile and os.path.exists(os.path.join(folder, project, "dummy_files")):
            upload_path = os.path.join(folder, project, "dummy_files")
            bash_command = f"gen3-client upload --upload-path={upload_path} --profile={args.profile} " \
                           f"--numparallel={args.numparallel}"
            process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
            output, error = process.communicate()

        endpoint = "https://data.acdc.ozheart.org"
        script_path = os.path.abspath(os.path.dirname(__file__))
        auth_path = os.path.join(script_path, "_local", "credentials.json")
        auth = Gen3Auth(endpoint=endpoint, refresh_file=auth_path)
        sub = Gen3Submission(endpoint=endpoint, auth_provider=auth)
        index = Gen3Index(endpoint=endpoint, auth_provider=auth)

        if not args.add_subjects:
            sub.create_program({
                "dbgap_accession_number": "prg123",
                "name": "program1",
                "type": "program"
            })
            proj = json.load(open(os.path.join(folder, project, "edited_jsons", "project.json")))
            sub.create_project("program1", proj)

        for line in open(os.path.join(folder, project, "DataImportOrder.txt"), "r"):
            line = line.strip()
            if args.add_subjects:
                skip_objects = ["program", "project", "acknowledgement", "publication"]
            else:
                skip_objects = ["program", "project", "acknowledgement", "publication"]
            if line not in skip_objects:
                print(f"uploading {line}")
                jsn = json.load(open(os.path.join(folder, project, "edited_jsons", f"{line}.json")))
                if line.endswith("file"):
                    for file_md in jsn:
                        try:
                            indexed_file = index.get_with_params({"file_name": file_md['file_name']})
                            file_md['object_id'] = indexed_file['did']
                            file_md['md5sum'] = indexed_file['hashes']['md5']
                            file_md['file_size'] = indexed_file['size']
                        except KeyError as e:
                            print(e)
                            print(f"{file_md['file_name']} data file not yet uploaded")
                        except requests.exceptions.HTTPError as e:
                            print(e)
                            content = e.response.content
                            print(f"{file_md['file_name']} data file not yet uploaded")
                            pass
                        except TypeError as e:
                            print(e)
                            print(f"{file_md['file_name']} data file not yet uploaded")
                try:
                    sub.submit_record("program1", project, jsn)
                except requests.exceptions.HTTPError as e:
                    content = e.response.content
                    try:
                        content = json.dumps(json.loads(content), indent=4, sort_keys=True)
                    except:
                        pass
                    raise requests.exceptions.HTTPError(content,response=e.response)
