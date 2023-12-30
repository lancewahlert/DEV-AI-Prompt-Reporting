# Price Chopper AI

This internal project utilizes AI to provide answers to grocery retail data questions.

## Usage

### Launching

Run the following command in a CLI to launch the streamlit app in a web browser. Give the chat AI prompts to see the options returned.

```
$ streamlit run streamlit_app.py
```

### Creating Options

Use `BuildOptions.py` to provide answer options that the AI can respond with.
Define parameterized answer templates in `src\json\AllTemplates.json` (Or optionally pass in a different filepath as the first CL argument)
Run `BuildOptions.py` to parse the templates, and generate option records. There are several arguments that can be passed to modify the behavior:
--useLocalModel or -l   Uses a trained, locally saved LLM instead of the default base model from hugging face.
--encode or -e          Uses the selected model to encode the option description. Exclude to speed up answer generation.
--truncateLoad or -t    Truncates any previously existing answer options. Excluding this argument allows for incremental additions.
--loadSnowflake or -s   Encodes the options and loads the records into the snowflake instance.
--runQueries or -q      Run the generated queries in snowflake and saves the results with the new records. Can greatly increase runtime.

Examples:
`py .\BuildOptions.py -tseq` to load the master template file's options into snowflake with encoding and cached queries.
`py .\BuildOptions.py src\json\templates2.json -seq` to add new options into snowflake with encoding and cached queries.

## Local App Setup

### Local Installation

Insure Python 3.9 and pip are installed.
Clone the repo, and run the following command to install necessary python packages.

```
$ pip install -r requirements.txt
```

### Crediential Setup
You must create or update the `.streamlit/secrets.toml` file. This file includes the necessary credentials to establish a connection
to Armeta's Snowflake instance. Fill in the `user` and `password` fields.

```
account = "kv21351-zs31584"
user = "<username>"
password = "<password>"
role = "ARMETA_AI_ROLE"
warehouse = "ARMETA_AI_WH"
database = "ARMETA_AI"
schema = "PC"
```

