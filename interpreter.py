#!/usr/bin/env python
import re

#############################################
# Architectural portion of the interpreter. #
# After the language has been parsed,       #
# this runs on the parsed data.             #
#############################################

operators = {
  "+": lambda a, b: a + b
}

ROOT = 0
PAREN = 1

operator_priority_list = [ROOT, "+", "-", "*", "/"]

def valuefy(tree): #DEBUGGING ONLY
  return tree.value if tree.value not in [ROOT, PAREN] else ["ROOT", "PAREN"][tree.value]

class Stack:
  #Fields
  state = {}
  parent = None

  def __init__(self, parent):
    #Initiate us with this parent
    self.parent = parent

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
    if self.manner == 0 or self.manner == 1: #Constant
      return self.value
    elif self.manner == 2: #Variable
      return closure.lookup(self.value)
    elif self.manner == 3: #Function call
      return closure.lookup(self.value[0]).call(self.value[1])
    elif self.manner == 4: #Operator
      return operators[self.value[0]](self.value[1].evaluate(closure), self.value[2].evaluate(closure))
    elif self.manner == 5: #Definition
      closure.set(self.value[0], self.value[1].evaluate(closure))
    elif self.manner == 6: #Function construction
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
        # Snip the addition in here and kick out the unwanted child.
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
          latest_token += character
        else:
          alphanumeric = character.isalnum() if character != ' ' else alphanumeric
          if len(latest_token) > 0:
            tokenization.append(latest_token)
          latest_token = character if character != ' ' else ''
      tokenization.append(latest_token)

      tree = TreeNode(ROOT, None, 0)
      current_paren_depth = 0

      # Parse the tokenization
      last_token = None
      for token in tokenization:
        print "%s has paren_depth %d" % (token, current_paren_depth)
        if last_token is not None and last_token.isalnum() and token.isalnum():
          tree.manner = 1 # Signify that this is a function call node
          tree = tree.birth(token, current_paren_depth)
        elif token == '(':
          tree = tree.birth(PAREN, current_paren_depth)
          current_paren_depth += 1
        elif token == ')':
          current_paren_depth -= 1
        else:
          strung_child = None
          while (tree.paren_depth > current_paren_depth) or (tree.paren_depth == current_paren_depth and (not hasPriority(tree.value, token)) and (not (tree.manner == 1))):
            print "(%s deferred %s for priority reasons)" % (token, tree.value)
            strung_child = tree
            tree = tree.parent
          if strung_child is not None:
            print "Stringing %s between %s and %s" % (token, valuefy(tree), valuefy(strung_child))
            tree = tree.replaceChild(strung_child, token)
          else:
            print "Birthing %s to %s." % (token, valuefy(tree))
            tree = tree.birth(token, current_paren_depth)
        last_token = token
        print "Tree is now:\n  %s" % tree.root().toString()
      while tree.parent is not None:
        tree = tree.parent
      block.append(tree)
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
