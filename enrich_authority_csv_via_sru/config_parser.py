import json
import os
from dotenv import load_dotenv
from string import Template

class ConfigParser:
  """An instance of this class can be used to access the configuration."""

  def __init__(self, filename):
    with open(filename, 'r') as inFile:
      self.config = json.load(inFile)

 
  # ---------------------------------------------------------------------------
  def containsEndpoint(self, endpoint):
    return True if endpoint in self.config['apis'].keys() else False

  def checkEndpointExistence(self, endpoint):
    if not self.containsEndpoint(endpoint):
      raise Exception(f'API "{endpoint}" not specified in provided config!')

  # ---------------------------------------------------------------------------
  def containsRecordSchemaDefinition(self, endpoint, recordSchema):
    self.checkEndpointExistence(endpoint)
    return True if recordSchema in self.config['apis'][endpoint]['data'].keys() else False

  def checkRecordSchemaExistence(self, endpoint, recordSchema):
    self.checkEndpointExistence(endpoint)
    if not self.containsRecordSchemaDefinition(endpoint, recordSchema):
      possibleSchemas = self.config['apis'][endpoint]['data'].keys()
      raise Exception(f'Record schema "{recordSchema}" not specified for API "{apiName}", possible values are {possibleSchemas}')


  def containsDatafieldDefinition(self, endpoint, recordSchema, datafield):
    self.checkRecordSchemaExistence(endpoint, recordSchema)
    return True if datafield in self.config['apis'][endpoint]['data'][recordSchema].keys() else False

  def getDatafieldNames(self, endpoint, recordSchema):
    self.checkRecordSchemaExistence(endpoint, recordSchema)
    return config['apis'][endpoint]['data'][recordSchema].keys()

  def checkDatafieldExistence(self, endpoint, recordSchema, datafield):
    self.checkRecordSchemaExistence(endpoint, recordSchema)
    if not self.containsDatafieldDefinition(endpoint, recordSchema, datafield):
      possibleFields = self.getDatafieldNames()
      raise Exception(f'Datafield "{datafield}" not specified for recordSchema "{recordSchema}" for API "{endpoint}", possible values are {possibleFields}')

  def getRecordSchemas(self, endpoint):
    self.checkEndpointExistence(endpoint)
    return self.config['apis'][endpoint]['data'].keys()

  # ---------------------------------------------------------------------------
  def getDatafieldDefinition(self, endpoint, recordSchema, datafield):
    """This function returns the definition of the specified datafield."""
    self.checkRecordSchemaExistence(endpoint, recordSchema)
    datafields = self.config['apis'][endpoint]['data'][recordSchema]
    if datafield in datafields:
      return datafields[datafield]
    else:
      raise Exception(f'Cannot find a definition for datafield "{datafield}" for record schema "{recordSchema}" for API "{endpoint}"')

  def getDatafieldDefinitions(self, endpoint, recordSchema):
    """This function returns definitions of all datafields."""
    self.checkRecordSchemaExistence(endpoint, recordSchema)
    return self.config['apis'][endpoint]['data'][recordSchema]
    
  def getURL(self, endpoint):
    """This function returns the URL of the API, if it is an API that requires authentication via the URL, the URL is built based on available information from the config and environment variables."""
    self.checkEndpointExistence(endpoint)

    connectionInfo = self.config['apis'][endpoint]['connection']
    connectionType = connectionInfo['type']
    if connectionType == "unauthenticated":
      return connectionInfo['url']
    elif connectionType == "authenticated":
      # we need to build a URL that contains username/password information from environment variables
      load_dotenv()
      username = os.getenv(connectionInfo['userVariable'])
      password = os.getenv(connectionInfo['passwordVariable'])
      urlPattern = Template(connectionInfo['url'])
      return urlPattern.substitute(userVariable=username, passwordVariable=password)
    else:
      raise Exception(f'Unrecognized connection type "{connectionType}"')
  
  def getPayload(self, endpoint):
    self.checkEndpointExistence(endpoint)

    if 'connection' not in self.config['apis'][endpoint] \
      or 'payload' not in self.config['apis'][endpoint]['connection']:
      raise Exception(f'No connection or no payload within the connection for API "{endpoint}"')
    else:
      return self.config['apis'][endpoint]['connection']['payload']

