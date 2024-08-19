import os
import shutil
import json
import yaml
import uuid
import glob


class gen3SynthFiles:
    def __init__(self, json_data_path, project_id_list, templates_path, output_dir):
        self.json_data_path = json_data_path
        self.project_id_list = project_id_list
        self.templates_path = templates_path
        self.output_dir = output_dir
        self.all_metadata_paths = self.list_all_metadata_paths()
        self.metadata_file_list = self.list_metadata_files()
        self.data_list = []
        self.synthetic_file_index = {}

        # Purging output dir
        if os.path.exists(self.output_dir):
            shutil.rmtree(self.output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

        self.synthetic_file_index = self.read_synthetic_file_index()

    def parse_json_data(self, project_id):
        print("Parsing JSON data from:", self.json_data_path)  # Debugging print
        for filename in os.listdir(f"{self.json_data_path}/{project_id}"):
            if filename.endswith('file.json'):
                print("Processing file:", filename)  # Debugging print
                with open(os.path.join(self.json_data_path, project_id, filename), 'r') as f:
                    self.data_list.extend(json.load(f))
        print("Completed parsing JSON data.")  # Debugging print
        
    def read_json_file(self, file_path):
        """
        Reads a JSON file from the given file path and returns the data.
        
        :param file_path: Path to the JSON file.
        :return: Data contained in the JSON file.
        """
        print(f"Reading JSON file from: {file_path}")  # Debugging print
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            print("Completed reading JSON file.")  # Debugging print
            return data
        except FileNotFoundError:
            print(f"Error: The file {file_path} does not exist.")
        except json.JSONDecodeError as exc:
            print(f"Error parsing JSON file: {exc}")
        return None
    
    def write_json_file(self, data, file_path):
        """
        Writes the given data to a JSON file at the specified file path.

        :param data: Data to be written to the JSON file.
        :param file_path: Path where the JSON file will be written.
        """
        print(f"Writing JSON file to: {file_path}")  # Debugging print
        try:
            # Extract directory path from file_path
            dir_path = os.path.dirname(file_path)
            # Create directory if it does not exist
            os.makedirs(dir_path, exist_ok=True)
            
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
            print("Completed writing JSON file.")  # Debugging print
        except IOError as exc:
            print(f"Error writing JSON file: {exc}")
            
    def list_all_metadata_paths(self, print_list: bool = False):
        all_outputs = []

        for project_id in self.project_id_list:
            project_path = os.path.join(self.json_data_path, project_id)
            filenames = os.listdir(project_path)

            for filename in filenames:
                output = {project_id: filename}
                all_outputs.append(output)

        if print_list:
            for entry in self.metadata_file_list:
                print(entry)
                
        return all_outputs
        
    def list_metadata_files(self, print_list: bool = False):
        all_outputs = []

        for project_id in self.project_id_list:
            project_path = os.path.join(self.json_data_path, project_id)
            filenames = os.listdir(project_path)
            filtered_filenames = [
                filename for filename in filenames if filename.endswith('file.json')
            ]

            for filename in filtered_filenames:
                output = {project_id: filename}
                all_outputs.append(output)

        if print_list:
            for entry in self.metadata_file_list:
                print(entry)
                
        return all_outputs
        

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
                # print(f'data format: {data_format} found in: {synth_fn}')
                return synth_fn
        if matched_fn is None:
            print(f'WARNING: "{data_format}" does not match any synthetic files')

    def copy_file(self, input_fn, rename_fn, project_id):
        src = os.path.join(self.templates_path, input_fn)
        dst = os.path.join(self.output_dir, project_id, rename_fn)

        if not os.path.exists(src):
            print(f"Error: The source file {src} does not exist.")
            return

        if not os.path.exists(os.path.join(self.output_dir, project_id)):
            os.makedirs(os.path.join(self.output_dir, project_id))

        print("Copying file from", src, "to", dst)  # Debugging print
        shutil.copy(src, dst)
        print("Completed copying file.")  # Debugging print

    def copy_dummy_files(self, preserve_dummy_names=False):
        for project_id in self.project_id_list:
            self.data_list = []
            self.parse_json_data(project_id)
            print(f"Total number of data objects: {len(self.data_list)}")
            
            for data_object in self.data_list:
                print(f"\nProcessing data object: {data_object}")  # Debugging print
                file_format = data_object['data_format']
                synth_file = self.find_dummy_file(file_format)
                
                if preserve_dummy_names:
                    file_name = synth_file
                else:
                    file_name = data_object['file_name']
                
                final_file_name = f'{file_name}.{file_format}'
                self.copy_file(synth_file, final_file_name, project_id)
                print(f"SUCCESS: Completed processing for file: {final_file_name}")  # Debugging print
                
                
    def copy_metadata_files(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
        for entry in self.all_metadata_paths:
            for project, filename in entry.items():
                print(f"Processing {project}: {filename}")  # Debugging print
                source_path = os.path.join(self.json_data_path, project, filename)
                dest_path = os.path.join(self.output_dir, project, filename)
                if not os.path.exists(source_path):
                    print(f"Error: The source file {source_path} does not exist.")
                    continue
                if not os.path.exists(os.path.dirname(dest_path)):
                    os.makedirs(os.path.dirname(dest_path))
                shutil.copy(source_path, dest_path)
                print(f"Copied {source_path} to {dest_path}")  # Debugging print
            

            
                
    def update_fn_metadata(self):
        # reading a metadata file
        for entry in self.metadata_file_list:
            for project, filename in entry.items():
                print(f"Processing {project}: {filename}")  # Debugging print
                metadata = self.read_json_file(os.path.join(self.json_data_path, project, filename))
                
                for data_object in metadata:
                    file_format = data_object['data_format']
                    synth_filename = self.find_dummy_file(file_format)
                    print(f"synth_filename: {synth_filename}")
                    synth_filename = synth_filename.split('.')[0]
                    print(f"updated synth_filename: {synth_filename}")
                    data_object['file_name'] = synth_filename
                
                self.write_json_file(metadata, os.path.join(self.output_dir, project, filename))