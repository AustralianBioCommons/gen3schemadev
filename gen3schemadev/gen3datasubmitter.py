from gen3.index import Gen3Index
import json
import os
import shutil


class Gen3IndexdUpdateMetadata:
    
    def __init__(self, auth, metadata_dir: str):
        self.index = Gen3Index(auth)
        self.metadata_dir = metadata_dir
    
    def pull_indexd_param(self, file_name: str):
        try:
            output = self.index.get_with_params({'file_name': file_name})
            if output:
                print(f"SUCCESS: pulled indexd parameters for: {file_name}")
            return {
                'file_name': output['file_name'],
                'object_id': output['did'],
                'file_size': output['size'],
                'md5sum': output['hashes']['md5']
            }
        except Exception as e:
            print(f"ERROR: No metadata found for: {file_name} | Check S3 | {e}")
            return None
    
    def read_metadata(self, file_path: str):
        with open(f"{self.metadata_dir}/{file_path}", "r") as f:
            metadata = json.load(f)
            print(f"Metadata read from: {file_path}")
        return metadata
    
    def write_metadata(self, file_path: str, metadata: dict):
        with open(f"{self.metadata_dir}/{file_path}", "w") as f:
            json.dump(metadata, f, indent=4, sort_keys=True)
        print(f"Metadata written to: {file_path}")
    
    def pull_filename(self, json_obj: dict):
        try:
            file_name = json_obj['file_name']
            data_format = json_obj['data_format']
            complete_fn = f"{file_name}.{data_format}"
            return complete_fn
        except KeyError as e:
            print(f"KeyError: {e} in entry {entry}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e} in entry {entry}")
            return None
    
    def update_metadata(self, file_path: str, output_dir: str):
        print(f"\n\n\n=======================================================\n=======================================================")
        print(f"UPDATING METADATA: {file_path}")
        print(f"=======================================================\n=======================================================")
        metadata = self.read_metadata(file_path)
        for entry in metadata:
            filename = self.pull_filename(entry)
            if filename:
                indexes = self.pull_indexd_param(filename)
                if indexes:
                    print(f"Appending metadata: {indexes}")
                    entry['file_name'] = indexes['file_name']
                    entry['object_id'] = indexes['object_id']
                    entry['file_size'] = indexes['file_size']
                    entry['md5sum'] = indexes['md5sum']
                else:
                    print(f"Skipping {filename} due to missing metadata.")
            else:
                print(f"Skipping {filename} due to missing metadata.")

        # writing metadata
        if os.path.exists(f"{self.metadata_dir}/{output_dir}"):
            print(f"Deleting output dir: {self.metadata_dir}/{output_dir}")
            shutil.rmtree(f"{self.metadata_dir}/{output_dir}")
        os.makedirs(f"{self.metadata_dir}/{output_dir}", exist_ok=True)
        print(f"Writing metadata to: {self.metadata_dir}/{output_dir}/{file_path}")
        self.write_metadata(f"{output_dir}/{file_path}", metadata)
