"""
User-facing messages for the CLI.

These are built as pure functions so they can be asserted in tests. A message
that stops the user is part of the tool's behaviour, not decoration: if it
regresses, someone loses a morning.

Every message follows the same four-part shape:

1. what happened, in plain language
2. which files or nodes are affected, named explicitly
3. why the tool stopped, or why this is only a warning
4. the ways forward, as concrete commands, with destructive ones marked

Each ends with a pointer to the documentation section that explains the
underlying concept. `tests/test_cli_messages.py` asserts every pointer resolves
to a real heading, so a message can never send someone to a page that does not
exist.
"""

DOCS_DICTIONARY_REPO = "docs/gen3schemadev/dictionary_repo.md"
DOCS_TROUBLESHOOTING = "docs/gen3schemadev/troubleshooting.md"
DOCS_PROPERTIES = "docs/gen3_data_modelling/properties.md"

# How many filenames to list before collapsing into "(+N more)".
_MAX_LISTED = 6


def _file_list(names, indent="    "):
    """Format a list of filenames, truncating long lists but keeping the count honest."""
    names = sorted(names)
    if len(names) <= _MAX_LISTED:
        return f"{indent}{', '.join(names)}"
    shown = ', '.join(names[:_MAX_LISTED])
    return f"{indent}{shown}, ... (+{len(names) - _MAX_LISTED} more)"


def overwrite_refusal(output_dir, would_overwrite, would_create, input_path):
    """
    Build the message shown when `generate` would overwrite existing files.

    This is the tool's most important message. A user hits it the second time
    they ever run generate, which for many people is the moment they decide
    whether the tool is on their side.

    Args:
        output_dir: Directory being generated into.
        would_overwrite: Filenames that already exist and would be replaced.
        would_create: Filenames that do not exist yet.
        input_path: Path to the input YAML, used to make the commands copy-pasteable.

    Returns:
        The formatted message string.
    """
    lines = [
        f"Refusing to overwrite {len(would_overwrite)} existing "
        f"file{'s' if len(would_overwrite) != 1 else ''} in {output_dir}",
        "",
        "  Would overwrite:",
        _file_list(would_overwrite, indent="    "),
    ]
    if would_create:
        lines += ["  Would create:", _file_list(would_create, indent="    ")]
    lines += [
        "",
        "  generate never overwrites by default, because these files may contain",
        "  edits that your input file does not know about.",
        "",
        "  Choose how this repository works:",
        "",
        f"  * {input_path} is the source of truth - regenerate every time:",
        f"      gen3schemadev generate -i {input_path} -o {output_dir} --input-driven",
        "",
        "  * The Gen3 YAMLs are the source of truth - you have bootstrapped them",
        "    and now edit them directly. Delete the input file so it cannot mislead",
        f"    the next developer ({input_path}), then use validate and bundle from here on.",
        "",
        "  * Regenerate one node and leave everything else alone:",
        f"      gen3schemadev generate -i {input_path} -o {output_dir} --only <node>",
        "",
        "  * Overwrite everything now - THIS DISCARDS ANY HAND EDITS in the files above:",
        f"      gen3schemadev generate -i {input_path} -o {output_dir} --force",
        "",
        f"  See: {DOCS_DICTIONARY_REPO}",
    ]
    return "\n".join(lines)


def orphan_report(output_dir, orphans, as_error):
    """
    Build the message describing files the input cannot produce.

    States the consequence rather than the observation: an orphan is not merely
    untidy, it is still bundled and still deployed. This is exactly how a stale
    node kept shipping in a production dictionary long after the input stopped
    describing it.

    Args:
        output_dir: Directory that was inspected.
        orphans: Filenames present but not generated from the input.
        as_error: True under --input-driven, where an orphan is a failure rather
            than a warning.

    Returns:
        The formatted message string.
    """
    headline = (
        f"{len(orphans)} file{'s' if len(orphans) != 1 else ''} in {output_dir} "
        f"{'is' if len(orphans) == 1 else 'are'} not produced by this input"
    )
    lines = [
        headline,
        "",
        _file_list(orphans, indent="    "),
        "",
        "  These files cannot be regenerated, but bundle still includes them, so",
        "  they will ship in the bundled schema and be deployed to Gen3.",
        "",
    ]
    if as_error:
        lines += [
            "  Under --input-driven the input is the source of truth, so an",
            "  unreproducible file is an error.",
            "",
            "  Either add the node to your input file, or delete the file if it is",
            "  no longer part of the model.",
        ]
    else:
        lines += [
            "  If they are deliberate hand-written nodes, nothing is wrong - this is",
            "  normal in a schema-first repository. If you expected your input to",
            "  produce them, the input and the dictionary have drifted apart.",
        ]
    lines += ["", f"  See: {DOCS_DICTIONARY_REPO}"]
    return "\n".join(lines)


def drift_report(output_dir, changed, missing, orphans, input_path=None):
    """
    Build the `--check` result describing how the dictionary differs from its input.

    Names which side is stale for each category, because "they differ" is not
    actionable on its own.

    Args:
        output_dir: Directory that was checked.
        changed: Files whose generated content differs from what is on disk.
        missing: Files the input produces that are absent from the directory.
        orphans: Files present that the input does not produce.
        input_path: The input file, named in the headline when known.

    Returns:
        The formatted message string.
    """
    source = f" generated from {input_path}" if input_path else ""
    lines = [f"{output_dir} does not match the dictionary{source}."]
    lines.append("")
    if changed:
        lines += [
            f"  Changed - on disk differs from generated ({len(changed)}):",
            _file_list(changed),
            "    The file was hand-edited, or the input changed without regenerating.",
            "",
        ]
    if missing:
        lines += [
            f"  Missing - your input produces these but they are not on disk ({len(missing)}):",
            _file_list(missing),
            "    Run generate to create them.",
            "",
        ]
    if orphans:
        lines += [
            f"  Orphaned - on disk but not produced by your input ({len(orphans)}):",
            _file_list(orphans),
            "    These still ship in the bundle. Add them to the input or delete them.",
            "",
        ]
    lines += [f"  See: {DOCS_DICTIONARY_REPO}"]
    return "\n".join(lines)


def extends_summary(node_name, preset, inherited, overridden, added, implicit=False):
    """
    Build the info line describing what an `extends` merge actually did.

    A merge that cannot be seen is a merge nobody can trust. This spells out
    which preset fields survived untouched and which the node replaced, so the
    Gen3-critical parts of a preset are visibly accounted for.

    Args:
        node_name: The declaring node.
        preset: Name of the preset it extends.
        inherited: Preset keys carried through unchanged.
        overridden: Preset keys the node replaced.
        added: Property names the node contributed.
        implicit: True when the node did not say `extends` and was merged
            because it shares a preset's name.

    Returns:
        The formatted message string.
    """
    if implicit:
        lines = [
            f"  '{node_name}' shares the name of a packaged preset, so it was merged",
            f"    onto it rather than replacing it. Building it from scratch would drop",
            f"    the preset's own properties and the node-level settings Gen3 relies on.",
            f"    Add 'extends: {preset}' to the node to make this explicit.",
        ]
    else:
        lines = [f"  '{node_name}' extends the packaged '{preset}' preset"]
    if added:
        lines.append(f"    added properties:  {', '.join(sorted(added))}")
    if overridden:
        lines.append(f"    overrode:          {', '.join(sorted(overridden))}")
    if inherited:
        lines.append(f"    inherited:         {', '.join(sorted(inherited))}")
    return "\n".join(lines)


def only_unknown_nodes(requested, known):
    """
    Build the error for `--only` naming nodes the input does not define.

    Suggests near-matches, because the overwhelmingly common cause is a typo or
    a node that was renamed in the input.

    Args:
        requested: Node names that could not be found.
        known: Every node name the input defines.

    Returns:
        The formatted message string.
    """
    lines = [
        f"--only named {len(requested)} node{'s' if len(requested) != 1 else ''} "
        f"that {'are' if len(requested) != 1 else 'is'} not in the input: "
        f"{', '.join(sorted(requested))}",
        "",
    ]
    for name in sorted(requested):
        close = [k for k in known if k.startswith(name[:3])] if len(name) >= 3 else []
        if close:
            lines.append(f"  '{name}' - did you mean: {', '.join(sorted(close))}?")
    lines += [
        "",
        f"  Nodes defined in this input: {', '.join(sorted(known))}",
        "",
        "  Nothing was written.",
        f"  See: {DOCS_DICTIONARY_REPO}",
    ]
    return "\n".join(lines)


def unparseable_input(input_path, error):
    """
    Build the error for an input file that is not valid YAML.

    Reports the position the parser stopped at, because YAML errors are almost
    always a punctuation slip a line or two above where they surface - a missing
    colon after a node name, most commonly.

    Args:
        input_path: The file that could not be parsed.
        error: The underlying YAML exception.

    Returns:
        The formatted message string.
    """
    mark = getattr(error, 'problem_mark', None)
    where = f" at line {mark.line + 1}, column {mark.column + 1}" if mark else ""
    problem = getattr(error, 'problem', None) or str(error)
    return "\n".join([
        f"{input_path} is not valid YAML{where}.",
        "",
        f"  {problem}",
        "",
        "  A missing colon after a node name is the usual cause, for example",
        "  '- name_of_node' where '- name: name_of_node' was meant. YAML reports",
        "  the line where parsing became impossible, which can be slightly below",
        "  the line actually at fault.",
        "",
        "  Nothing was written.",
        f"  See: {DOCS_TROUBLESHOOTING}",
    ])


def invalid_input(input_path, error):
    """
    Build the error for input that parses as YAML but does not match the schema.

    Pydantic's own output is accurate but dense, so it is reproduced under a
    plain-language heading and a pointer to the guide that decodes it.

    Args:
        input_path: The file that failed validation.
        error: The pydantic ValidationError.

    Returns:
        The formatted message string.
    """
    lines = [
        f"{input_path} is valid YAML but does not describe a valid data model.",
        "",
    ]
    for err in error.errors():
        location = ".".join(str(part) for part in err.get('loc', ()))
        lines.append(f"  {location or '<root>'}")
        lines.append(f"    {err.get('msg', '')}")
    lines += [
        "",
        "  The location above reads as a path into your input file, so",
        "  'nodes.0.category' means the category of the first node.",
        "",
        "  Nothing was written.",
        f"  See: {DOCS_TROUBLESHOOTING}",
    ]
    return "\n".join(lines)


def cannot_write(output_dir, error):
    """
    Build the error for a dictionary that could not be written.

    Reassures the reader that the existing dictionary is intact, because the
    obvious worry on seeing a write failure is that the directory has been left
    half-updated.

    Args:
        output_dir: The directory being written to.
        error: The underlying OSError.

    Returns:
        The formatted message string.
    """
    return "\n".join([
        f"Could not write the dictionary to {output_dir}.",
        "",
        f"  {error}",
        "",
        "  Your existing dictionary has not been modified. Files are staged and",
        "  only moved into place once all of them have been written, so a failure",
        "  part way through cannot leave the directory half updated.",
        "",
        "  Check file permissions and available disk space, then run the same",
        "  command again.",
        f"  See: {DOCS_TROUBLESHOOTING}",
    ])


def _ref_lines(dangling, indent="    "):
    """Format dangling references as 'file  path  ->  ref' lines."""
    return [
        f"{indent}{source}  {path}  ->  {ref}"
        for source, path, ref in sorted(dangling)
    ]


def shadowed_property_report(shadowed):
    """
    Build the warning shown when input properties duplicate a shared definition.

    Args:
        shadowed: List of {'node', 'block', 'properties'} dicts.

    Returns:
        The formatted message string.
    """
    lines = [
        f"WARNING: {len(shadowed)} node{'s' if len(shadowed) != 1 else ''} "
        f"declare{'' if len(shadowed) != 1 else 's'} a property that "
        f"_definitions.yaml already supplies",
        "",
    ]
    for entry in shadowed:
        lines.append(
            f"    {entry['node']} - also supplied by {entry['block']}: "
            f"{', '.join(entry['properties'])}"
        )
    lines += [
        "",
        "  This is allowed, and sometimes deliberate - the dictionary Gen3 publishes",
        "  does it on nearly every node. Nothing was blocked and your files were written.",
        "",
        "  What it means: the generated file keeps both the shared $ref and your own",
        "  property, so the duplication is invisible when reading the YAML. When the",
        "  resolver gen3schemadev uses resolves the dictionary, your definition is the",
        "  one that takes effect. If you are relying on that override, confirm the",
        "  behaviour on your Gen3 instance before depending on it.",
        "",
        "  If you meant to add a property, rename it.",
        "  If you meant to override the shared one, keep it - this line is the record",
        "  that you did.",
        "",
        f"  See: {DOCS_PROPERTIES}",
    ]
    return "\n".join(lines)


def rule_violation_report(violations, schemas_checked):
    """
    Build the report listing every rule violation found across a dictionary.

    Args:
        violations: List of {'source', 'rule', 'message'} dicts.
        schemas_checked: How many schemas were checked in total.

    Returns:
        The formatted message string.
    """
    by_source = {}
    for violation in violations:
        by_source.setdefault(violation['source'], []).append(violation)

    lines = [
        f"FAILED: {len(violations)} rule violation"
        f"{'s' if len(violations) != 1 else ''} across {len(by_source)} of "
        f"{schemas_checked} schemas",
        "",
    ]
    for source in sorted(by_source):
        lines.append(f"  {source}")
        for violation in by_source[source]:
            lines.append(f"    [{violation['rule']}] {violation['message']}")
        lines.append("")
    lines += [
        "  Every schema was checked, so this is the complete list - there is no",
        "  second round of failures waiting behind it.",
        "",
        "  Fix the nodes above and run validate again.",
        "",
        f"  See: {DOCS_TROUBLESHOOTING}",
    ]
    return "\n".join(lines)


def dangling_term_warning(dangling):
    """
    Build the warning for references to terms that do not exist.

    Args:
        dangling: List of (source_file, dotted_path, ref) tuples.

    Returns:
        The formatted message string.
    """
    lines = [
        f"WARNING: {len(dangling)} documentation reference"
        f"{'s' if len(dangling) != 1 else ''} "
        f"point{'' if len(dangling) != 1 else 's'} at a term that does not exist",
        "",
    ]
    lines += _ref_lines(dangling)
    lines += [
        "",
        "  A 'term' is an ontology pointer used for documentation, not a JSON Schema",
        "  keyword, so nothing about the shape of your data depends on it. Validation",
        "  continued with the term left out.",
        "",
        "  To clear this, either add the missing key to _terms.yaml or remove the",
        "  'term' block from the definition above. The dictionary Gen3 publishes",
        "  currently carries one of these, so seeing it is not necessarily your mistake.",
        "",
        f"  See: {DOCS_TROUBLESHOOTING}",
    ]
    return "\n".join(lines)


def unresolvable_dictionary(target, detail, dangling):
    """
    Build the message shown when a dictionary cannot be resolved at all.

    Args:
        target: The file or directory being validated.
        detail: The resolver's description of what was missing.
        dangling: List of (source_file, dotted_path, ref) tuples.

    Returns:
        The formatted message string.
    """
    lines = [
        f"FAILED: {target} could not be resolved, so no schema was checked "
        f"against the metaschema.",
        "",
        f"  Missing: {detail}",
    ]
    if dangling:
        lines += ["", "  References that point at nothing:"]
        lines += _ref_lines(dangling)
    lines += [
        "",
        "  Resolution has to finish before any schema can be checked. Validating only",
        "  the parts that did resolve would mean reporting success for a dictionary",
        "  that was never fully read.",
        "",
        "  Add the missing definition, or remove the reference to it.",
        "",
        f"  See: {DOCS_TROUBLESHOOTING}",
    ]
    return "\n".join(lines)


def unresolved_nodes(target, unresolved, resolved_count):
    """
    Build the message for schemas that went into resolution but did not come out.

    Args:
        target: The file or directory being validated.
        unresolved: Names of the schemas that did not resolve.
        resolved_count: How many schemas did resolve.

    Returns:
        The formatted message string.
    """
    total = len(unresolved) + resolved_count
    return "\n".join([
        f"FAILED: {len(unresolved)} of {total} schemas in {target} could not be "
        f"resolved and were not checked.",
        "",
        "  Not checked:",
        _file_list(unresolved),
        "",
        "  validate used to print SUCCESS for the schemas that resolved and say",
        "  nothing about the rest, so a dictionary could pass with most of it",
        "  unchecked. A schema that cannot be resolved has not been validated.",
        "",
        "  Check that each schema above has an 'id' and that every reference it",
        "  makes points at something that exists.",
        "",
        f"  See: {DOCS_TROUBLESHOOTING}",
    ])


def validate_needs_a_target():
    """
    Build the usage error for `validate` with neither -b nor -y.

    Previously this path raised an unhandled NameError, which reads as a tool
    crash rather than a usage mistake.

    Returns:
        The formatted message string.
    """
    return "\n".join([
        "validate needs something to validate.",
        "",
        "  Give it a directory of Gen3 YAML files:",
        "      gen3schemadev validate -y dictionary/",
        "",
        "  or a bundled schema:",
        "      gen3schemadev validate -b dictionary/schema.json",
        "",
        f"  See: {DOCS_TROUBLESHOOTING}",
    ])
