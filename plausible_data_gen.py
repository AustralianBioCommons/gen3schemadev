import datetime
import json
import argparse
import glob
import os
import sys
from datetime import datetime
from datetime import timedelta
from random import randrange
import copy

import pandas as pd
import numpy as np
import random
import shutil


def parse_arguments():
    parser = argparse.ArgumentParser("Replace random numbers with plausible values in gen3 simulated metadata files.")
    parser.add_argument('--path', type=str, action='store', help="Path where the simulated data is")
    parser.add_argument('--values', type=str, action='store',
                        help="Path to table defining distribution of plausible values. Either this or gurl should be "
                             "specified")
    parser.add_argument('--name', type=str, action='store', required=False,
                        help="Name of the dictionary you are generating data for. If not specified will guess "
                             "from the path (optional).")
    parser.add_argument('--gurl', type=str, action='store', required=False,
                        help="The url of the google sheet with plausible values for variables. Either this or values "
                             "arg should be specified.")
    parser.add_argument('--dummy-seq-files', action='store_true', default=False, required=False,
                        help="If specified, dummy text files will be generated for data_files.")
    parser.add_argument('--dummy-lipid-files', action='store_true', default="vcf", required=False,
                        help="Specify the type seq file to generate")
    args = parser.parse_args()
    return args


def parse_json(json_path):
    sim_data = {}
    json_files = glob.glob(json_path + "/*.json")
    for file in json_files:
        object_filename = os.path.basename(os.path.normpath(file))
        object_name = object_filename.split(".json")[0]
        with open(file, "r") as f:
            metadata = json.load(f)
            sim_data[object_name] = metadata
    return sim_data


def parse_values(values_path):
    if values_path.startswith("https"):
        values_table = pd.read_csv(values_path.replace("edit#", "export?format=csv&"))
    else:
        values_table = pd.read_csv(values_path)
    return values_table


def generate_mean_number(mean, sd, schema_type):
    if schema_type == "number":
        return round(np.random.normal(mean, sd), 2)
    else:
        return int(round(np.random.normal(mean, sd), 0))


def generate_median_number(median, first_q, third_q, schema_type):
    estimated_sd = (third_q - first_q) / 1.35
    if schema_type == "number":
        return round(np.random.normal(median, estimated_sd), 2)
    else:
        return int(round)(np.random.normal(median, estimated_sd), 0)


def generate_range_number(range_min, range_max, schema_type):
    if schema_type in ["string", "datetime"]:
        return str(random.randint(range_min, range_max))
    else:
        return random.randint(range_min, range_max)


def generate_date(date_min, date_max):
    date_start = datetime.strptime(date_min, '%Y-%m-%d')
    date_end = datetime.strptime(date_max, '%Y-%m-%d')
    delta = date_end - date_start
    random_day = randrange(delta.days)
    rand_date = date_start + timedelta(days=random_day)
    return rand_date.strftime('%d/%m/%Y')


def replace_values(sim_data, table):
    for index, row in table.iterrows():
        if row['property'] == "dob":
            for item in sim_data[row['object']]:
                new_value = generate_date(row['range_start'], row['range_end'])
                item[row['property']] = new_value
                item['year_of_birth'] = int(new_value.split("/")[2])
        elif row['data_type'] == "mean":
            for item in sim_data[row['object']]:
                new_value = generate_mean_number(row['mean'], row['sd'], row['schema_type'])
                item[row['property']] = new_value
        elif row['data_type'] == "range":
            if row['schema_type'] == "date":
                for item in sim_data[row['object']]:
                    new_value = generate_date(row['range_start'], row['range_end'])
                    item[row['property']] = new_value
            else:
                for item in sim_data[row['object']]:
                    new_value = generate_range_number(int(row['range_start']), int(row['range_end']), row['schema_type'])
                    item[row['property']] = new_value
        elif row['data_type'] == "median":
            for item in sim_data[row['object']]:
                new_value = generate_median_number(row['median'], row['first_quart'], row['third_quart'], row['schema_type'])
                item[row['property']] = new_value


def write_dummy_seq_files(sim_data, dict_name):
    """
    Big ugly method to generate dummy files with appropriate template and other metadata fields. All files are copies
    of the relevant file in `file_type_templates`.
    :param sim_data:
    :param dict_name:
    :return:
    """
    cwd = os.getcwd()
    write_dir = os.path.join(cwd, "dummy_files", dict_name)
    script_path = os.path.abspath(os.path.dirname(__file__))
    with open(os.path.join(script_path, "file_type_templates", "file_stats.json")) as f:
        file_stats = json.load(f)
    if not os.path.exists(write_dir):
        os.makedirs(write_dir)
    dummy_index_file_name = None
    dummy_file_name = None
    index_files = []
    for seq_file in sim_data['sequencing_file']:
        if seq_file['data_format'] in ['cram', 'crai']:
            dummy_file_name = "dummy_cram.cram"
            file_name = f"{seq_file['file_name']}.cram"
            if seq_file['data_format'] == "crai":
                seq_file['data_format'] = "cram"
            seq_file['data_type'] = "aligned reads"
            seq_file['data_category'] = "sequencing Reads"
            seq_file['sequencing_assay'] = "WES"
            # add the index file
            copied_seq_file = copy.deepcopy(seq_file)
            copied_seq_file['data_format'] = "crai"
            dummy_index_file_name = f"{dummy_file_name}.crai"
            copied_seq_file['file_name'] = f"{seq_file['file_name']}.cram.crai"
        elif seq_file['data_format'] == "VCF":
            dummy_file_name = "dummy_vcf.vcf.gz"
            file_name = f"{seq_file['file_name']}.vcf.gz"
            seq_file['data_type'] = "variants annotation"
            seq_file['data_category'] = "single nucleotide variation"
            seq_file['sequencing_assay'] = "SNP Chip"
        elif seq_file['data_format'] in ['bam', 'bai']:
            if seq_file['data_format'] == 'bai':
                seq_file['data_format'] = "bam"
            dummy_file_name = "dummy_bam.bam"
            file_name = f"{seq_file['file_name']}.bam"
            seq_file['data_type'] = "aligned reads"
            seq_file['data_category'] = "sequencing Reads"
            seq_file['sequencing_assay'] = "WES"
            # add index file
            copied_seq_file = copy.deepcopy(seq_file)
            copied_seq_file['data_format'] = "bai"
            dummy_index_file_name = f"{dummy_file_name}.bai"
            copied_seq_file['file_name'] = f"{seq_file['file_name']}.bam.bai"
        if dummy_file_name:
            shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_file_name),
                            os.path.join(write_dir, file_name))
            seq_file['file_name'] = file_name
            seq_file['file_size'] = file_stats[dummy_file_name]['file_size']
            seq_file['md5sum'] = file_stats[dummy_file_name]['md5']
        if dummy_index_file_name:
            shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_index_file_name),
                            os.path.join(write_dir, copied_seq_file['file_name']))
            copied_seq_file['file_size'] = file_stats[dummy_index_file_name]['file_size']
            copied_seq_file['md5sum'] = file_stats[dummy_file_name]['md5']
            index_files.append(copied_seq_file)
    sim_data['sequencing_file'].append(index_files)


def write_dummy_lipid_files(sim_data, dict_name):
    cwd = os.getcwd()
    write_dir = os.path.join(cwd, "dummy_files", dict_name)
    script_path = os.path.abspath(os.path.dirname(__file__))
    dummy_lipids_file = "dummy_lipids.csv"
    with open(os.path.join(script_path, "file_type_templates", "file_stats.json")) as f:
        file_stats = json.load(f)
    if not os.path.exists(write_dir):
        os.makedirs(write_dir)
    for lipid_file in sim_data['lipidomics_file']:
        lipid_file['data_format'] = "csv"
        lipid_file['data_type'] = "MS"
        lipid_file['data_category'] = "summarised results"
        lipid_file['mass_spectromatery_type'] = "LC-MS"
        lipid_file['lipid_extraction_method'] = "shotgun"
        lipid_file['file_name'] = f"{lipid_file['file_name']}.csv"
        lipid_file['md5sum'] = file_stats[dummy_lipids_file]['md5']
        lipid_file['file_size'] = file_stats[dummy_lipids_file]['file_size']
        shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_lipids_file),
                        os.path.join(write_dir, lipid_file['file_name']))


def _write_files(sim_data, dict_name):
    cwd = os.getcwd()
    write_dir = os.path.join(cwd, "edited_jsons", dict_name)
    if not os.path.exists(write_dir):
        os.makedirs(write_dir)
    for key, item in sim_data.items():
        file_name = f"{key}.json"
        with open(os.path.join(write_dir, file_name), "w+") as f:
            json.dump(item, f, indent=4, sort_keys=True)


def main():
    args = parse_arguments()
    print(f"parsing jsons from {args.path}")
    simulated_data = parse_json(args.path)
    print("Parsing values sheet")
    if args.gurl:
        values_table = parse_values(args.gurl)
    elif args.values:
        values_table = parse_values(args.values)
    else:
        print("Either 'values' or 'gurl' should be specified. See usage.")
        sys.exit()
    replace_values(simulated_data, values_table)
    if not args.name:
        name = os.path.basename(os.path.split(args.path)[0])
    else:
        name = args.name
    if args.dummy_seq_files:
        print("writing dummy seq files...")
        write_dummy_seq_files(simulated_data, name)
        print("done.")
    if args.dummy_lipid_files:
        print("writing dummy lipid files...")
        write_dummy_lipid_files(simulated_data, name)
        print("done.")
    print("writing metadata jsons to file")
    _write_files(simulated_data, name)
    print("all done.")


if __name__ == '__main__':
    main()
