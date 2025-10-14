import argparse
import logging
import sys
import os

from gen3schemadev.schema.gen3_template import (
    get_metaschema,
    generate_gen3_template,
    generate_def_template,
    generate_setting_template,
    generate_terms_template,
    generate_core_metadata_template,
)
from gen3schemadev.utils import write_yaml, load_yaml, bundle_yamls, write_json
from gen3schemadev.schema.input_schema import DataModel
from gen3schemadev.converter import get_node_names, populate_template
from gen3schemadev.utils import bundled_schema_to_list_dict, resolve_schema
from gen3schemadev.validators.metaschema_validator import validate_schema_with_metaschema
from gen3schemadev.ddvis import visualise_with_docker


def get_version():
    """
    Returns the version string from pyproject.toml, or 'unknown' if not found.
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    root_dir = os.path.abspath(os.path.join(current_dir, "..", ".."))
    pyproject_path = os.path.join(root_dir, "pyproject.toml")
    try:
        with open(pyproject_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip().startswith("version"):
                    parts = line.split("=")
                    if len(parts) == 2:
                        return parts[1].strip().strip('"').strip("'")
    except Exception:
        pass
    return "unknown"


def main():
    parser = argparse.ArgumentParser(
        description="Gen3 Schema Development Tool"
    )
    parser.add_argument(
        "--version",
        action="store_true",
        help="Show version and exit"
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    # Print help and exit if no arguments are provided
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(0)

    # Create 'generate' subcommand
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate schemas"
    )
    generate_parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input YAML file"
    )
    generate_parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output directory"
    )
    generate_parser.add_argument(
        "--debug",
        action="store_true",
        help="Set logging level to DEBUG"
    )

    # Create 'bundle' subcommand
    bundle_parser = subparsers.add_parser(
        "bundle",
        help="Bundle YAML files"
    )
    bundle_parser.add_argument(
        "-i", "--input",
        required=True,
        help="Input directory"
    )
    bundle_parser.add_argument(
        "-f", "--filename",
        required=True,
        help="Output Filename"
    )
    bundle_parser.add_argument(
        "--debug",
        action="store_true",
        help="Set logging level to DEBUG"
    )

    # Create 'validate' subcommand
    validate_parser = subparsers.add_parser(
        "validate",
        help="Validate schemas"
    )
    validate_parser.add_argument(
        "-b", "--bundled",
        required=False,
        help="Bundled JsonSchema file"
    )
    validate_parser.add_argument(
        "-y", "--yamls",
        required=False,
        help="Directory of Gen3 Yaml files"
    )
    validate_parser.add_argument(
        "--debug",
        action="store_true",
        help="Set logging level to DEBUG"
    )
    
    # Create 'visualise' subcomand
    visualise_parser = subparsers.add_parser(
        "visualise",
        help="Visualise schemas"
    )
    visualise_parser.add_argument(
        "-i", "--input",
        required=True,
        help="Path to Bundled Gen3 JsonSchema file"
    )
    visualise_parser.add_argument(
        "--debug",
        action="store_true",
        help="Set logging level to DEBUG"
    )

    args = parser.parse_args()

    # Set up basic logging configuration
    # If the subcommand has --debug, set to DEBUG, else INFO
    log_level = logging.ERROR
    if hasattr(args, "debug") and getattr(args, "debug", False):
        log_level = logging.DEBUG
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(levelname)s] %(message)s"
    )
    logger = logging.getLogger(__name__)

    if getattr(args, "version", False):
        print(get_version())
        sys.exit(0)

    if args.command == "generate":
        print("Starting schema generation process...")
        metaschema = get_metaschema()
        converter_template = generate_gen3_template(metaschema)
        print(f"Loading input YAML from: {args.input}")
        data = load_yaml(args.input)
        print("Validating input data model...")
        validated_model = DataModel.model_validate(data)
        node_names = get_node_names(validated_model)
        print(f"Found nodes: {node_names}")

        for node in node_names:
            print(f"Populating template for node: '{node}'")
            out_template = populate_template(node, validated_model, converter_template)
            print(f"Writing output YAML to: {args.output}/{node}.yaml")
            write_yaml(out_template, f"{args.output}/{node}.yaml")

        print('Writing auxiliary files')
        write_yaml(generate_def_template(), f"{args.output}/_definitions.yaml")
        write_yaml(generate_setting_template(), f"{args.output}/_settings.yaml")
        write_yaml(generate_terms_template(), f"{args.output}/_terms.yaml")
        write_yaml(generate_core_metadata_template(), f"{args.output}/core_metadata_collection.yaml")

        print("Schema generation process complete.")

    elif args.command == "bundle":
        print(f"Bundling YAML files from directory: {args.input}")
        bundle_dict = bundle_yamls(args.input)
        print(f"Writing bundled schema to file: {args.filename}")
        write_json(bundle_dict, args.filename)
        print("Bundling process complete.")

    elif args.command == "validate":
        print("Starting validation process...")
        metaschema = get_metaschema()

        resolve_schema_obj = None
        if args.bundled:
            print(f"Resolving schema from bundled file: {args.bundled}")
            resolve_schema_obj = resolve_schema(schema_path=args.bundled)
        elif args.yamls:
            print(f"Bundling and resolving schemas from directory: {args.yamls}")
            bundled_dir = bundle_yamls(args.yamls)
            resolve_schema_obj = resolve_schema(schema_dir=bundled_dir)

        if resolve_schema_obj is None:
            logger.error("You must provide either --bundled or --yamls for validation.")
            sys.exit(1)

        schema_list = bundled_schema_to_list_dict(resolve_schema_obj)
        print(f"Found {len(schema_list)} schemas to validate.")

        for schema in schema_list:
            schema_id = schema.get('id', '<no id>')
            print(f"Validating schema: {schema_id}")
            validate_schema_with_metaschema(
                schema,
                metaschema=metaschema,
                verbose=True
            )
            print(f"Successfully validated schema: {schema_id}")
        
        print("Validation process complete.")

    elif args.command == "visualise":
        print(f"Visualising schema from file: {args.input}")
        visualise_with_docker(args.input)

if __name__ == "__main__":
    main()
