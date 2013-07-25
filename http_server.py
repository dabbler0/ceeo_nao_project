#!/usr/bin/env python
import BaseHTTPServer
import urllib
import urlparse
import simplejson as json
import interpreter
import math

from naoqi import ALProxy

SAVED_COMMANDS_FILE = "commands.json"

#Create the proxies we'll need to execute commands
ttsproxy = ALProxy("ALTextToSpeech", "localhost", 9559)
walkproxy = ALProxy("ALMotion", "localhost", 9559)
bmproxy = ALProxy("ALBehaviorManager", "localhost", 9559)
netproxy = ALProxy("ALNetwork", "localhost", 9559)

'''
#These aren't needed right now but might be in the future

adproxy = ALProxy("ALAudioDevice", "localhost", 9559)

'''

def dVFloat (dic, key, val):
  #Parse a dictionary element as a float if it exists, otherwise default to (val).
  return float(dic[key]) if key in dic else val

class NaoHandler (BaseHTTPServer.BaseHTTPRequestHandler):
  def do_GET(self):
    #Parse the given path
    parsed = urlparse.urlparse(self.path)
    path = parsed.path.split("/")
    qwargs = urlparse.parse_qs(parsed.query)

    #Enforce one value per query string argument
    for key in qwargs:
      qwargs[key] = qwargs[key][0]
    
    print path

    if len(path) < 2 or path[1] == '' or path[1] == 'index.html':
      index_file = open("index.html")
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write(index_file.read())
      index_file.close()
    elif path[len(path) - 1] == 'favicon.ico':
      favicon_file = open('favicon.ico')
      self.send_response(200)
      self.send_header("Content-type", "image/x-icon")
      self.end_headers()
      self.wfile.write(favicon_file.read())
      favicon_file.close()
    elif path[1] == "src-noconflict":
      rfile = open("/".join(path[1:]))
      self.send_response(200)
      if path[len(path) - 1].index('.js') == -1: self.send_header("Content-type", "text/css")
      else: self.send_header("Content-type", "text/javascript")
      self.end_headers()
      self.wfile.write(rfile.read())
      rfile.close()
    elif path[1] == "execute":
      """
        Execute a command, described in the query string arguments.
      """

      reply = {}
    
      if qwargs["command"] == 'say':
        #Say whatever the client wanted us to
        tosay = qwargs["text"]
        ttsproxy.post.say(tosay)
        
        #Reply that we've said it.
        reply["success"] = True

      elif qwargs["command"] == 'move':
        #Initiate a walk command in our walk proxy
        walkproxy.stiffnessInterpolation("Body", 1, 0.1)
        walkproxy.walkInit()

        #Walk. Turn by "turn" radians, then move fowards by "forward", right by "right" meters.
        walkproxy.walkTo(dVFloat(qwargs, "forward", 0), dVFloat(qwargs, "right", 0), dVFloat(qwargs, "turn", 0) * 180 / math.pi)
        
        #Reply with success.
        reply["success"] = True

      elif qwargs["command"] == 'halt':
        #Tell our walk proxy to stop
        walkproxy.stopWalk()
        
        #Reply with success.
        reply["success"] = True
        
      elif qwargs["command"] == 'relax':
        #Reduce stiffness.
        walkproxy.stiffnessInterpolation("Body", 0, 0.1)
        
        #Reply with success.
        reply["success"] = True

      elif qwargs["command"] == 'stiffen':
        #Increase stiffness.
        walkproxy.stiffnessInterpolation("Body", 1, 0.1)

        #Reply with success.
        reply["success"] = True

      elif qwargs["command"] == 'stand':
        #Stand up.
        bmproxy.post.runBehavior("Stand Up")

        #Reply with success.
        reply["success"] = True
      
      elif qwargs["command"] == 'sit':
        #Sit down.
        bmproxy.post.runBehavior("Sit Down")

        #Reply with success.
        reply["success"] = True

      elif qwargs["command"] == 'wave':
        #Wave.
        bmproxy.post.runBehavior("Wave")

        #Reply with success.
        reply["success"] = True

      elif qwargs["command"] == 'setvol':
        #Set the volume to the given volume.
        adproxy.setOutputVolume(int(commands["volume"]))

        #Reply with success.
        reply["success"] = True

      elif qwargs["command"] == 'ping':
        reply["response"] = "pong"

        #Reply with success
        reply["success"] = True
      
      else:
        #Otherwise, we have no idea what's going on.
        reply["success"] = False
        reply["response"] = "Unknown command."
    
      self.send_response(200)
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile.write(json.dumps(reply))
    elif path[1] == "load":
      lfile = open(SAVED_COMMANDS_FILE, "r")
      self.send_response(200)
      self.send_header("Content-Type", "application/json")
      self.end_headers()
      self.wfile.write(lfile.read())
      lfile.close()
    elif path[1] == 'getbuttons':
      buttonsfile = open('buttons.json')
      self.send_response(200)
      self.send_header("Content-Type", "application.json")
      self.end_headers()
      self.wfile.write(buttonsfile.read())
      buttonfile.close()

  def do_POST(self):
    #Parse the given path
    parsed = urlparse.urlparse(self.path)
    path = parsed.path.split("/")
    qwargs = urlparse.parse_qs(parsed.query)

    #Enforce one value per query string argument
    for key in qwargs:
      qwargs[key] = qwargs[key][0]
    
    reply = {}
    
    if path[1] == "save":
      wfile = open(SAVED_COMMANDS_FILE, "w")
      wfile.write(self.rfile.read())
      wfile.close()
      reply["success"] = True
    if path[1] == "code":
      length = int(self.headers.getheader('content-length'))
      postvars = urlparse.parse_qs(self.rfile.read(length), keep_blank_values=1)
      code = urllib.unquote(postvars["code"][0])
      lines = interpreter.fullParse(code)
      for line in lines:
        line.evaluate(interpreter.global_scope)
      reply["success"] = True
    elif path[1] == 'setbutton':
      buttondata = json.loads(urllib.unquote(self.rfile.read(int(self.headers.getheader('content-length')), keep_blank_values=1)).replace('data=', '').replace('+', ' '))
      buttonsfile = open('buttons.json')
      contents = json.loads(buttonsfile.read())
      buttonsfile.close()
      reply["success"] = False
      if buttondata['name'] in contents:
        if buttondata['delete']:
          del(contents[buttondata['name']])
          wbuttonsfile = open('buttons.json', 'w')
          wbuttonsfile.write(json.dumps(contents))
          wbuttonsfile.close()
        else:
          contents[buttondata['name']] = buttondata['commands']
          startlocation = contents.index('\n[' + buttondata['name'] + ']')
          wbuttonsfile = open('buttons.json', 'w')
          wbuttonsfile.write(json.dumps(contents))
          wbuttonsfile.close()
        reply["success"] = True
      else:
        wbuttonsfile = open('buttons.json', 'w')
        contents[buttondata['name']] = buttondata['commands']
        wbuttonsfile.write(json.dumps(contents));
        wbuttonsfile.close()
        reply["success"] = True

    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    self.wfile.write(json.dumps(reply))

if __name__ == "__main__":
  ip_address = netproxy.getLocalIP()
  print 'Starting server on %s:8080' % ip_address
  httpd = BaseHTTPServer.HTTPServer(('', 8080), NaoHandler)
  httpd.serve_forever()
