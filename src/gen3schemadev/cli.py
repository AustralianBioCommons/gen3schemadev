import argparse
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
from gen3schemadev.utils import write_yaml, load_yaml
from gen3schemadev.schema.input_schema import DataModel
from gen3schemadev.converter import get_entity_names, populate_template

import logging

# Set up basic logging configuration
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger(__name__)


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
                    # Handles: version = "0.1.0"
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

    args = parser.parse_args()

    if getattr(args, "version", False):
        print(get_version())
        sys.exit(0)

    if args.command == "generate":
        import logging
        logger = logging.getLogger("gen3schemadev.cli")

        logger.info("Starting schema generation process...")
        current_dir = os.path.dirname(os.path.abspath(__file__))
        logger.debug(f"Current directory: {current_dir}")
        metaschema = get_metaschema()
        logger.debug(f"Successfully loaded metaschema: {metaschema}")
        converter_template = generate_gen3_template(metaschema)
        logger.info(f"Loading input YAML from: {args.input}")
        data = load_yaml(args.input)
        logger.info("Validating input data model...")
        validated_model = DataModel.model_validate(data)
        entity_names = get_entity_names(validated_model)
        logger.info(f"Found entities: {entity_names}")
        
        for entity in entity_names:
            logger.info(f"Populating template for entity: '{entity}'")
            out_template = populate_template(entity, validated_model, converter_template)
            logger.info(f"Writing output YAML to: {args.output}/{entity}.yaml")
            write_yaml(out_template, f"{args.output}/{entity}.yaml")

        logger.info('Writing auxiliary files')
        write_yaml(generate_def_template(), f"{args.output}/_definitions.yaml")
        write_yaml(generate_setting_template(), f"{args.output}/_settings.yaml")
        write_yaml(generate_terms_template(), f"{args.output}/_terms.yaml")
        write_yaml(generate_core_metadata_template(), f"{args.output}/core_metadata_collection.yaml")

        logger.info("Schema generation process complete.")


if __name__ == "__main__":
    main()
