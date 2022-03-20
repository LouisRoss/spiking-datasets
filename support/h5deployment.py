import sys
import scipy.stats as stats
import random
import json
import requests
from support.h5Rest import h5Rest

class h5deployment:
  rootId = None
  groups = {}
  datasets = {}
  modelName = ""
  deploymentsName = ""
  deploymentsGroupId = None
  configuration = None
  responseStatus = 200
  responseSuccessPayload = ""
  errorMessage = ""
  restManager = None

  def __init__(self, modelName):
    self.modelName = modelName
    self.deploymentsName = modelName + "_deployments" if len(modelName) > 0 else ""
    self.restManager = h5Rest(self.deploymentsName)
    self.failureReason = ""

    f = open('/configuration/configuration.json')
    self.configuration = json.load(f)

    # When enumerating models, we can be created with an empty model name.  This is ok.
    if (len(self.deploymentsName) > 0):
      modelRest = self.restManager.getRest("", True)
      if modelRest.status_code == 200:
        self.rootId = modelRest.json()['root']

        rootGroupRest = self.restManager.getRest("/groups/" + self.rootId + "/links", True)
        if rootGroupRest.status_code == 200:
          rootGroup = rootGroupRest.json()
          rootDeploymentsLink = next((x for x in rootGroup["links"] if x["title"] == "deployments"), None)
          self.deploymentsGroupId = rootDeploymentsLink["id"] if rootDeploymentsLink else None


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
    self.responseSuccessPayload = domainLinks
    self.responseStatus = 200

  def initializeModelDeployment(self):
    """ Immediately after a new model_deployments file is created, it must be initialized here.
    """

    # Create the deployments group as a subgroup of the root.
    data = { 'link': { 'id': self.rootId, 'name': 'deployments' }}
    responseRest = self.restManager.postRest('/groups', json.dumps(data), True)
    if not responseRest.ok:
      self.failureReason = "Unable to create 'deployments' group for model deployments '" + self.deploymentsName + "': " + responseRest.reason
      self.responseStatus = 500
      return

    self.deploymentsGroupId = responseRest.json()["id"]

    self.responseSuccessPayload = "Successfully created model deployments '" + self.deploymentsName + "'"
    self.responseStatus = 200


  def createModelDeployment(self):
    """ Create a model deployment file for this model object.
    """
    responseRest = self.restManager.putRest("", None, True)
    if responseRest.status_code == 201:
      response = responseRest.json()
      self.rootId = response["root"]
      self.initializeModelDeployment()
      # NOTE: Leave successful payload the status to initializeModelDeployment()
      return
    elif responseRest.status_code == 409:
      self.responseSuccessPayload = 'Model deployment for model ' + self.modelName + ' already exists, not creating'
      self.responseStatus = 200
      return
    else:
      self.failureReason = 'Model creating (PUT ' + self.deploymentsName + ') failed with HTTP status ' + str(response.status_code)
      self.responseStatus = 503
      return

  def deleteModelDeployments(self):
    """ Delete the whole model deployment file from persistent store.
    """
    deleteRest = self.restManager.deleteRest("", True)
    if deleteRest.status_code != 200:
      self.errorMessage = "Unable to delete model deployment for '" + self.modelName + "': " + deleteRest.reason
      self.responseStatus = 503
      return

    #print(deleteRest)
    self.responseSuccessPayload = "Successfully deleted model deployment for '" + self.modelName + "'"
    self.responseStatus = 200

  def addDeploymentToModel(self, deploymentName, deployment):
    """ Record the named deployment into persistent store.
        deploymentName  The name of the deployment.
        deployment      The deployment object.  This will be rendered as json and stored as a string.
    """

    # Get the /deployments group description from the h5serv, and extract the 'links' element.
    if not self.deploymentsGroupId:
      self.errorMessage = "Model deployments file for '" + self.modelName + "' is malformed, has no 'deployments' group"
      self.responseStatus = 503
      return
    
    deploymentsRest = self.restManager.getRest("/groups/" + self.deploymentsGroupId + "/links", True)
    if deploymentsRest.status_code != 200:
      self.errorMessage = "Model deployments file for '" + self.modelName + "' 'deployments' group contains no sub-links"
      self.responseStatus = 503
      return

    deploymentsLinks = deploymentsRest.json()["links"]

    # If a dataset for the deployment already exists, we are done.
    deploymentsLink = next((x for x in deploymentsLinks if x["title"] == deploymentName), None)
    if deploymentsLink:
      print('Deployment ' + deploymentName + ' already exists in deployments for model ' + self.modelName + ', not adding')
      self.responseSuccessPayload = "Deployment " + deploymentName + " already exists in deployments for model " + self.modelName
      self.responseStatus = 200
      return

    # First create the dataset with the required shape.
    deploymentData = {
      "type": {
          "class": "H5T_STRING",
          "length": "H5T_VARIABLE",
          "charSet": "H5T_CSET_ASCII",
          "strpad": "H5T_STR_NULLTERM"
      },
      "shape": [1],
      "link": {
          "id": self.deploymentsGroupId,
          "name": deploymentName
      }
    }

    print('Adding deployment ' + deploymentName + ' to deployments for model ' + self.modelName)
    dataSetRest = self.restManager.postRest('/datasets', json.dumps(deploymentData), True)
    if dataSetRest.status_code != 201:
      self.errorMessage = "Unable to add deployment " + deploymentName + " to deployments file for Model '" + self.modelName
      self.responseStatus = 503
      return

    # After creating the dataset, write the value into the dataset, a JSON-formatted string representing the template.
    dataSetResponse = dataSetRest.json()
    dataSetId = dataSetResponse["id"]

    payload = { "value": json.dumps(deployment) }
    dataValueRest = self.restManager.putRest('/datasets/' + dataSetId + '/value', json.dumps(payload), True)
    if dataValueRest.status_code != 200:
      self.errorMessage = "Unable to add deployment " + deploymentName + " data to deployments file for Model '" + self.modelName + "'"
      self.responseStatus = 503
      return

    self.responseSuccessPayload = "Successfully added deployment '" + deploymentName + "' to deployments file for model '" + self.modelName + "'"
    self.responseStatus = 201

  def deleteDeploymentFromModel(self, deploymentName):
    """ Delete the named deployment from persistent store.
        deploymentName  The name of the deployment.
    """

    # Get the /deployments group description from the h5serv, and extract the 'links' element.
    if not self.deploymentsGroupId:
      self.errorMessage = "Model deployments file for '" + self.modelName + "' is malformed, has no 'deployments' group"
      self.responseStatus = 503
      return None
    
    deploymentsRest = self.restManager.getRest("/groups/" + self.deploymentsGroupId + "/links", True)
    if deploymentsRest.status_code != 200:
      self.errorMessage = "Model deployments file for '" + self.modelName + "' 'deployments' group contains no sub-links"
      self.responseStatus = 503
      return None

    deploymentsLinks = deploymentsRest.json()["links"]

    # If no dataset for the deployments exists, we are done.
    deploymentLink = next((deployment for deployment in deploymentsLinks if deployment["title"] == deploymentName), None)
    if not deploymentLink:
      self.errorMessage = "Deployment " + deploymentName + " does not exist in deployments file for model " + self.modelName
      self.responseStatus = 503
      return None

    deploymentId = deploymentLink["id"]
    deploymentValueRest = self.restManager.deleteRest("/datasets/" + deploymentId, True)
    if deploymentsRest.status_code != 200:
      self.errorMessage = "Unable to delete deployment '" + deploymentName + "' from Model deployments file for '" + self.modelName + "'"
      self.responseStatus = 503

    self.responseSuccessPayload = "Successfully deleted deployment '" + deploymentName + "' from deployments file for model '" + self.modelName + "'"
    self.responseStatus = 200

  def getDeploymentFromModel(self, deploymentName):
    """ Extract and return the named deployment from persistent store.
        deploymentName  The name of the deployment.
        Returns:        A Json object with the deployment definition.
    """

    # Get the /deployments group description from the h5serv, and extract the 'links' element.
    if not self.deploymentsGroupId:
      self.errorMessage = "Model deployments file for '" + self.modelName + "' is malformed, has no 'deployments' group"
      self.responseStatus = 503
      return None
    
    deploymentsRest = self.restManager.getRest("/groups/" + self.deploymentsGroupId + "/links", True)
    if deploymentsRest.status_code != 200:
      self.errorMessage = "Model deployments file for '" + self.modelName + "' 'deployments' group contains no sub-links"
      self.responseStatus = 503
      return None

    deploymentsLinks = deploymentsRest.json()["links"]

    # If no dataset for the deployments exists, we are done.
    deploymentLink = next((deployment for deployment in deploymentsLinks if deployment["title"] == deploymentName), None)
    if not deploymentLink:
      self.errorMessage = "Deployment " + deploymentName + " does not exist in deployments file for model " + self.modelName
      self.responseStatus = 503
      return None

    deploymentId = deploymentLink["id"]
    deploymentValueRest = self.restManager.getRest("/datasets/" + deploymentId + "/value", True)
    if deploymentValueRest.status_code != 200:
      self.errorMessage = "Deployment '" + deploymentName + "' in deployments file for model '" + self.modelName + "' has no value: " + deploymentValueRest.reason
      self.responseStatus = 503
      return None

    #print("Successfully read deployment '" + deploymentName + "' from deployments file for model '" + self.modelName + "'")

    deploymentValue = deploymentValueRest.json()['value']
    self.responseSuccessPayload =  json.loads(deploymentValue[0])
    self.responseStatus = 201


  def getExistingDeployments(self):
    """ Get a list containing the existing deployments for this model.
    """
    if not self.deploymentsGroupId:
      self.errorMessage = "Deployment file for model '" + self.modelName + "' is malformed, has no 'deployments' group"
      self.responseStatus = 503
      return
    
    deploymentsRest = self.restManager.getRest("/groups/" + self.deploymentsGroupId + "/links", True)
    if deploymentsRest.status_code != 200:
      self.errorMessage = "Deployment file for model '" + self.modelName + "' 'deployments' group contains no sub-links"
      self.responseStatus = 503
      return

    deploymentsLinks = deploymentsRest.json()["links"]

    self.responseSuccessPayload = [deployment['title'] for deployment in deploymentsLinks]
    self.responseStatus = 200
