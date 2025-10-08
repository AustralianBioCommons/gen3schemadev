"""
Module for validating Gen3 YAML schemas against the Gen3 metaschema.

This module provides a function to validate a Gen3 YAML schema (as a Python dict)
against the Gen3 metaschema using the external `check-jsonschema` CLI tool.

Typical usage example:

    from gen3schemadev.validators.metaschema_validator import validate_schema_with_metaschema
    from gen3schemadev.schema.gen3_template import get_metaschema

    schema = ...  # Load your Gen3 schema as a dict
    metaschema = get_metaschema()
    validate_schema_with_metaschema(schema, metaschema)

"""

import logging
import subprocess
import tempfile
import json

logger = logging.getLogger(__name__)



def validate_schema_with_metaschema(schema: dict, metaschema: dict, verbose: bool = False) -> None:
    """
    Validate a single Gen3 resolved schema dictionary against the Gen3 metaschema using check-jsonschema.

    This function writes the provided schema and metaschema to temporary files and
    invokes the external `check-jsonschema` command-line tool to perform validation.

    Args:
        schema (dict): The Gen3 resolved schema to validate.
        metaschema (dict): The Gen3 metaschema to validate against.
        verbose (bool, optional): If True, enables verbose output from check-jsonschema.

    Raises:
        RuntimeError: If the check-jsonschema tool is not found or fails to execute.
        ValueError: If the schema or metaschema is not a dictionary.

    Returns:
        None

    Note:
        This function does not return a value. It will raise an error if validation fails.
    """
    if not isinstance(schema, dict):
        logger.error("Provided schema is not a dictionary.")
        raise ValueError("Provided schema must be a dictionary.")
    if not isinstance(metaschema, dict):
        logger.error("Provided metaschema is not a dictionary.")
        raise ValueError("Provided metaschema must be a dictionary.")

    logger.info(f"Validating schema '{schema.get('id', '<no id>')}' against the Gen3 metaschema.")

    import os

    try:
        # Write temp files to a .tmp directory in the current working directory
        tmp_dir = os.path.join(os.getcwd(), ".cache")
        os.makedirs(tmp_dir, exist_ok=True)

        schema_path = None
        metaschema_path = None

        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            dir=tmp_dir,
            delete=False
        ) as schema_file, tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.json',
            dir=tmp_dir,
            delete=False
        ) as metaschema_file:
            json.dump(schema, schema_file)
            schema_file.flush()
            json.dump(metaschema, metaschema_file)
            metaschema_file.flush()
            schema_path = schema_file.name
            metaschema_path = metaschema_file.name

        cmd = [
            "check-jsonschema",
            "--schemafile", metaschema_path,
            schema_path
        ]
        if verbose:
            cmd.insert(1, "--verbose")

        logger.debug(f"Running command: {' '.join(cmd)}")
        completed_process = subprocess.run(cmd, capture_output=True, text=True)

        if completed_process.returncode != 0:
            logger.error(
                f"check-jsonschema failed with exit code {completed_process.returncode}"
            )
            if completed_process.stdout:
                logger.error(f"STDOUT: {completed_process.stdout}")
            if completed_process.stderr:
                logger.error(f"STDERR: {completed_process.stderr}")
            raise RuntimeError(
                f"check-jsonschema validation failed for schema '{schema.get('id', '<no id>')}'. "
                f"See logs for details."
            )
        else:
            logger.info(
                f"Schema '{schema.get('id', '<no id>')}' successfully validated against metaschema."
            )
    except FileNotFoundError as e:
        logger.error(
            "The 'check-jsonschema' tool was not found. Please ensure it is installed and in your PATH."
        )
        raise RuntimeError("check-jsonschema tool not found.") from e
    except Exception as e:
        logger.exception("An unexpected error occurred during metaschema validation.")
        raise
