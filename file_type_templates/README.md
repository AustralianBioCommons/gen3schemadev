### Documentation for `synthetic_file_index.yaml`

#### Overview
The `synthetic_file_index.yaml` file is used by the [gen3SynthFiles](file:./gen3schemadev/gen3synthdata.py) class to map data formats to corresponding synthetic files. This mapping allows the class to generate synthetic data files based on the specified data formats.

#### YAML File Structure
The `synthetic_file_index.yaml` file is structured as a dictionary where each key is the name of a synthetic file, and the value is a list of data formats that the synthetic file can represent.

#### Example Structure
```yaml
dummy_vcf.vcf.gz:
  - vcf
  - vcf.gz
  - VCF
  - variant
  - variant file
  - variant_file
dummy_varbed.bed:
  - varbed
  - bed
  - variant
  - variant file
  - variant_file
dummy_clinical.txt:
  - clinical
  - extra clinical file
  - extra_clinical_file
# ... more entries ...
```

#### How It Is Read
1. **Initialization**: When an instance of `gen3SynthFiles` is created, it initializes various attributes and calls the `read_synthetic_file_index` method to read the `synthetic_file_index.yaml` file.

2. **Reading the YAML File**:
    - The method constructs the path to the `synthetic_file_index.yaml` file.
    - It attempts to open and read the file using `yaml.safe_load`.
    - If the file is successfully read, the contents are stored in the `self.synthetic_file_index` attribute.
    - If the file is not found or there is an error parsing the YAML, appropriate error messages are printed.

3. **Finding a Dummy File**:
    - The `find_dummy_file` method is used to find a synthetic file that matches a given data format.
    - It iterates over the items in `self.synthetic_file_index`.
    - For each synthetic file, it checks if the given data format is in the list of formats associated with that file.
    - If a match is found, the synthetic file name is returned.
    - If no match is found, a warning message is printed.

#### Example Usage in Code
```python 
# gen3schemadev/gen3schemadev/gen3synthdata.py
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
```

#### Key Points
- **Keys**: The keys in the YAML file are the names of synthetic files.
- **Values**: The values are lists of data formats that the corresponding synthetic file can represent.
- **Error Handling**: The code handles file not found and YAML parsing errors gracefully, providing informative error messages.
- **Case Sensitivity**: The data formats in the list are case-sensitive. Ensure consistency in format naming.

#### Example of Matching Process
To illustrate how a file format like `'cram'` would match to the synthetic data file name `dummy_cram.cram`, consider the following entry in the `synthetic_file_index.yaml` file:

```yaml
dummy_cram.cram:
  - cram
  - CRAM
  - genome
  - genomic
  - genomics
  - compressed
  - alignment
  - aligned_read_file
  - aligned read file
  - aligned reads
  - aligned reads file
  - aligned_reads_file
```

The `find_dummy_file` method in the `gen3SynthFiles` class works as follows:

1. **Input Data Format**: Suppose the input data format is `'cram'`.
2. **Iteration**: The method iterates over the dictionary items in `self.synthetic_file_index`.
3. **Checking**: For the key `dummy_cram.cram`, it checks if `'cram'` is in the associated list of formats.
4. **Match Found**: Since `'cram'` is in the list, the method prints a message and returns `dummy_cram.cram`.

Example output:
```plaintext
data format: cram found in: dummy_cram.cram
```

By following this structure and understanding how the `gen3SynthFiles` class reads and uses the `synthetic_file_index.yaml` file, you can effectively map data formats to synthetic files for generating synthetic data.