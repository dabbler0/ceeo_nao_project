#!/usr/bin/env python
import re
import sys
import time
import math
from naoqi import ALProxy

#############################################
# Architectural portion of the interpreter. #
# After the language has been parsed,       #
# this runs on the parsed data.             #
#############################################

ROOT = 0
PAREN = 1

NORMAL_MANNER = 0
FUNCTION_CALL_MANNER = 1
OPERANT_MANNER = 2
WHILE_MANNER = 3
CONDITIONAL_MANNER = 4
RETURN_STATEMENT_MANNER = 5

operator_priority_list = [ROOT, "=", "is", ">", "<", "+", "-", "mod", "*", "/"]

ttsproxy = ALProxy("ALTextToSpeech", "localhost", 9559)
sonarproxy = ALProxy("ALSonar", "localhost", 9559)
walkproxy = ALProxy("ALMotion", "localhost", 9559)
bmproxy = ALProxy("ALBehaviorManager", "localhost", 9559)
darkproxy = ALProxy("ALDarknessDetection", "localhost", 9559)

darkproxy.subscribe("naoscript")
sonarproxy.subscribe("naoscript")

memproxy = ALProxy("ALMemory", "localhost", 9559)

def valuefy(tree): #DEBUGGING ONLY
  return tree.value if tree.value not in [ROOT, PAREN] else ["ROOT", "PAREN"][tree.value]

def isStaticAtomic(string):
  return (string.isalnum() and not string in operator_priority_list) or (string[0] == '"' and string[len(string) - 1] == '"')

def isFutureAtomic(string):
  return isStaticAtomic(string) or string == "("

def isPastAtomic(string):
  return isStaticAtomic(string) or string == ")"

class Stack:
  #Fields
  state = {}
  parent = None
  return_value = None

  def __init__(self, parent, state = {}):
    #Initiate us with this parent
    self.parent = parent
    self.state = state

  def lookup(self, name):
    #If we have this variable, return it; otherwise ask for it from our parent.
    if name in self.state:
      return self.state[name]
    elif self.parent is not None:
      return self.parent.lookup(name)
    else:
      return None

  def close(self):
    #Return a stack with us as the parent.
    return Stack(self)

  def unclose(self):
    #Return our parent
    return self.parent

  def set(self, name, value):
    #Set a variable.
    self.state[name] = value

class Expression:
  manner = None
  value = None
  
  def __init__(self, manner, value, to_return = False):
    self.manner = manner
    self.value = value
  
  def evaluate(self, closure):
    if self.manner == 0: # Constant
      return self.value
    elif self.manner == 1: # Variable dereference or function call
      deref = closure.lookup(self.value[0])
      if isinstance(deref, Function) or isinstance(deref, NativeFunction): # If the variable is a function, call it on its arguments
        args = []
        for arg in self.value[1]:
          args.append(arg.evaluate(closure))
        return deref.call(args)
      else:
        return deref # Otherwise, return the value of the variable.
    elif self.manner == 2: # Definition
      closure.set(self.value[0], self.value[1].evaluate(closure))
    elif self.manner == 3: # Function construction
      closure.set(self.value[0], Function(closure, self.value[1], self.value[2], name = self.value[0]))
    elif self.manner == 4: # Loop
      while (self.value[0].evaluate(closure)):
        for line in self.value[1]:
          line.evaluate(closure)
      return closure.return_value
    elif self.manner == 5: # Conditional
      result = None
      if (self.value[0].evaluate(closure)): # The condition succeeds
        for line in self.value[1]:
          result = line.evaluate(closure)
      elif (self.value[1] is not None): # The condition did not succeed, but there is an "else"
        for line in self.value[2]:
          result = line.evaluate(closure)
      return result
    elif self.manner == 6: # Return statement
      closure.return_value = self.value.evaluate(closure)
      return closure.return_value

class Function:
  arguments = []
  closure = None
  block = []
  name = None

  def __init__(self, stack, args, statements, name = "anonymous"):
    self.arguments = args
    self.block = statements
    self.closure = stack
    self.name = name

  def call(self, args):
    new_closure = self.closure.close()
    return_value = None
    if len(args) < len(self.arguments):
      print "%s is not enough arguments to call function %s." % (args, self.name)
      sys.exit(1)
    for i in range(0, len(self.arguments)):
      new_closure.set(self.arguments[i], args[i])
    for expression in self.block:
      expression.evaluate(new_closure)
      if (new_closure.return_value is not None):
        return new_closure.return_value
    return None

class NativeFunction:
  # Function here will be a lambda.
  function = None
  name = None

  def __init__(self, function, name="anonymous"):
    self.function = function
    self.name = name

  def call(self, args):
    return self.function(args)

def walk ((x,)):
  walkproxy.stiffnessInterpolation("Body", 1, 0.1)
  walkproxy.walkInit()
  walkproxy.walkTo(x, 0, 0)
  return True

def turn ((x,)):
  walkproxy.stiffnessInterpolation("Body", 1, 0.1)
  walkproxy.walkInit()
  walkproxy.walkTo(0, 0, x * math.pi / 180)
  return True

# The global scope, which to begin with contains the native functions.
global_scope = Stack(None, state = {
  "+": NativeFunction(lambda (a, b): a + b, name = "+"),
  "-": NativeFunction(lambda (a, b): a - b, name = "-"),
  "*": NativeFunction(lambda (a, b): a * b, name = "*"),
  "/": NativeFunction(lambda (a, b): a / b, name = "/"),
  ">": NativeFunction(lambda (a, b): a > b, name = "/"),
  "<": NativeFunction(lambda (a, b): a < b, name = "/"),
  "mod": NativeFunction(lambda (a, b): a % b, name = "mod"),
  "is": NativeFunction(lambda (a, b): a == b, name = "is"),
  "print": NativeFunction(lambda (x,): sys.stdout.write(str(x) + "\n"), name = "print"),
  "walk": NativeFunction(walk, name = "walk"),
  "say": NativeFunction(lambda (x,): ttsproxy.say(str(x)), name = "say"),
  "stand": NativeFunction(lambda l: bmproxy.runBehavior("Stand Up"), name="stand"),
  "sit": NativeFunction(lambda l: bmproxy.runBehavior("Sit Down"), name="sit"),
  "wait": NativeFunction(lambda l: time.sleep(l[0]) if len(l) > 0 else time.sleep(1), name = "wait"),
  "relax": NativeFunction(lambda l: walkproxy.stiffnessInterpolation("Body", 0, 0.1), name = "relax"),
  "volume": NativeFunction(lambda (x,): adproxy.setOutputVolume(int(commands["volume"])), name="volume"),
  "neg": NativeFunction(lambda (x,): -x, name = "neg"),
  "distance": NativeFunction(lambda (x,): memproxy.getData("Device/SubDeviceList/US/Left/Sensor/Value") if x == "left" else memproxy.getData("Device/SubDeviceList/US/Right/Sensor/Value"), name = "distance"),
  "brightness": NativeFunction(lambda l: 100 - (memproxy.getData("DarknessDetection/DarknessValue") * 50 / 47), name = "brightness")
})

##########
# Parser #
##########

class TreeNode:
  manner = None
  value = None
  parent = None
  children = None
  paren_depth = 0

  def __init__(self, value, parent, paren_depth, manner = 0):
    self.parent = parent
    self.value = value
    self.paren_depth = paren_depth
    self.manner = manner
    self.children = []
  
  def birth(self, value, paren_depth, manner = 0):
    new_child = TreeNode(value, self, paren_depth, manner = manner)
    self.children.append(new_child)
    return new_child
  
  def replaceChild(self, to_remove, to_add, manner = 0):
    new_node = TreeNode(to_add, self, to_remove.paren_depth, manner = manner)
    for i in range(0, len(self.children)):
      if self.children[i] is to_remove:
        self.children[i] = new_node
        new_node.children.append(to_remove)
        to_remove.parent = new_node
    return new_node

  def toString(self):
    if len(self.children) == 0:
      return valuefy(self)
    else:
      strung_array = []
      for child in self.children:
        strung_array.append(child.toString())
      #if self.value in [ROOT, PAREN]:
      #  return " ".join(strung_array)
      else:
        return "(%r [%d] %s)" % (valuefy(self), self.manner, " ".join(strung_array))

  def root(self):
    if (self.value == ROOT):
      return self
    else:
      return self.parent.root()

def hasPriority(o1, o2):
  for operator in operator_priority_list:
    if operator == o1:
      return True
    elif operator == o2:
      return False
  return None

def parse (lines, indentation):
  # Parse a program into a list of parse trees.
  block = []
  current_block_index = 0
  current_line_index = 0 
  current_parent_depth = 0
  seeking_else = False
  found_else = False
  length = len(lines)

  while current_line_index < length:
    line = lines[current_line_index]

    # Determine the indentation of this line.
    old_length = len(line)
    new_line = line.lstrip()
    indent = old_length - len(new_line)

    if len(new_line) == 0:
      current_line_index += 1
      continue
    
    if (indent < indentation):
      # They unindented, so we're done here.
      return (block, current_line_index)

    elif (indent > indentation):
      # They indented, so we recurse.
      temporary_tuple = parse(lines[current_line_index:], indent) # Here we hang the parsed stuff as a block on the last parsed statement.
      if found_else:
        block[current_block_index - 1][2] = temporary_tuple[0]
        current_line_index += temporary_tuple[1]
        found_else = False
      else:
        block[current_block_index - 1][1] = temporary_tuple[0]
        current_line_index += temporary_tuple[1]
    
    else:
      tokenization = []
      latest_token = ""
      alphanumeric = True
      in_string = False
      
      # Tokenize the line
      for character in new_line:
        escaped = False
        if character == '\\' and in_string:
          escaped = True
        elif character == '"':
          if in_string and not escaped:
            latest_token += character
            tokenization.append(latest_token)
            latest_token = ''
            in_string = False
          else:
            if len(latest_token) > 0:
              tokenization.append(latest_token)
            latest_token = '"'
            in_string = True
        elif in_string:
          latest_token += character
        else:
          if character == '(' or character == ')':
            alphanumeric = False
            if len(latest_token) > 0:
              tokenization.append(latest_token)
            tokenization.append(character)
            latest_token = ''
          elif character.isalnum() == alphanumeric and character != ' ':
            # We're still in the same token, so keep constructing it
            latest_token += character
          else:
            # We're switching tokens.
            alphanumeric = character.isalnum() if character != ' ' else alphanumeric
            if len(latest_token) > 0:
              # Append our token to the tokenization.
              # Token will be '' if if it was created because of a space-separated
              # alphanumeric-nonalphanumeric pair, so we don't add those.
              tokenization.append(latest_token)
            
            # If we're supposed to, also begin constructing the next token.
            latest_token = character if character != ' ' else ''
    
      # Append the last token to the tokenization
      if len(latest_token) > 0:
        tokenization.append(latest_token)
      
      found_else = False
      
      if len(tokenization) == 0:
        current_line_index += 1
        continue
      elif tokenization[0] == "function":
        parameters = []
        if len(tokenization) > 3 and tokenization[2] == "takes":
          for token in tokenization[3:]:
            if token == ",":
              continue
            else:
              parameters.append(token)
        block.append([("FUNCTION", tokenization[1], parameters), None, None])
        current_line_index += 1
        current_block_index += 1
        continue
      else:
        # Begin constructing the parse tree
        if tokenization[0] == "while":
          tokenization.pop(0)
          tree = TreeNode(ROOT, None, 0, manner = WHILE_MANNER)
        elif tokenization[0] == "if":
          tokenization.pop(0)
          tree = TreeNode(ROOT, None, 0, manner = CONDITIONAL_MANNER)
          seeking_else = True
        elif tokenization[0] == "return":
          tokenization.pop(0)
          tree = TreeNode(ROOT, None, 0, manner = RETURN_STATEMENT_MANNER)
        elif seeking_else and tokenization[0] == "else":
          found_else = True
          seeking_else = False
          current_line_index += 1
          continue
        else:
          tree = TreeNode(ROOT, None, 0)
        current_paren_depth = 0
        
        # Parse the tokenization
        last_token = None
        for token in tokenization:
          
          # DEBUGGING
          # print "Token: %s" % token
          # print "Paren depth: %d" % current_paren_depth

          if last_token is not None and isPastAtomic(last_token) and isFutureAtomic(token):
            # Two consecutive alphanumeric sequences can only be a function call
            tree.manner = FUNCTION_CALL_MANNER # Signify that this is a function call node
            if token == "(":
              tree = tree.birth(PAREN, current_paren_depth)
              current_paren_depth += 1
            else:
              tree = tree.birth(token, current_paren_depth)


          elif token == ",":
            # It's not the comma that's significant, but the token after it
            last_token = ","
            continue
          
          elif last_token == "," and isFutureAtomic(token):
            # Immediately seek the function call that this argument is a part of.
            while (tree.manner != 1):
              tree = tree.parent

            tree = tree.birth(token, current_paren_depth)

            if token == "(":
              current_paren_depth += 1
          
          elif token == '(':
            # Create a parenthetical node and increase our paren_depth
            tree = tree.birth(PAREN, current_paren_depth)
            current_paren_depth += 1

          elif token == ')':
            # Decrease the paren depth
            current_paren_depth -= 1
          
          else:
            # Otherwise, we have an atomic or operant token.
            strung_child = None # This will be for in case we have insert our node between two others
            new_manner = OPERANT_MANNER if token in operator_priority_list else NORMAL_MANNER

            while (tree.paren_depth > current_paren_depth) or (tree.paren_depth == current_paren_depth and (not hasPriority(tree.value, token)) and (not (tree.manner == 1))):
              # DEBUGGING
              # print "  deferring %s." % valuefy(tree)
              
              # Travel up the tree until we find the node we want to be beneath
              strung_child = tree
              tree = tree.parent

            if strung_child is not None:
              # Insert our node between two others
              tree = tree.replaceChild(strung_child, token, manner = new_manner)
            
            else:
              # Make our node (a leaf)
              tree = tree.birth(token, current_paren_depth, manner = new_manner)
          
          # Update last_token
          last_token = token
          # DEBUGGING
          # print tree.root().toString()
         

      current_line_index += 1
      current_block_index += 1

      # Seek the root node of our tree and append it to our list of parsed lines
      block.append([tree.root(),None,None])
  return (block, current_line_index)

def expressionize(tree):
  if tree.value == PAREN or tree.value == ROOT:
    # The root and parenthetical nodes disappear.
    return expressionize(tree.children[0])

  elif tree.manner == 1 or tree.manner == 2:
    # This is either variable assignment, variable access, or a function call.
    
    if tree.value == "=":
      # This is variable assignment.
      return Expression(2, (tree.children[0].value, expressionize(tree.children[1])))
    else:
      # This is either variable access or a function call.

      # Expressionize the children.
      f_args = []
      for child in tree.children:
        f_args.append(expressionize(child))
      
      return Expression(1, (tree.value, f_args))
  
  elif tree.manner == 0:
    # This is either a constant, variable access, or a function call.

    if tree.value.isdigit():
      # It's a numeric constant.
      return Expression(0, int(tree.value))
    
    elif len(tree.value) > 0 and tree.value[0] == '"' and tree.value[len(tree.value) - 1] == '"':
      # It's a string constant.
      return Expression(0, tree.value.strip('"'))
    
    else:
      # It's variable access or a function call.
      return Expression(1, (tree.value, []))

def lineParse(line):
  tree = line[0]

  if isinstance(tree, tuple) and tree[0] == "FUNCTION":
    expression_block = []
    for statement in line[1]:
      expression_block.append(lineParse(statement))
    return Expression(3, (tree[1], tree[2], expression_block))

  elif tree.value == ROOT and tree.manner == RETURN_STATEMENT_MANNER:
    return Expression(6, expressionize(tree.children[0]))
  
  elif tree.value == ROOT and tree.manner == WHILE_MANNER:
    # Expressionize the looped block
    expression_block = []
    for statement in line[1]:
      expression_block.append(lineParse(statement))

    # Expressionize the whole thing
    return Expression(4, (expressionize(tree.children[0]), expression_block))

  elif tree.value == ROOT and tree.manner == CONDITIONAL_MANNER:
    # Expressionize the conditional expression block
    if_expression_block = []
    for statement in line[1]:
      if_expression_block.append(lineParse(statement))

    # Expressionize the opposite expression block
    else_expression_block = None
    if line[2] is not None:
      else_expression_block = []
      for statement in line[2]:
        else_expression_block.append(lineParse(statement))

    # Expressionize the entire expression
    return Expression(5, (expressionize(tree.children[0]), if_expression_block, else_expression_block))

  else:
    return expressionize(tree)

def indentify(line):
  string = ""
  string += line[0].toString() if isinstance(line[0], TreeNode) else str(line[0])
  if line[1] is not None:
    for subline in line[1]:
      string += "\n  " + "\n  ".join(indentify(subline).split("\n"))
  if line[2] is not None:
    for subline in line[2]:
      string += "\n  " + indentify(subline)
  return string

def fullParse(text):
  parsed = parse(text.split("\n"), 0)[0]
  block = []
  for line in parsed:
    # DEBUGGING
    # print indentify(line)
    block.append(lineParse(line))
  return block

if __name__ == "__main__":
  lines = fullParse(open(sys.argv[1]).read())
  for line in lines:
    line.evaluate(global_scope)
