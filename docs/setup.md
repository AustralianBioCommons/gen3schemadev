# Setup

## Pre-requisites
- `python v3.12.10` or higher
- `poetry v2.1.3` or higher
- `docker compose` (optional for dictionary visualisation)


## Install Gen3SchemaDev
- We use `pyenv` to install python version `3.12.10` specifically.
```
# For MacOS and Linux
brew install pyenv
pyenv install 3.12.10
pyenv global 3.12.10
pip install gen3schemadev
gen3schemadev --version
```
*Note: For windows users we recommend you install a [linux subsystem](https://learn.microsoft.com/en-us/windows/wsl/install) the install with the above command.*


## Installation for Developers
- First clone the repo
```
pip install poetry
poetry install
source $(poetry env info --path)/bin/activate
gen3schemadev --version
```