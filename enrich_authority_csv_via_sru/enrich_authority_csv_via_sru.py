import os
import csv
from dotenv import load_dotenv
from config_parser import ConfigParser
import lib
import time
from tqdm import tqdm
from argparse import ArgumentParser

     
# -----------------------------------------------------------------------------
def main():

  parser = ArgumentParser(description='This script reads a CSV file and requests for each found ISNI identifier (in the column specified with --column-name-isni) the identifier(s) specified with --identifier')
  parser.add_argument('-i', '--input-file', action='store', required=True, help='A CSV file that contains records about contributors')
  parser.add_argument('-o', '--output-file', action='store', required=True, help='The CSV file in which the enriched records are stored')
  parser.add_argument('--data', metavar='KEY=VALUE', required=True, nargs='+', help='A key value pair where the key is the name of the data column in the input that should be fetched and the value is the name of the datafield as stated in the configuration.')
  parser.add_argument('--api', action='store', required=True, help='The name of the API that should be queried, as specified in the configuration')
  parser.add_argument('--record-schema', action='store', required=True, help='The name of the record schema that should be requested, for example "isni-e" or "unimarcxchange"')
  parser.add_argument('-q', '--query', action='store', required=True, help='The query pattern used to query, e.g. "aut.isni all" for BnF or "pica.isn=" for ISNI')
  parser.add_argument('--column-name-lookup-identifier', action='store', required=True, help='The name of the column in the input file that contains the identifier to lookup')
  parser.add_argument('-c', '--config', action='store', required=True, help='The JSON configuration that specifies SRU APIs and which data fields an be retrieved from it.')
  parser.add_argument('--wait', action='store', type=float, default = 1, help='The number of seconds to wait in between API requests')
  parser.add_argument('-d', '--delimiter', action='store', default=',', help='The delimiter of the input CSV')
  args = parser.parse_args()


  config = ConfigParser(args.config)
  apiName = args.api
  query = args.query
  recordSchema = args.record_schema

  dataFields = dict(map(lambda s: s.split('='), args.data))

  # check if the requested data can be fetched based on the given API config
  lib.verifyTask(config, apiName, recordSchema, dataFields)


  delimiter = args.delimiter
  secondsBetweenAPIRequests = args.wait
  identifierColumnName = args.column_name_lookup_identifier

  with open(args.input_file, 'r') as inFile, \
       open(args.output_file, 'w') as outFile:


    # Count some stats and reset the file pointer afterwards
    countReader = csv.DictReader(inFile, delimiter=delimiter)

    # the CSV should at least contain columns for the ISNI identifier and the local identifier we want to enrich
    minNeededColumns = [identifierColumnName] + list(dataFields.keys())
    lib.checkIfColumnsExist(countReader.fieldnames, minNeededColumns)

    counters = lib.initializeCounters(countReader, dataFields, identifierColumnName)
    inFile.seek(0, 0)
    
    numberRowsAtLeastOneIdentifierMissing = counters['numberRowsMissingAtLeastOneIdentifier']
    inputRowCountAll = counters['numberRows']
    inputRowCountISNI = counters['numberRowsHaveISNI']
    isniPercentage = (inputRowCountISNI*100)/inputRowCountAll
    print()
    print(f'In total, the file contains {inputRowCountAll} lines from which {inputRowCountISNI} have an ISNI ({isniPercentage:.2f}%)')
    for column, isniSourceName in dataFields.items():
      inputRowCountMissing = counters[isniSourceName]['numberMissingIdentifierRows']
      inputRowCountMissingAndISNI = counters[isniSourceName]['numberRowsToBeEnrichedHaveISNI']
      missingPercentage = (inputRowCountMissing*100)/inputRowCountAll
      print(f'Stats for column "{column}" that should be enriched via "{isniSourceName}" field from the ISNI database')
      print(f'{inputRowCountMissing} {isniSourceName} identifiers are missing and we want to get them ({missingPercentage:.2f}%).')
      if inputRowCountMissing > 0:
        missingChancePercentage = (inputRowCountMissingAndISNI*100)/inputRowCountMissing
        print(f'From those {inputRowCountMissing} missing, we could enrich {inputRowCountMissingAndISNI}, because they have an ISNI ({missingChancePercentage:.2f}%)')
      print()
    print()

    inputReader = csv.DictReader(inFile, delimiter=delimiter)


    outputWriter = csv.DictWriter(outFile, fieldnames=inputReader.fieldnames)
    outputWriter.writeheader()

    # the payload for each request (the actual query will be appended for each request)
    payload = config.getPayload(apiName)
    payload['recordSchema'] = recordSchema
    url = config.getURL(apiName)

    skippedRows = 0
    # instantiating tqdm separately, such that we can add a description
    # The total number of lines is the one we have to make requests for
    requestLog = tqdm(position=0, total=numberRowsAtLeastOneIdentifierMissing)

    for row in inputReader:

      # we are not interested in rows that already have values for identifier we look for
      if not lib.atLeastOneIdentifierMissing(row, minNeededColumns):
        skippedRows += 1

        # write the input as-is to the output and stop processing of this row
        outputWriter.writerow(row)
        continue

      # if there is no ISNI there is also nothing we can do
      isniRaw = row[identifierColumnName]
      if isniRaw == '':
        outputWriter.writerow(row)
        continue
      else:
        isniList = isniRaw.split(';') if ';' in isniRaw else [isniRaw]

      # update the progress bar description
      descriptions = []
      for identifierColumn, identifierNameISNI in dataFields.items():
        descriptions.append(f'{identifierNameISNI} ' + str(counters[identifierNameISNI]['numberFoundISNIRows']))
      requestLog.set_description(f'found ' + ','.join(descriptions))

      foundIdentifiers = {}
      rowAlreadyProcessed = False
      for isni in isniList:

        # request the record for the found ISNI
        payload['query'] = f'{query} "{isni}"'
        xmlRecord = lib.requestRecord(url, payload)

        if not xmlRecord:
          outputWriter.writerow(row)
          requestLog.update(1)
          continue

        # extract information for each needed identifier
        for identifierColumn, identifierNameISNI in dataFields.items():
          # Only enrich it when the currently looked for identifier is missing
          # note: in the future we could think of an 'update' functionality
          if row[identifierColumn] == '':
      
            datafieldDefinition = config.getDatafieldDefinition(apiName, recordSchema, identifierNameISNI)
            foundIdentifier = lib.extractIdentifier(xmlRecord, identifierNameISNI, datafieldDefinition)

            if foundIdentifier:
              if not rowAlreadyProcessed:
                counters[identifierNameISNI]['numberFoundISNIRows'] += 1
                rowAlreadyProcessed = True

              if identifierNameISNI in foundIdentifiers: 
                foundIdentifiers[identifierNameISNI].add(lib.getPrefixedIdentifier(foundIdentifier, identifierNameISNI))
              else:
                foundIdentifiers[identifierNameISNI] = set([lib.getPrefixedIdentifier(foundIdentifier, identifierNameISNI)])
              counters[identifierNameISNI]['numberFoundISNIs'] += 1

      for identifierColumn, identifierNameISNI in dataFields.items():
        # we can only add something if we found something
        if identifierNameISNI in foundIdentifiers:
          currentValue = row[identifierColumn]
          row[identifierColumn] = ';'.join(foundIdentifiers[identifierNameISNI])
      requestLog.update(1)


      outputWriter.writerow(row)
      time.sleep(secondsBetweenAPIRequests)

  for identifierColumn, identifierNameISNI in dataFields.items():
    counterFound = counters[identifierNameISNI]['numberFoundISNIRows']
    inputRowCountMissingAndISNI = counters[isniSourceName]['numberRowsToBeEnrichedHaveISNI']
    counterFoundISNI = counters[identifierNameISNI]['numberFoundISNIs']
    if inputRowCountMissingAndISNI > 0:
      percentage = (counterFound*100)/inputRowCountMissingAndISNI
      print()
      print(f'{counterFound} from possible {inputRowCountMissingAndISNI} records ({percentage:.2f}%) could be enriched with {identifierNameISNI} identifiers!')
      print(f'(In total {counterFoundISNI} were found (this number might be higher, because there can be more than one ISNI per row)')
      print()
    else:
      print()
      print(f'{identifierNameISNI}: No missing values that would have an ISNI')

main()
