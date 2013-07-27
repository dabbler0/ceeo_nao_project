#!/usr/bin/env python
import BaseHTTPServer
import urllib
import urlparse
import simplejson as json
import interpreter
import math

from naoqi import ALProxy

#Create the proxies we'll need to execute commands
ttsproxy = ALProxy('ALTextToSpeech', 'localhost', 9559)
walkproxy = ALProxy('ALMotion', 'localhost', 9559)
bmproxy = ALProxy('ALBehaviorManager', 'localhost', 9559)
netproxy = ALProxy('ALNetwork', 'localhost', 9559)

'''
#These aren't needed right now but might be in the future

adproxy = ALProxy('ALAudioDevice', 'localhost', 9559)

'''

def dVFloat (dic, key, val):
  #Parse a dictionary element as a float if it exists, otherwise default to (val).
  return float(dic[key]) if key in dic else val

class NaoHandler (BaseHTTPServer.BaseHTTPRequestHandler):
  def do_GET(self):
    #Parse the given path
    parsed = urlparse.urlparse(self.path)
    path = parsed.path.split('/')
    qwargs = urlparse.parse_qs(parsed.query)

    #Enforce one value per query string argument
    for key in qwargs:
      qwargs[key] = qwargs[key][0]
    
    print path

    if len(path) < 2 or path[1] == '' or path[1] == 'index.html':
      index_file = open('index.html')
      self.send_response(200)
      self.send_header('Content-type', 'text/html')
      self.end_headers()
      self.wfile.write(index_file.read())
      index_file.close()
    elif path[len(path) - 1] == 'favicon.ico':
      favicon_file = open('favicon.ico')
      self.send_response(200)
      self.send_header('Content-type', 'image/x-icon')
      self.end_headers()
      self.wfile.write(favicon_file.read())
      favicon_file.close()
    elif path[1] == 'getprograms':
      programsfile = open('programs.json')
      contents = json.load(programsfile)
      programsfile.close()
      self.send_response(200)
      self.send_header('Content-Type', 'application/json')
      self.end_headers()
      if not ('username' in qwargs): qwargs['username'] = ''
      if not (qwargs['username'] in contents):
      	contents[qwargs['username']] = {}
      	wprogramsfile = open('programs.json', 'w')
      	wprogramsfile.write(json.dumps(contents))
      	wprogramsfile.close()
      self.wfile.write(json.dumps(contents[qwargs['username']]))

  def do_POST(self):
    #Parse the given path
    parsed = urlparse.urlparse(self.path)
    path = parsed.path.split('/')
    qwargs = urlparse.parse_qs(parsed.query)

    #Enforce one value per query string argument
    for key in qwargs:
      qwargs[key] = qwargs[key][0]
    
    reply = {}
    
    if path[1] == 'code':
      length = int(self.headers.getheader('content-length'))
      postvars = urlparse.parse_qs(self.rfile.read(length), keep_blank_values = 1)
      code = urllib.unquote(postvars['code'][0])
      log = []
      interpreter.resetGlobalScope(log)
      lines = interpreter.fullParse(code)
      for line in lines:
        line.evaluate(interpreter.global_scope)
      print log
      reply['success'] = True
      reply['response'] = '\n'.join(log)
    elif path[1] == 'delprogram':
      programdata = json.loads(urllib.unquote(urlparse.parse_qs(self.rfile.read(int(self.headers.getheader('content-length'))), keep_blank_values = 1)['data'][0]))
      programsfile = open('programs.json')
      contents = json.load(programsfile)
      programsfile.close()
      reply['nameerror'] = True
      if programdata['name'] in contents[programdata['username']]:
        del(contents[programdata['username']][programdata['name']])
        wprogramsfile = open('programs.json', 'w')
        wprogramsfile.write(json.dumps(contents))
        wprogramsfile.close()
        reply['nameerror'] = False
    elif path[1] == 'addprogram':
      programdata = json.loads(urllib.unquote(urlparse.parse_qs(self.rfile.read(int(self.headers.getheader('content-length'))), keep_blank_values = 1)['data'][0]))
      programsfile = open('programs.json')
      contents = json.load(programsfile)
      programsfile.close()
      reply['success'] = False
      if not (programdata['name'] in contents[programdata['username']]):
        contents[programdata['username']][programdata['name']] = programdata['commands']
        wprogramsfile = open('programs.json', 'w')
        wprogramsfile.write(json.dumps(contents))
        wprogramsfile.close()
        reply['success'] = True
    elif path[1] == 'editprogram':
      programdata = json.loads(urllib.unquote(urlparse.parse_qs(self.rfile.read(int(self.headers.getheader('content-length'))), keep_blank_values = 1)['data'][0]))
      programsfile = open('programs.json')
      contents = json.load(programsfile)
      programsfile.close()
      reply['success'] = False
      if not (programdata['newname'] in contents[programdata['username']]) or programdata['newname'] == programdata['oldname']:
        if programdata['oldname'] in contents[programdata['username']]: del(contents[programdata['username']][programdata['oldname']])
        contents[programdata['username']][programdata['newname']] = programdata['commands']
        wprogramsfile = open('programs.json', 'w')
        wprogramsfile.write(json.dumps(contents))
        wprogramsfile.close()
        reply['success'] = True

    self.send_response(200)
    self.send_header('Content-Type', 'application/json')
    self.end_headers()
    self.wfile.write(json.dumps(reply))

if __name__ == '__main__':
  ip_address = netproxy.getLocalIP()
  print 'Starting server on %s:8080' % ip_address
  httpd = BaseHTTPServer.HTTPServer(('', 8080), NaoHandler)
  httpd.serve_forever()
