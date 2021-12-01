import pandas as pd
import numpy as np
import gen3schemadev

def main():
    pass

if __name__ == "__main__":
    properties = pd.read_excel("Harm_vars.xlsx", "property_definitions")
    properties.replace({np.nan: None}, inplace=True)

    enums = pd.read_excel("Harm_vars.xlsx", "enum_definitions")
    enums.replace({np.nan: None}, inplace=True)

    bundle = gen3schemadev.ConfigBundle("schema/cad")

    for object_name in properties.OBJECT.unique():
        g3_obj = bundle.objects["%s.yaml"%object_name]
        object_fields = properties.loc[properties.OBJECT == object_name]
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
                g3_obj.add_property(gen3schemadev.Gen3String(field.VARIABLE_NAME,field.DESCRIPTION,field.TERM,field.TERM_SOURCE,field.TERM_ID,field.CDE_VERSION))
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


    for object in bundle.objects:
        bundle.objects[object].namespace = "https://gen3.biocommons.org.au"

    bundle.dump("schema_out/")
