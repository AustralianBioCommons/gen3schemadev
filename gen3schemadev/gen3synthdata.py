import os
import shutil
import json
import yaml


class gen3SynthFiles:
    def __init__(self, json_data_path, project_id, templates_path, output_dir):
        self.json_data_path = json_data_path
        self.project_id = project_id
        self.templates_path = templates_path
        self.output_dir = output_dir
        self.data_list = []
        self.synthetic_file_index = {}

        # Purging output dir
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.parse_json_data()
        self.synthetic_file_index = self.read_synthetic_file_index()

    def parse_json_data(self):
        print("Parsing JSON data from:", self.json_data_path)  # Debugging print
        for filename in os.listdir(self.json_data_path):
            if filename.endswith('file.json'):
                print("Processing file:", filename)  # Debugging print
                with open(os.path.join(self.json_data_path, filename), 'r') as f:
                    self.data_list.extend(json.load(f))
        print("Completed parsing JSON data.")  # Debugging print

    def read_synthetic_file_index(self):
        index_file_path = os.path.join(self.templates_path, 'synthetic_file_index.yaml')
        print("Reading synthetic file index from:", index_file_path)  # Debugging print
        try:
            with open(index_file_path, 'r') as f:
                synthetic_file_index = yaml.safe_load(f)
            print("Completed reading synthetic file index.")  # Debugging print
        except FileNotFoundError:
            print(f"Error: The file {index_file_path} does not exist.")
        except yaml.YAMLError as exc:
            print(f"Error parsing YAML file: {exc}")
        return synthetic_file_index

    def find_dummy_file(self, data_format: str):
        matched_fn = None
        for synth_fn, synth_lookup in self.synthetic_file_index.items():
            if any(data_format in x for x in synth_lookup):
                print(f'data format: {data_format} found in: {synth_fn}')
                return synth_fn
        if matched_fn is None:
            print(f'WARNING: "{data_format}" does not match any synthetic files')

    def copy_file(self, input_fn, rename_fn):
        src = os.path.join(self.templates_path, input_fn)
        dst = os.path.join(self.output_dir, rename_fn)

        if not os.path.exists(src):
            print(f"Error: The source file {src} does not exist.")
            return

        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        print("Copying file from", src, "to", dst)  # Debugging print
        shutil.copy(src, dst)
        print("Completed copying file.")  # Debugging print

    def synth_data_file_gen(self):
        for data_object in self.data_list:
            print(f"\nProcessing data object: {data_object}")  # Debugging print
            file_name = data_object['file_name']
            file_format = data_object['data_format']
            synth_file = self.find_dummy_file(file_format)
            final_file_name = f'{file_name}.{file_format}'
            self.copy_file(synth_file, final_file_name)
            print(f"SUCCESS: Completed processing for file: {final_file_name}")  # Debugging print