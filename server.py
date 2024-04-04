from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import cgi
from urllib.parse import urlparse, parse_qs, unquote
from pydub import AudioSegment
from datetime import datetime
import json

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'flac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_audio(input_file, output_file):
    audio = AudioSegment.from_file(input_file)
    # Convert to desired format (16-bit PCM, 16 KSPS, MONO)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    # Export to WAV format
    audio.export(output_file, format='wav')

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "x-api-key,Content-Type")

    def do_GET(self):
        if self.path.startswith('/uploads/'):
            file_path = os.path.join('.', unquote(self.path[1:]))
            print("File path:", file_path)
            if os.path.isfile(file_path):
                with open(file_path, 'rb') as f:
                    self.send_response(200)
                    self.send_header('Content-type', 'audio/wav')
                    self.end_headers()
                    self.wfile.write(f.read())
            else:
                self.send_response(404)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'File not found'}).encode())
        else:
            self.send_response(404)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({'message': 'Not found'}).encode())

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

        content_type, pdict = cgi.parse_header(self.headers.get('content-type', ''))
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

        if 'audioFile' not in form or 'sequenceNumber' not in form:
            self.send_response(400, 'Bad Request')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write("Missing file or sequence number".encode())
            return

        file_item = form['audioFile']
        sequence_number = form['sequenceNumber'].value.strip()

        if not sequence_number.isdigit():
            self.send_response(400, 'Bad Request')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write("Sequence number must be a positive integer".encode())
            return

        if file_item.filename:
            filename = os.path.basename(file_item.filename)
            if allowed_file(filename):
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)

                file_extension = filename.split('.')[-1]
                wav_filename = f"{sequence_number}_{datetime.now().strftime('%Y-%m-%d_%H%M%S')}.wav"
                wav_path = os.path.join(UPLOAD_FOLDER, wav_filename)

                # Check if file with the same name already exists
                if os.path.exists(wav_path):
                    print(f"File {wav_path} already exists.")
                    feedback_message = f"File with this number already exists."
                    self.send_response(400, 'Bad Request')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({'message': feedback_message}).encode())
                    return

                # Convert audio file to WAV format (if needed)
                if file_extension.lower() == 'flac':
                    convert_audio(file_item.file, wav_path)
                else:
                    with open(wav_path, 'wb') as output_file:
                        output_file.write(file_item.file.read())

                # Debugging: Log the uploaded file path
                print("Uploaded file path:", wav_path)

                # Provide feedback to the user
                feedback_message = f"File uploaded and processed successfully: {wav_path}. Format: 16-bit PCM, 16 KSPS, MONO."
                download_url = f"http://{self.headers['Host']}/uploads/{wav_filename}"
                self.send_response(200, 'OK')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'message': feedback_message, 'download_url': download_url}).encode())

            else:
                self.send_response(400, 'Bad Request')
                self._send_cors_headers()
                self.end_headers()
                self.wfile.write(json.dumps({'message': 'Invalid file format'}).encode())
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
