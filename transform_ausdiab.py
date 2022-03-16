import pandas as pd
import numpy as np
import shutil
from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission
from gen3.index import Gen3Index
import requests
import os
import json
import sys
import subprocess
import argparse
import datetime
from datetime import datetime
from datetime import timedelta
from random import randrange
from time import sleep
import glob
import math
import http


def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--sim-data", required=True, type=str,
                        help="path to simulated data matrix")
    parser.add_argument("--mapping-file", required=True, type=str, default="configs/mapping.json",
                        help="path to a mapping json file that maps columns to fields in gen3 data dictionary")
    parser.add_argument("--id-prefix", required=False, type=str,
                        help="If specified, will add this prefix to all identifiers")
    parser.add_argument("--profile", required=True,
                        help="The name of a configured gen3-client profile with access to upload data and metadata.")
    return parser.parse_args()


def read_mapping_file(file_path):
    with open(file_path, "r") as f:
        mapping = json.load(f)
    return mapping


def read_sim_data(file_path):
    sim_data_frame = pd.read_csv(file_path)
    return sim_data_frame


def _split_file(df, prefix=""):
    num_subjects = len(df.index)
    num_digits = len(str(num_subjects))
    if not os.path.exists("split_file"):
        os.makedirs("split_file")
    groups = df.groupby(np.arange(len(df.index)))
    for frameno, frame in groups:
        identifier = f"{prefix}{str(frameno + 1).zfill(num_digits)}"
        if os.path.isfile(f"split_file/{identifier}.csv"):
            continue
        else:
            frame.to_csv(f"split_file/{identifier}.csv")


def _upload_data_files(profile):
    upload_path = "split_file"
    bash_command = f"gen3-client upload --upload-path={upload_path} --profile={profile} " \
                   f"--numparallel=2"
    process = subprocess.Popen(bash_command.split(), stdout=subprocess.PIPE)
    output, error = process.communicate()
    print("all files uploaded.")


def _upload_metadata_files(jsons_dict):
    endpoint = "https://data.acdc.ozheart.org"
    script_path = os.path.abspath(os.path.dirname(__file__))
    auth_path = os.path.join(script_path, "_local", "credentials.json")
    auth = Gen3Auth(endpoint=endpoint, refresh_file=auth_path)
    sub = Gen3Submission(endpoint=endpoint, auth_provider=auth)
    upload_order = list(jsons_dict.keys())
    for node in upload_order:
        # if node in ["subject", "demographic", "laboratory_result", "exposure", "sample", "core_metadata_collection",
        #             "medical_history"]:
        #     continue
        print(f"Uploading {node} metadata.")
        # find batch_size
        full_list_len = len(jsons_dict[node])
        max_size = 500000
        batch_size = len(jsons_dict[node])
        list_size = len(json.dumps(jsons_dict[node]))
        while list_size > max_size:
            batch_size = int(batch_size/2)
            list_size = len(json.dumps(jsons_dict[node][:batch_size]))
        print(f"splitting into batches of {batch_size}")
        min_index = 0
        max_index = min_index + batch_size
        batch = 1
        batches = math.ceil(full_list_len/batch_size)
        while min_index < max_index <= full_list_len:
            print(f"Submitting batch {batch} of {batches}...")
            try:
                print(len(json.dumps(jsons_dict[node][min_index:max_index])))
                sub.submit_record("program1", "AusDiabSim", jsons_dict[node][min_index:max_index])
            except requests.exceptions.HTTPError as e:
                content = e.response.content
                try:
                    content = json.dumps(json.loads(content), indent=4, sort_keys=True)
                except:
                    pass
                raise requests.exceptions.HTTPError(content, response=e.response)
            except ConnectionError as e:
                print(f"couldn't upload batch {batch}")
                print(e)
            except http.client.RemoteDisconnected as e:
                print(f"couldn't upload batch {batch}")
                print(e)
            min_index += batch_size
            max_index += batch_size
            max_index = min(max_index, full_list_len)
            batch += 1


def generate_date(date_min, date_max):
    date_start = datetime.strptime(date_min, '%Y-%m-%d')
    date_end = datetime.strptime(date_max, '%Y-%m-%d')
    delta = date_end - date_start
    random_day = randrange(delta.days)
    rand_date = date_start + timedelta(days=random_day)
    return rand_date.strftime('%d/%m/%Y')


def generate_mean_number(mean, sd, schema_type):
    if schema_type == "number":
        return round(np.random.normal(mean, sd), 2)
    else:
        return int(round(np.random.normal(mean, sd), 0))


def create_jsons(data, mapping, prefix=""):
    endpoint = "https://data.acdc.ozheart.org"
    script_path = os.path.abspath(os.path.dirname(__file__))
    auth_path = os.path.join(script_path, "_local", "credentials.json")
    auth = Gen3Auth(endpoint=endpoint, refresh_file=auth_path)
    gen3_index = Gen3Index(endpoint="https://data.acdc.ozheart.org", auth_provider=auth)
    subjects = []
    demographics = []
    laboratory_results = []
    exposures = []
    medical_histories = []
    samples = []
    lipidomics_files = []
    core_metadata_collections = []
    num_subjects = len(data.index)
    num_digits = len(str(num_subjects))
    for index, row in data.iterrows():
        identifier = f"{prefix}{str(index+1).zfill(num_digits)}"
        print(f"Processing subject {identifier} of {num_subjects} subjects.")
        subject = {
            "projects": {
                "code": "AusDiabSim"
            },
            "submitter_id": f"subject_{identifier}",
            "type": "subject"
        }
        subjects.append(subject)
        demographic = {
            "dob": generate_date("1955-01-01", "1984-01-01"),
            "sex": f"{mapping['drsex_00_n']['enum_map'][str(int(row['drsex_00_n']))]}",
            "baseline_age": round(row['drage_00'], 2),
            "bmi_baseline": round(row['bmi_00'], 2),
            "submitter_id": f"demographic_{identifier}",
            "subjects": {
                "submitter_id": f"subject_{identifier}"
            },
            "type": "demographic"
        }
        demographics.append(demographic)
        lab_result = {
            "total_cholesterol": round(row["chol_00"], 2),
            "hdl": round(row["hdl_00"], 2),
            "ldl": generate_mean_number(3.984, 1.06, "number"),
            "collection_stage": "baseline",
            "triglycerides": round(row["trig_00"], 2),
            "glucose_fasting": round(row["fbg_00"], 2),
            "hba1c_ngsp": round(row['hba1c_00'], 2),
            "submitter_id": f"laboratory_result_{identifier}",
            "subjects": {
                "submitter_id": f"subject_{identifier}"
            },
            "type": "lab_result"
        }
        laboratory_results.append(lab_result)
        exposure = {
            "smoking_status": f"{mapping['smokstat_00_n']['enum_map'][str(int(row['smokstat_00_n']))]}",
            "subjects": {
                "submitter_id": f"subject_{identifier}"
            },
            "submitter_id": f"exposure_{identifier}",
            "type": "exposure"
        }
        exposures.append(exposure)
        medical_history = {
            "diabetes": f"{mapping['diabstat_00_n']['enum_map'][str(int(row['diabstat_00_n']))]}",
            "subjects": {
                "submitter_id": f"subject_{identifier}"
            },
            "submitter_id": f"medical_history_{identifier}",
            "type": "medical_history"
        }
        medical_histories.append(medical_history)
        sample = {
            "sample_source": "UBERON:0000178",
            "sample_type": "whole blood",
            "storage_location": "Baker IDI",
            "subjects": {
                "submitter_id": f"subject_{identifier}"
            },
            "submitter_id": f"sample_{identifier}",
            "type": "sample"
        }
        samples.append(sample)
        for x in range(0, 10):
            # Get indexed file info
            try:
                str_error = None
                indexed_file = gen3_index.get_with_params({"file_name": f"{identifier}.csv"})
                lipidomics_file = {
                    "data_format": "csv",
                    "data_type": "MS",
                    "data_category": "mass spec analysed",
                    "samples": {
                        "submitter_id": f"sample_{identifier}"
                    },
                    "core_metadata_collections": {
                        "submitter_id": f"core_metadata_collection_{identifier}"
                    },
                    "object_id": indexed_file['did'],
                    "md5sum": indexed_file['hashes']['md5'],
                    "file_size": indexed_file['size'],
                    "submitter_id": f"lipidomics_file_{identifier}",
                    "type": "lipidomics_file"
                }
            except KeyError as str_error:
                print(str_error)
                pass
            except requests.exceptions.HTTPError as str_error:
                print(str_error)
                pass
            except TypeError as str_error:
                print(str_error)
                pass
            if str_error:
                print("file not indexed yet, waiting 2 mins and trying again...")
                sleep(120)
            else:
                break
        lipidomics_files.append(lipidomics_file)
        core_metadata_collection = {
            "projects": {
                "code": "AusDiabSim"
            },
            "submitter_id": f"core_metadata_collection_{identifier}",
            "type": "core_metadata_collection"
        }
        core_metadata_collections.append(core_metadata_collection)
    return {"subject": subjects,
            "demographic": demographics,
            "laboratory_result": laboratory_results,
            "exposure": exposures,
            "medical_history": medical_histories,
            "sample": samples,
            "core_metadata_collection": core_metadata_collections,
            "lipidomics_file": lipidomics_files
            }


def main():
    args = parse_arguments()
    map_config = read_mapping_file(args.mapping_file)
    sim_data = read_sim_data(args.sim_data)
    print("Splitting matrix per subject ...")
    _split_file(sim_data, args.id_prefix)
    print("Uploading split data files ...")
    _upload_data_files(args.profile)
    print("Creating metadata jsons ...")
    if os.path.exists("transformed_jsons") and len(glob.glob("transformed_jsons/*.json")) > 0:
        with open("transformed_jsons/subject.json", "r") as f:
            subjects = json.load(f)
        with open("transformed_jsons/demographic.json", "r") as f:
            demographics = json.load(f)
        with open("transformed_jsons/laboratory_result.json", "r") as f:
            laboratory_results = json.load(f)
        with open("transformed_jsons/exposure.json", "r") as f:
            exposures = json.load(f)
        with open("transformed_jsons/medical_history.json", "r") as f:
            medical_histories = json.load(f)
        with open("transformed_jsons/sample.json", "r") as f:
            samples = json.load(f)
        with open("transformed_jsons/core_metadata_collection.json", "r") as f:
            core_metadata_collections = json.load(f)
        with open("transformed_jsons/lipidomics_file.json", "r") as f:
            lipidomics_files = json.load(f)
        jsons = {"subject": subjects,
                 "demographic": demographics,
                 "laboratory_result": laboratory_results,
                 "exposure": exposures,
                 "medical_history": medical_histories,
                 "sample": samples,
                 "core_metadata_collection": core_metadata_collections,
                 "lipidomics_file": lipidomics_files
                 }
    else:
        jsons = create_jsons(sim_data, map_config, args.id_prefix)
        if not os.path.exists("transformed_jsons"):
            os.makedirs("transformed_jsons")
        for k, v in jsons.items():
            with open(f"transformed_jsons/{k}.json", "w+") as f:
                json.dump(v, f, indent=4)
    print("Uploading metadata files...")
    _upload_metadata_files(jsons)
    print("All done.")


if __name__ == "__main__":
    main()

