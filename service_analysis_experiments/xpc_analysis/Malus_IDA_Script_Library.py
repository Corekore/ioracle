###########################################################################################
#It's arguable whether this is really a library or not.
#IDA seems to have issues with importing python modules.
#The only way I can make this code easier to share across interfaces is by using cat...
#Seriously, the way to import these functions to an IDA script is as follows:
#cat Malus_IDA_Script_Library.py interfaceUsingTheLibrary.py > idaScriptToInvoke.py
###########################################################################################

import idaapi
import idc
import idautils
import os

###########################################################################################
#BEGIN DEFINITION OF getRegisterValueAtAddress
#this function will return the value of a given register at a given address
#it does this via backtracing
#if it backtraces to the address set by minEa, it will give up and return an error
###########################################################################################
def getRegisterValueAtAddress(ea,minEa,targetReg):
  global errorMessage
  #f.write("%x" % ea + "\n")
  #f.write("%x" % minEa + "\n")
  #f.write(str(targetReg) + "\n")

  #give up if you hit the top of the function
  if ea <= minEa:
    errorMessage+="ERROR: Hit top of function or hit top of basic block with multiple parents"
    return 0

  count_far_code_references = len(list(idautils.XrefsTo(ea, 1)))
  if count_far_code_references > 0:
    #if this gets reached, then we seem to be at the top of a basic block with multiple parents.
    #for now, we can't figure out which parent to follow, so we evaluate the current instruction, and if that doesn't allow us to finish, then we act like we hit top of function.
    minEa = ea

  if idc.GetMnem(ea) in ['ADR','ADRP']:
    dest_op = 0
    src_op = 1
    srcOpType = idc.GetOpType(ea, src_op)
    srcOpValue = idc.GetOperandValue(ea, src_op)
    destOpType = idc.GetOpType(ea, dest_op)
    destOpValue = idc.GetOperandValue(ea, dest_op)
    #f.write(str(destOpValue)+"\n")
    if destOpType == idc.o_reg and destOpValue == targetReg and srcOpType == idc.o_imm:
      #found goal, so return it as a string
      return srcOpValue


  #load register with address in another register and an immediate offset
  if idc.GetMnem(ea) in ['LDR']:
    i = DecodeInstruction(ea)
    srcOpType = i.Op2.n
    srcOpValue = i.Op2.reg
    
    dest_op = 0
    #src op not relevant for displ type
    offset_op = 1

    destOpType = idc.GetOpType(ea, dest_op)
    destOpValue = idc.GetOperandValue(ea, dest_op)
    offsetOpType = idc.GetOpType(ea, offset_op)
    offsetOpValue = idc.GetOperandValue(ea, offset_op)

    """
    print "destOpType: " + str(destOpType)
    print "destOpValue: " + str(destOpValue)
    print "srcOpType: " + str(srcOpType)
    print "srcOpValue: " + str(srcOpValue)
    print "offsetOpType: " + str(offsetOpType)
    print "offsetOpValue: " + str(offsetOpValue)
    """

    if destOpType == idc.o_reg and destOpValue == targetReg and srcOpType == idc.o_reg and offsetOpType == idc.o_displ:
      targetReg = srcOpValue
      ea = idc.PrevHead(ea)
      #print str(hex(ea))
      #print str(hex(minEa))
      return offsetOpValue + getRegisterValueAtAddress(ea,minEa,targetReg)
    

  #TODO deal with adding PC or some other number to the address
  #should be easy with recursion. Just get return the sum of recursively tracking both addends.
  if idc.GetMnem(ea) in ['ADD']:
    dest_op = 0
    src_op = 1
    srcOpType = idc.GetOpType(ea, src_op)
    srcOpValue = idc.GetOperandValue(ea, src_op)
    destOpType = idc.GetOpType(ea, dest_op)
    destOpValue = idc.GetOperandValue(ea, dest_op)
    #I'm assuming the source is the PC register with a 32 bit executable
    if destOpType == idc.o_reg and destOpValue == targetReg and srcOpType == idc.o_reg and srcOpValue == 15:
      pcValue = ea + 4
      #f.write("%x" % pcValue + "\n")
      ea = idc.PrevHead(ea)
      return pcValue + getRegisterValueAtAddress(ea,minEa,targetReg)

  #TODO include how to handle this if the src is an address that probably points to a string
  if idc.GetMnem(ea) in ['MOV']:
    dest_op = 0
    src_op = 1
    srcOpType = idc.GetOpType(ea, src_op)
    srcOpValue = idc.GetOperandValue(ea, src_op)
    destOpType = idc.GetOpType(ea, dest_op)
    destOpValue = idc.GetOperandValue(ea, dest_op)
    if destOpType == idc.o_reg and destOpValue == targetReg: 
      if srcOpType == idc.o_reg:
	#start tracking a new register.
	targetReg = srcOpValue
	ea = idc.PrevHead(ea)
	return getRegisterValueAtAddress(ea,minEa, targetReg)    
      if srcOpType == idc.o_imm:
	#this should be the address we are looking for, so return it
	return srcOpValue

  if idc.GetMnem(ea) in ['MOVT']:
    src_op = 1
    dest_op = 0
    srcOpType = idc.GetOpType(ea, src_op)
    srcOpValue = idc.GetOperandValue(ea, src_op)
    destOpType = idc.GetOpType(ea, dest_op)
    destOpValue = idc.GetOperandValue(ea, dest_op)
    #Are we writing to a register and is that register the one we are tracking?
    if destOpType == idc.o_reg and destOpValue == targetReg:
      if srcOpType == idc.o_imm:
	#this represents the top half of the value we want
	#but we need to track the register farther to know what the bottom half is
	ea = idc.PrevHead(ea)
	bottomHalf = getRegisterValueAtAddress(ea,minEa,targetReg)
	#I should have a sanity check here to know when something has gone wrong.
	#I should refine my error messages to also include addresses, see dispatchExtractor for examples
	if errorMessage != "":
	  errorMessage += "ERROR: Failed to get value in MOVT."
	  return 0
	else:
	  #I hope that I'm correctly overwriting the first 16 bits with the src of MOVT
	  topHalf = srcOpValue << 16
	  botHalf = bottomHalf & 0x0000ffff
	  afterMOVT = topHalf ^ botHalf
	  return afterMOVT
      else:
	errorMessage += "ERROR: cannot handle this type of MOVT."
	return 0
    #This instruction has no impact on the register we are tracking. Skip it.
  #end of code for MOVT

  #keep backtracking and move on to previous instruction
  ea = idc.PrevHead(ea)
  return getRegisterValueAtAddress(ea,minEa, targetReg)    

