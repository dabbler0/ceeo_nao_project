

#############################################
# Architectural portion of the interpreter. #
# After the language has been parsed,       #
# this runs on the parsed data.             #
#############################################

operators = {
  "+": lambda a, b: a + b
}

class Stack:
  #Fields
  state = {}
  parent = None

  def __init__(self, parent):
    #Initiate us with this parent
    self.parent = parent

  def lookup(self, name):
    #If we have this variable, return it; otherwise ask for it from our parent.
    if name in state:
      return state[name]
    elif parent is not None:
      return parent.lookup(name)
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
    state[name] = value

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
      return value.call(closure)
    elif self.manner == 4: #Operator
      return operators[self.value[0]](self.value[1].evaluate(closure), self.value[2].evaluate(closure))
    elif self.manner == 5: #Definition
      closure.set(self.value[0].evaluate(closure), self.value[1].evaluate(closure))

class Function:
  arguments = []
  closure = None
  block = []

  def __init__(self, stack, args, statements):
    arguments = args
    block = statements
    closure = stack

  def call(self, args):
    new_closure = closure.close()
    return_value = None
    for expression in block:
      result = expression.evaluate(new_closure)
      if result is not None:
        return_value = result
        break
    return return_value

if __name__ == "__main__":
  global_closure = Stack(None)
  addition = Expression(4, ["+", Expression(0, 2), Expression(0, 3)])
  print addition.evaluate(global_closure)
