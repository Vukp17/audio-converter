from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import cgi
from urllib.parse import urlparse
from pydub import AudioSegment

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'flac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_audio(input_file, output_file):
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio.export(output_file, format='wav')

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "x-api-key,Content-Type")
    
    def do_POST(self):
        
        # Debugging: Log the incoming request path
        print("Incoming request path:", self.path)

        # Check if the request is intended for the /upload path
        if urlparse(self.path).path != '/upload':
            self.send_response(404, 'Not Found')
            self._send_cors_headers()
            self.end_headers()

            self.wfile.write("404 Not Found".encode())
            return

        content_type, pdict = cgi.parse_header(self.headers.get('content-type',''))
        if content_type != 'multipart/form-data':
            self.send_response(400, 'Bad Request')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write('POST request is multipart/form-data ! \n'.encode())
            return

        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST', 'CONTENT_TYPE': self.headers['Content-Type']}
        )

        if 'audioFile' not in form:
            self.send_response(400, 'Bad Request')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write("No file part".encode())
            return

        file_item = form['audioFile']
        if file_item.filename:
            filename = os.path.basename(file_item.filename)
            if allowed_file(filename):
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)

                file_path = os.path.join(UPLOAD_FOLDER, filename)
                with open(file_path, 'wb') as output_file:
                    output_file.write(file_item.file.read())

                # Debugging: Log the uploaded file path
                print("Uploaded file path:", file_path)

                # Check and perform conversion if necessary
                if filename.lower().endswith('.flac'):
                    wav_filename = filename.rsplit('.', 1)[0] + '.wav'
                    wav_path = os.path.join(UPLOAD_FOLDER, wav_filename)
                    convert_audio(file_path, wav_path)
                    os.remove(file_path)  # Remove the original file
                else:
                    wav_path = file_path
                    convert_audio(file_path, wav_path)

                self.send_response(200, 'OK')
                self._send_cors_headers()
                self.end_headers()

                self.wfile.write(f"File uploaded and processed successfully: {wav_path}".encode())
            else:
                self.send_response(400, 'Bad Request')
                self._send_cors_headers()
                self.end_headers()

                self.wfile.write("Invalid file format".encode())
        else:
            self.send_response(400, 'Bad Request')
            self._send_cors_headers()
            self.end_headers()
            
            self.wfile.write("No selected file".encode())

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting httpd on port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
