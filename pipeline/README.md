# Airflow

This guide details the steps to set up and run the Airflow project. Follow these instructions to
get the project up and running on your local machine.

## Prerequisites

- **Python 3.12**: Ensure Python 3.12 is installed and set as the global version in your development environment. We
  recommend using `pyenv` for managing Python versions.

## Setup Instructions

after clone the project

### 1. Setting Up Python 3.11 with `pyenv`

If you haven't installed Python 3.11, use `pyenv` to install and set it as your global Python version:

```bash
pyenv install 3.12.4 # Skip if already installed
pyenv local 3.12.4
```

### 2. Create virtual environments

```bash
python -m venv .venv
```

### 3. Activate virtual environments

```bash
source .venv/bin/activate
```

This command will either create a new virtual environment for the project or activate an existing one.

### 4. Install Project Dependencies

With the virtual environment activated, install the project dependencies:

```bash
pip install -r requirements.txt
```

### 5. Setup AIRFLOW_HOME=your_folder_project

### 6. Run docker

```Docker file
docker build --pull --rm -f "dockerfile" -t pipeline:latest "."
```

```Docker compose
docker compose -f "docker-compose.yml" up -d --build
```

### 7. Running the Development Server

Once the dependencies are installed, you can only run the server in Chrome by :
```
localhost:8080
```

### username:admin
### password ( in your_file: standalone_admin_password.txt)

