import numpy as np
import pandas as pd
import argparse
import os
import subprocess

import gen3schemadev


def parse_arguments():
    parser = argparse.ArgumentParser("Generate Gen3 Schema YAMLs from a google sheet.")
    parser.add_argument('--google-id', type=str, action='store', required=True,
                        help="The alpha-numeric identifier for the sheet e.g. 1G5mVh0KGR4PvXEr1Q-Mg68bEkv8N_Usl92dCmj1yeAk")
    parser.add_argument('--objects-gid', type=str, action='store', required=True,
                        help="The numeric identifier for the `object_definitions` tab in the google sheet")
    parser.add_argument('--links-gid', type=str, action='store', required=True,
                        help="The numeric identifier for the `link_definitions` tab in the google sheet")
    parser.add_argument('--properties-gid', type=str, action='store', required=True,
                        help="The numeric identifier for the `property_definitions` tab in the google sheet")
    parser.add_argument('--enums-gid', type=str, action='store', required=True,
                        help="The numeric identifier for the `enum_definitions` sheet in the google sheet")
    parser.add_argument('--download', action='store_true', required=False,
                        help="Whether to download the google sheet or not")
    parser.add_argument('--output-dir', type=str, action='store', required=False,
                        help="The directory to save the downloaded Google Sheets")
    args = parser.parse_args()
    return args

def download_gsheet(google_base_link: str, output_dir: str, object_gid: str, link_gid: str, prop_gid: str, enum_gid: str):
    # Making dirs
    os.makedirs(f'{output_dir}/xlsx', exist_ok=True)
    os.makedirs(f'{output_dir}/csv', exist_ok=True)
    print('created dirs: ', output_dir)
   
    # storing gids
    gid_dict = {'object': object_gid, 'link': link_gid, 'prop': prop_gid, 'enum': enum_gid}
    
    # building command list
    cmd_list = []
    for key, gid in gid_dict.items():
        dl_link_xlsx = google_base_link + '/export?format=xlsx&gid=' + gid
        dl_link_csv = google_base_link + '/export?format=csv&gid=' + gid
        cmd = f'wget -O "{output_dir}/xlsx/{key}_def.xlsx" "{dl_link_xlsx}"'
        cmd_csv = f'wget -O "{output_dir}/csv/{key}_def.csv" "{dl_link_csv}"'
        cmd_list.append(cmd)
        cmd_list.append(cmd_csv)
    
    # running commands
    for command in cmd_list:
        result = subprocess.run(command, shell=True, check=True)
        print(result)

def main():
    pass


if __name__ == "__main__":
    args = parse_arguments()
    
    # Download Google Sheets
    if args.download:
        if args.output_dir:
            print('=== downloading google sheets ===')
            google_base_link = f"https://docs.google.com/spreadsheets/d/{args.google_id}"
            download_gsheet(google_base_link, args.output_dir, args.objects_gid, args.links_gid, args.properties_gid, args.enums_gid)
            print('=== successfully downloaded google sheets ===')
        elif args.output_dir is None:
            print('=== please provide an output directory ===')
            exit(1)

    
    url = f"https://docs.google.com/spreadsheets/d/{args.google_id}/export?format=csv&gid={args.objects_gid}"
    objects = pd.read_csv(url)

    url = f"https://docs.google.com/spreadsheets/d/{args.google_id}/export?format=csv&gid={args.links_gid}"
    links = pd.read_csv(url)
    links.replace({np.nan: None}, inplace=True)

    url = f"https://docs.google.com/spreadsheets/d/{args.google_id}/export?format=csv&gid={args.properties_gid}"
    properties = pd.read_csv(url)
    properties.replace({np.nan: None}, inplace=True)

    url = f"https://docs.google.com/spreadsheets/d/{args.google_id}/export?format=csv&gid={args.enums_gid}"
    enums = pd.read_csv(url)
    enums.replace({np.nan: None}, inplace=True)

    bundle = gen3schemadev.ConfigBundle("schema/templates")

    for idx, row in objects.iterrows():
        # parse object definition
        try:
            g3_obj = bundle.objects[f"{row.ID}.yaml"]
            g3_obj.set_object_definitions(row.ID, row.TITLE, row.CATEGORY, row.DESCRIPTION, row.NAMESPACE)
        except KeyError:
            g3_obj = gen3schemadev.Gen3Object.create_empty(f"{row.ID}.yaml", row.ID, row.TITLE, row.NAMESPACE,
                                                           row.CATEGORY, row.DESCRIPTION)
            g3_obj.set_systemProperties(row.SYSTEM_PROPERTIES.split(";"))
            bundle.addObject(g3_obj)

        # parse link definitions
        link_rows = links[links['SCHEMA'] == row.ID]
        if len(link_rows) > 0:
            links_list = []
            single_links = link_rows[link_rows.SUBGROUP.values == None]
            group_links = link_rows[link_rows.SUBGROUP.values != None]
            for each_idx, each_row in single_links.iterrows():
                this_link = gen3schemadev.Gen3Link(each_row.NAME, each_row.BACKREF, each_row.LABEL, each_row.PARENT,
                                                   gen3schemadev.Gen3Link.MULTIPLICITY(each_row.MULTIPLICITY),
                                                   each_row.REQUIRED)
                links_list.append(this_link)
            if len(group_links) > 0:
                subgroups = list(set(group_links.SUBGROUP.tolist()))
                for subgroup in subgroups:
                    this_subgroup = group_links[group_links['SUBGROUP'] == subgroup]
                    subgroup_dict = {"exclusive": group_links.EXCLUSIVE.iloc[0],
                                     "required": group_links.SG_REQUIRED.iloc[0],
                                     "subgroup": []}
                    for this_idx, each_row in this_subgroup.iterrows():
                        this_link = {"name": each_row.NAME,
                                     "backref": each_row.BACKREF,
                                     "label": each_row.LABEL,
                                     "target_type": each_row.PARENT,
                                     "multiplicity": each_row.MULTIPLICITY,
                                     "required": each_row.REQUIRED}
                        subgroup_dict['subgroup'].append(this_link)
                    links_list.append(gen3schemadev.Gen3LinkGroup.from_dict(subgroup_dict))
            g3_obj.set_links(links_list)

        # parse property definitions
        object_fields = properties.loc[properties.OBJECT == row.ID]
        for idx, field in object_fields.iterrows():
            if field.OBJECT == "deprecated":
                continue
            elif field.TYPE == "datetime":
                g3_obj.add_property(gen3schemadev.Gen3DatetimeProperty(field.VARIABLE_NAME, field.DESCRIPTION))
            elif field.TYPE == "integer":
                g3_obj.add_property(
                    gen3schemadev.Gen3Integer(field.VARIABLE_NAME, field.DESCRIPTION, field.TERM, field.TERM_SOURCE,
                                              field.TERM_ID, field.CDE_VERSION))
            elif field.TYPE == "number":
                g3_obj.add_property(
                    gen3schemadev.Gen3Number(field.VARIABLE_NAME, field.DESCRIPTION, field.TERM, field.TERM_SOURCE,
                                             field.TERM_ID, field.CDE_VERSION))
            elif field.TYPE == "boolean":
                g3_obj.add_property(
                    gen3schemadev.Gen3Boolean(field.VARIABLE_NAME, field.DESCRIPTION, field.TERM, field.TERM_SOURCE,
                                              field.TERM_ID, field.CDE_VERSION))
            elif field.TYPE == "string":
                g3_obj.add_property(
                    gen3schemadev.Gen3String(field.VARIABLE_NAME, field.DESCRIPTION, field.PATTERN, field.TERM,
                                             field.TERM_SOURCE, field.TERM_ID, field.CDE_VERSION))
            elif field.TYPE.startswith("enum"):
                prop = gen3schemadev.Gen3Enum(field.VARIABLE_NAME, field.DESCRIPTION, field.TERM, field.TERM_SOURCE,
                                              field.TERM_ID, field.CDE_VERSION)
                evals = enums.loc[enums.type_name == field.TYPE]
                for idx, evline in evals.iterrows():
                    prop.add_enum_option(evline.enum, evline.source, evline.term_id, evline.version)
                g3_obj.add_property(prop)
            elif field.TYPE == "array":
                if field.ARRAY_ITEMS_TYPE.startswith("enum"):
                    tmpenum = gen3schemadev.Gen3Enum("", "")

                    evals = enums.loc[enums.type_name == field.ARRAY_ITEMS_TYPE]
                    for idx, evline in evals.iterrows():
                        tmpenum.add_enum_option(evline.enum, source=evline.source, term_id=evline.term_id,
                                                version=evline.version)

                    prop = gen3schemadev.Gen3Array(name=field.VARIABLE_NAME, description=field.DESCRIPTION,
                                                   items_type=tmpenum, termdef=field.TERM_REF, source=field.TERM_SOURCE,
                                                   term_id=field.TERM_ID, term_version=field.TERM_VERSION)
                    g3_obj.add_property(prop)
                elif field.ARRAY_ITEMS_TYPE == "string":
                    tmpstring = gen3schemadev.Gen3String(name=field.VARIABLE_NAME, description=field.DESCRIPTION,
                                                         pattern=field.PATTERN, termdef=field.TERM_REF,
                                                         source=field.TERM_SOURCE, term_id=field.TERM_ID,
                                                         term_version=field.TERM_VERSION)
                    prop = gen3schemadev.Gen3Array(name=field.VARIABLE_NAME, description=field.DESCRIPTION,
                                                   items_type=tmpstring)
                    g3_obj.add_property(prop)
                elif field.ARRAY_ITEMS_TYPE == "number":
                    tmpnumber = gen3schemadev.Gen3Number(name=field.VARIABLE_NAME, description=field.DESCRIPTION,
                                                         termdef=field.TERM_REF, source=field.TERM_SOURCE,
                                                         term_id=field.TERM_ID, term_version=field.TERM_VERSION)
                    prop = gen3schemadev.Gen3Array(name=field.VARIABLE_NAME, description=field.DESCRIPTION,
                                                   items_type=tmpnumber)
                    g3_obj.add_property(prop)
                elif field.ARRAY_ITEMS_TYPE == "integer":
                    tmpnumber = gen3schemadev.Gen3Integer(name=field.VARIABLE_NAME, description=field.DESCRIPTION,
                                                          termdef=field.TERM_REF, source=field.TERM_SOURCE,
                                                          term_id=field.TERM_ID, term_version=field.TERM_VERSION)
                    tmpnumber.set_minimum(field.NUM_MIN)
                    tmpnumber.set_maximum(field.NUM_MAX)
                    prop = gen3schemadev.Gen3Array(name=field.VARIABLE_NAME, description=field.DESCRIPTION,
                                                   items_type=tmpnumber)
                    g3_obj.add_property(prop)
            else:
                raise KeyError(field.TYPE)

            if field.REQUIRED:
                g3_obj.add_required(field.VARIABLE_NAME)

    bundle.dump("schema_out/")

    # import networkx as nx
    # g=bundle.getDependencyGraph()
    # columns=[]
    # for object_name in list(nx.bfs_tree(g,"program")):
    #     if object_name in ["program","project"]:
    #         continue
    #     obj = bundle.getObjectByID(object_name)
    #     req = obj.get_required()
    #     columns.append((object_name,"object"))
    #     for attr in obj.get_properties():
    #         if attr not in req and attr not in ['$ref',"id","type","authz","consent_codes"]:
    #             columns.append((attr,"Attribute"))