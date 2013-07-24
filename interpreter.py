#!/usr/bin/env python
import re

#############################################
# Architectural portion of the interpreter. #
# After the language has been parsed,       #
# this runs on the parsed data.             #
#############################################

ROOT = 0
PAREN = 1

operator_priority_list = [ROOT, "=", "==", "+", "-", "*", "/"]

def valuefy(tree): #DEBUGGING ONLY
  return tree.value if tree.value not in [ROOT, PAREN] else ["ROOT", "PAREN"][tree.value]

class Stack:
  #Fields
  state = {}
  parent = None

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
  
  def __init__(self, manner, value):
    self.manner = manner
    self.value = value
  
  def evaluate(self, closure):
    if self.manner == 0 or self.manner == 1: # Constant
      return self.value
    elif self.manner == 2: # Variable dereference or function call
      deref = closure.looup(self.value[1])
      if isinstance(deref, Function):
        return deref.call(self.value[1])
      else:
        return deref
    elif self.manner == 3: # Definition
      closure.set(self.value[0], self.value[1].evaluate(closure))
    elif self.manner == 4: # Function construction
      closure.set(self.value[0], Function(closure, self.value[1], self.value[2]))

class Function:
  arguments = []
  closure = None
  block = []

  def __init__(self, stack, args, statements):
    self.arguments = args
    self.block = statements
    self.closure = stack

  def call(self, args):
    new_closure = self.closure.close()
    return_value = None
    for i in range(0, len(self.arguments)):
      new_closure.set(self.arguments[i], args[i])
    for expression in self.block:
      result = expression.evaluate(new_closure)
      return_value = result
    return return_value

class NativeFunction:
  # Function here will be a lambda.
  function = None

  def __init__(self, function):
    self.function = function

  def call(self, args):
    return function(args)

# The global scope, which to begin with contains the native functions.
global_scope = Stack(None, state = {
  "+": lambda (a, b): a + b,
  "-": lambda (a, b): a - b,
  "*": lambda (a, b): a * b,
  "/": lambda (a, b): a / b,
  "%": lambda (a, b): a % b
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
  
  def birth(self, value, paren_depth):
    new_child = TreeNode(value, self, paren_depth)
    self.children.append(new_child)
    return new_child
  
  def replaceChild(self, to_remove, to_add):
    new_node = TreeNode(to_add, self, to_remove.paren_depth)
    for i in range(0, len(self.children)):
      if self.children[i] is to_remove:
        self.children[i] = new_node
        new_node.children.append(to_remove)
        to_remove.parent = new_node
    return new_node

  def toString(self):
    if len(self.children) == 0:
      return self.value if self.value not in [ROOT, PAREN] else ""
    else:
      strung_array = []
      for child in self.children:
        strung_array.append(child.toString())
      if self.value in [ROOT, PAREN]:
        return " ".join(strung_array)
      else:
        return "(%s %s)" % (self.value, " ".join(strung_array))
  def root(self): #DEBUGGING ONLY
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

def parse (text, indentation):
  # Parse a program into a list of parse trees.
  lines = text.split("\n")
  block = []
  current_index = 0
  current_parent_depth = 0

  for line in lines:
    # Determine the indentation of this line.
    old_length = len(line)
    new_line = line.lstrip()
    indent = old_length - len(new_line)
    
    if (indent < indentation):
      # They unindented, so we're done here.
      return (block, lines[current_index:])

    elif (indent > indentation):
      # They indented, so we recurse.
      (block[current_index][1], lines) = parse(text[current_index:], indent) # Here we hang the parsed stuff as a block on the last parsed statement.
    
    else:
      tokenization = []
      latest_token = ""
      alphanumeric = True
      
      # Tokenize the line
      for character in new_line:
        if character.isalnum() == alphanumeric and character != ' ':
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

      # Append the last token to the tokennization
      tokenization.append(latest_token)

      # Begin constructing the parse tree
      tree = TreeNode(ROOT, None, 0)
      current_paren_depth = 0

      # Parse the tokenization
      last_token = None
      for token in tokenization:
        
        if last_token is not None and last_token.isalnum() and token.isalnum():
          # Two consecutive alphanumeric sequences can only be a function call
          tree.manner = 1 # Signify that this is a function call node
          tree = tree.birth(token, current_paren_depth)

        elif token == ",":
          # It's not the comma that's significant, but the token after it
          continue
        
        elif last_token == "," and token.isalnum():
          # Immediately seek the function call that this argument is a part of.
          while (tree.manner != 1):
            tree = tree.parent
          tree = tree.birth(token, current_paren_depth)
        
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
          
          while (tree.paren_depth > current_paren_depth) or (tree.paren_depth == current_paren_depth and (not hasPriority(tree.value, token)) and (not (tree.manner == 1))):
            # Travel up the tree until we find the node we want to be beneath
            strung_child = tree
            tree = tree.parent

          if strung_child is not None:
            # Insert our node between two others
            tree = tree.replaceChild(strung_child, token)
          
          else:
            # Make our node (a leaf)
            tree = tree.birth(token, current_paren_depth)
        
        # Update last_token
        last_token = token
      
      # Seek the root node of our tree and append it to our list of parsed lines
      block.append(tree.root())
  return (block, [])

if __name__ == "__main__":
  (lines,throw_away) = parse(raw_input(), 0)
  for line in lines:
    print line.toString()
"""
def jsonConvertLine(line):
  if isinstance(line, int):
    return Expression(0, line)
  elif issinstance(line, str):
    return Expression(2, line)
  elif line[0] in operators:
    return Expression(4, (line[0], jsonConvertLine(line[1]), jsonConvertLine(line[2])))
  elif line[0] == "defun":
    return Expression(6, (line[1], line[2], jsonConvert(line[3])))
  else:
    return Expression(3, (line[0], line[1:]))

def jsonConvert(json):
  expressions = []
  for line in json:
    expressions.append(jsonConvertLine(line))
  return expressions

def jsonRun(expressions):
  global_closure = Stack(None)
  rval = None
  for exp in expressions:
    rval = exp.evaluate(global_closure)
    print rval
  return rval
"""
