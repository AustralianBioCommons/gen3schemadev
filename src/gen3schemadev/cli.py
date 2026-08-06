import argparse
import logging
import sys
import os

import yaml
from pydantic import ValidationError

from gen3schemadev.schema.gen3_template import (
    get_metaschema,
    generate_gen3_template,
    generate_def_template,
    generate_setting_template,
    generate_terms_template,
    generate_core_metadata_template,
    generate_project_template,
    generate_program_template,
    get_input_example_text
)
from gen3schemadev.utils import (
    write_yaml, load_yaml, bundle_yamls, write_json, resolve_schema, read_json,
    create_dir_if_not_exists, is_documentation_ref, SchemaResolutionError,
)
from gen3schemadev.schema.input_schema import DataModel
from gen3schemadev.converter import get_node_names, populate_template
from gen3schemadev.validators.metaschema_validator import validate_schema_with_metaschema
from importlib.metadata import version
from gen3schemadev.ddvis import visualise_with_docker
from gen3schemadev.validators.rule_validator import RuleValidator
from gen3schemadev.refs import find_null_descriptions, find_dangling_refs
from gen3schemadev import messages
from gen3schemadev.generation import (
    build_dictionary,
    plan_write,
    find_orphans,
    diff_against_disk,
    write_dictionary,
    find_shadowed_properties,
)


def print_null_description_warning(hits):
    """
    Print a warning block listing every null-valued 'description' key found
    in the dictionary ("file: dotted.path" strings). No-op when hits is empty.
    """
    if not hits:
        return
    print(
        "\nWARNING: found 'description: null' placeholders. The Gen3 metaschema "
        "requires 'description' to be a string, and null placeholders in shared "
        "definitions fail metaschema validation once exposed through bare or "
        "allOf-wrapped $refs. Remove the null 'description' keys (removing adds "
        "no shared description, so nothing leaks onto referencing properties):"
    )
    for hit in hits:
        print(f"  - {hit}")


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
        "--force",
        action="store_true",
        help="Overwrite existing files, discarding any hand edits in them"
    )
    generate_parser.add_argument(
        "--input-driven",
        action="store_true",
        dest="input_driven",
        help=(
            "Treat the input file as the source of truth: regenerate everything, "
            "and fail if the output directory contains files the input cannot produce"
        )
    )
    generate_parser.add_argument(
        "--only",
        help="Comma-separated node names to regenerate, leaving all other files untouched"
    )
    generate_parser.add_argument(
        "--check",
        action="store_true",
        help="Report whether the output directory matches the input; write nothing. Exits non-zero on drift"
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
        try:
            data = load_yaml(args.input)
        except yaml.YAMLError as exc:
            # A punctuation slip in the input used to surface as a raw parser
            # traceback. One consumer repo shipped an unparseable input for
            # weeks without anyone realising generation had stopped working.
            print()
            print(messages.unparseable_input(args.input, exc))
            sys.exit(1)
        print("Validating input data model...")
        try:
            validated_model = DataModel.model_validate(data)
        except ValidationError as exc:
            print()
            print(messages.invalid_input(args.input, exc))
            sys.exit(1)
        node_names = get_node_names(validated_model)
        print(f"Found nodes: {node_names}")

        only = None
        if args.only:
            only = [n.strip() for n in args.only.split(',') if n.strip()]
            unknown = set(only) - set(node_names)
            if unknown:
                print(messages.only_unknown_nodes(unknown, node_names))
                sys.exit(1)

        # Build the whole dictionary before touching disk. If a node is
        # malformed we fail here, with the existing dictionary untouched,
        # rather than leaving a half-written directory behind.
        print("Building dictionary...")
        files, merge_summaries = build_dictionary(validated_model, converter_template, only=only)
        for summary in merge_summaries:
            print(messages.extends_summary(
                summary['node'], summary['preset'],
                summary['inherited'], summary['overridden'], summary['added'],
                implicit=summary.get('implicit', False),
            ))

        # Printed before the --check branch returns, so continuous integration
        # sees the same warning a developer does.
        shadowed = find_shadowed_properties(validated_model)
        if shadowed:
            print()
            print(messages.shadowed_property_report(shadowed))

        if args.check:
            diff = diff_against_disk(files, args.output)
            if diff['changed'] or diff['missing'] or diff['orphans']:
                print()
                print(messages.drift_report(
                    args.output, diff['changed'], diff['missing'], diff['orphans'],
                    input_path=args.input,
                ))
                sys.exit(1)
            print(f"OK: {args.output} matches {args.input}. {len(files)} files checked.")
            sys.exit(0)

        plan = plan_write(files, args.output)
        # --only names exactly which nodes to rewrite, so it carries its own
        # consent; refusing it would make the flag useless. --force and
        # --input-driven are the blanket permissions.
        may_overwrite = args.force or args.input_driven or only is not None
        if plan['overwrite'] and not may_overwrite:
            print()
            print(messages.overwrite_refusal(
                args.output, plan['overwrite'], plan['create'], args.input
            ))
            sys.exit(1)

        orphans = find_orphans(files, args.output) if only is None else []
        if orphans:
            print()
            print(messages.orphan_report(args.output, orphans, as_error=args.input_driven))
            if args.input_driven:
                sys.exit(1)

        try:
            written = write_dictionary(files, args.output)
        except OSError as exc:
            print()
            print(messages.cannot_write(args.output, exc))
            sys.exit(1)
        print(f"Wrote {len(written)} files to {args.output}")
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
            '_definitions',
            '_settings',
            '_terms',
            'core_metadata_collection',
        ]
        if args.no_exclude:
            print(f"Validation now includes: {exclude_schema_list}")
            exclude_schema_list = []

        # Conducting business rule validation
        if args.bundled:
            schema_dict = read_json(args.bundled)
        elif args.yamls:
            schema_dict = bundle_yamls(args.yamls)
        else:
            # Previously this fell through to an unhandled NameError on
            # schema_dict, which reads as a crash rather than a usage mistake.
            print(messages.validate_needs_a_target())
            sys.exit(1)

        # Pre-resolution diagnostic: report every null 'description' up front,
        # because the metaschema stage fails on the first resolved node schema,
        # far away from the definition that carries the null.
        null_hits = []
        for schema_name, schema in schema_dict.items():
            for hit in find_null_descriptions(schema):
                null_hits.append(f"{schema_name}: {hit}")
        print_null_description_warning(null_hits)

        # Every schema is checked before anything is reported. Stopping at the
        # first violation meant a dictionary with six problems took six runs.
        violations = []
        checked = []
        for schema_name, schema in schema_dict.items():

            if '.' in schema_name:
                schema_name = os.path.splitext(schema_name)[0]

            if schema_name in exclude_schema_list:
                continue

            checked.append(schema_name)
            for violation in RuleValidator(schema).validate():
                # A schema's 'id' can differ from its filename, and the reader
                # is looking for the file, so carry both.
                violation['source'] = schema_name
                violations.append(violation)

        if violations:
            print()
            print(messages.rule_violation_report(violations, len(checked)))
            sys.exit(1)
        print(f"SUCCESS: rule validation passed for {len(checked)} schemas.")

        # A reference into a 'term' block is documentation, so a missing one is
        # reported and stepped over rather than being fatal. Anything else that
        # dangles stops resolution below.
        dangling = find_dangling_refs(schema_dict)
        documentation_refs = [hit for hit in dangling if is_documentation_ref(hit[1])]
        if documentation_refs:
            print()
            print(messages.dangling_term_warning(documentation_refs))

        # Resolving bundled schema which is required for metaschema validation
        target = args.bundled or args.yamls
        try:
            if args.bundled:
                print(f"Resolving schema from bundled file: {args.bundled}")
                resolved_schema_dict = resolve_schema(schema_path=args.bundled)
            else:
                print(f"Bundling and resolving schemas from directory: {args.yamls}")
                resolved_schema_dict = resolve_schema(schema_dir=args.yamls)
        except SchemaResolutionError as exc:
            print()
            print(messages.unresolvable_dictionary(
                target, str(exc),
                [hit for hit in dangling if not is_documentation_ref(hit[1])],
            ))
            sys.exit(1)

        # Anything that went into resolution but did not come out was never
        # checked. validate used to print SUCCESS for the schemas that resolved
        # and say nothing at all about the rest.
        expected = {
            os.path.splitext(name)[0] for name in schema_dict
            if not os.path.basename(name).startswith('_')
        }
        resolved_ids = {os.path.splitext(name)[0] for name in resolved_schema_dict}
        unresolved = sorted(expected - resolved_ids)
        if unresolved:
            print()
            print(messages.unresolved_nodes(target, unresolved, len(resolved_ids)))
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
        output_path = args.output or "input_example.yaml"
        dir_path = os.path.dirname(output_path)
        if dir_path:
            create_dir_if_not_exists(output_path)
        with open(output_path, "w") as f:
            f.write(get_input_example_text())
        print(f"Wrote example input YAML to: {output_path}")

if __name__ == "__main__":
    main()
