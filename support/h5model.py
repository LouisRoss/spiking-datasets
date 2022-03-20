import sys
import scipy.stats as stats
import random
import math
import json
import requests
from support.h5Rest import h5Rest

class h5model:
  rootId = None
  groups = {}
  datasets = {}
  modelName = ""
  populationDatasetId = None
  templatesGroupId = None
  expansionsGroupId = None
  configuration = None
  responseStatus = 200
  responseSuccessPayload = ""
  errorMessage = ""
  restManager = None

  def __init__(self, modelName):
    self.restManager = h5Rest(modelName)
    self.modelName = modelName
    self.failureReason = ""

    f = open('/configuration/configuration.json')
    self.configuration = json.load(f)

    # When enumerating models, we can be created with an empty model name.  This is ok.
    if (len(modelName) > 0):
      modelRest = self.restManager.getRest("", True)
      if modelRest.status_code == 200:
        self.rootId = modelRest.json()['root']

        rootGroupRest = self.restManager.getRest("/groups/" + self.rootId + "/links", True)
        if rootGroupRest.status_code == 200:
          rootGroup = rootGroupRest.json()
          rootTemplatesLink = next((x for x in rootGroup["links"] if x["title"] == "templates"), None)
          self.templatesGroupId = rootTemplatesLink["id"] if rootTemplatesLink else None
          rootExpansionsLink = next((x for x in rootGroup["links"] if x["title"] == "expansions"), None)
          self.expansionsGroupId = rootExpansionsLink["id"] if rootExpansionsLink else None
          rootPopulationLink = next((x for x in rootGroup["links"] if x["title"] == "population"), None)
          self.populationDatasetId = rootPopulationLink["id"] if rootPopulationLink else None


  def getExistingModels(self):
    """ Enumerate all existing model files.
    """
    # Get the starting REST response, extract the group base element.
    groupBaseRest = self.restManager.getRest("")
    if groupBaseRest.status_code != 200:
      self.errorMessage = "Starting REST response contains no root link"
      responseStatus = 500
      return

    # Get the group base root links REST response, extract the list of domain links.
    # NOTE: domains in H5serv are individual files, which represent individual models.
    rootId = groupBaseRest.json()["root"]
    rootLinkRest = self.restManager.getRest("/groups/" + rootId + "/links")
    if rootLinkRest.status_code != 200:
      self.errorMessage = "Root link REST response contains no sub-links"
      responseStatus = 500
      return

    domainLinks = rootLinkRest.json()["links"]

    #print([x["title"] for x in domainLinks])
    self.responseSuccessPayload = [domainLink for domainLink in domainLinks if not '_deployments' in domainLink['title']]
    self.responseStatus = 200

  def initializeModel(self):
    """ Immediately after a new model file is created, it must be initialized here.
    """

    # Create the population dataset at the root.  This is a strigified Json object with information about all templates in the model.
    populationData = {
      "type": {
          "class": "H5T_STRING",
          "length": "H5T_VARIABLE",
          "charSet": "H5T_CSET_ASCII",
          "strpad": "H5T_STR_NULLTERM"
      },
      "shape": [1],
      "link": {
          "id": self.rootId,
          "name": "population"
      }
    }

    dataSetRest = self.restManager.postRest('/datasets', json.dumps(populationData), True)
    if dataSetRest.status_code != 201:
      self.errorMessage = "Unable add 'population' dataset to Model file for '" + self.modelName
      self.responseStatus = 503
      return

    dataSetResponse = dataSetRest.json()
    self.populationDatasetId = dataSetResponse["id"]

    # Create the templates group as a subgroup of the root.
    data = { 'link': { 'id': self.rootId, 'name': 'templates' }}
    responseRest = self.restManager.postRest('/groups', json.dumps(data), True)
    if not responseRest.ok:
      self.failureReason = "Unable to create 'templates' group for model '" + self.modelName + "': " + responseRest.reason
      self.responseStatus = 500
      return

    self.templatesGroupId = responseRest.json()["id"]

    # Create the expansions group as a subgroup of the root.
    data = { 'link': { 'id': self.rootId, 'name': 'expansions' }}
    responseRest = self.restManager.postRest('/groups', json.dumps(data), True)
    if not responseRest.ok:
      self.failureReason = "Unable to create 'expansions' group for model '" + self.modelName + "': " + responseRest.reason
      self.responseStatus = 500
      return

    self.expansionsGroupId = responseRest.json()["id"]

    # Create the maxindex attribute in the expansions group.
    data = { 'type': 'H5T_STD_I32LE', 'value': '0' }
    responseRest = self.restManager.putRest('/groups/' + self.expansionsGroupId + '/attributes/maxindex', json.dumps(data), True)
    if not responseRest.ok:
      self.failureReason = "Unable to create 'maxindex' attribute in the 'expansions' group for model '" + self.modelName + "': " + responseRest.reason
      self.responseStatus = 500
      return

    self.responseSuccessPayload = "Successfully created model '" + self.modelName + "'"
    self.responseStatus = 200


  def getExistingTemplates(self):
    """ Get a list containing the existing templates for this model.
    """
    if not self.populationDatasetId:
      self.errorMessage = "Model file for '" + self.modelName + "' is malformed, has no 'population' dataset"
      self.responseStatus = 503
      return
    
    populationRest = self.restManager.getRest("/datasets/" + self.populationDatasetId + "/value", True)
    if populationRest.status_code != 200:
      self.errorMessage = "Model file for '" + self.modelName + "' 'population' dataset contains no value"
      self.responseStatus = 503
      return

    population = populationRest.json()["value"][0]
    if len(population) == 0:
      self.responseSuccessPayload = []
    else:
      populationJson = json.loads(population)
      self.responseSuccessPayload = [template["template"] for template in populationJson["templates"]]
    self.responseStatus = 200


  def getPopulation(self):
    """ Get the defined population for this model.
    """
    if not self.populationDatasetId:
      self.errorMessage = "Model file for '" + self.modelName + "' is malformed, has no 'population' dataset"
      self.responseStatus = 503
      return
    
    populationRest = self.restManager.getRest("/datasets/" + self.populationDatasetId + "/value", True)
    if populationRest.status_code != 200:
      self.errorMessage = "Model file for '" + self.modelName + "' 'population' dataset contains no value"
      self.responseStatus = 503
      return

    population = populationRest.json()["value"][0]
    if len(population) == 0:
      self.responseSuccessPayload = []
    else:
      self.responseSuccessPayload = json.loads(population)
    self.responseStatus = 200


  def createModel(self):
    """ Create a model file for this model object.
    """

    responseRest = self.restManager.putRest("", None, True)
    if responseRest.status_code == 201:
      response = responseRest.json()
      self.rootId = response["root"]
      self.initializeModel()
      # NOTE: Leave successful payload the status to initializeModel()
      return
    elif responseRest.status_code == 409:
      self.responseSuccessPayload = 'Model ' + self.modelName + ' already exists, not creating'
      self.responseStatus = 200
      return
    else:
      self.failureReason = 'Model creating (PUT ' + self.modelName + ') failed with HTTP status ' + str(response.status_code)
      self.responseStatus = 503
      return

  def deleteModel(self):
    """ Delete the whole model file from persistent store.
    """
    deleteRest = self.restManager.deleteRest("", True)
    if deleteRest.status_code != 200:
      self.errorMessage = "Unable to delete Model '" + self.modelName + "': " + deleteRest.reason
      self.responseStatus = 503
      return

    #print(deleteRest)
    self.responseSuccessPayload = "Successfully deleted model '" + self.modelName + "'"
    self.responseStatus = 200

  def updatePopulationInModel(self, population):
    """ Update the value of the population dataset at the root of the file.
        population    A Json object containing information about all templates.
    """
    payload = { "value": json.dumps(population) }
    dataValueRest = self.restManager.putRest('/datasets/' + str(self.populationDatasetId) + '/value', json.dumps(payload), True)
    if dataValueRest.status_code != 200:
      self.errorMessage = "Unable to add population data to Model file for '" + self.modelName + "'"
      self.responseStatus = 503
      return

    self.responseSuccessPayload = "Successfully added population to model '" + self.modelName + "'"
    self.responseStatus = 201

  def compileExpansion(self, templateName, sequence):
    print('Compiling template ' + templateName + ' into model ' + self.modelName + " as sequence " + str(sequence))
    template = self.getTemplateFromModel(templateName)

    # Calculate the total neurons needed plus the starting offset and count for each population.
    nextIndex = 0
    populations = template["neurons"]
    for population in populations:
      count = 1
      for dim in population["dims"]:
        count *= dim
      population.update({ "index": nextIndex, "count": count })
      nextIndex += count

    connections = []
    for policy in template["policies"]:
      sourcePopulation = next((pop for pop in populations if pop["name"] == policy["source"]), None)
      targetPopulation = next((pop for pop in populations if pop["name"] == policy["target"]), None)
      connectionCount = int(sourcePopulation["count"] * policy["fraction"])

      start = 0
      end = 1000
      scalefactor = 1000
      mu = int(policy["mean"] * scalefactor)
      if mu < 0:
        mu *= -1
        scalefactor *= -1
      sigma = int(policy["sd"] * 1000)
      dist = stats.truncnorm((start - mu) / sigma, (end - mu) / sigma, loc=mu, scale=sigma)
      #connectionStrengths = dist.rvs(connectionCount)
      #print('Using mu=' + str(mu) + " sigma=" + str(sigma))

      for i in range(connectionCount):
        #sourceIndex = random.randrange(sourcePopulation["index"], sourcePopulation["index"] + sourcePopulation["count"])
        #targetIndex = random.randrange(targetPopulation["index"], targetPopulation["index"] + targetPopulation["count"])
        #print(' Connection: source=' + str(sourceIndex) + ' target=' + str(targetIndex) + ' strength=' + str(connectionStrengths[i] / scalefactor))
        #connections.append([sourceIndex, targetIndex, connectionStrengths[i] / scalefactor])
        sourceNeuron, targetNeurons = self.getTargetFanout(sourcePopulation, targetPopulation, policy["fanout"])
        connectionStrengths = dist.rvs(len(targetNeurons))
        connectionIndex = 0
        for targetNeuron in targetNeurons:
          connections.append([sourcePopulation["index"] + sourceNeuron, targetPopulation["index"] + targetNeuron, connectionStrengths[connectionIndex] / scalefactor])
          connectionIndex += 1

    #print(connections)
    self.addExpansionToModel(sequence, templateName, nextIndex, connections)

  def getTargetFanout(self, sourcePopulation, targetPopulation, fanout):
    sourceXMax, sourceYMax = sourcePopulation["dims"]
    sourceNeuron = [random.randrange(0, sourceXMax - 1), random.randrange(0, sourceYMax - 1)]
    sourceRatio = [sourceNeuron[0] / sourceXMax, sourceNeuron[1] / sourceYMax]


    targetMax = targetPopulation["dims"]
    targetCenter = [round(sourceRatio[0] * targetMax[0]), round(sourceRatio[1] * targetMax[1])]
    targetArea = [math.ceil(targetMax[0] * fanout), math.ceil(targetMax[1] * fanout)]
    if targetArea[0] % 2 == 0:
      targetArea[0] += 1
    if targetArea[1] % 2 == 0:
      targetArea[1] += 1

    # targetArea is now always odd, so (targetArea - 1) / 2 is an integer margin above and below targetCenter.
    targetXLimits = [int(targetCenter[0] - ((targetArea[0] - 1) / 2)), int(targetCenter[0] + ((targetArea[0] - 1) / 2) + 1)]
    if targetXLimits[0] < 0:
      targetXLimits[0] = 0
    if targetXLimits[1] > targetMax[0]:
      targetXLimits[1] = targetMax[0]

    targetYLimits = [int(targetCenter[1] - ((targetArea[1] - 1) / 2)), int(targetCenter[1] + ((targetArea[1] - 1) / 2) + 1)]
    if targetYLimits[0] < 0:
      targetYLimits[0] = 0
    if targetYLimits[1] > targetMax[1]:
      targetYLimits[1] = targetMax[1]

    #targetXMax, targetYMax = targetPopulation["dims"]
    #targetCenter = [sourceRatio[0] * targetXMax, sourceRatio[1] * targetYMax]
    #targetArea =  [targetXMax * fanout, targetYMax * fanout]

    #targetXLimits = [int(targetCenter[0] - targetArea[0] / 2), int(targetCenter[0] + targetArea[0] / 2)]
    #if targetXLimits[0] < 0:
    #  targetXLimits[0] = 0
    #if targetXLimits[1] >= targetXMax:
    #  targetXLimits[1] = targetXMax - 1
    
    #targetYLimits = [int(targetCenter[1] - targetArea[1] / 2), int(targetCenter[1] + targetArea[1] / 2)]
    #if targetYLimits[0] < 0:
    #  targetYLimits[0] = 0
    #if targetYLimits[1] >= targetYMax:
    #  targetYLimits[1] = targetYMax - 1

    targetNeurons = []
    for x in range(targetXLimits[0], targetXLimits[1]):
      for y in range(targetYLimits[0], targetYLimits[1]):
        targetNeurons.append(targetMax[0] * y + x)

    return sourceXMax * sourceNeuron[1] + sourceNeuron[0], targetNeurons
    

  def addTemplateToModel(self, templateName, template):
    """ Record the named template into persistent store.
        templateName    The name of the template.
        template        The template object.  This will be rendered as json and stored as a string.
    """

    # Get the /templates group description from the h5serv, and extract the 'links' element.
    if not self.templatesGroupId:
      self.errorMessage = "Model file for '" + self.modelName + "' is malformed, has no 'templates' group"
      self.responseStatus = 503
      return
    
    templatesRest = self.restManager.getRest("/groups/" + self.templatesGroupId + "/links", True)
    if templatesRest.status_code != 200:
      self.errorMessage = "Model file for '" + self.modelName + "' 'templates' group contains no sub-links"
      self.responseStatus = 503
      return

    templatesLinks = templatesRest.json()["links"]

    # If a dataset for the template already exists, we are done.
    templateLink = next((x for x in templatesLinks if x["title"] == templateName), None)
    if templateLink:
      print('Template ' + templateName + ' already exists for model ' + self.modelName + ', not adding')
      self.responseSuccessPayload = "Template " + templateName + " already exists for model " + self.modelName
      self.responseStatus = 200
      return

    # First create the dataset with the required shape.
    templateData = {
      "type": {
          "class": "H5T_STRING",
          "length": "H5T_VARIABLE",
          "charSet": "H5T_CSET_ASCII",
          "strpad": "H5T_STR_NULLTERM"
      },
      "shape": [1],
      "link": {
          "id": self.templatesGroupId,
          "name": templateName
      }
    }

    print('Adding template ' + templateName + ' to model ' + self.modelName)
    dataSetRest = self.restManager.postRest('/datasets', json.dumps(templateData), True)
    if dataSetRest.status_code != 201:
      self.errorMessage = "Unable to add template " + templateName + " to Model file for '" + self.modelName
      self.responseStatus = 503
      return

    # After creating the dataset, write the value into the dataset, a JSON-formatted string representing the template.
    dataSetResponse = dataSetRest.json()
    dataSetId = dataSetResponse["id"]

    payload = { "value": json.dumps(template) }
    dataValueRest = self.restManager.putRest('/datasets/' + dataSetId + '/value', json.dumps(payload), True)
    if dataValueRest.status_code != 200:
      self.errorMessage = "Unable to add template " + templateName + " data to Model file for '" + self.modelName + "'"
      self.responseStatus = 503
      return

    self.responseSuccessPayload = "Successfully added template '" + templateName + "' to model '" + self.modelName + "'"
    self.responseStatus = 201


  def getTemplateFromModel(self, templateName):
    """ Extract and return the named template from persistent store.
        templateName    The name of the template.
        Returns:        A Json object with the template definition.
    """

    # Get the /templates group description from the h5serv, and extract the 'links' element.
    if not self.templatesGroupId:
      self.errorMessage = "Model file for '" + self.modelName + "' is malformed, has no 'templates' group"
      self.responseStatus = 503
      return None
    
    templatesRest = self.restManager.getRest("/groups/" + self.templatesGroupId + "/links", True)
    if templatesRest.status_code != 200:
      self.errorMessage = "Model file for '" + self.modelName + "' 'templates' group contains no sub-links"
      self.responseStatus = 503
      return None

    templatesLinks = templatesRest.json()["links"]

    # If no dataset for the template exists, we are done.
    templateLink = next((x for x in templatesLinks if x["title"] == templateName), None)
    if not templateLink:
      self.errorMessage = "Template " + templateName + " does not exist in model " + self.modelName
      self.responseStatus = 503
      return None

    templateId = templateLink["id"]
    templateValueRest = self.restManager.getRest("/datasets/" + templateId + "/value", True)
    if templateValueRest.status_code != 200:
      self.errorMessage = "Template '" + templateName + "' in model '" + self.modelName + "' has no value: " + templateValueRest.reason
      self.responseStatus = 503
      return None

    self.responseSuccessPayload = "Successfully read template '" + templateName + "' from model '" + self.modelName + "'"
    self.responseStatus = 201

    templateValue = templateValueRest.json()['value']
    return json.loads(templateValue[0])


  def addExpansionToModel(self, sequence, expansionName, nextIndex, expansion):
    """ Record the specified expansion of the named template into persistent store.
        sequence        A unique sequence number assigned to this expansion.
        expansionName   The name of the template that this is an expansion of (do we use this?).
        nextIndex       The next number of neurons needed for this expansion.
        expansion       A list of connections.  Each connection is a list in the form of
                        [from, to, strength].
    """

    # Get the /expansions group description from the h5serv, and extract the 'links' element.
    if not self.expansionsGroupId:
      self.errorMessage = "Model file for '" + self.modelName + "' is malformed, has no 'expansions' group"
      self.responseStatus = 503
      return
    
    expansionsRest = self.restManager.getRest("/groups/" + self.expansionsGroupId + "/links", True)
    if expansionsRest.status_code != 200:
      self.errorMessage = "Model file for '" + self.modelName + "' 'expansions' group contains no sub-links"
      self.responseStatus = 503
      return

    expansionsLinks = expansionsRest.json()["links"]

    # If the 'expansions' group has an existing dataset link for the specified expansion sequence, use its Id, otherwise make it and use the new Id.
    dataSetId = ""
    dataSetCreated = False
    expansionLink = next((x for x in expansionsLinks if x["title"] == str(sequence)), None)
    if expansionLink:
      print('An expansion for sequence ' + str(sequence) + ' exists, deleting')
      dataSetDeleteRest = self.restManager.deleteRest('/datasets/' + expansionLink["id"], True)
      if dataSetDeleteRest.status_code != 200:
        self.errorMessage = "Unable to delete expansion " + expansionName + " to Model file for '" + self.modelName
        self.responseStatus = 503
        return


    print('Creating a new expansion for sequence ' + str(sequence))
    expansionData = {
      "type": "H5T_IEEE_F32LE",
      "shape": [len(expansion), 4],
      "link": {
          "id": self.expansionsGroupId,
          "name": str(sequence)
      }
    }

    dataSetRest = self.restManager.postRest('/datasets', json.dumps(expansionData), True)
    if dataSetRest.status_code != 201:
      self.errorMessage = "Unable to add expansion " + expansionName + " to Model file for '" + self.modelName
      self.responseStatus = 503
      return

    dataSetResponse = dataSetRest.json()
    dataSetId = dataSetResponse["id"]
    dataSetCreated = True

    # Add the expansion as the dataset value, either overwriting the old dataset or filling in the new one.
    print('Injecting content into expansion ' + str(sequence))
    payload = { "value": expansion }
    dataValueRest = self.restManager.putRest('/datasets/' + dataSetId + '/value', json.dumps(payload), True)
    if dataValueRest.status_code != 200:
      self.errorMessage = "Unable to add expansion " + expansionName + " data to Model file for '" + self.modelName + "'"
      self.responseStatus = 503
      return

    # Update the 'maxindex' attribute by summing in the count of neurons just added in this expansion.
    if dataSetCreated:
      maxIndexRest = self.restManager.getRest('/groups/' + self.expansionsGroupId + '/attributes/maxindex', True)
      if maxIndexRest.status_code != 200:
        print('Returned status is ' + str(maxIndexRest.status_code))
        self.errorMessage = "Unable to update maxindex attribute to Model file for '" + self.modelName + "'"
        self.responseStatus = 503
        return

      # Read the current value of maxindex, add in the number of neurons for this expansion.
      # NOTE: Although the docs say writing will overwrite an existing attribute, it needs to be deleted first.
      maxIndexAttr = maxIndexRest.json()
      maxindex = maxIndexAttr["value"]
      print('Updating the value of maxindex attribute from ' + str(maxindex) + ' to ' + str(maxindex + nextIndex))
      data = { 'type': 'H5T_STD_I32LE', 'value': maxindex + nextIndex }
      self.restManager.deleteRest('/groups/' + self.expansionsGroupId + '/attributes/maxindex', True)
      response = self.restManager.putRest('/groups/' + self.expansionsGroupId + '/attributes/maxindex', json.dumps(data), True)
      if response.status_code != 201:
        self.errorMessage = "Unable to update maxindex attribute of expansion " + expansionName + " in Model file '" + self.modelName + "'"
        self.responseStatus = 503
        return

    self.responseSuccessPayload = "Successfully added expansion '" + str(sequence) + "' to model '" + self.modelName + "'"
    self.responseStatus = 201
