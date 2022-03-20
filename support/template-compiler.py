import sys
from pathlib import Path
import json
from h5model import h5model

# Validate the arguments, load the common configuration, and the template file.
if len(sys.argv) < 2:
  print('Usage: ' + sys.argv[0] + ' <model> ' + '[<population1/template1> <population2/template2> ...]', file = sys.stderr)
  exit(1)

with open('/configuration/configuration.json') as f:
  configuration = json.load(f)
#print(configuration)

modelName = sys.argv[1]
print('Capturing a template population into model ' + modelName)

populationNames = []
templateNames = []
populationAndTemplatePairs = sys.argv[2:]
for populationAndTemplatePair in populationAndTemplatePairs:
  pair = populationAndTemplatePair.split('/')
  if len(pair) == 1:
    # For backward compatiblity, can be removed after complete upgrade.
    populationNames.append('')
    templateNames.append(pair[0])
  else:
    populationNames.append(pair[0])
    templateNames.append(pair[1])

population = {}
populationTemplates = []
nextIndex = 0
print('Population has ' + str(len(populationAndTemplatePairs)) + ' population/template pairs')

# We will need a persistence object specific to the specified model.
model = h5model(modelName)
if not model.rootId:
  print("Model file for '" + modelName + "' not found", file = sys.stderr)
  exit(1)

sequence = 0
for index, (templateName, populationName) in enumerate(zip(templateNames, populationNames)):
  templateFile = templateName
  if (not(templateFile.endswith('json'))):
    templateFile += '.json'

  templateFilePath = Path('/templates/' + templateFile)
  if not templateFilePath.is_file():
    print("Template '" + sys.argv[2] + "' does not exist", file = sys.stderr)
    exit(1)

  print('Adding template file ' + templateFilePath.as_posix())

  with templateFilePath.open() as f:
    template = json.load(f)
  #print(template)

  # Calculate the total neurons needed plus the starting offset and count for each layer.
  neuronIndexes = {}

  neurons = template["neurons"]
  for neuron in neurons:
    count = 1
    for dim in neuron["dims"]:
      count *= dim
    neuronIndexes[neuron["name"]] = { "shape": neuron["dims"], "index": nextIndex, "count": count }
    neuron["index"] = nextIndex
    neuron["count"] = count
    nextIndex += count

  populationTemplates.append({'template': templateName, 'population': populationName, 'indexes': neuronIndexes })

  model.addTemplateToModel(templateName, template)
  if model.responseStatus >= 400:
    print("Unable to add template '" + templateFile + "' to model '" + modelName + "': " + model.errorMessage, file = sys.stderr)
    exit(1)

  model.compileExpansion(templateName, sequence)
  if model.responseStatus >= 400:
    print("Unable to compile expansion for template '" + templateFile + "' in model '" + modelName + "': " + model.errorMessage, file = sys.stderr)
    exit(1)

  sequence += 1

population["neuroncount"] = nextIndex
population["templates"] = populationTemplates
model.updatePopulationInModel(population)

print("Successfully updated and compiled templates " + str(templateNames) + " into model '" + modelName + "'")