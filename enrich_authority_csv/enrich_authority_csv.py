import os
import csv
from dotenv import load_dotenv
from enrich_authority_csv.config_parser import ConfigParser
import enrich_authority_csv.lib as lib
import time
from tqdm import tqdm
from argparse import ArgumentParser

     
# -----------------------------------------------------------------------------
def parseArguments():
  parser = ArgumentParser(description='This script reads a CSV file and requests for each found lookup identifier (in the column specified with --column-name-lookup-identifier) the datafields specified with --data')
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

  return args

# -----------------------------------------------------------------------------
def main(configFile, inputFile, outputFile, apiName, query, recordSchema, dataFields, delimiter, secondsBetweenAPIRequests, identifierColumnName):


  config = ConfigParser(configFile)


  # check if the requested data can be fetched based on the given API config
  lib.verifyTask(config, apiName, recordSchema, dataFields)



  with open(inputFile, 'r') as inFile, \
       open(outputFile, 'w') as outFile:


    # Count some stats and reset the file pointer afterwards
    countReader = csv.DictReader(inFile, delimiter=delimiter)

    # the CSV should at least contain columns for the lookup identifier and the local datafields we want to enrich
    minNeededColumns = [identifierColumnName] + list(dataFields.keys())
    lib.checkIfColumnsExist(countReader.fieldnames, minNeededColumns)

    counters = lib.initializeCounters(countReader, dataFields, identifierColumnName)
    inFile.seek(0, 0)
    
    numberRowsAtLeastOneDatafieldMissing = counters['numberRowsMissingAtLeastOneIdentifier']
    inputRowCountAll = counters['numberRows']
    inputRowCountHaveLookupIdentifier = counters['numberRowsHaveISNI']
    rowsWithLookupIdentifierPercentage = (inputRowCountHaveLookupIdentifier*100)/inputRowCountAll
    inputRowCountEmptyAndPossibleToEnrich = counters['numberRowsMissingAndPossibleToBeEnriched']
    print()
    print(f'In total, the file contains {inputRowCountAll} lines from which {inputRowCountHaveLookupIdentifier} contain the identifier to lookup ({rowsWithLookupIdentifierPercentage:.2f}%)')
    print()
    for column, remoteFieldName in dataFields.items():
      inputRowCountMissing = counters[remoteFieldName]['numberMissingIdentifierRows']
      inputRowCountFieldMissingAndLookupIdentifier = counters[remoteFieldName]['numberRowsToBeEnrichedHaveISNI']
      missingPercentage = (inputRowCountMissing*100)/inputRowCountAll
      print(f'Stats for column "{column}" that should be enriched via "{remoteFieldName}" field from the remote SRU API')
      print(f'{inputRowCountMissing} {remoteFieldName} values are missing and we want to get them ({missingPercentage:.2f}%).')
      if inputRowCountMissing > 0:
        missingChancePercentage = (inputRowCountFieldMissingAndLookupIdentifier*100)/inputRowCountMissing
        print(f'From those {inputRowCountMissing} missing, we could enrich {inputRowCountFieldMissingAndLookupIdentifier}, because they have a lookup identifier ({missingChancePercentage:.2f}%)')
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
    requestLog = tqdm(position=0, total=inputRowCountEmptyAndPossibleToEnrich)

    for row in inputReader:

      # we are not interested in rows that already have values for identifier we look for
      if not lib.atLeastOneIdentifierMissing(row, minNeededColumns):
        skippedRows += 1

        # write the input as-is to the output and stop processing of this row
        outputWriter.writerow(row)
        continue

      # if there is no lookup identifier there is also nothing we can do
      identifierRaw = row[identifierColumnName]
      if identifierRaw == '':
        outputWriter.writerow(row)
        continue
      else:
        lookupIdentifierList = identifierRaw.split(';') if ';' in identifierRaw else [identifierRaw]

      # update the progress bar description
      descriptions = []
      for identifierColumn, lookupIdentifier in dataFields.items():
        descriptions.append(f'{lookupIdentifier} ' + str(counters[lookupIdentifier]['numberFoundISNIRows']))
      requestLog.set_description(f'found ' + ','.join(descriptions))

      foundIdentifiers = {}
      rowAlreadyProcessed = False
      for lookupIdentifier in lookupIdentifierList:

        # request the record for the found identifier
        payload['query'] = f'{query} "{lookupIdentifier}"'
        xmlRecord = lib.requestRecord(url, payload)

        if not xmlRecord:
          outputWriter.writerow(row)
          requestLog.update(1)
          continue

        # extract information for each needed identifier
        for identifierColumn, lookupIdentifierName in dataFields.items():
          # Only enrich it when the currently looked for identifier is missing
          # note: in the future we could think of an 'update' functionality
          if row[identifierColumn] == '':
      
            datafieldDefinition = config.getDatafieldDefinition(apiName, recordSchema, lookupIdentifierName)
            foundIdentifier = lib.extractIdentifier(xmlRecord, lookupIdentifierName, datafieldDefinition)

            if foundIdentifier:
              if not rowAlreadyProcessed:
                counters[lookupIdentifierName]['numberFoundISNIRows'] += 1
                rowAlreadyProcessed = True

              if lookupIdentifierName in foundIdentifiers: 
                foundIdentifiers[lookupIdentifierName].add(lib.getPrefixedIdentifier(foundIdentifier, lookupIdentifierName))
              else:
                foundIdentifiers[lookupIdentifierName] = set([lib.getPrefixedIdentifier(foundIdentifier, lookupIdentifierName)])
              counters[lookupIdentifierName]['numberFoundISNIs'] += 1

      for identifierColumn, lookupIdentifierName in dataFields.items():
        # we can only add something if we found something
        if lookupIdentifierName in foundIdentifiers:
          currentValue = row[identifierColumn]
          row[identifierColumn] = ';'.join(foundIdentifiers[lookupIdentifierName])
      requestLog.update(1)


      outputWriter.writerow(row)
      time.sleep(secondsBetweenAPIRequests)

  for identifierColumn, lookupIdentifierName in dataFields.items():
    counterFound = counters[lookupIdentifierName]['numberFoundISNIRows']
    inputRowCountMissingFieldHavingLookupIdentifier = counters[lookupIdentifierName]['numberRowsToBeEnrichedHaveISNI']
    counterFoundIdentifier = counters[lookupIdentifierName]['numberFoundISNIs']
    if inputRowCountMissingFieldHavingLookupIdentifier > 0:
      percentage = (counterFound*100)/inputRowCountMissingFieldHavingLookupIdentifier
      print()
      print(f'{counterFound} from possible {inputRowCountMissingFieldHavingLookupIdentifier} records ({percentage:.2f}%) could be enriched with {lookupIdentifierName}-values from the SRU API!')
      print(f'(In total {counterFoundIdentifier} were found (this number might be higher, because there can be more than one lookup identifier per row)')
      print()
    else:
      print()
      print(f'{lookupIdentifierName}: No missing values that would have a lookup identifier. So there is nothing to enrich')

if __name__ == '__main__':
  args = parseArguments()
  dataFields = dict(map(lambda s: s.split('='), args.data))
  main(args.config, args.input_file, args.output_file, args.api, args.query, args.record_schema, dataFields, args.delimiter, args.wait, args.column_name_lookup_identifier)
