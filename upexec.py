#!/usr/bin/python3

import http.server
import os
import random
import string
import subprocess

http_interface = '0.0.0.0'
http_port = 8080

# Use %input_file% and %output_file% to specify input/output files
command = 'upx -9 %input_file% -o%output_file%'
working_dir = './working_dir'
timeout = 600
DEBUG = True
CLEANUP = True


class http_server(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if DEBUG:
            self.send_response(200)
        else:
            self.send_response(404)
        self.send_header('server', 'nginx')
        self.send_header('content-type', 'text/html')
        self.end_headers()
        if DEBUG:
            self.wfile.write(bytes(f'curl -X POST --data-binary "@/path/to/file" http://server:{http_port}', 'utf-8'))

    def do_POST(self):
        # Create working dir and generate filenames
        try:
            os.mkdir(working_dir)
        except FileExistsError:
            pass
        rand = ''.join(random.choice(string.ascii_lowercase) for i in range(16))
        upload_file = f'{working_dir}/{rand}_a'
        result_file = f'{working_dir}/{rand}_b'

        # Save file
        file_length = int(self.headers['Content-Length'])
        read = 0
        with open(upload_file, 'wb') as file:
            while read < file_length:
                new_read = self.rfile.read(min(66556, file_length - read))
                read += len(new_read)
                file.write(new_read)

        # Replace stubs in command with actual files paths and run
        cmd = command.replace('%input_file%', upload_file)
        cmd = cmd.replace('%output_file%', result_file)
        result = subprocess.run(cmd.split(), capture_output=True, text=True, timeout=timeout)
        if DEBUG:
            print(f'Exit code: {result.returncode}\n{result.stdout}\n{result.stderr}')

        # Send data back
        if os.path.exists(result_file):
            self.send_response(200)
            self.send_header('server', 'nginx')
            self.send_header('content-type', 'application/octet-stream')
            self.end_headers()

            with open(result_file, 'rb') as file:
                result_file_data = file.read()
            self.wfile.write(result_file_data)

        else:
            self.send_response(500)
            self.send_header('server', 'nginx')
            self.send_header('content-type', 'text/html')
            self.end_headers()
            if DEBUG:
                self.wfile.write(bytes(f'Subprocess result: {result.stdout} {result.stderr}', 'utf-8'))

        # Remove processed files
        if CLEANUP:
            try:
                os.remove(upload_file)
                os.remove(result_file)
            except:
                pass


server = http.server.HTTPServer((http_interface, http_port), http_server)
server.serve_forever()
server.server_close()
