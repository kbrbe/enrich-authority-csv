import urllib
import requests
import xml.etree.ElementTree as ET

NS_SRW = 'http://www.loc.gov/zing/srw/'
NS_MARC_EXCHANGE = 'info:lc/xmlns/marcxchange-v2'
ALL_NS = {'srw': NS_SRW, 'mxc': NS_MARC_EXCHANGE}


# -----------------------------------------------------------------------------
def getBnFIdentifierWithControlCharacter(identifier):
  """This function computes the BnF control character based on documentation from BnF.

  It correctly works for the two following real life examples
  >>> getBnFIdentifierWithControlCharacter('cb13741679')
  'cb13741679s'
  >>> getBnFIdentifierWithControlCharacter('cb11896963')
  'cb11896963c'

  Also return the correct control character if the 'cb' prefix is missing
  >>> getBnFIdentifierWithControlCharacter('11896963')
  'cb11896963c'

  Return the same identifier if there is already a valid control character
  >>> getBnFIdentifierWithControlCharacter('cb11896963c')
  'cb11896963c'

  Return a corrected identifier if the given control character is wrong
  >>> getBnFIdentifierWithControlCharacter('cb11896963d')
  'cb11896963c'

  Throw an error if the identifier is too short
  >>> getBnFIdentifierWithControlCharacter('cb118969c')
  Traceback (most recent call last):
      ...
  Exception: Invalid BnF identifier, too short: cb118969c

  Throw an error if the identifier is too long
  >>> getBnFIdentifierWithControlCharacter('cb118969631c')
  Traceback (most recent call last):
      ...
  Exception: Invalid BnF identifier, too long: cb118969631c
  """

  correspondenceTable = ['0','1','2','3','4','5','6','7','8',
                         '9','b','c','d','f','g','h','j','k',
                         'm','n','p','q','r','s','t','v','w',
                         'x','z']

  # make sure the identifier starts with 'cb'
  identifier = f'cb{identifier}' if not identifier.startswith('cb') else identifier

  if len(identifier) == 11:
    # perfect length, so there seems to be already a control character
    # don't trust it, to be sure compute the control character again
    return getBnFIdentifierWithControlCharacter(identifier[0:10])
  elif len(identifier) > 11:
    # this identifier is too long for being a BnF identifier
    raise Exception(f'Invalid BnF identifier, too long: {identifier}')
  elif len(identifier) < 10:
    # this identifier is too short for being a BnF identifier
    raise Exception(f'Invalid BnF identifier, too short: {identifier}')

  values = []
  position = 1
  for digit in identifier:
    digitBase10Value = correspondenceTable.index(digit)
    values.append(digitBase10Value * position)
    position += 1
  sumMod29 = sum(values)%29
  return identifier + str(correspondenceTable[sumMod29])

# -----------------------------------------------------------------------------
def checkIfColumnsExist(inputColumnNames, outputColumnNames):
    """This function checks if all names of the second list are present in the first, if not an Error is raised.

    The function simply returns true if all names are present
    >>> checkIfColumnsExist(['a', 'b', 'c'], ['a', 'c'])
    True

    If a name is missing an Exception is thrown mentioning which names are missing
    >>> checkIfColumnsExist(['a', 'b', 'c'], ['a', 'd'])
    Traceback (most recent call last):
        ...
    Exception: The following requested column is not in the input: {'d'}
    """
    inputColumns = set(inputColumnNames)
    outputColumns = set(outputColumnNames)
    nonExistentColumns = outputColumns.difference(inputColumns)
    if len(nonExistentColumns) > 0:
      text = 'columns are' if len(nonExistentColumns) > 1 else 'column is'
      raise Exception(f'The following requested {text} not in the input: {nonExistentColumns}')
    else:
        return True

# -----------------------------------------------------------------------------
def getElementValue(elem, sep=';'):
  """This function returns the value of the element if it is not None, otherwise an empty string.

  The function returns the 'text' value if there is one
  >>> class Test: text = 'hello'
  >>> obj = Test()
  >>> getElementValue(obj)
  'hello'

  It returns nothing if there is no text value
  >>> class Test: pass
  >>> obj = Test()
  >>> getElementValue(obj)
  ''

  And the function returns a semicolon separated list in case the argument is a list of objects with a 'text' attribute
  >>> class Test: text = 'hello'
  >>> obj1 = Test()
  >>> obj2 = Test()
  >>> getElementValue([obj1,obj2])
  'hello;hello'
  """
  if elem is not None:
    if isinstance(elem, list):
      valueList = list()
      for e in elem:
        if hasattr(e, 'text'):
          valueList.append(e.text)
      return ';'.join(valueList)
    else:
      if hasattr(elem, 'text'):
        return elem.text
  
  return ''

# -----------------------------------------------------------------------------
def atLeastOneIdentifierMissing(row, columnNames):
  """This function returns true if at least one of the given columns are empty.
  >>> atLeastOneIdentifierMissing({'kbrIDs': '', 'ntaIDs':''}, ['kbrIDs', 'ntaIDs'])
  True
  >>> atLeastOneIdentifierMissing({'kbrIDs': '123', 'ntaIDs':''}, ['kbrIDs', 'ntaIDs'])
  True
  >>> atLeastOneIdentifierMissing({'kbrIDs': '123', 'ntaIDs':'456'}, ['kbrIDs', 'ntaIDs'])
  False
  """
  
  relevantValues = [row[c] for c in columnNames]
  return True if any([True for v in relevantValues if v == '' ]) else False


# -----------------------------------------------------------------------------
def countISNIs(isniString, delimiter=';', validateISNI=False):
  """Counts how many ISNIs are in the delimited string.

  An empty string should be counted as 0 ISNIs
  >>> countISNIs('')
  0

  One ISNI should be counted
  >>> countISNIs('0000000000000001')
  1
  
  Multiple ISNI values should be counted
  >>> countISNIs('0000000000000001;0000000000000002')
  2

  Multiple value should be counted, in default even if not valid ISNIs
  >>> countISNIs('001;002')
  2

  If something does not seem like an ISNI (currently only checking for length) an exception is thrown
  >>> countISNIs('0001', validateISNI=True)
  Traceback (most recent call last):
   ...
  Exception: Invalid ISNI: "0001"

  >>> countISNIs('000000000001;002', validateISNI=True)
  Traceback (most recent call last):
   ...
  Exception: Invalid ISNI: "000000000001"
  
  """
  if isniString == '':
    return 0
  isniList = isniString.split(delimiter)
  if validateISNI:
    for isni in isniList:
      if len(isni) != 16:
        raise Exception(f'Invalid ISNI: "{isni}"')
  else:
    return len(isniList)



# -----------------------------------------------------------------------------
def initializeCounters(countReader, identifiers, isniColumnName, nationalityColumnName=None):
  """This function counts statistics from the given arra of dicts (or DictReader).

  >>> rows = [{'kbrIDs':'', 'isniIDs':'001','ntaIDs':''},
  ... {'kbrIDs':'123', 'isniIDs':'', 'ntaIDs':''},
  ... {'kbrIDs':'', 'ntaIDs':'', 'isniIDs':''},
  ... {'kbrIDs':'','ntaIDs':'','isniIDs':'002;003'},
  ... {'kbrIDs':'123','ntaIDs':'456','isniIDs':'002;003'}]
  >>> initializeCounters(rows, {'kbrIDs':'KBR', 'ntaIDs':'NTA'}, 'isniIDs')
  {'numberRows': 5, 'numberRowsHaveISNI': 3, 'numberISNIs': 5, 'numberRowsMissingAtLeastOneIdentifier': 4, 'KBR': {'numberMissingIdentifierRows': 3, 'numberISNIs': 5, 'numberRowsToBeEnrichedHaveISNI': 2, 'numberRowsThatCannotBeEnriched': 1}, 'NTA': {'numberMissingIdentifierRows': 4, 'numberISNIs': 5, 'numberRowsToBeEnrichedHaveISNI': 2, 'numberRowsThatCannotBeEnriched': 2}}
  """

  # initialize counters
  counters = {'numberRows': 0, 'numberRowsHaveISNI': 0, 'numberISNIs': 0, 'numberRowsMissingAtLeastOneIdentifier': 0}
  for column, isniSourceName in identifiers.items():
    counters[isniSourceName] = {
      'numberMissingIdentifierRows': 0,
      'numberISNIs': 0,
      'numberRowsToBeEnrichedHaveISNI': 0,
      'numberRowsThatCannotBeEnriched': 0,
      'numberFoundISNIRows': 0,
      'numberFoundISNIs': 0
    }
  

  identifierColumns = identifiers.keys()
  for row in countReader:

    # do some general counting for the row
    counters['numberRows'] += 1
    counters['numberISNIs'] += countISNIs(row[isniColumnName])
    if atLeastOneIdentifierMissing(row, identifierColumns):
      counters['numberRowsMissingAtLeastOneIdentifier'] += 1

    if row[isniColumnName] != '':
        counters['numberRowsHaveISNI'] += 1

    # count for the specific identifiers we want to add via ISNI
    for columnName, isniSourceName in identifiers.items():

      counters[isniSourceName]['numberISNIs'] += countISNIs(row[isniColumnName])
      # the identifier column is empty, a possible candidate to be enriched
      if row[columnName] == '':
        counters[isniSourceName]['numberMissingIdentifierRows'] += 1

        # If there is also an ISNI there is the chance that we can enrich it
        if row[isniColumnName] == '':
          counters[isniSourceName]['numberRowsThatCannotBeEnriched'] += 1
        else:
          counters[isniSourceName]['numberRowsToBeEnrichedHaveISNI'] += 1

  return counters

# -----------------------------------------------------------------------------
def getPrefixedIdentifier(identifier, identifierName):
  if identifierName == 'NTA':
    return f'p{identifier}'
  elif identifierName == 'BNF':
    return getBnFIdentifierWithControlCharacter(identifier)
  else:
    return identifier




# -----------------------------------------------------------------------------
def extractIdentifier(xmlContent, datafieldName, datafieldDefinition, delimiter=';'):
  """This function tries to extract the identifier with the given name. If not found it returns None."""

  root = ET.fromstring(xmlContent)

  foundData = set()
  datafieldType = datafieldDefinition['type']
  if datafieldType == 'element':
    for record in root.findall(datafieldDefinition['path'], ALL_NS):
      foundData.add(record.text)
    return delimiter.join(sorted(foundData))

  elif datafieldType == 'identifier':
    for record in root.findall(datafieldDefinition['path'], ALL_NS):
      sourceName = getElementValue(record.find(datafieldDefinition['identifierCodeSubpath']))
      identifier = getElementValue(record.find(datafieldDefinition['identifierNameSubpath']))

      if datafieldName == sourceName:
        return identifier
  else:
    print(f'undefined datafield type "{datafieldType}"')


  # if this statement is reached nothing was found so we return None
  return None

# -----------------------------------------------------------------------------
def requestRecord(url, payload):

  try: 
    payloadStr = urllib.parse.urlencode(payload, safe=',+*\\')
    r = requests.get(url, params=payloadStr)
    r.raise_for_status()

    return r.content

  except requests.exceptions.Timeout:
    print(f'There was a timeout in iteration for url "{url}" and payload "{payloadStr}"')
  except requests.exceptions.TooManyRedirects:
    print(f'There were too many redirects in iteration for url "{url}" and payload "{payloadStr}"')
  except requests.exceptions.HTTPError as err:
    print(f'There was an HTTP response code which is not 200 for url "{url}" and payload "{payloadStr}"')
    print(err)
  except requests.exceptions.RequestException as e:
    print(f'There was an exception in the request')
  except Exception as e:
    print(f'There was a general exception!')
    print(e)

# -----------------------------------------------------------------------------
def verifyTask(config, apiName, recordSchema, requestedDataFields):

  # Do we even have information about the requested API?
  config.checkEndpointExistence(apiName)

  # Do we have specifications for the requested record schema?
  config.checkRecordSchemaExistence(apiName, recordSchema)

  atLeastOneException = False
  for columnName, datafield in requestedDataFields.items():

    # Do we have a datafield specification for the given record schema?
    # print possible exceptions and continue checking
    try:
      config.checkDatafieldExistence(apiName, recordSchema, datafield)

      # TODO
      # check based on a possible JSONSchema if the structure of the datafield is correct

    except Exception as e:
      atLeastOneException = True
      print(e)

  if atLeastOneException:
    raise Exception(f'There have been issues with the requested datafields and the specified APIs')

# -----------------------------------------------------------------------------
if __name__ == "__main__":
  import doctest
  doctest.testmod()
