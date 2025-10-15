import subprocess
import os
import shutil
import webbrowser
import logging
import sys

def stop_existing_ddvis_container():
    """Checks for a running container named 'ddvis' and stops/removes it."""
    logging.info("Checking for existing 'ddvis' container...")

    # Command to find the container ID of a container named 'ddvis'
    container_id_cmd = ["docker", "ps", "-q", "--filter", "name=ddvis"]

    try:
        # Get the container ID
        result = subprocess.run(container_id_cmd, capture_output=True, text=True, check=False)
        container_id = result.stdout.strip()

        if container_id:
            logging.info(f"Found running 'ddvis' container with ID: {container_id}. Stopping it...")
            # Stop the container
            subprocess.run(["docker", "stop", container_id], check=True)
            # Remove the container
            subprocess.run(["docker", "rm", container_id], check=True)
            logging.info("Container stopped and removed successfully.")
        else:
            logging.info("No existing 'ddvis' container found.")

    except FileNotFoundError:
        logging.error("Error: 'docker' command not found. Please ensure Docker is installed and in your PATH.")
        sys.exit(1)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error during Docker operation: {e}")
        sys.exit(1)


def visualise_with_docker(schema_path):
    """
    Launch the DDVis Docker container for visualizing a Gen3 schema file.

    This function creates a temporary directory `.ddvis`, changes to it,
    checks for docker-compose installation, validates the existence
    of the provided schema file, writes the necessary docker-compose.yml file,
    copies the schema into a ./schema directory, starts the DDVis container, and
    attempts to open the DDVis URL in the default web browser.

    Args:
        schema_path (str): Path to the schema file to be visualized.

    Returns:
        None

    Prints user-friendly error messages if prerequisites are missing, if Docker 
    operations fail, or if the web browser could not be opened.
    """
    import os

    if not shutil.which("docker"):
        logging.error("Error: docker is not installed. Please install it to continue.")
        return

    if not os.path.exists(schema_path):
        logging.error(f"Error: Schema file '{schema_path}' does not exist.")
        return

    # Work in temp directory
    temp_dir = os.path.join(os.getcwd(), ".ddvis")
    try:
        os.makedirs(temp_dir, exist_ok=True)
        logging.info(f"Created .ddvis directory: {temp_dir}")
    except Exception as e:
        logging.error(f"Error creating .ddvis directory: {e}")
        return

    try:
        os.chdir(temp_dir)
    except Exception as e:
        logging.error(f"Error changing directory to .ddvis: {e}")
        return

    schema_filename = os.path.basename(schema_path)
    logging.debug(f"Schema filename: {schema_filename}")
    schema_path = f"../{schema_path}"
    logging.debug(f"Schema path: {schema_path}")

    # Docker compose configuration as a string
    docker_compose_content = (
        "version: '3.1'\n"
        "services:\n"
        "  ddvis:\n"
        "    image: quay.io/umccr/ddvis\n"
        "    container_name: ddvis\n"
        "    volumes:\n"
        "      - ./schema:/usr/share/nginx/html/schema:ro\n"
        "    ports:\n"
        "      - \"8080:80\"\n"
    )

    try:
        # Write the docker-compose.yml file
        with open("docker-compose.yml", "w") as f:
            f.write(docker_compose_content)
    except Exception as e:
        logging.error(f"Error writing docker-compose.yml: {e}")
        return

    try:
        # Create schema directory and copy the file
        os.makedirs("schema", exist_ok=True)
        shutil.copy(schema_path, "schema/")
    except Exception as e:
        logging.error(f"Error preparing schema directory or copying file: {e}")
        return

    try:
        stop_existing_ddvis_container()
    except Exception as e:
        logging.error(f"Error stopping existing ddvis container: {e}")
        return

    try:
        # Run docker-compose commands
        logging.info("Pulling Docker image and starting container...")
        subprocess.run(["docker", "compose", "pull"], check=True)
        subprocess.run(["docker", "compose", "up", "-d"], check=True)
    except subprocess.CalledProcessError as e:
        logging.error(f"Error running docker-compose command: {e}")
        return
    except Exception as e:
        logging.error(f"Unexpected error during docker-compose execution: {e}")
        return

    # Open the browser
    url = f"http://localhost:8080/#schema/{schema_filename}"
    logging.info(f"Attempting to open DDVis at {url}")
    try:
        webbrowser.open(url)
    except Exception as e:
        logging.warning(f"Error opening web browser: {e}")

