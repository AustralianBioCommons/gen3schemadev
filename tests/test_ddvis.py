import pytest
from unittest.mock import patch, MagicMock, mock_open, call
import subprocess

# Replace 'ddvis_module' with your actual module name (without .py)
import gen3schemadev.ddvis as m


# -----------------------
# stop_existing_ddvis_container tests
# -----------------------

@patch.object(m.subprocess, "run")
def test_stop_existing_ddvis_container_stops_and_removes(mock_run):
    # docker ps finds a running container
    mock_run.side_effect = [
        MagicMock(stdout="abc123\n"),  # docker ps
        MagicMock(),                   # docker stop
        MagicMock(),                   # docker rm
    ]

    m.stop_existing_ddvis_container()

    assert mock_run.call_count == 3
    assert mock_run.call_args_list[0].args[0] == ["docker", "ps", "-q", "--filter", "name=ddvis"]
    assert mock_run.call_args_list[1].args[0] == ["docker", "stop", "abc123"]
    assert mock_run.call_args_list[2].args[0] == ["docker", "rm", "abc123"]


@patch.object(m.subprocess, "run")
def test_stop_existing_ddvis_container_no_container(mock_run):
    # docker ps finds nothing
    mock_run.return_value = MagicMock(stdout="")

    m.stop_existing_ddvis_container()

    # Only docker ps should be called
    assert mock_run.call_count == 1
    assert mock_run.call_args_list[0].args[0] == ["docker", "ps", "-q", "--filter", "name=ddvis"]


@patch.object(m.subprocess, "run", side_effect=FileNotFoundError)
def test_stop_existing_ddvis_container_docker_not_found(mock_run):
    with pytest.raises(SystemExit):
        m.stop_existing_ddvis_container()


@patch.object(m.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["docker", "stop"]))
def test_stop_existing_ddvis_container_called_process_error(mock_run):
    with pytest.raises(SystemExit):
        m.stop_existing_ddvis_container()


# -----------------------
# visualise_with_docker tests
# -----------------------

def _docker_compose_content():
    # Must match the module string exactly
    return (
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


@patch.object(m.webbrowser, "open")
@patch.object(m.subprocess, "run")
@patch.object(m, "stop_existing_ddvis_container")
@patch.object(m.shutil, "copy")
@patch("builtins.open", new_callable=mock_open)
@patch.object(m.os, "chdir")
@patch.object(m.os, "makedirs")
@patch.object(m.os.path, "exists")
@patch.object(m.shutil, "which")
@patch.object(m.os, "getcwd", return_value="/work")
def test_visualise_with_docker_success(
    mock_getcwd,
    mock_which,
    mock_exists,
    mock_makedirs,
    mock_chdir,
    mock_open_file,
    mock_copy,
    mock_stop,
    mock_run,
    mock_web_open,
):
    mock_which.return_value = "/usr/local/bin/docker"
    mock_exists.return_value = True

    m.visualise_with_docker("schema.json")

    # .ddvis directory created under CWD and we chdir into it
    mock_makedirs.assert_any_call("/work/.ddvis", exist_ok=True)
    mock_chdir.assert_called_once_with("/work/.ddvis")

    # docker-compose.yml written with exact content
    mock_open_file.assert_called_once_with("docker-compose.yml", "w")
    handle = mock_open_file()
    handle.write.assert_called_once_with(_docker_compose_content())

    # schema copied and existing container stopped
    mock_copy.assert_called_once_with("../schema.json", "schema/")
    mock_stop.assert_called_once()

    # docker commands run
    assert call(["docker", "compose", "pull"], check=True) in mock_run.call_args_list
    assert call(["docker", "compose", "up", "-d"], check=True) in mock_run.call_args_list

    # Browser opened with correct URL using original filename
    mock_web_open.assert_called_once_with("http://localhost:8080/#schema/schema.json")


@patch.object(m.shutil, "which", return_value=None)
def test_visualise_with_docker_missing_docker_compose(mock_which):
    # Early return if docker not available
    m.visualise_with_docker("schema.json")


@patch.object(m.shutil, "which", return_value="/usr/local/bin/docker")
@patch.object(m.os.path, "exists", return_value=False)
def test_visualise_with_docker_missing_schema(mock_exists, mock_which):
    # Early return if schema does not exist
    m.visualise_with_docker("schema.json")


@patch.object(m.shutil, "which", return_value="/usr/local/bin/docker")
@patch.object(m.os.path, "exists", return_value=True)
@patch.object(m.os, "makedirs", side_effect=Exception("mkdir fail"))
def test_visualise_with_docker_makedirs_fail(mock_makedirs, mock_exists, mock_which):
    m.visualise_with_docker("schema.json")


@patch.object(m.shutil, "which", return_value="/usr/local/bin/docker")
@patch.object(m.os.path, "exists", return_value=True)
@patch.object(m.os, "makedirs")
@patch.object(m.os, "chdir", side_effect=Exception("chdir fail"))
def test_visualise_with_docker_chdir_fail(mock_chdir, mock_makedirs, mock_exists, mock_which):
    m.visualise_with_docker("schema.json")


@patch.object(m.shutil, "which", return_value="/usr/local/bin/docker")
@patch.object(m.os.path, "exists", return_value=True)
@patch.object(m.os, "makedirs")
@patch.object(m.os, "chdir")
@patch("builtins.open", side_effect=Exception("open fail"))
def test_visualise_with_docker_write_compose_fail(mock_open_file, mock_chdir, mock_makedirs, mock_exists, mock_which):
    m.visualise_with_docker("schema.json")


@patch.object(m.shutil, "which", return_value="/usr/local/bin/docker")
@patch.object(m.os.path, "exists", return_value=True)
@patch.object(m.os, "makedirs")
@patch.object(m.os, "chdir")
@patch("builtins.open", new_callable=mock_open)
@patch.object(m.shutil, "copy", side_effect=Exception("copy fail"))
def test_visualise_with_docker_copy_fail(mock_copy, mock_open_file, mock_chdir, mock_makedirs, mock_exists, mock_which):
    m.visualise_with_docker("schema.json")


@patch.object(m.shutil, "which", return_value="/usr/local/bin/docker")
@patch.object(m.os.path, "exists", return_value=True)
@patch.object(m.os, "makedirs")
@patch.object(m.os, "chdir")
@patch("builtins.open", new_callable=mock_open)
@patch.object(m.shutil, "copy")
@patch.object(m, "stop_existing_ddvis_container", side_effect=Exception("stop fail"))
def test_visualise_with_docker_stop_fail(mock_stop, mock_copy, mock_open_file, mock_chdir, mock_makedirs, mock_exists, mock_which):
    m.visualise_with_docker("schema.json")


@patch.object(m.shutil, "which", return_value="/usr/local/bin/docker")
@patch.object(m.os.path, "exists", return_value=True)
@patch.object(m.os, "makedirs")
@patch.object(m.os, "chdir")
@patch("builtins.open", new_callable=mock_open)
@patch.object(m.shutil, "copy")
@patch.object(m, "stop_existing_ddvis_container")
@patch.object(m.subprocess, "run", side_effect=subprocess.CalledProcessError(1, ["docker", "compose", "pull"]))
def test_visualise_with_docker_docker_compose_fail(mock_run, mock_stop, mock_copy, mock_open_file, mock_chdir, mock_makedirs, mock_exists, mock_which):
    m.visualise_with_docker("schema.json")


@patch.object(m.webbrowser, "open", side_effect=Exception("browser fail"))
@patch.object(m.subprocess, "run")
@patch.object(m, "stop_existing_ddvis_container")
@patch.object(m.shutil, "copy")
@patch("builtins.open", new_callable=mock_open)
@patch.object(m.os, "chdir")
@patch.object(m.os, "makedirs")
@patch.object(m.os.path, "exists")
@patch.object(m.shutil, "which")
@patch.object(m.os, "getcwd", return_value="/work")
def test_visualise_with_docker_browser_fail(mock_getcwd, mock_which, mock_exists, mock_makedirs, mock_chdir,
                                            mock_open_file, mock_copy, mock_stop, mock_run, mock_web_open):
    mock_which.return_value = "/usr/local/bin/docker"
    mock_exists.return_value = True

    m.visualise_with_docker("schema.json")

    # Even if browser fails, function should have reached that point
    assert call(["docker", "compose", "pull"], check=True) in mock_run.call_args_list
    assert call(["docker", "compose", "up", "-d"], check=True) in mock_run.call_args_list
