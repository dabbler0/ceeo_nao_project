#!/usr/bin/env python
import re

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
    if self.manner == 0: # Constant
      return self.value
    elif self.manner == 1: # Variable dereference or function call
      deref = closure.lookup(self.value[0])
      if isinstance(deref, Function) or isinstance(deref, NativeFunction): # If the variable is a function, call it on its arguments
        args = []
        for arg in self.value[1]:
          print arg.value
          args.append(arg.evaluate(closure))
        return deref.call(args)
      else:
        return deref # Otherwise, return the value of the variable.
    elif self.manner == 2: # Definition
      closure.set(self.value[0], self.value[1].evaluate(closure))
    elif self.manner == 3: # Function construction
      closure.set(self.value[0], Function(closure, self.value[1], self.value[2]))
    elif self.manner == 4: # Loop
      while (self.value[0].evaluate(closure)):
        print "Looping"
        for line in self.value[1]:
          print line.evaluate(closure)
      return None
    elif self.manner == 5: # Conditional
      result = None
      if (self.value[0].evaluate(closure)): # The condition succeeds
        for line in self.value[1]:
          result = line.evaluate(closure)
      elif (self.value[1] is not None): # The condition did not succeed, but there is an "else"
        for line in self.value[1]:
          result = line.evaluate(closure)
      return result

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
    return self.function(args)

# The global scope, which to begin with contains the native functions.
global_scope = Stack(None, state = {
  "+": NativeFunction(lambda (a, b): a + b),
  "-": NativeFunction(lambda (a, b): a - b),
  "*": NativeFunction(lambda (a, b): a * b),
  "/": NativeFunction(lambda (a, b): a / b),
  "%": NativeFunction(lambda (a, b): a % b),
  "==": NativeFunction(lambda (a, b): a == b)
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

def parse (lines, indentation):
  # Parse a program into a list of parse trees.
  block = []
  current_index = 0
  current_parent_depth = 0

  for line in lines:
    print lines
    print "Parsing %s." % line
    # Determine the indentation of this line.
    old_length = len(line)
    new_line = line.lstrip()
    indent = old_length - len(new_line)
    
    if (indent < indentation):
      # They unindented, so we're done here.
      return (block, lines[current_index:])

    elif (indent > indentation):
      current_index -= 1
      print "Indented."
      # They indented, so we recurse.
      print current_index, len(lines), block[current_index]
      (block[current_index][1], lines) = parse(lines[current_index:], indent) # Here we hang the parsed stuff as a block on the last parsed statement.
      print "Parsed as %r." % block[current_index][1]
    
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

      # Append the last token to the tokenization
      tokenization.append(latest_token)
      
      # Begin constructing the parse tree
      if tokenization[0] == "while":
        tokenization.pop(0)
        tree = TreeNode(ROOT, None, 0, manner = WHILE_MANNER)
      else:
        tree = TreeNode(ROOT, None, 0)
      current_paren_depth = 0
      
      # Parse the tokenization
      last_token = None
      for token in tokenization:
        
        # DEBUGGING
        # print "Token: %s" % token

        if last_token is not None and last_token.isalnum() and token.isalnum():
          # Two consecutive alphanumeric sequences can only be a function call
          tree.manner = FUNCTION_CALL_MANNER # Signify that this is a function call node
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
      current_index += 1
      # Seek the root node of our tree and append it to our list of parsed lines
      block.append([tree.root(),None,None])
  return (block, [])

def expressionize(tree):
  if tree.value == PAREN or tree.value == ROOT:
    return expressionize(tree.children[0])
  elif tree.manner == 1 or tree.manner == 2:
    f_args = []
    for child in tree.children:
      f_args.append(expressionize(child))
    return Expression(1, (tree.value, f_args))
  elif tree.manner == 0:
    if tree.value.isdigit():
      return Expression(0, int(tree.value))
    else:
      return Expression(0, tree.value)

def lineParse(line):
  tree = line[0]
  if tree.value == ROOT and tree.manner == WHILE_MANNER:
    return Expression(4, (expressionize(tree.children[0]), line[1]))
  elif tree.value == ROOT and tree.manner == CONDITIONAL_MANNER:
    return Expression(4, (expressionize(tree.children[0]), line[1], line[2]))
  else:
    return expressionize(tree)

def fullParse(text):
  parsed = parse(text.split("\n"), 0)[0]
  block = []
  for line in parsed:
    print line[0].toString()
    block.append(lineParse(line))
  return block

if __name__ == "__main__":
  lines = fullParse(open(raw_input()).read())
  for line in lines:
    print line.evaluate(global_scope)
