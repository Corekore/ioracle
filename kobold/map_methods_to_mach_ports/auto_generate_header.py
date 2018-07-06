import pickle
import re

def parseMessyTypes(messyType,alreadyDeclaredTypeList):
  cleanTypes = []
  #remove pointer notation
  messyType = messyType.replace(' *','')

  #we might need to treat these as protocols instead of just declaring them...
  #in that case, it would be necessary to store these with some kind of tag like in a dictionary
  if "<" in messyType:
    #NOTE regex in python wants to match the entire line...
    #This is probably why I've been having so much trouble with it lately.
    regexResult = re.match('^.*<(.*)>.*$',messyType)
    angleBracMatch = regexResult.group(1)
    cleanTypes.append(angleBracMatch)
    messyType = messyType.replace('<'+angleBracMatch+'>','')

  #split based on spaces
  messyType = messyType.strip()
  if " " in messyType:
    for spaceSlice in messyType.split(" "):
      if spaceSlice[0].isupper():
        cleanTypes.append(spaceSlice)
  else:
    if messyType[0].isupper():
      cleanTypes.append(messyType)

  #The NSSecureType Heuristic Doesn't seem to help since some types in that set still need to be faked
  for type in cleanTypes:
    if type in alreadyDeclaredTypeList:
      cleanTypes.remove(type)

  return cleanTypes

def filterNSSecureCodingTypes(parameterTypes, NSSecureTypeList):
  filteredTypes= set()
  for type in parameterTypes:
    shouldDeclare = True
    for nsType in NSSecureTypeList:
      if nsType in type:
        shouldDeclare = False
    if shouldDeclare:
      filteredTypes.add(type)
  return filteredTypes
    

def handleBlockArgument(blockParameter):
  argsToReturn = []
  pattern = re.compile("(.*)\ \(\^\)\((.*)\)")
  match = pattern.match(blockParameter)
  argsToReturn.append(match.group(1))
  if ", " in match.group(2):
    argsToReturn += match.group(2).split(", ")
  else:
    argsToReturn.append(match.group(2))
  return argsToReturn

def getReturnType(declaration):
  pattern = re.compile(".*?\(([^)]*)")
  match = pattern.match(declaration)
  return_type = match.group(1)
  return return_type

def getParameterTypes(method):
  argsToReturn = []
  raw_arguments = method.split(':')[1:]
  for argument in raw_arguments:
    pattern = re.compile("\((.*)\)")
    match = pattern.match(argument)
    arg_type = match.group(1)

    if "(^)" in arg_type:
      argsToReturn += handleBlockArgument(arg_type)
    else:
      argsToReturn.append(arg_type)
  return argsToReturn

with open('./input_data/invocationDictionary.pk', 'rb') as handle:
    invocationDictionary = pickle.load(handle)
alreadyDeclaredTypeList = open('./input_data/alreadyDeclaredTypes.txt','rb').read().strip().split('\n')

headerDict = {}
headerDict["methods"] = set()
headerDict["types"] = set()

for id in invocationDictionary:
  thisInvocation = invocationDictionary[id]
  thisMethod = thisInvocation["method"]
  headerDict["methods"].add(thisMethod)
  parameterTypes = []
  parameterTypes.append(getReturnType(thisMethod))
  parameterTypes += getParameterTypes(thisMethod)
  parsedTypes = []
  for messyType in parameterTypes:
    parsedTypes += parseMessyTypes(messyType, alreadyDeclaredTypeList)
  for type in parsedTypes:
    headerDict["types"].add(type)
  headerDict["methods"].add(thisMethod)

#define types
#@interface TIKeyboardActivityContext : NSObject
#@end
for type in headerDict["types"]:
  print "@interface "+type+" : NSObject @end"

#auto-generate preamble
preamble = """
@protocol fakeProts <NSObject>

@required

"""
print preamble

#list method declarations
for method in headerDict["methods"]:
  print method

#auto-generate epilogue
print "@end"
