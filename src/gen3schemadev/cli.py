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
    generate_project_template
)
from gen3schemadev.utils import write_yaml, load_yaml, bundle_yamls, write_json, resolve_schema, read_json
from gen3schemadev.schema.input_schema import DataModel
from gen3schemadev.converter import get_node_names, populate_template
from gen3schemadev.validators.metaschema_validator import validate_schema_with_metaschema
from importlib.metadata import version
from gen3schemadev.ddvis import visualise_with_docker
from gen3schemadev.validators.rule_validator import RuleValidator


def main():
    version_parser = argparse.ArgumentParser(add_help=False)
    version_parser.add_argument(
        '--version',
        action='version',
        version=f"gen3schemadev {version('gen3schemadev')}"
    )

    version_parser.parse_known_args()

    parser = argparse.ArgumentParser(
        description="Gen3 Schema Development Tool"
    )
    parser.add_argument(
        '--version',
        action='version',
        version=f"%(prog)s {version('gen3schemadev')}"
    )

    subparsers = parser.add_subparsers(dest="command", required=False)

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
    validate_parser.add_argument(
        "--no-exclude",
        action="store_true",
        help="Disables the exclusion of specific schema from the validation"
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

    # Create 'init' subcommand
    init_parser = subparsers.add_parser(
        "init",
        help="Initialize gen3schemadev"
    )
    init_parser.add_argument(
        "-o", "--output",
        required=False,
        help="Output directory"
    )
    init_parser.add_argument(
        "--debug",
        action="store_true",
        help="Set logging level to DEBUG"
    )
    
    args = parser.parse_args()
    
    # Handle case where no command is provided
    if args.command is None:
        parser.print_help(sys.stderr)
        sys.exit(0)

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
        setting_dict = generate_setting_template()
        setting_dict['_dict_version'] = validated_model.version
        write_yaml(setting_dict, f"{args.output}/_settings.yaml")
        write_yaml(generate_terms_template(), f"{args.output}/_terms.yaml")
        write_yaml(generate_core_metadata_template(), f"{args.output}/core_metadata_collection.yaml")
        write_yaml(generate_project_template(), f"{args.output}/project.yaml")

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

        # Exclusion list
        exclude_schema_list = [
            'project', '_definitions', '_settings',
            '_terms', 'core_metadata_collection',
            'program'
        ]
        if args.no_exclude:
            print(f"Validation now includes: {exclude_schema_list}")
            exclude_schema_list = []

        # Conducting business rule validation
        if args.bundled:
            schema_dict = read_json(args.bundled)
        elif args.yamls:
            schema_dict = bundle_yamls(args.yamls)

        for schema_name, schema in schema_dict.items():

            if '.' in schema_name:
                schema_name = os.path.splitext(schema_name)[0]

            if schema_name in exclude_schema_list:
                continue
  
            rule_validator = RuleValidator(schema)
            rule_validator.validate()
            print(f"SUCCESS: Rule validation complete for: {schema_name}")

        # Resolving bundled schema which is required for metaschema validation
        resolved_schema_dict = None

        if args.bundled:
            print(f"Resolving schema from bundled file: {args.bundled}")
            resolved_schema_dict = resolve_schema(schema_path=args.bundled)
        elif args.yamls:
            print(f"Bundling and resolving schemas from directory: {args.yamls}")
            resolved_schema_dict = resolve_schema(schema_dir=args.yamls)

        if resolved_schema_dict is None:
            logger.error("You must provide either --bundled or --yamls for validation.")
            sys.exit(1)


        for schema_name, schema in resolved_schema_dict.items():
            validate_schema_with_metaschema(
                schema,
                metaschema=metaschema,
                verbose=True
            )
            print(f"SUCCESS: Metaschema validation complete for: {schema_name}")

        print("Validation process complete.")

    elif args.command == "visualise":
        print(f"Visualising schema from file: {args.input}")
        visualise_with_docker(args.input)
    
    
    elif args.command == "init":
        init_yaml = {
            "version": "0.1.0",
            "url": "https://link-to-data-portal",
            "nodes": [
                {
                    "name": "subject",
                    "description": "The subject or patient",
                    "category": "clinical",
                    "properties": [
                        {
                            "name": "subject_id",
                            "type": "string",
                            "description": "A deidentified identifier for the subject",
                            "required": True
                        }
                    ]
                },
                {
                    "name": "sample",
                    "description": "Info about sample",
                    "category": "clinical",
                    "properties": [
                        {
                            "name": "sample_id",
                            "type": "string",
                            "description": "Sample ID (string)",
                            "required": True
                        }
                    ]
                }
            ],
            "links": [
                {
                    "parent": "subject",
                    "multiplicity": "one_to_many",
                    "child": "sample"
                }
            ]
        }

        output_path = args.output or "input_example.yaml"
        write_yaml(init_yaml, output_path)

if __name__ == "__main__":
    main()
