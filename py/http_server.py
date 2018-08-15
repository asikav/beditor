#!/usr/bin/env python

import os
import re
import BaseHTTPServer
import urlparse
import mimetypes
import cgi
import json
import base64
import argparse

auth_key = ''

class BeditorServer(BaseHTTPServer.BaseHTTPRequestHandler):

    def start_response(self, code, headers):
        self.send_response(code)
        for h in headers:
            self.send_header(h[0], h[1])#'Content-type', 'text/html')
        self.end_headers()

    def content_file(self, path):
        s = open(path).read()
        self.start_response(200, [('Content-Type', mimetypes.guess_type(path)[0])])
        return s

    def content_success(self, ctype='text/html'):
        self.start_response(200, [('Content-Type', ctype)])
        return ''

    def content_bad_request(self):
        self.start_response(400, [('Content-Type', 'text/html')])
        return ''

    def content_unauthorized(self):
        self.start_response(401, [('Content-Type', 'text/html'), ('WWW-Authenticate', 'Basic realm=all')])
        return False

    def do_HEAD(self):
        self.send_headers()

    def do_GET(self):
        self.wfile.write(self.my_get())

    def do_POST(self):
        self.wfile.write(self.my_post())

    def authorized(self):
        if self.headers.getheader('Authorization') == None:
            return self.content_unauthorized()
        if self.headers.getheader('Authorization') != 'Basic ' + auth_key:
            return self.content_unauthorized()
        return True


    def my_get(self):

        if not self.authorized():
            return ''

        # print dir(self.headers)
        url_split = urlparse.urlsplit(self.path)
        path = url_split.path

        if re.match('/favicon.ico', path):
            return self.content_file('../img/favicon.ico')

        if re.match('/js/.+', path):
            return self.content_file('..' + path)

        if re.match('/codemirror/.+', path):
            return self.content_file('..' + path)

        if re.match('/bootstrap-3.3.7-dist/.+', path):
            return self.content_file('..' + path)

        if re.match('/load/.+', path):
            m = re.match('/load(.+)', path)
            dir_path = m.group(1)

            if os.path.isdir(dir_path):
                return self.content_file('../html/list.html')
            else:
                return self.content_file('../html/edit.html')

        if re.match('/do/load/.+', path):
            m = re.match('/do/load(.+)', path)
            dir_path = m.group(1)
            dir_path = dir_path.rstrip('/') + '/'

            if os.path.isdir(dir_path):

                try:
                    def make_dir_ref(root_ref, root_path, path):
                        if path == root_path:
                            return root_ref
                        opath = path
                        prefix = root_path
                        ref = root_ref
                        while True:
                            path = path[len(prefix):]
                            prefix = path.split('/')[0] + '/'
                            if prefix == path:
                                i = 0
                                for i in range(len(ref['nodes'])):
                                    if 'nodes' not in ref['nodes'][i] or ref['nodes'][i]['text'] > path:
                                        break
                                ref['nodes'].insert(i, {
                                    'text': path,
                                    'href': '/load' + opath,
                                    'nodes': list(),
                                    'state': {
                                        'expanded': False,
                                    },
                                })
                                ref = ref['nodes'][i]
                                break
                            for n in ref['nodes']:
                                if n['text'] == prefix:
                                    ref = n
                                    break
                        return ref

                    d = {
                        'text': dir_path,
                        'nodes': list(),
                        'state': {
                            'expanded': True,
                        },
                    }

                    for (dirpath, dirnames, filenames) in os.walk(dir_path):
                        dirpath = dirpath.rstrip('/') + '/'
                        ref = make_dir_ref(d, dir_path, dirpath)
                        for f in filenames:
                            ref['nodes'].append({
                                'text': f,
                                'href': '/load' + dirpath + f,
                            })
                            ref['nodes'].sort(key=lambda x: x['text'])

                    self.content_success(ctype='application/json')
                    return json.dumps(d)
                except Exception as e:
                    import traceback

                    traceback.print_exc()
                    print str(e)
                    print ("directory {} not found".format(dir_path))

            else:

                try:
                    return self.content_file(dir_path)
                except Exception as e:
                    print e
                    print ("file {} not found".format(dir_path))

        return self.content_bad_request()
        
    def my_post(self):

        if not self.authorized():
            return ''

        url_split = urlparse.urlsplit(self.path)
        path = url_split.path

        if re.match('/do/save/.+', path):
            m = re.match('/do/save(.+)', path)
            file_path = m.group(1)
            length = int(self.headers.getheader('content-length'))
            try:
                with open(file_path, 'w') as f:
                    f.write(self.rfile.read(length))
                return self.content_success()
            except:
                return self.content_bad_request()


if __name__ == "__main__":

    args = argparse.ArgumentParser()
    args.add_argument('--port', nargs=1, default=8080, type=int)
    args.add_argument('--username', nargs=1, required=True)
    args.add_argument('--password', nargs=1, required=True)
    args = args.parse_args()

    auth_key = base64.b64encode(args.username[0] + ':' + args.password[0])

    httpd = BaseHTTPServer.HTTPServer(('', args.port[0]), BeditorServer)
    httpd.serve_forever()

