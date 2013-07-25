#!/usr/bin/env python
import BaseHTTPServer
import urlparse
import simplejson as json
import interpreter

from naoqi import ALProxy

SAVED_COMMANDS_FILE = "commands.json"

#Create the proxies we'll need to execute commands
ttsproxy = ALProxy("ALTextToSpeech", "localhost", 9559)
walkproxy = ALProxy("ALMotion", "localhost", 9559)

'''
#These aren't needed right now but might be in the future

bmproxy = ALProxy("ALBehaviorManager", "localhost", 9559)
adproxy = ALProxy("ALAudioDevice", "localhost", 9559)

'''

def dVFloat (dic, key, val):
  #Parse a dictionary element as a float if it exists, otherwise default to (val).
  return float(dic[key]) if key in dic else val

class MaoHandler (BaseHTTPServer.BaseHTTPRequestHandler):
  def do_GET(self):
    #Parse the given path
    parsed = urlparse.urlparse(self.path)
    path = parsed.path.split("/")
    qwargs = urlparse.parse_qs(parsed.query)

    #Enforce one value per query string argument
    for key in qwargs:
      qwargs[key] = qwargs[key][0]
    
    print path

    if len(path) < 2 or path[1] == '' or path[1] == "index.html":
      index_file = open("index.html")
      self.send_response(200)
      self.send_header("Content-type", "text/html")
      self.end_headers()
      self.wfile.write(index_file.read())
    if path[1] == "src-noconflict":
      rfile = open("/".join(path[1:]))
      self.send_response(200)
      self.send_header("Content-type", "text/plain")
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
        ttsproxy.post.say(tosay) #TODO maybe daemonize this, so as to respond more quickly.
        
        #Reply that we've said it.
        reply["success"] = True

      elif qwargs["command"] == 'move':
        #Initiate a walk command in our walk proxy
        walkproxy.stiffnessInterpolation("Body", 1, 0.1)
        walkproxy.walkInit()

        #Walk. Turn by "turn" radians, then move fowards by "forward", right by "right" meters.
        walkproxy.walkTo(dVFloat(qwargs, "forward", 0), dVFloat(qwargs, "right", 0), dVFloat(qwargs, "turn", 0))
        
        #Reply with success.
        reply["success"] = True

      elif qwargs["command"] == "halt":
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
      
      else:
        #Otherwise, we have no idea what's going on.
        reply["success"] = False
        reply["error"] = "Unknown command."
    
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
      code = urllib.unquote(urlparse.parse_qs(self.wfile.read())["code"][0])
      lines = interpreter.fullParse(open(sys.argv[1]).read())
      for line in lines:
        interpreter.line.evaluate(global_scope)

    self.send_response(200)
    self.send_header("Content-Type", "application/json")
    self.end_headers()
    self.wfile.write(simplejson.dumps(reply))

if __name__ == "__main__":
  print "Starting server on port 8080."
  httpd = BaseHTTPServer.HTTPServer(('', 8080), MaoHandler)
  httpd.serve_forever()
