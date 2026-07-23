"""
Tests for the non-destructive behaviour of `gen3schemadev generate`.

Background: a Gen3 data dictionary can be maintained in more than one way. Some
repositories treat the input file as the source of truth and regenerate from it
every time. Others generate once to get started and then edit the Gen3 YAML
files directly, so the generated files become the real dictionary. Both are
legitimate, and the tool cannot tell which one you are doing.

Before this behaviour existed, `generate` simply overwrote everything it found.
In a repository that had moved to hand-editing, a single command silently
destroyed work, and because the generated files are large and numerous, nobody
noticed until much later. These tests pin down the guarantee that replaced it:
generate writes nothing over your files unless you have told it to.
"""

from tests.conftest import snapshot


def test_first_generate_into_empty_directory_succeeds(run_cli, input_file, output_dir):
    """
    Input: an empty output directory and a valid input file.

    Expected: generation succeeds and writes the dictionary.

    Why it matters: the safety rules must not get in the way of the very first
    run. Someone starting a new dictionary, or bootstrapping one before they
    switch to hand-editing, should see the tool simply work.
    """
    code, out = run_cli("generate", "-i", input_file, "-o", output_dir)

    assert code == 0
    assert "subject.yaml" in snapshot(output_dir)
    assert "biospecimen.yaml" in snapshot(output_dir)
    assert "Schema generation process complete." in out


def test_second_generate_refuses_and_leaves_every_file_byte_identical(
    run_cli, input_file, generated
):
    """
    Input: a dictionary that has already been generated, where a developer has
    since hand-edited subject.yaml.

    Expected: a second `generate` exits non-zero and every file in the directory
    is byte-for-byte what it was beforehand, including the hand edit.

    Why it matters: this is the whole safety promise. Exiting non-zero is not
    sufficient on its own - a refusal that had already rewritten three of the
    nineteen files would be worse than no refusal at all, because the dictionary
    would be left in a state that matches neither the input nor the previous
    commit. So the assertion is about the bytes on disk, not the exit code.
    """
    edited = f"{generated}/subject.yaml"
    with open(edited, "a") as handle:
        handle.write("\n# a deliberate hand edit\n")
    before = snapshot(generated)

    code, out = run_cli("generate", "-i", input_file, "-o", generated)

    assert code == 1
    assert snapshot(generated) == before
    assert "Refusing to overwrite" in out


def test_force_overwrites_and_discards_hand_edits(run_cli, input_file, generated):
    """
    Input: a generated dictionary containing a hand edit, regenerated with --force.

    Expected: the command succeeds and the hand edit is gone.

    Why it matters: --force is the escape hatch, and the refusal message
    explicitly warns that it discards hand edits. That warning has to be true.
    A --force that quietly preserved edits would be just as confusing as one
    that destroyed them without saying so.
    """
    edited = f"{generated}/subject.yaml"
    with open(edited, "a") as handle:
        handle.write("\n# a deliberate hand edit\n")

    code, _ = run_cli("generate", "-i", input_file, "-o", generated, "--force")

    assert code == 0
    assert "a deliberate hand edit" not in open(edited).read()


def test_input_driven_regenerates_every_node(run_cli, input_file, generated):
    """
    Input: an already-generated dictionary, regenerated with --input-driven.

    Expected: the command succeeds and overwrites without needing --force.

    Why it matters: --input-driven is how a repository declares that its input
    file is the source of truth. In that mode regeneration is the normal, safe
    operation, so it should not require the flag that means "yes, destroy my
    edits" - the two situations deserve different words.
    """
    code, _ = run_cli("generate", "-i", input_file, "-o", generated, "--input-driven")

    assert code == 0
    assert "subject.yaml" in snapshot(generated)


def test_only_regenerates_named_node_and_leaves_hand_edits_in_others(
    run_cli, input_file, generated
):
    """
    Input: a generated dictionary where subject.yaml has been hand-edited, and
    `--only biospecimen` is used to regenerate a different node.

    Expected: biospecimen.yaml is rewritten, subject.yaml keeps its hand edit,
    and no other file changes.

    Why it matters: this is what makes the mixed workflow safe. A repository
    that hand-maintains most of its dictionary may still want the tool to
    regenerate one node. Without this, the only options were to overwrite
    everything or to hand-copy files between directories, which is what several
    repositories ended up doing.
    """
    edited = f"{generated}/subject.yaml"
    with open(edited, "a") as handle:
        handle.write("\n# a deliberate hand edit\n")
    before = snapshot(generated)

    code, _ = run_cli(
        "generate", "-i", input_file, "-o", generated, "--only", "biospecimen"
    )
    after = snapshot(generated)

    assert code == 0
    assert "a deliberate hand edit" in open(edited).read()
    assert after["subject.yaml"] == before["subject.yaml"]
    # Every file other than the one named is untouched.
    changed = {name for name in before if before[name] != after.get(name)}
    assert changed <= {"biospecimen.yaml"}


def test_only_with_unknown_node_writes_nothing_and_suggests_a_match(
    run_cli, input_file, generated
):
    """
    Input: `--only subjcet`, a misspelling of the node "subject".

    Expected: the command fails, nothing on disk changes, and the message
    suggests "subject".

    Why it matters: a typo in --only could otherwise look like a successful
    no-op, leaving someone convinced they had regenerated a node when they had
    not. Naming the near-match turns a confusing silence into a one-second fix.
    """
    before = snapshot(generated)

    code, out = run_cli(
        "generate", "-i", input_file, "-o", generated, "--only", "subjcet"
    )

    assert code == 1
    assert snapshot(generated) == before
    assert "did you mean" in out and "subject" in out


def test_failed_generation_leaves_output_directory_untouched(
    run_cli, tmp_path, generated
):
    """
    Input: an already-generated dictionary, regenerated with --force from an
    input file that is malformed.

    Expected: the command fails and every existing file is unchanged.

    Why it matters: generation builds many files, so a failure partway through
    could leave a dictionary that is half old and half new - the worst possible
    state, because it is neither recoverable by regenerating nor trustworthy as
    committed work. The implementation builds everything in memory before
    touching disk specifically to make this impossible, and this test is what
    holds that design in place.
    """
    broken = tmp_path / "broken.yaml"
    broken.write_text(
        "version: 0.1.0\n"
        "url: https://example.biocommons.org.au\n"
        "nodes:\n"
        "  - name: subject\n"
        "    category: not_a_real_category\n"
        "    properties: []\n"
        "links: []\n"
    )
    before = snapshot(generated)

    code, _ = run_cli("generate", "-i", str(broken), "-o", generated, "--force")

    assert code != 0
    assert snapshot(generated) == before
