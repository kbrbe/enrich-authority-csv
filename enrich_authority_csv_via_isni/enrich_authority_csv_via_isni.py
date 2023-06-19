import os
import csv
from dotenv import load_dotenv
import lib
import time
from tqdm import tqdm
from argparse import ArgumentParser

     
# -----------------------------------------------------------------------------
def main():

  parser = ArgumentParser(description='This script reads a CSV file and requests for each found ISNI identifier (in the column specified with --column-name-isni) the identifier(s) specified with --identifier')
  parser.add_argument('-i', '--input-file', action='store', required=True, help='A CSV file that contains records about contributors')
  parser.add_argument('-o', '--output-file', action='store', required=True, help='The CSV file in which the enriched records are stored')
  parser.add_argument('--identifiers', metavar='KEY=VALUE', required=True, nargs='+', help='A key value pair where the key is the name of the identifier column in the input that should be fetched and the value is the name of the identifier as stated in the ISNI database.')
  parser.add_argument('--column-name-isni', action='store', required=True, help='The name of the column in the input file that contains the ISNI identifier to lookup')
  parser.add_argument('--wait', action='store', type=float, default = 1, help='The number of seconds to wait in between API requests')
  parser.add_argument('-d', '--delimiter', action='store', default=',', help='The delimiter of the input CSV')
  args = parser.parse_args()


  #
  # load environment variables from .env file
  #
  load_dotenv()

  USERNAME = os.getenv('ISNI_SRU_USERNAME')
  PASSWORD = os.getenv('ISNI_SRU_PASSWORD')

  delimiter = args.delimiter
  secondsBetweenAPIRequests = args.wait
  isniColumnName = args.column_name_isni
  identifiers = dict(map(lambda s: s.split('='), args.identifiers))

  with open(args.input_file, 'r') as inFile, \
       open(args.output_file, 'w') as outFile:


    # Count some stats and reset the file pointer afterwards
    countReader = csv.DictReader(inFile, delimiter=delimiter)

    # the CSV should at least contain columns for the ISNI identifier and the local identifier we want to enrich
    minNeededColumns = [isniColumnName] + list(identifiers.keys())
    lib.checkIfColumnsExist(countReader.fieldnames, minNeededColumns)

    counters = lib.initializeCounters(countReader, identifiers, isniColumnName)
    inFile.seek(0, 0)
    
    numberRowsAtLeastOneIdentifierMissing = counters['numberRowsMissingAtLeastOneIdentifier']
    inputRowCountAll = counters['numberRows']
    inputRowCountISNI = counters['numberRowsHaveISNI']
    isniPercentage = (inputRowCountISNI*100)/inputRowCountAll
    print()
    print(f'In total, the file contains {inputRowCountAll} lines from which {inputRowCountISNI} have an ISNI ({isniPercentage:.2f}%)')
    for column, isniSourceName in identifiers.items():
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
    payload = {'operation': 'searchRetrieve', 'version': '1.1', 'recordSchema': 'isni-e', 'sortKeys': 'none'}
    baseURL = 'https://isni-m.oclc.org/sru'
    url = f'{baseURL}/username={USERNAME}/password={PASSWORD}/DB=1.3'

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
      isniRaw = row[isniColumnName]
      if isniRaw == '':
        outputWriter.writerow(row)
        continue
      else:
        isniList = isniRaw.split(';') if ';' in isniRaw else [isniRaw]

      # update the progress bar description
      descriptions = []
      for identifierColumn, identifierNameISNI in identifiers.items():
        descriptions.append(f'{identifierNameISNI} ' + str(counters[identifierNameISNI]['numberFoundISNIRows']))
      requestLog.set_description(f'found ' + ','.join(descriptions))

      foundIdentifiers = {}
      rowAlreadyProcessed = False
      for isni in isniList:

        # request the record for the found ISNI
        query = f'pica.isn = "{isni}"'
        payload['query'] = query
        xmlRecord = lib.requestRecord(url, payload)

        # extract information for each needed identifier
        for identifierColumn, identifierNameISNI in identifiers.items():
          # Only enrich it when the currently looked for identifier is missing
          # note: in the future we could think of an 'update' functionality
          if row[identifierColumn] == '':
      
            foundIdentifier = lib.extractIdentifier(xmlRecord, identifierNameISNI)

            if foundIdentifier:
              if not rowAlreadyProcessed:
                counters[identifierNameISNI]['numberFoundISNIRows'] += 1
                rowAlreadyProcessed = True

              if identifierNameISNI in foundIdentifiers: 
                foundIdentifiers[identifierNameISNI].add(lib.getPrefixedIdentifier(foundIdentifier, identifierNameISNI))
              else:
                foundIdentifiers[identifierNameISNI] = set([lib.getPrefixedIdentifier(foundIdentifier, identifierNameISNI)])
              counters[identifierNameISNI]['numberFoundISNIs'] += 1

      for identifierColumn, identifierNameISNI in identifiers.items():
        # we can only add something if we found something
        if identifierNameISNI in foundIdentifiers:
          currentValue = row[identifierColumn]
          row[identifierColumn] = ';'.join(foundIdentifiers[identifierNameISNI])
      requestLog.update(1)


      outputWriter.writerow(row)
      time.sleep(secondsBetweenAPIRequests)

  for identifierColumn, identifierNameISNI in identifiers.items():
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
