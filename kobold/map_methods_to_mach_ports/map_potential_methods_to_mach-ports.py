#three input files, 1) mach-port to exec mapping, 2) protocol to exec mapping, 3) list of accessible mach-ports
#one output file, mapping of protocols that might be related to accessible mach-ports
#bonus output, mapping of specific methods to try for each accessible mach-port

import pickle
import re


def generateMethodCall(method, variables, id):
  #[myConnection.remoteObjectProxy enumerateInstalledAppsWithOptions:dictTest completion:completionHandler];
  invocation = ""

  #set up return value for the call if it isn't void
  if "void" not in variables[0]["type"]:
    invocation += variables[0]["name"] +' = '

  invocation += '[myConnection_' +id+ '.remoteObjectProxy '
    
  #if there are colons, then there are parameters, and we need to use the right variable names
  if ':' in method: 
    #strip away the irrelevant parts of the method declaration
    pattern = re.compile(".*?\)(.*);")
    match = pattern.match(method)
    methodStripped = match.group(1)

    methodSlices = methodStripped.split(":")
    print "!!!about to print slices!!!"
    #the first slice won't have any variables, so it's ok to just use it as is
    invocation += methodSlices[0] +':'

    #if there is only one argument, then this loop will simply be skipped
    argument_count = 1
    for slice in methodSlices[1:]:
      pattern = re.compile("(.*?arg[0-9]*)")
      match = pattern.match(slice)
      spotForVarName = match.group(1)
      variableNameForSlice = variables[argument_count]["name"]
      print "variableNameForSlice " + variableNameForSlice
      modifiedSlice = slice.replace(spotForVarName, variableNameForSlice, 1)
      print "spotForVarName " + spotForVarName
      print "modifiedSlice " + modifiedSlice
      argument_count += 1
      invocation += modifiedSlice

    #finish after the last slice
    invocation += '];\n'

   

  #if there are no colons, then there are not parameters, and no names need to be used
  else:
    pattern = re.compile(".*?\)(.*);")
    match = pattern.match(method)
    methodToInvoke = match.group(1)
    invocation += methodToInvoke + "];"

  return invocation



#return the strings to declare a block and the new var_id number
def handleBlockDeclaration(var_type, id, var_id):
  #example of a block declaration
  """
  //type definition. I really don't understand this syntax...
  typedef void (^objectOperationBlock)(NSError *error);

  //declare the block
  objectOperationBlock completionHandler = ^(NSError *error){
    //Generic message signalling completion of the method
    NSLog(@"Dosomething");
    //For each variable in the handler, try to log them.
    //We might run into trouble if any of these aren't NSObjects...
    NSLog(@"error: %@",error);};
  """
  block_arg_list = []
  for v_type in var_type:
    this_block_arg = {}
    this_block_arg["type"] = v_type
    #It shouldn't hurt anything if we create a name for a void type here.
    this_block_arg["name"] = "var_"+id+"_"+str(var_id)
    var_id += 1
    block_arg_list.append(this_block_arg)
  print "block_arg_list: "+str(block_arg_list)

  block_declaration = ""
  print "Block Variable Type: "+str(var_type)
  #The first variable type in the var_type list should be the return type.
  #It will probably be void, but might not always be void...
  return_type = block_arg_list[0]["type"]
  #set up return type and type name
  #I need a handle on the block type name, so I can use it again.
  block_type = "objectOperationBlock_"+id+"_"+str(var_id)
  var_id += 1
  block_declaration += "typedef "+return_type+" (^"+block_type+")"
  #fill in the argument types and finish the statement with semicolon
  block_args = ""
  block_args += "("+block_arg_list[1]["type"]+" "+block_arg_list[1]["name"]
  for this_block_arg in block_arg_list[2:]:
    block_args += ", "+this_block_arg["type"]+" "+this_block_arg["name"]
  block_declaration += block_args
  block_declaration += ");\n"

  #declare the block
  #set up a name for the handler variable
  block_variable_name = "blockHandler_"+id+"_"+str(var_id)
  var_id += 1
  
  #create the block's heading
  block_declaration += block_type +" "+ block_variable_name + " = ^"
  block_declaration += block_args + "){\n"
  #generic completion message
  block_declaration += 'NSLog(@"This is the completion message for invocation id number ' +id+ '");\n'


  #I need to print each of the block variables (except for return type which I hope is void...)
  #TODO we should probably wrap each of these in error catching code so that execution doesn't get 
  #TODO interrupted when one of our fake objects explodes...
  for this_block_arg in block_arg_list[1:]:
    block_declaration += 'NSLog(@"' +this_block_arg["type"] + ' ' +this_block_arg["name"]+ ': %@",' +this_block_arg["name"]+ ');\n'
  block_declaration += '};\n'

  #TODO I think I should also return the variable name for the block_handler, so that it can be used in the method invocation.
  return block_declaration,var_id,block_variable_name


def handleBlockArgument(blockParameter):
  argsToReturn = []
  pattern = re.compile("(.*)\ \(\^\)\((.*)\)")
  match = pattern.match(blockParameter)
  argsToReturn.append(match.group(1))
  #print argsToReturn
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
      argsToReturn.append(handleBlockArgument(arg_type))
    else:
      argsToReturn.append(arg_type)
  return argsToReturn

def autoCodeThisMethod(method, machPort, id):
  objcCode = ""
  id = str(id)
  #loadProtocol
  fake_protocol_name = "fakeProts"
  objcCode += "NSXPCInterface *myInterface_"+id+" = [NSXPCInterface interfaceWithProtocol: @protocol("+fake_protocol_name+")];\n"
  #initialize connection
  objcCode += 'NSXPCConnection *myConnection_'+id+' = [[NSXPCConnection alloc] initWithMachServiceName:@"'+machPort+'"options:0];\n'
  objcCode += 'myConnection'+id+'.remoteObjectInterface = myInterface_'+id+';\n'
  objcCode += '[myConnection_'+id+' resume];\n'
  #handle error messages
  objcCode += 'myConnection_'+id+'.interruptionHandler = ^{NSLog(@"Connection Terminated for id:'+id+'");};\n'
  objcCode += 'myConnection_'+id+'.invalidationHandler = ^{NSLog(@"Connection Invalidated for id:'+id+'");};\n'


  #extract return and argument types
  varTypes = []
  varTypes.append(getReturnType(method))
  varTypes += getParameterTypes(method)
  print method
  print varTypes 
  var_id = 0
  var_declarations = ""
  variables = []
  for var in varTypes:
    thisVariable = {}
    thisVariable["type"]=var
    #for none block types, it should be sufficient to just declare a variable.
    if "list" in str(type(var)):
      #set up declaration for block
      block_declaration,var_id,thisVariable["name"] = handleBlockDeclaration(var, id, var_id)
      var_declarations += block_declaration
      #set up dictionary for this block with type and variable name
    elif "void" not in var:
      #declare simple variable
      var_declarations += var+' var_'+id+'_'+str(var_id)+';\n'
      thisVariable["name"] = 'var_'+id+'_'+str(var_id)
      var_id += 1
    variables.append(thisVariable)
  print variables
  objcCode += var_declarations

  objcCode += generateMethodCall(method, variables, id)

  #declare method parameters by iterating through argument type list.
  #I don't think we actually need to initialize these parameters, I think they just need to be declared.
    #check for block parameters
    #set up blocks if necessary
  #invoke the method using initialized parameters
  print "this is the method " + method
  return objcCode
  


def prettyPrint(executableDict):
  for executable in executableDict:
    print executable
    for machport in executableDict[executable]["mach-ports"]:
      print "  mach-port: " + machport
    if "protocols" in executableDict[executable]:
      protsDict = executableDict[executable]["protocols"] 
      if len(protsDict) == 1:
        print "GOOD FOR TESTING"
      for protocol in protsDict:
        print "  protocol: " + protocol
        for method in protsDict[protocol]:
          print "    method: " + method

executableDictionary = {}

#map sandbox accessible mach-ports to executables
machPort_to_Exec_Mappings = open("./input_data/sorted_uniq_mach-port_to_executable.txt", "rb").read().strip().split("\n")
sandboxAccessibleMachPorts = open("./input_data/sandbox_accessible_services.txt", "rb").read().strip().split("\n")
#print machPort_to_Exec_Mappings
for mapping in machPort_to_Exec_Mappings: 
  machPort, executable = mapping.split(",")
  if machPort in sandboxAccessibleMachPorts:
    #initialize an entry for the executable if there isn't one already
    if executable not in executableDictionary:
      executableDictionary[executable] = {}
      executableDictionary[executable]["mach-ports"] = []
    #TODO it should be possible for an executable to map to more than one accessible mach-port
    executableDictionary[executable]["mach-ports"].append(machPort)

prettyPrint(executableDictionary)

#map protocols to executables
with open('./input_data/mystery_pickle_file.pk', 'rb') as handle:
    class_dump_results = pickle.load(handle)

#at this point, only executable using sandbox accessible mach-ports should be in the dictionary
for executable in executableDictionary:
  if class_dump_results[executable] != {}:
    executableDictionary[executable]["protocols"] = {}
    protsDict = executableDictionary[executable]["protocols"] 
    for protocol in class_dump_results[executable]:
      protsDict[protocol] = []
      raw_header = class_dump_results[executable][protocol]
      for line in raw_header.split('\n'):
        if ((line.startswith("-") or line.startswith("+")) and line.endswith(";")):
          protsDict[protocol].append(line)

#for each executable in executableDict, search through the pickle dictionary for protocols.
#if any protocols are found, then add them to executable's dictionary.
# executable {mach-port: ..., protocols: {protocol: [methodDeclarationStrings]}}

prettyPrint(executableDictionary)

id = 1
for executable in executableDictionary:
  if "protocols" in executableDictionary[executable]:
    protsDict = executableDictionary[executable]["protocols"] 
    for protocol in protsDict:
      for method in protsDict[protocol]:
        for machport in executableDictionary[executable]["mach-ports"]:
          objcCode = autoCodeThisMethod(method, machPort, id)
          id += 1
          print "##################################################"
          print "BEGIN OBJC CODE"
          print "##################################################"
          print objcCode
          print "##################################################"
          print "END OBJC CODE"
          print "##################################################"


