# Running a Gen3 Dictionary Repository

This guide is about the repository that holds your dictionary, rather than the modelling itself.
It covers the question that causes the most trouble in practice: **where is the source of truth?**

A dictionary repository usually contains two things that describe the same model — an `input_yaml`
file, and the folder of `Gen3 Schema` files generated from it. Both get committed. Nothing forces
them to agree. Once they disagree, it is genuinely hard to tell which one is real, and the answer
tends to be discovered months later by someone who was not there when it happened.

Pick a workflow below, say so in your README, and let the tooling enforce it.

---

## Which workflow are you in?

| You want to... | Workflow | Command you run | What CI enforces |
|---|---|---|---|
| Describe the model in one readable file and regenerate from it | **Input-driven** | `generate --input-driven` | `generate --check` passes |
| Edit `Gen3 Schema` files directly, using their full expressiveness | **Schema-first** | `validate` and `bundle` only | `validate` passes |
| Scaffold with an `input_yaml`, then take over the YAMLs by hand | **Bootstrap, then fork** | `generate` once, then delete the input | `validate` passes |

If you cannot answer "where is the source of truth in this repository?" in one sentence, that is the
problem this page exists to fix.

---

## Input-driven

The `input_yaml` is the source of truth. The generated `Gen3 Data Dictionary` is a build artefact
that happens to be committed, and nobody edits it by hand.

- Best when the model is mostly ordinary nodes and properties, and you value reviewable diffs. A
  pull request shows a few lines of intent in the input file rather than hundreds of generated lines.
- Costs you the parts of Gen3 the input language does not express. Most of these now have an answer
  — see [Extending the packaged presets](#extending-the-packaged-presets) below.

```bash
gen3schemadev generate -i dictionary/input_dd.yaml -o dictionary/schema/ --input-driven
gen3schemadev validate -y dictionary/schema
gen3schemadev bundle -i dictionary/schema -f dictionary/schema/dictionary.json
```

`--input-driven` says regeneration is expected and safe. It overwrites without complaint, and it
treats a file it cannot regenerate as an error rather than a warning — which is the point, because
in this workflow such a file should not exist.

**Use one dictionary folder.** A separate "test" and "production" folder is a common habit here, but
in an input-driven repository the two are always identical, so it doubles the size of every diff
without ever being used. Use a branch instead: your branch is the test dictionary, `main` is
production. That is what branches are for, and unlike a folder a branch cannot be left half-promoted.

---

## Schema-first

The `Gen3 Data Dictionary` folder is the source of truth. There is no `input_yaml`, and `generate`
is not part of your workflow at all.

- Best when you need the full expressiveness of Gen3 schemas, or when the dictionary was inherited
  from somewhere else.
- Costs you the readable overview. Reviewing a change means reading generated-style YAML.

```bash
gen3schemadev validate -y dictionary/schema
gen3schemadev bundle -i dictionary/schema -f dictionary/schema/dictionary.json
```

Nothing about this is second-class. If it is how your repository works, write that in the README so
nobody arrives later, finds no input file, and assumes one has gone missing.

---

## Bootstrap, then fork

Use the `input_yaml` to sketch the shape of the model — nodes, links, the bulk of the properties —
then generate once and hand-edit from there.

Be clear-eyed about what this is: **after the fork you are schema-first.** The `input_yaml` is
scaffolding that has served its purpose, not a fallback you can quietly regenerate from later.

```bash
# 1. Sketch the model, then generate once
gen3schemadev generate -i input_dd.yaml -o dictionary/schema/

# 2. Check you are happy with the result
gen3schemadev validate -y dictionary/schema

# 3. Commit the fork explicitly, so the intent is recorded
git rm input_dd.yaml
git commit -m "chore: fork the dictionary from its input; the YAMLs are now the source of truth"
```

Deleting the input file is the important step, and it is worth doing deliberately rather than
leaving it lying around. A stale input file left in a repository is read by the next person as a
description of the model. It is not — it is a description of what the model looked like on the day
someone stopped using it. Two real repositories have been bitten by exactly this: one carried a node
YAML that no input could reproduce, which kept being bundled and deployed long after the input
stopped mentioning it; another committed an input file that had stopped parsing altogether and
nobody noticed for weeks, because the generated files were still sitting there looking healthy.

If you want to keep the input file for reference, keep it somewhere that cannot be mistaken for a
build input — `reference/`, with a comment at the top saying when it was forked and that it is no
longer authoritative.

### Regenerating one node after forking

You do not have to choose between "regenerate everything" and "never regenerate". `--only` rewrites
the nodes you name and leaves every other file untouched:

```bash
gen3schemadev generate -i input_dd.yaml -o dictionary/schema/ --only biospecimen
```

---

## generate never overwrites by default

Running `generate` into a folder that already contains files stops with an error listing exactly
what it would have replaced, and the ways forward. This is deliberate: the tool cannot tell which
workflow you are in, and guessing wrong destroys work.

The four ways forward are `--input-driven`, `--only`, deleting the input file to go schema-first,
and `--force`. Only `--force` discards hand edits, and the message says so.

---

## Extending the packaged presets

Gen3 ships three nodes its own microservices depend on: `program`, `project` and
`core_metadata_collection`. Their schemas carry settings the input language cannot express — the
properties Gen3 manages rather than the submitter, `project`'s uniqueness on `code` rather than
`submitter_id`, defaults for the project state machine, and Data Use Ontology term identifiers on
the consent codes.

Declaring one of these as an ordinary node rebuilds it from generic defaults and silently drops all
of that. Use `extends` instead, and declare only what you are adding:

```yaml
nodes:
  - name: project
    extends: project
    properties:
      - name: institute_name
        description: "Institution leading the study."
        type: string
      - name: ethics_approval_id
        description: "Ethics approval identifier covering these samples."
        type: string
```

Everything you declare overrides the preset; everything you omit is inherited. `generate` prints
what it inherited, overrode and added, so the merge is visible in your terminal and in CI logs
rather than being something you have to take on trust.

---

## Checking for drift

`generate --check` regenerates in memory, compares against what is committed, writes nothing, and
exits non-zero if they disagree. It reports three distinct problems:

- **Changed** — the file on disk differs from what the input produces. Someone hand-edited it, or
  the input changed without regenerating.
- **Missing** — the input describes a node that is not in the folder. It will not be deployed.
- **Orphaned** — a file the input cannot produce. It cannot be regenerated, but `bundle` still
  includes it, so it ships and is deployed regardless.

In an input-driven repository all three are failures. In a schema-first one, `--check` is not
meaningful — validate instead.

### Continuous integration

For an input-driven repository, this is the job that keeps the two sources honest:

```yaml
name: Dictionary
on: [pull_request]

jobs:
  check:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'
      - run: pip install poetry && poetry install
      - name: Dictionary matches its input
        run: poetry run gen3schemadev generate -i dictionary/input_dd.yaml -o dictionary/schema/ --check
      - name: Dictionary is valid
        run: poetry run gen3schemadev validate -y dictionary/schema
```

For a schema-first repository, drop the first step and keep the second.

---

## Versioning

Pick one canonical version and derive the rest. Three separate version numbers that disagree is a
real state repositories reach: one had `1.0.1` in `pyproject.toml`, `1.3.0` in `_settings.yaml`, and
a most-recent git tag of `v1.2.0`.

The recommendation is that the dictionary version is canonical:

- **Input-driven** — the `version` field at the top of your `input_yaml`. `generate` copies it into
  `_settings.yaml` as `_dict_version`, so the two cannot drift.
- **Schema-first** — `_dict_version` in `_settings.yaml`, edited directly.

Tag releases to match (`v1.3.0` for `_dict_version: 1.3.0`). Leave `pyproject.toml`'s version out of
it — it describes the tooling in the repository, not the dictionary, and trying to keep it in step
adds a step everyone forgets.

---

## The bundled schema is an external contract

The `Gen3 Bundled Schema` is fetched by whatever deploys your model, usually by URL. That means
**the folder name and the filename are part of your deployment contract**, not internal detail.

Renaming `dictionary/prod_dict/` or `your_schema.json` breaks deployment silently — the file simply
stops being where something else expects it, and nothing in this repository will tell you. If you
need to rename, find the consumer first.

The corollary is that consolidating folders is safe as long as the surviving folder keeps the name
the deployment already fetches.

---

## Reviewing dictionary changes

Generated dictionaries produce large pull requests. A change of a few lines in an input file can
touch fifty generated files, and the important part is invisible among them.

- Review the `input_yaml` diff, and treat the generated files as build output.
- Let CI assert the generated files match, so nobody has to read them to be sure.
- Do not commit the same dictionary twice under different folder names. If a reviewer has to read
  every change in duplicate, they will stop reading — which is how a broken input file survived a
  review and two subsequent commits.
