# Enrich authority csv via SRU

A python script that uses specified Search/Retrieve via URL (SRU) APIs to complete a CSV file with missing data based on an available lookup identifier column

Possible scenarios could be to fetch data from the SRU APIs of the ISNI database or of the National Library of France (BnF).

ISNI is the [ISO 27729:2012](https://www.iso.org/standard/44292.html) standard name identifier that uniquely identifies public entities who contributed to creative works.

Given a CSV file where each row is a contributor to creative works, this script uses a specified identifier in one of the columns to
fill data gaps in other specified columns based on data available via a specified SRU API.

## Usage

Create and activate a Python virtual environment
```bash

# Create a new Python virtual environment
python3 -m venv py-enrich-csv-via-isni-env

# Activate the virtual environment
source py-request-isni-env/bin/activate

# Install dependencies
pip -r requirements.txt
```

Given a CSV file with the input data, you can call the script in the following way to use the ISNI identifier of the column `isniID`
for requests against the ISNI SRU API to fill possible gaps in the column

* `kbrID` with the `KBR` identifier found in public ISNI records (Royal Library of Belgium)
* `bnfID` with the `BNF` identifier found in public ISNI records (National Library of France)
* `ntaID` with the `NTA` identifier found in public ISNI records (Royal Library of the Netherlands)
* `gender` with gender information found in ISNI records
* `nationality` with nationality information found in ISNI records

```bash
python get_identifier_from_sru.py \
  -i input-file.csv \
  -o enriched-file.csv \
  --column-name-lookup-identifier isniID \
  --wait 0.3
  --config config.json
  --api ISNI
  --data kbrID=KBR ntaID=NTA bnfID=BNF gender=gender nationalities=nationality
```
In the given example, details about the specified `api` will be looked up in the config file.
Based on this in can also be determined if the specified data can be enriched,
i.e. if the config file provides a XPath expression to find the data in the specified source.

Please note that you should provide a `.env` file with your credentials for the ISNI SRU API (this is not needed for public SRU APIs such as for BnF):

```
ISNI_SRU_USERNAME=yourUser
ISNI_SRU_PASSWORD=yourPassword
```

The script will first provide some statistics of how many rows could possibly be enriched
by looping over the input file in a streaming fashion.
Afterwards the script starts requesting data, progress is shown in a progress bar.

Example statistics that are printed before the requests

```bash
In total, the file contains 25633 lines from which 13601 have an ISNI (53.06%)
Stats for column "kbrIDs" that should be enriched via "KBR" field from the ISNI database
12186 KBR identifiers are missing and we want to get them (47.54%).
From those 12186 missing, we could enrich 3016, because they have an ISNI (24.75%)

Stats for column "ntaIDs" that should be enriched via "NTA" field from the ISNI database
19177 NTA identifiers are missing and we want to get them (74.81%).
From those 19177 missing, we could enrich 7992, because they have an ISNI (41.67%)

Stats for column "bnfIDs" that should be enriched via "BNF" field from the ISNI database
19126 BNF identifiers are missing and we want to get them (74.61%).
From those 19126 missing, we could enrich 7105, because they have an ISNI (37.15%)

Stats for column "gender" that should be enriched via "gender" field from the ISNI database
14279 gender identifiers are missing and we want to get them (55.71%).
From those 14279 missing, we could enrich 3373, because they have an ISNI (23.62%)

Stats for column "nationalities" that should be enriched via "nationality" field from the ISNI database
15505 nationality identifiers are missing and we want to get them (60.49%).
From those 15505 missing, we could enrich 3751, because they have an ISNI (24.19%)

```

Example output of the progress bar that constantly updates the number of found data elements

```bash
found KBR 1398,NTA 6504,BNF 1234,gender 159,nationality 137:  50%|█████████████████████████████████████████████████▉                                                 | 12218/24250 [36:57<34:54,  5.74it/s]
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

