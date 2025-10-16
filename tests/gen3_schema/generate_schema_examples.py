import os
import argparse
from gen3schemadev.utils import read_json, write_yaml, write_json, resolve_schema

def main():
    try:
        # Get the current file path
        current_file_path = os.path.abspath(__file__)
        print(f"Current file path: {current_file_path}")

        # Set up paths relative to current_file_path
        base_dir = os.path.dirname(current_file_path)
        examples_dir = os.path.join(base_dir, "examples")
        json_dir = os.path.join(examples_dir, "json")
        yaml_dir = os.path.join(examples_dir, "yaml")
        resolved_yaml_dir = os.path.join(yaml_dir, "resolved")

        print(f"Base directory: {base_dir}")
        print(f"Examples directory: {examples_dir}")
        print(f"JSON directory: {json_dir}")
        print(f"YAML directory: {yaml_dir}")
        print(f"Resolved YAML directory: {resolved_yaml_dir}")

        bundled_schema_path = os.path.join(json_dir, "schema_dev.json")
        print(f"Bundled schema path: {bundled_schema_path}")

        try:
            bundled_schema = read_json(bundled_schema_path)
        except Exception as e:
            print(f"Error reading bundled schema: {e}")
            return

        print(f"Loaded bundled schema with {len(bundled_schema)} entries.")

        # write to yamls
        output_folder = yaml_dir
        print(f"Writing individual YAML files to: {output_folder}")
        for k, v in bundled_schema.items():
            w_path = os.path.join(output_folder, k)
            try:
                print(f"Writing YAML for {k} to {w_path}")
                write_yaml(v, w_path)
            except Exception as e:
                print(f"Error writing YAML for {k}: {e}")

        # Resolve the schema and write to yamls
        print("Resolving schema...")
        try:
            resolved_schema = resolve_schema(schema_path=bundled_schema_path)
        except Exception as e:
            print(f"Error resolving schema: {e}")
            return

        print(f"Resolved schema contains {len(resolved_schema)} entries.")
        for v in resolved_schema:
            k = v['id'] + '.yaml'
            w_path = os.path.join(resolved_yaml_dir, k)
            try:
                print(f"Writing resolved YAML for {k}")
                write_yaml(v, w_path)
            except Exception as e:
                print(f"Error writing resolved YAML for {k}: {e}")

        # write the bundled resolved schema
        resolved_json_path = os.path.join(json_dir, "schema_dev_resolved.json")
        try:
            print(f"Writing bundled resolved schema to: {resolved_json_path}")
            write_json(resolved_schema, resolved_json_path)
        except Exception as e:
            print(f"Error writing bundled resolved schema: {e}")
            return

        print("All done.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")

if __name__ == "__main__":
    main()
