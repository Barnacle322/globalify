# Globalify

This is the main project of the Globalify Ecosystem. It is a web app that help entrepreneurs and investors find each other easeier.

## Pre-requisites

-   Node.js 14+
-   Python 3.11+
-   Docker

## Installation

1. Clone the repository
1. Run `npm install` to install the dependencies.
1. Run `python -m venv .venv` to create a virtual environment.
1. Run `source .venv/bin/activate`(Mac/Linux) or `.\.venv\Scripts\activate`(Windows) to activate the virtual environment.
1. Run `pip install poetry` to install poetry.
1. Run `poetry install` to install the python dependencies.

## Running the app

1. Make sure that the virtual environment is activated and the .env file is present in the root directory.
1. Run `source start.sh`(Mac/Linux) or `.\start.ps1`(Windows) to start the app.
1. The app will be available at `http://localhost:5000`.

<br>
<br>

# TailwindCSS

We use TailwindCSS for styling. To run the TailwindCSS watcher, run the following command in a separate terminal:

```bash
npm run css
```

To format the HTML files, run the following command:

```bash
npm run html
```

<br>
<br>

# Typesense

To facilitate the search functionality, we use Typesense. Typesense is an open source search engine that is simple to use, has a REST API, and is fast. It is a good alternative to Elasticsearch and Algolia.

## Installation

To install Typesense, first create a directory to store the data. Then, run the following command:

```bash
mkdir typesense-data
```

Then, run the following command to pull the Typesense image and run it:

### Windows

```ps1
docker run --name typesense -p 8108:8108 -v $pwd\typesense-data:/data typesense/typesense:26.0 --data-dir /data --api-key=xyz --enable-cors
```

### MacOS/Linux

```bash
docker run --name typesense -p 8108:8108 -v $(pwd)/typesense-data:/data typesense/typesense:26.0 --data-dir /data --api-key=xyz --enable-cors
```

## Control

Start the Typesense server by running the following command:

```sh
docker start typesense
```

To stop the Typesense server, run the following command:

```sh
docker stop typesense
```

To remove the Typesense server, run the following command:

```sh
docker rm typesense
```

## Usage

To perform DDL operations, we have a CLI tool that can be used to create collections and define their schemas. The CLI tool is located in the `typesense-cli` directory. To use the CLI tool, run the following command:

```bash
python -m src.project.utils.typesense_helpers.typesense_cli setup
```

### Sidenote

Running the setup should automatically download an AI model, if that has failed you can downloadi it manually from [this repo](https://huggingface.co/typesense/models/tree/main/all-MiniLM-L12-v2).

Download all files and add them to the `typesense-data/models/all-MiniLM-L12-v2` directory. Make sure to rename the config file to `config.json` and the vocab file to `vocab.txt`.

After that you may need to restart the docker container.
