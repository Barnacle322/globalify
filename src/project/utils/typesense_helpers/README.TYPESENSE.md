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

This was only tested on Windows. If you are using a different OS, you may need to change the volume mount.
13
After that you need to install a model from an official [repo of typesense](https://huggingface.co/typesense/models/tree/main/all-MiniLM-L12-v2).

Download all files and add them to the `typesense-data/models/all-MiniLM-L12-v2` directory. Make sure to rename the config file to `config.json` and the vocab file to `vocab.txt`.

After that you may need to restart the docker container.

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
