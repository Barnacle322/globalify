# Typesense

To facilitate the search functionality, we use Typesense. Typesense is an open source search engine that is simple to use, has a REST API, and is fast. It is a good alternative to Elasticsearch and Algolia.

## Installation

To install Typesense, first create a directory to store the data. Then, run the following command:

```bash
mkdir typesense-data
```

Then, run the following command to pull the Typesense image and run it:

```bash
docker run --name typesense -p 8108:8108 -v $pwd/typesense-data:/data typesense/typesense:0.26.0.rc54 --data-dir /data --api-key=xyz --enable-cors
```
This was only tested on Windows. If you are using a different OS, you may need to change the volume mount.


## Control

Start the Typesense server by running the following command:

```bash
docker start typesense
```

To stop the Typesense server, run the following command:

```bash
docker stop typesense
```

To remove the Typesense server, run the following command:

```bash
docker rm typesense
```

## Usage

To perform DDL operations, we have a CLI tool that can be used to create collections and define their schemas. The CLI tool is located in the `typesense-cli` directory. To use the CLI tool, run the following command:

```bash
python -m src.project.utils.typesense-cli setup
```
