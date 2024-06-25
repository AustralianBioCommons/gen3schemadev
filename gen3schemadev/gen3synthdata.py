import os
import json
import yaml
import re
import shutil


class SyntheticDataGenerator:
    def __init__(self, json_data_path, project_id, templates_path, output_dir):
        """
        Initializes a SyntheticDataGenerator object.
        Args:
            json_data_path (str): The path to the directory containing JSON data files.
            project_id (str): The ID of the project.
            templates_path (str): The path to the directory containing template files.
            output_dir (str): The path to the output directory.

        Initializes the following instance variables:
            - json_data_path (str): The path to the directory containing JSON data files.
            - project_id (str): The ID of the project.
            - templates_path (str): The path to the directory containing template files.
            - output_dir (str): The path to the output directory.
            - data_dict (dict): An empty dictionary to store JSON data.
            - file_index (dict): An empty dictionary to store template file information.
            - synthetic_file_index (dict): An empty dictionary to store synthetic file information.
        """
        self.json_data_path = json_data_path
        self.project_id = project_id
        self.templates_path = templates_path
        self.output_dir = output_dir
        self.data_dict = {}
        self.file_index = {}
        self.synthetic_file_index = {}

    def parse_json_data(self):
        print("Parsing JSON data from:", self.json_data_path)  # Debugging print
        for filename in os.listdir(self.json_data_path):
            if filename.endswith('file.json'):
                print("Processing file:", filename)  # Debugging print
                with open(os.path.join(self.json_data_path, filename), 'r') as f:
                    self.data_dict[filename] = json.load(f)
        print("Completed parsing JSON data.")  # Debugging print
        
    def return_data_dict(self):
        return self.data_dict
        
    # def get_filename_id(self):
    #     for i in self.data_dict:
    #         filename_id = i['file_name']
    #         file_format = i['data_format']

    def read_template_files(self):
        print("Reading template files from:", self.templates_path)  # Debugging print
        for filename in os.listdir(self.templates_path):
            if filename.startswith('dummy_'):
                file_type = filename.split('dummy_')[1].split('.')[0]
                self.file_index[file_type] = filename
                print("Indexed template file:", filename, "as type:", file_type)  # Debugging print
        print("Completed reading template files.")  # Debugging print

    def read_synthetic_file_index(self):
        index_file_path = os.path.join(self.templates_path, 'synthetic_file_index.yaml')
        print("Reading synthetic file index from:", index_file_path)  # Debugging print
        with open(index_file_path, 'r') as f:
            self.synthetic_file_index = yaml.safe_load(f)
        print("Completed reading synthetic file index.")  # Debugging print

    def print_synthetic_file_index(self):
        print("Synthetic file index:")  # Debugging print
        print(json.dumps(self.synthetic_file_index, indent=4))
        
    def find_dummy_file(self, file_type: str):
        """
        Searches for a file based on the provided search term.
        Args:
            search_term (str): The term to search for in the search terms.
        Returns:
            str: The parent key name if a match is found, otherwise None.
        """
        print('Searching for file type:', file_type)  # Debugging print
        for parent_key, details in self.synthetic_file_index.items():
            print(f"Checking parent key: {parent_key}")  # Debugging print
            if any(file_type in detail for detail in details):
                print(f"Search terms found in details for {parent_key}: {details}")  # Debugging print
                return parent_key
            else:
                print(f"No match found for search term '{file_type}' in {parent_key}")  # Debugging print
        print(f"No match found for file type: {file_type} in any parent key")  # Debugging print

    def extract_file_info(self):
        print("Extracting file information from template files.")  # Debugging print
        file_info_list = []
        for file_type, filename in self.file_index.items():
            file_name, file_extension = os.path.splitext(filename)
            file_info_list.append((file_name, file_extension, file_type))
            print("Extracted info - Name:", file_name, "Extension:", file_extension, "Type:", file_type)  # Debugging print
        print("Completed extracting file information.")  # Debugging print
        return file_info_list

    def copy_file(self, input_fn, rename_fn):
        src = os.path.join(self.templates_path, input_fn)
        dst = os.path.join(self.output_dir, rename_fn)
        print("Copying file from", src, "to", dst)  # Debugging print
        shutil.copy(src, dst)
        print("Completed copying file.")  # Debugging print

    def synth_data_file_gen(self):
        print("Generating synthetic data files.")  # Debugging print
        file_info_list = self.extract_file_info()
        for file_info in file_info_list:
            file_name, file_extension, file_type = file_info
            best_match = None
            for key, lookups in self.synthetic_file_index.items():
                if any(file_type in lookup for lookup in lookups):
                    best_match = key
                    print("Found best match for type", file_type, ":", best_match)  # Debugging print
                    break
            if best_match:
                new_filename = f"{file_name}{file_extension}"
                print("New filename generated:", new_filename)  # Debugging print
                self.copy_file(f'{file_name}{file_extension}', new_filename)  # Copy the file_name, new_filename)
        print("Completed generating synthetic data files.")  # Debugging print
