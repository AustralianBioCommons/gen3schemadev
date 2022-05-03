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
import random
import string

import pandas as pd
import numpy as np
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
    parser.add_argument('--generate-files', action='store_true', default=False, required=False,
                        help="If specified, dummy text files will be generated for data_files.")
    parser.add_argument('--file-types', action='store', nargs="*",
                        default=["aligned_reads", "variant", "metabolomics", "proteomics", "lipidomics", "serum_marker"],
                        help="Space separated list of file types, must be one or more of aligned_reads, variant, "
                             "metabolomics, proteomics, lipidomics, serum_marker")
    parser.add_argument('--num-files', action="store", type=int,
                        help="Specify a limit on the number of dummy files to generate per file type object.")
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


def generate_random_string(length):
    result = ''.join((random.choice(string.ascii_lowercase) for x in range(length)))  # run loop until the define length
    return result


def generate_mean_number(mean, sd, schema_type):
    if schema_type == "number":
        return round(np.random.normal(mean, sd), 1)
    else:
        return int(round(np.random.normal(mean, sd), 0))


def generate_median_number(median, first_q, third_q, schema_type):
    estimated_sd = (third_q - first_q) / 1.35
    if schema_type == "number":
        return round(np.random.normal(median, estimated_sd), 1)
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


def calculate_age(birth_year, birth_month, baseline_year):
    baseline_date = generate_date(f"{baseline_year}-01-01", f"{baseline_year}-12-31")
    timepoint = datetime.strptime(baseline_date, '%d/%m/%Y')
    if birth_month in [11, 4, 6, 9]:
        max_day = 30
    elif birth_month == 2:
        max_day = 28
    else:
        max_day = 31
    birth_day = randrange(1, max_day)
    str_birthdate = f"{birth_year}-{birth_month}-{birth_day}"
    birthdate = datetime.strptime(str_birthdate, '%Y-%m-%d')
    age = timepoint - birthdate
    age_years = round(age.days * 0.002738, 1)
    return age_years


def get_molecules(num, enum_name):
    enum_sheet = pd.read_csv("https://docs.google.com/spreadsheets/d/1AX9HLzIV6wtkVylLkwOr3kdKDaZf4ukeYACTJ7lYngk/edit#gid=1170119639".replace("edit#", "export?format=csv&"),
                             keep_default_na=False, na_values=['_'])
    molecule_list = list(enum_sheet.loc[enum_sheet['type_name'] == enum_name]['enum'])
    random_molecules = sorted(random.sample(molecule_list, num))
    return random_molecules


def replace_values(sim_data, table):
    for index, row in table.iterrows():
        if row['property'] == "baseline_age":
            for item in sim_data[row['object']]:
                calculated_age = calculate_age(item['year_birth'], item['month_birth'], item['baseline_year'])
                item['baseline_age'] = calculated_age
        if row['property'] == "cigarettes_per_day":
            for item in sim_data[row['object']]:
                if item['smoking_status'] in ['never', 'not collected', None]:
                    item['cigarettes_per_day'] = None
                else:
                    item['cigarettes_per_day'] = generate_mean_number(row['mean'], row['sd'], row['schema_type'])
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
                new_value = generate_median_number(row['median'], row['first_quart'], row['third_quart'],
                                                   row['schema_type'])
                item[row['property']] = new_value


def write_dummy_reads_files(sim_data, dict_name, copy_files, num_files):
    """
    Big ugly method to generate dummy files with appropriate template and other metadata fields. All files are copies
    of the relevant file in `file_type_templates`.
    :param sim_data:
    :param dict_name:
    :return:
    """
    if copy_files:
        cwd = os.getcwd()
        write_dir = os.path.join(cwd, "dummy_files", dict_name)
        script_path = os.path.abspath(os.path.dirname(__file__))
        if not os.path.exists(write_dir):
            os.makedirs(write_dir)
    reads_cmc = f"core_metadata_collection_{sim_data['project']['code']}_reads_{generate_random_string(10)}"
    cmc = {
        "contributor": generate_random_string(10),
        "coverage": generate_random_string(10),
        "creator": generate_random_string(10),
        "projects": {
            "code": sim_data['project']['code']
        },
        "source": generate_random_string(10),
        "submitter_id": reads_cmc,
        "title": generate_random_string(10),
        "type": "core_metadata_collection"
    }
    sim_data['core_metadata_collection'].append(cmc)
    i = 0
    for reads_file, index_file, sample in zip(sim_data['aligned_reads_file'], sim_data['aligned_reads_index_file'], sim_data['sample']):
        dummy_index_file_name = None
        dummy_file_name = None
        if 'samples' not in reads_file.keys():
            reads_file['samples'] = {'submitter_id': sample['submitter_id']}
        reads_file['core_metadata_collections'] = {'submitter_id': reads_cmc}
        if copy_files:
            if reads_file['data_format'] == 'cram':
                dummy_file_name = "dummy_cram.cram"
                reads_file['file_name'] = f"{reads_file['file_name']}.cram"
                reads_file['data_type'] = "aligned reads"
                reads_file['data_category'] = "sequencing reads"
                reads_file['reference_genome_build'] = "GRCh37"
                index_file['data_format'] = "crai"
                index_file['data_type'] = "aligned reads"
                index_file['data_category'] = "sequencing reads"
                dummy_index_file_name = f"{dummy_file_name}.crai"
                index_file['file_name'] = f"{reads_file['file_name']}.crai"
                index_file['aligned_reads_files'] = {"submitter_id": reads_file['submitter_id']}

            elif reads_file['data_format'] == 'bam':
                dummy_file_name = "dummy_bam.bam"
                reads_file['file_name'] = f"{reads_file['file_name']}.bam"
                reads_file['data_type'] = "aligned reads"
                reads_file['data_category'] = "sequencing reads"
                reads_file['reference_genome_build'] = "GRCh37"
                index_file['data_format'] = "bai"
                index_file['data_category'] = "sequencing reads"
                index_file['data_type'] = "aligned reads"
                dummy_index_file_name = "dummy_bam.bam.bai"
                index_file['file_name'] = f"{reads_file['file_name']}.bai"

            if dummy_file_name and i < num_files:
                shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_file_name),
                                os.path.join(write_dir, reads_file["file_name"]))
                i += 1
            if dummy_index_file_name and i < num_files:
                shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_index_file_name),
                                os.path.join(write_dir, index_file['file_name']))
                index_file['core_metadata_collections'] = {'submitter_id': reads_cmc}
                i += 1
    all_aligned_reads = [{"submitter_id": x['submitter_id']} for x in sim_data['aligned_reads_file']]
    genomics_assay = {
        "aligned_reads_files": all_aligned_reads,
        "assay_description": "This is an example description. Ideally you would detail the methods and any useful information that someone would want to know when analysing the data files that are linked to this assay.",
        "assay_instrument": "5dbe5b48b8",
        "assay_type": "WES",
        "submitter_id": "genomics_assay_4ed12374e5",
        "type": "genomics_assay"
    }
    sim_data['genomics_assay'].append(genomics_assay)


def write_dummy_variant_files(sim_data, dict_name, copy_files, num_files):
    if copy_files:
        cwd = os.getcwd()
        write_dir = os.path.join(cwd, "dummy_files", dict_name)
        script_path = os.path.abspath(os.path.dirname(__file__))
        if not os.path.exists(write_dir):
            os.makedirs(write_dir)
    i = 0
    variants_cmc = f"core_metadata_collection_{sim_data['project']['code']}_variants_{generate_random_string(10)}"
    cmc = {
        "contributor": generate_random_string(10),
        "coverage": generate_random_string(10),
        "creator": generate_random_string(10),
        "projects": {
            "code": sim_data['project']['code']
        },
        "source": generate_random_string(10),
        "submitter_id": variants_cmc,
        "title": generate_random_string(10),
        "type": "core_metadata_collection"
    }
    sim_data['core_metadata_collection'].append(cmc)
    for variant_file, sample in zip(sim_data['variant_file'], sim_data['sample']):
        if 'samples' not in variant_file.keys():
            variant_file['samples'] = {'submitter_id': sample['submitter_id']}
        dummy_file_name = "dummy_vcf.vcf.gz"
        variant_file['data_format'] = "VCF"
        variant_file['file_name'] = f"{variant_file['file_name']}.vcf.gz"
        variant_file['data_type'] = "variants annotation"
        variant_file['data_category'] = "single nucleotide variation"
        variant_file['reference_genome_build'] = "GRCh37"
        variant_file['core_metadata_collections'] = {'submitter_id': variants_cmc}
        if 'aligned_reads_files' in variant_file.keys():
            del variant_file['aligned_reads_files']

        if copy_files and i < num_files:
            shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_file_name),
                            os.path.join(write_dir, variant_file['file_name']))
        i += 1
    all_variants = [{"submitter_id": x['submitter_id']} for x in sim_data['variant_file']]
    genomics_assay = {
        "variant_files": all_variants,
        "assay_description": "This is an example description. Ideally you would detail the methods and any useful information that someone would want to know when analysing the data files that are linked to this assay.",
        "assay_instrument": "Infinium CytoSNP-850K BeadChip",
        "assay_type": "SNP Chip",
        "submitter_id": f"genomics_assay_{generate_random_string(10)}",
        "type": "genomics_assay"
    }
    sim_data['genomics_assay'].append(genomics_assay)


def write_dummy_metabolomics_files(sim_data, dict_name, copy_files, num_files):
    if copy_files:
        cwd = os.getcwd()
        write_dir = os.path.join(cwd, "dummy_files", dict_name)
        script_path = os.path.abspath(os.path.dirname(__file__))
        if not os.path.exists(write_dir):
            os.makedirs(write_dir)
    i = 0
    metab_cmc = f"core_metadata_collection_{sim_data['project']['code']}_metab_{generate_random_string(10)}"
    cmc = {
        "contributor": generate_random_string(10),
        "coverage": generate_random_string(10),
        "creator": generate_random_string(10),
        "projects": {
            "code": sim_data['project']['code']
        },
        "source": generate_random_string(10),
        "submitter_id": metab_cmc,
        "title": generate_random_string(10),
        "type": "core_metadata_collection"
    }
    sim_data['core_metadata_collection'].append(cmc)
    for metab_file, sample in zip(sim_data['metabolomics_file'], sim_data['sample']):
        if 'samples' not in metab_file.keys():
            metab_file['samples'] = {'submitter_id': sample['submitter_id']}
        dummy_file_name = "dummy_metab.wiff"
        metab_file['data_format'] == "WIFF"
        metab_file['file_name'] = f"{metab_file['file_name']}.wiff"
        metab_file['data_type'] = "MS"
        metab_file['data_category'] = "mass spec analysed"
        metab_file['core_metadata_collections'] = {'submitter_id': metab_cmc}

        if copy_files and i < num_files:
            shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_file_name),
                            os.path.join(write_dir, metab_file['file_name']))
        i += 1
    all_metabolomics_files = [{"submitter_id": x['submitter_id']} for x in sim_data['metabolomics_file']]
    metabolomics_assay = {
        "metabolomics_files": all_metabolomics_files,
        "assay_description": "This is an example description. Ideally you would detail the methods and any useful information that someone would want to know when analysing the data files that are linked to this assay.",
        "metabolite_names": get_molecules(30, "enum_metab"),
        "submitter_id": f"metabolomics_assay_{generate_random_string(10)}",
        "type": "metabolomics_assay"
    }
    sim_data['metabolomics_assay'] = [metabolomics_assay]


def write_dummy_proteomics_files(sim_data, dict_name, copy_files, num_files):
    if copy_files:
        cwd = os.getcwd()
        write_dir = os.path.join(cwd, "dummy_files", dict_name)
        script_path = os.path.abspath(os.path.dirname(__file__))
        if not os.path.exists(write_dir):
            os.makedirs(write_dir)
    i = 0
    prot_cmc = f"core_metadata_collection_{sim_data['project']['code']}_prot_{generate_random_string(10)}"
    cmc = {
        "contributor": generate_random_string(10),
        "coverage": generate_random_string(10),
        "creator": generate_random_string(10),
        "projects": {
            "code": sim_data['project']['code']
        },
        "source": generate_random_string(10),
        "submitter_id": prot_cmc,
        "title": generate_random_string(10),
        "type": "core_metadata_collection"
    }
    sim_data['core_metadata_collection'].append(cmc)
    for prot_file, sample in zip(sim_data['proteomics_file'], sim_data['sample']):
        if 'samples' not in prot_file.keys():
            prot_file['samples'] = {'submitter_id': sample['submitter_id']}
        dummy_file_name = "dummy_prot.mgf"
        prot_file['data_format'] == "MGF"
        prot_file['file_name'] = f"{prot_file['file_name']}.mgf"
        prot_file['data_type'] = "MS"
        prot_file['data_category'] = "mass spec analysed"
        prot_file['core_metadata_collections'] = {'submitter_id': prot_cmc}

        if copy_files and i < num_files:
            shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_file_name),
                            os.path.join(write_dir, prot_file['file_name']))
        i += 1
    all_proteomics_files = [{"submitter_id": x['submitter_id']} for x in sim_data['proteomics_file']]
    proteomics_assay = {
        "proteomics_files": all_proteomics_files,
        "assay_description": "This is an example description. Ideally you would detail the methods and any useful information that someone would want to know when analysing the data files that are linked to this assay.",
        "protein_names": get_molecules(100, "enum_proteins"),
        "submitter_id": f"proteomics_assay_{generate_random_string(10)}",
        "type": "proteomics_assay"
    }
    sim_data['proteomics_assay'] = [proteomics_assay]


def write_dummy_serum_marker_files(sim_data, dict_name, copy_files, num_files):
    if copy_files:
        cwd = os.getcwd()
        write_dir = os.path.join(cwd, "dummy_files", dict_name)
        script_path = os.path.abspath(os.path.dirname(__file__))
        if not os.path.exists(write_dir):
            os.makedirs(write_dir)
    i = 0
    serum_cmc = f"core_metadata_collection_{sim_data['project']['code']}_serum_{generate_random_string(10)}"
    cmc = {
        "contributor": generate_random_string(10),
        "coverage": generate_random_string(10),
        "creator": generate_random_string(10),
        "projects": {
            "code": sim_data['project']['code']
        },
        "source": generate_random_string(10),
        "submitter_id": serum_cmc,
        "title": generate_random_string(10),
        "type": "core_metadata_collection"
    }
    sim_data['core_metadata_collection'].append(cmc)
    for serum_file, sample in zip(sim_data['serum_marker_file'], sim_data['sample']):
        if 'samples' not in serum_file.keys():
            serum_file['samples'] = {'submitter_id': sample['submitter_id']}
        dummy_file_name = "dummy_serum.csv"
        serum_file['data_format'] == "WIFF"
        serum_file['file_name'] = f"{serum_file['file_name']}.wiff"
        serum_file['data_type'] = "MS"
        serum_file['data_category'] = "mass spec analysed"
        serum_file['core_metadata_collections'] = {'submitter_id': serum_cmc}

        if copy_files and i < num_files:
            shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_file_name),
                            os.path.join(write_dir, serum_file['file_name']))
        i += 1
    all_serum_files = [{"submitter_id": x['submitter_id']} for x in sim_data['serum_marker_file']]
    serum_marker_assay = {
        "serum_marker_files": all_serum_files,
        "assay_description": "This is an example description. Ideally you would detail the methods and any useful information that someone would want to know when analysing the data files that are linked to this assay.",
        "serum_markers": get_molecules(8, "enum_serum"),
        "submitter_id": f"serum_marker_assay_{generate_random_string(10)}",
        "type": "serum_marker_assay"
    }
    sim_data['serum_marker_assay'] = [serum_marker_assay]


def write_dummy_lipid_files(sim_data, dict_name, copy_files, num_files):
    cwd = os.getcwd()
    if copy_files:
        write_dir = os.path.join(cwd, "dummy_files", dict_name)
        script_path = os.path.abspath(os.path.dirname(__file__))
        dummy_lipids_file = "dummy_lipids.csv"
        if not os.path.exists(write_dir):
            os.makedirs(write_dir)
    lipids_cmc = f"core_metadata_collection_{sim_data['project']['code']}_lipids_{generate_random_string(10)}"
    cmc = {
        "contributor": generate_random_string(10),
        "coverage": generate_random_string(10),
        "creator": generate_random_string(10),
        "projects": {
            "code": sim_data['project']['code']
        },
        "source": generate_random_string(10),
        "submitter_id": lipids_cmc,
        "title": generate_random_string(10),
        "type": "core_metadata_collection"
    }
    sim_data['core_metadata_collection'].append(cmc)
    i = 0
    for lipid_file, sample in zip(sim_data['lipidomics_file'], sim_data['sample']):
        if 'samples' not in lipid_file.keys():
            lipid_file['samples'] = {'submitter_id': sample['submitter_id']}
        lipid_file['core_metadata_collections'] = {'submitter_id': lipids_cmc}
        lipid_file['data_format'] = "csv"
        lipid_file['data_type'] = "MS"
        lipid_file['data_category'] = "summarised results"
        lipid_file['file_name'] = f"{lipid_file['file_name']}.csv"
        if copy_files and i < num_files:
            shutil.copyfile(os.path.join(script_path, "file_type_templates", dummy_lipids_file),
                            os.path.join(write_dir, lipid_file['file_name']))
        i += 1
    all_lipidomics_files = [{"submitter_id": x['submitter_id']} for x in sim_data['lipidomics_file']]
    lipidomics_assay = {
        "lipidomics_files": all_lipidomics_files,
        "assay_description": "This is an example description. Ideally you would detail the methods and any useful information that someone would want to know when analysing the data files that are linked to this assay.",
        "lipid_names": get_molecules(250, "enum_lipids"),
        "submitter_id": f"lipidomics_assay_{generate_random_string(10)}",
        "type": "lipidomics_assay"
    }
    sim_data['lipidomics_assay'] = [lipidomics_assay]
    # link all files to one lipidomics assay


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
    if args.generate_files:
        del simulated_data['core_metadata_collection']
        simulated_data['core_metadata_collection'] = []
        if "aligned_reads" in args.file_types:
            print("generating aligned reads files")
            simulated_data['genomics_assay'] = []
            write_dummy_reads_files(simulated_data, name, args.generate_files,
                                    args.num_files if args.num_files else len(simulated_data['aligned_reads_file']))
        if "variant" in args.file_types:
            print("generating variant files")
            if len(simulated_data['genomics_assay']) > 1:
                simulated_data['genomics_assay'] = []
            write_dummy_variant_files(simulated_data, name, args.generate_files,
                                      args.num_files if args.num_files else len(simulated_data['aligned_reads_file']))
        if "lipidomics" in args.file_types:
            print("generating lipid files")
            write_dummy_lipid_files(simulated_data, name, args.generate_files,
                                    args.num_files if args.num_files else len(simulated_data["lipidomics_file"]))
            print("done with lipid files.")
        if "metabolomics" in args.file_types:
            print("generating metabolomics files")
            write_dummy_metabolomics_files(simulated_data, name, args.generate_files,
                                           args.num_files if args.num_files else len(simulated_data["metabolomics_file"]))
        if "proteomics" in args.file_types:
            print("generating proteomics files")
            write_dummy_proteomics_files(simulated_data, name, args.generate_files,
                                         args.num_files if args.num_files else len(simulated_data["proteomics_file"]))
        if "serum_marker" in args.file_types:
            print("serum marker files")
            write_dummy_serum_marker_files(simulated_data, name, args.generate_files,
                                           args.num_files if args.num_files else len(simulated_data["serum_marker_file"]))
    full_file_set = set(["aligned_reads", "variant", "metabolomics", "proteomics", "lipidomics", "serum_marker"])
    ungenerated_files = full_file_set.difference(set(args.file_types))
    for file_type in ungenerated_files:
        del simulated_data[f"{file_type}_file"]
        if f"{file_type}_assay" in simulated_data.keys():
            del simulated_data[f"{file_type}_assay"]
    if "aligned_reads" in ungenerated_files and "variant" in ungenerated_files:
        del simulated_data['genomics_assay']

    print("writing metadata jsons to file")
    del simulated_data['acknowledgement']
    del simulated_data['publication']
    _write_files(simulated_data, name)
    print("all done.")


if __name__ == '__main__':
    main()

