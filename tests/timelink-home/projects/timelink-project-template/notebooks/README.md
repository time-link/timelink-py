## How to use the notebooks in this folder

This folder contains Jupyter notebooks that interact with `timelink`.

In order to use the notebooks you need to install VSCode, the Python interpreter and support libraries.

You also need to install Docker.

1. Install VSCode from https://code.visualstudio.com/download
2. Install the Python VSCode extension from  https://marketplace.visualstudio.com/items?itemName=ms-python.python
3. Use one shared timelink venv outside this project, not a per-project one — see "Python environment" in [AGENTS.md](../AGENTS.md). If you do not have one yet:
   * `python3 -m venv ~/venvs/timelink`
   * `~/venvs/timelink/bin/pip install -r notebooks/requirements.txt`
   * `~/venvs/timelink/bin/python -m ipykernel install --user --name timelink --display-name "Python (timelink)"`

   Do not accept the VS Code "Create Environment" suggestion: it would create a `.venv` inside this project.
4. Install jupyter extension
5. Open notebook [00-tutorial-index.ipynb](00-tutorial-index.ipynb)
6. In the upper right corner select the **Python (timelink)** kernel
7. Install Docker. See https://docs.docker.com/get-docker/

See the notebook [02-tutorial.ipynb](02-tutorial.ipynb) for a tutorial on how to use `timelink` in a notebook.

If you have problems create an issue or start a discussion in https://github.com/time-link/timelink-py

## Install Docker

Go to https://www.docker.com/products/docker-desktop/

And install the version for your system.

