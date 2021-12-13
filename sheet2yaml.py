import pandas as pd
import numpy as np
import gen3schemadev
from collections import OrderedDict
import networkx as nx

def main():
    pass


if __name__ == "__main__":
    sheet_id = "1AX9HLzIV6wtkVylLkwOr3kdKDaZf4ukeYACTJ7lYngk"

    objects_gid = "1815863480"
    url = "https://docs.google.com/spreadsheets/d/{}/export?format=csv&gid={}".format(sheet_id, objects_gid)
    objects = pd.read_csv(url)

    links_gid = "1073266181"
    url = "https://docs.google.com/spreadsheets/d/{}/export?format=csv&gid={}".format(sheet_id, links_gid)
    links = pd.read_csv(url)
    links.replace({np.nan: None}, inplace=True)

    properties_gid = "804936807"
    url = "https://docs.google.com/spreadsheets/d/{}/export?format=csv&gid={}".format(sheet_id, properties_gid)
    properties = pd.read_csv(url)
    properties.replace({np.nan: None}, inplace=True)

    enums_gid = "1170119639"
    url = "https://docs.google.com/spreadsheets/d/{}/export?format=csv&gid={}".format(sheet_id, enums_gid)
    enums = pd.read_csv(url)
    enums.replace({np.nan: None}, inplace=True)

    bundle = gen3schemadev.ConfigBundle("schema/templates")

    for idx, row in objects.iterrows():
        # parse object definition
        try:
            g3_obj = bundle.objects["%s.yaml"%row.ID]
            g3_obj.set_object_definitions(row.ID, row.TITLE, row.CATEGORY, row.DESCRIPTION, row.NAMESPACE)
        except KeyError:
            this_data = OrderedDict([('$schema', "http://json-schema.org/draft-04/schema#"),
                                     ('id', row.ID),
                                     ('title', row.TITLE),
                                     ('type', 'object'),
                                     ('namespace', row.NAMESPACE),
                                     ('category', row.CATEGORY),
                                     ('program', '*'),
                                     ('project', '*'),
                                     ('description', row.DESCRIPTION),
                                     ('additionalProperties', False),
                                     ('submittable', True),
                                     ('validators', None),
                                     ('systemProperties', row.SYSTEM_PROPERTIES.split(";")),
                                     ('links', []),
                                     ('required', ['type', 'submitter_id']),
                                     ('uniqueKeys', [
                                         ['id'],
                                         ['project_id', 'submitter_id']]),
                                     ('properties', {})
                                     ])
            bundle.objects["%s.yaml"%row.ID] = gen3schemadev.Gen3Object("%s.yaml"%row.ID, this_data)
            g3_obj = bundle.objects["%s.yaml"%row.ID]
            if g3_obj.data['category'] == "data_file":
                g3_obj.data['properties']['$ref'] = "_definitions.yaml#/data_file_properties"
                g3_obj.add_required('object_id')
            else:
                g3_obj.data['properties']['$ref'] = "_definitions.yaml#/ubiquitous_properties"

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
                    subgroup_dict = {"exclusive": group_links.EXCLUSIVE[0],
                                     "required": group_links.SG_REQUIRED[0],
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
        for idx,field in object_fields.iterrows():
            if field.TYPE == "datetime":
                g3_obj.add_property(gen3schemadev.Gen3DatetimeProperty(field.VARIABLE_NAME,field.DESCRIPTION))
            elif field.TYPE == "integer":
                g3_obj.add_property(gen3schemadev.Gen3Integer(field.VARIABLE_NAME,field.DESCRIPTION,field.TERM,field.TERM_SOURCE,field.TERM_ID,field.CDE_VERSION))
            elif field.TYPE == "number":
                g3_obj.add_property(gen3schemadev.Gen3Number(field.VARIABLE_NAME,field.DESCRIPTION,field.TERM,field.TERM_SOURCE,field.TERM_ID,field.CDE_VERSION))
            elif field.TYPE == "boolean":
                g3_obj.add_property(gen3schemadev.Gen3Boolean(field.VARIABLE_NAME,field.DESCRIPTION,field.TERM,field.TERM_SOURCE,field.TERM_ID,field.CDE_VERSION))
            elif field.TYPE == "string":
                g3_obj.add_property(gen3schemadev.Gen3String(field.VARIABLE_NAME,field.DESCRIPTION,field.PATTERN,field.TERM,field.TERM_SOURCE,field.TERM_ID,field.CDE_VERSION))
            elif field.TYPE.startswith("enum"):
                prop = gen3schemadev.Gen3Enum(field.VARIABLE_NAME, field.DESCRIPTION, field.TERM, field.TERM_SOURCE, field.TERM_ID, field.CDE_VERSION)
                evals = enums.loc[enums.type_name == field.TYPE]
                for idx,evline in evals.iterrows():

                    prop.add_enum_option(evline.enum,evline.source,evline.term_id,evline.version)
                g3_obj.add_property(prop)
            else:
                raise KeyError(field.TYPE)

            if field.REQUIRED:
                g3_obj.add_required(field.VARIABLE_NAME)

    bundle.dump("schema_out/")
