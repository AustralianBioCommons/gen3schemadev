
from gen3.auth import Gen3Auth
from gen3.submission import Gen3Submission
from gen3.metadata import Gen3Metadata
from gen3.query import Gen3Query
import time

start_time = time.time()

endpoint = "https://data.acdc.ozheart.org"
auth = Gen3Auth(endpoint=endpoint, refresh_file="_local/credentials.json")
metadata = Gen3Metadata(auth)
sub = Gen3Submission(auth)
query_obj = Gen3Query(auth)

flat_query = '{ project(accessibility: accessible) { name, full_name, code, data_access_url, _subjects_count, _sequencing_files_count, _lipidomics_files_count }}'
flat_query_response = query_obj.graphql_query(flat_query)
flat_dict = {x['code']: x for x in flat_query_response['data']['project']}

query = '{ project(first:0) { code, name, full_name, project_description, id }}'
project_info = sub.query(query)
null_values = ["null", "not collected", "no data", "unknown", "not stated or inadequately described", "not reported"]
gen3_dd = sub.get_dictionary_all()
wanted_objects = ["subject", "blood_pressure_test", "lab_result", "exposure", "demographic", "medical_history", "medication"]
skip_properties = ["submitter_id", "id", "updated_datetime", "type", "project_id", "state", "projects", "created_datetime", "subjects"]
summarised_dict = {}
for project in project_info['data']['project']:
    print(f"Processing project: {project['code']} with id {project['id']}")
    summarised_dict[project['code']] = {"_guid_type": "discovery_metadata",
                                        "gen3_discovery": {"id": project['id'],
                                                           "code": project['code'],
                                                           "name": project['name'],
                                                           "data_access_url": flat_dict[project['code']]['data_access_url'],
                                                           "project_description": project["project_description"],
                                                           "subjects_count": flat_dict[project['code']]['_subjects_count'],
                                                           "sequencing_files_count": flat_dict[project['code']]['_sequencing_files_count'],
                                                           "lipidomics_files_count": flat_dict[project['code']]['_lipidomics_files_count'],
                                                           "tags": []},
                                        }
    if summarised_dict[project['code']]['gen3_discovery']['sequencing_files_count'] > 0:
        summarised_dict[project['code']]['gen3_discovery']['tags'].append({"name": "sequencing", "category": "data type"})
    if summarised_dict[project['code']]['gen3_discovery']['lipidomics_files_count'] > 0:
        summarised_dict[project['code']]['gen3_discovery']['tags'].append({"name": "lipidomics", "category": "data type"})
    for obj in wanted_objects:
        property_list = gen3_dd[obj]['properties'].keys()
        property_dict = {}
        for prop in property_list:
            if prop not in skip_properties:
                full_key = f"{obj}.{prop}"
                summarised_dict[project['code']]['gen3_discovery'][full_key] = 0
    total_subjects = summarised_dict[project['code']]['gen3_discovery']['subjects_count']
    batch_size = 500
    min_index = 0
    max_index = min(min_index + batch_size, total_subjects)
    while min_index < total_subjects:
        print(f"Processing subjects {min_index} to {max_index}.")
        query = f'{{ project(code: \"{project["code"]}\") {{ code, name, full_name, project_description, id\
                    subject: subjects(first: {batch_size}, offset: {min_index}){{ \
                        blood_pressure_test: blood_pressure_tests{{ collection_stage, bp_systolic, bp_diastolic}}\
                        exposure: exposures{{ cigarettes_per_day, drinking_current, smoking_status }}\
                        demographic: demographics{{ submitter_id, subjects:submitter_id, sex, baseline_age, bmi_baseline, education, height_baseline, weight_baseline}}\
                        lab_result: lab_results{{ submitter_id, subjects:submitter_id, triglycerides, total_cholesterol, ldl, hdl, age_at_collection, creatinine_serum, egfr_baseline, fasting, glucose_fasting, hba1c_ngsp}} \
                        medical_history: medical_histories{{ angina, diabetes, hypertension, incident_diabetes, myocardial_infarction, stroke }}\
                        medication: medications{{ antihypertensive_meds, diabetes_therapy, lipid_lowering_medication }}\
                  }}}}}}'
        batch_query = sub.query(query)
        for subject in batch_query['data']['project'][0]['subject']:
            for key, value in subject.items():
                if len(value) > 0:
                    for k2, v2 in value[0].items():
                        if k2 not in skip_properties:
                            if v2 is None or v2 in null_values:
                                continue
                            else:
                                full_key = f"{key}.{k2}"
                                summarised_dict[project['code']]["gen3_discovery"][full_key] += 1
        min_index = max_index
        max_index = min(batch_size + max_index, total_subjects )

for k, v in summarised_dict.items():
    metadata.create(v['gen3_discovery']['id'], v, overwrite=True)

# TODO: clean up any deleted projects:

print(f"--- {str(time.time() - start_time)} seconds ---")
