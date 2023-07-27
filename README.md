# Enrich authority csv

[![DOI](https://zenodo.org/badge/655869471.svg)](https://zenodo.org/badge/latestdoi/655869471)

A python script that uses specified Search/Retrieve via URL (SRU) APIs to complete a CSV file with missing data based on an available lookup identifier column

Possible scenarios could be to fetch data from the SRU APIs of the ISNI database or of the National Library of France (BnF).

ISNI is the [ISO 27729:2012](https://www.iso.org/standard/44292.html) standard name identifier that uniquely identifies public entities who contributed to creative works.

Given a CSV file where each row is a contributor to creative works, this script uses a specified identifier in one of the columns to
fill data gaps in other specified columns based on data available via a specified SRU API.

## Usage via the commandline

Create and activate a Python virtual environment
```bash

# Create a new Python virtual environment
python3 -m venv py-enrich-csv-via-isni-env

# Activate the virtual environment
source py-request-isni-env/bin/activate

# Install dependencies
pip install -r requirements.txt
```

Given a CSV file with the input data, you can call the script in the following way to use the ISNI identifier of the column `isniID`
for requests against the ISNI SRU API to fill possible gaps in the column

* `kbrID` with the `KBR` identifier found in public ISNI records (Royal Library of Belgium)
* `bnfID` with the `BNF` identifier found in public ISNI records (National Library of France)
* `ntaID` with the `NTA` identifier found in public ISNI records (Royal Library of the Netherlands)
* `nationality` with nationality information found in ISNI records

```bash
python enrich_authority_csv.py \
  -i input-file.csv \
  -o enriched-file.csv \
  --column-name-lookup-identifier isniID \
  --wait 0.3 \
  --query "pica.isn=" \
  --config config.json \
  --record-schema isni-e \
  --api ISNI \
  --data kbrID=KBR ntaID=NTA bnfID=BNF nationalities=nationality
```

Example of enriching data via the SRU API of the National Library of France (BnF):

```
python enrich_authority_csv.py \
  -i input-file.csv \
  -o enriched-file.csv \
  --column-name-lookup-identifier isniIDs \
  --data nationalities=nationality \
  --wait 0 \
  --query "aut.isni all" \
  --config ../config-example.json \
  --record-schema unimarcxchange \
  --api BnF
```

The `--api` parameter has to be a name from the config file specified with `--config`

The script will also give errors if the caller uses non-specified datafields,
e.g. for exmaple `--data kbrIDs=KBR` (enriching KBR identifiers of column `kbrIDs` based on the remote field `KBR`) does not work with the given configuration,
because the config file does not specify how to get `KBR` from the BnF records.
For this specific example this is not possible, because the records do not contain this information.
The ISNI SRU API on the other hand, provides that data field and it is specified in the configuration for the ISNI SRU API.

In the given example, details about the specified `api` will be looked up in the config file.
Based on this in can also be determined if the specified data can be enriched,
i.e. if the config file provides a XPath expression to find the data in the specified source.

In case of the ISNI API, the username and password are part of the URL.
Currently the script does not take other forms of authentication, for example via HTTP authentication, into account.


The script will first provide some statistics of how many rows could possibly be enriched
by looping over the input file in a streaming fashion.
Afterwards the script starts requesting data, progress is shown in a progress bar.

## Usage as a library

The tool can also be used as a library within another Python script or a Jupyter notebook.

```python
from enrich_authority_csv.enrich_authority_csv import main as enrich_authority_csv

enrich_authority_csv(
  configFile='config-example.json',
  inputFile='input-file.csv',
  outputFile='output-file.csv',
  apiName='BnF',
  query='aut.isni all',
  recordSchema='unimarcxchange',
  dataFields={'nationalities': 'nationality'},
  delimiter=',',
  secondsBetweenAPIRequests=0,
  identifierColumnName='isniIDs')

```


## Example output

```bash
In total, the file contains 299 lines from which 298 contain the identifier to lookup (99.67%)

Stats for column "kbrIDs" that should be enriched via "KBR" field from the remote SRU API
7 KBR values are missing and we want to get them (2.34%).
From those 7 missing, we could enrich 7, because they have a lookup identifier (100.00%)

Stats for column "ntaIDs" that should be enriched via "NTA" field from the remote SRU API
0 NTA values are missing and we want to get them (0.00%).

Stats for column "bnfIDs" that should be enriched via "BNF" field from the remote SRU API
137 BNF values are missing and we want to get them (45.82%).
From those 137 missing, we could enrich 136, because they have a lookup identifier (99.27%)

Stats for column "nationalities" that should be enriched via "nationality" field from the remote SRU API
19 nationality values are missing and we want to get them (6.35%).
From those 19 missing, we could enrich 18, because they have a lookup identifier (94.74%)


found KBR 3,NTA 0,BNF 116,nationality 6: 100%|██████████████████████████████████████████████████████████████████████████████████████████████████████████████████| 155/155 [00:16<00:00, 11.50it/s]
3 from possible 7 records (42.86%) could be enriched with KBR-values from the SRU API!
(In total 3 were found (this number might be higher, because there can be more than one lookup identifier per row)


NTA: No missing values that would have a lookup identifier. So there is nothing to enrich

117 from possible 136 records (86.03%) could be enriched with BNF-values from the SRU API!
(In total 120 were found (this number might be higher, because there can be more than one lookup identifier per row)


6 from possible 18 records (33.33%) could be enriched with nationality-values from the SRU API!
(In total 8 were found (this number might be higher, because there can be more than one lookup identifier per row)

```

## Authentication

Please note that you should provide a `.env` file with your credentials for the ISNI SRU API (this is not needed for public SRU APIs such as for BnF):
You can refer to these environment variables in the configuration file.


```
ISNI_SRU_USERNAME=yourUser
ISNI_SRU_PASSWORD=yourPassword
```


## Software tests

Functions in `lib.py` contain doctests. An additional overal test file with integration tests is currently still missing.

## License

The license of this software was chosen using https://ufal.github.io/public-license-selector and based on licenses of software libraries used by this repo:

| Library | Description | License |
|---------|-------------|---------|
| certifi | Providing the list of Mozilla's carefully curated collection of Root certificates, such that we can communicate securely with the ISNI server via https. | [MPL 2.0](https://www.mozilla.org/en-US/MPL/2.0/) |
| charset-normalizer | A library to help reading text from an unknown charset encoding, this library is used by the `requests` library we are using. | [MIT](https://opensource.org/licenses/MIT) |
| idna | A library to handle internationalized domain names. It is used by `urllib3` and therefore indirectly by our project . | [BSD 3-clause](https://opensource.org/licenses/BSD-3-Clause) |
| python-dotenv | Functionality to load a .env environment file and make the environment variables accessible in Python. We use this library to provide the functionality of specifying the ISNI API URL in an environment variable instead of via a commandline parameter. | [BSD 3-clause](https://opensource.org/licenses/BSD-3-Clause) |
| requests | We use this library to perform HTTP requests against the ISNI APIs. | [Apache 2.0](https://www.apache.org/licenses/LICENSE-2.0) |
| tqdm | A library to provide a user-friendly progress bar, used to show the progress of enriched data from the ISNI database. | [MPL 2.0](https://www.mozilla.org/en-US/MPL/2.0/) |
| urllib3 | Used by the requests library to make requests, thus implicitly used to make API requests against the ISNI APIs. | [MIT](https://opensource.org/licenses/MIT) |


## Contact

Sven Lieber - Sven.Lieber@kbr.be - Royal Library of Belgium (KBR) - https://www.kbr.be/en/

