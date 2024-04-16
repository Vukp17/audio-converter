from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import cgi
from urllib.parse import urlparse, parse_qs, unquote
from pydub import AudioSegment
from datetime import datetime
import json

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'flac'}
LOGS = []

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# check for correct data signature in chunk data
def has_audio_signature(file):
    # Save current position in file
    current_position = file.tell()

    # Go to start of file
    file.seek(0)

    # Read the first 12 bytes of the file to check for signatures
    header = file.read(12)

    # Go back to original position
    file.seek(current_position)

    # Common headers for WAV and FLAC files
    # WAV files typically start with "RIFF" and "WAVE"
    # FLAC files start with "fLaC"
    if header.startswith(b'RIFF') and b'WAVE' in header[:12]:
        return True
    elif header.startswith(b'fLaC'):
        return True
    else:        
        return False

# convert audio 
def convert_audio(input_file, output_file):
    # First, check if the input file has an audio file signature
    if not has_audio_signature(input_file):
       return False
    else:
        try:
            audio = AudioSegment.from_file(input_file)
            # Convert to desired format (16-bit PCM, 16 KSPS, MONO)
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            # Export to WAV format
            audio.export(output_file, format='wav')
            return True
        except Exception as e:
            LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": "Failed to convert the file: {e}"})
            raise Exception("Failed to convert the file: {e}")

class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    

    # cors headers
    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
        self.send_header("Access-Control-Allow-Headers",
                         "x-api-key,Content-Type")
    #get requests
    def do_GET(self):
        
        
        if self.path == "/uploads.json":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
    
            files = []
            for i in os.listdir(UPLOAD_FOLDER):
               
                file = {"filename": i, 
                        "ctime": os.path.getctime(UPLOAD_FOLDER+"/"+i), 
                        "mtime": os.path.getmtime(UPLOAD_FOLDER+"/"+i), 
                        "size": os.path.getsize(UPLOAD_FOLDER+"/"+i)}
                files.append(file)
        
            self.wfile.write(json.dumps(files).encode())
            
            
        elif self.path == "/":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("index.html", "rb") as f:
                self.wfile.write(f.read())
            
            
        elif self.path == "/uploads":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("uploads.html", "rb") as f:
                self.wfile.write(f.read())
            
            
        elif self.path == "/logs":
            self.send_response(200)
            self.send_header("Content-type", "text/html")
            self.end_headers()
            with open("logs.html", "rb") as f:
                self.wfile.write(f.read())
        
        elif self.path == "/logs.json":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            
            self.wfile.write(json.dumps(LOGS).encode())

            
        else:
            self.send_response(404)
            self.send_header("Content-type", "text/html")
            self.end_headers()
    
    # post requests
    def do_POST(self):
        # Debugging: Log the incoming request path
        print("Incoming request path:", self.path)

        # Check if the request is intended for the /upload path
        if urlparse(self.path).path != '/upload':
            self.send_response(404, 'Not Found')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write("404 Not Found".encode())
            LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": '404 Not Found'})
            return 
        content_type, pdict = cgi.parse_header(self.headers.get('content-type', ''))
            
        if content_type != 'multipart/form-data':
            self.send_response(400, 'Bad Request')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(
                'POST request is multipart/form-data ! \n'.encode())
            LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": 'bad Request'})
            return     
        # user input form
        form = cgi.FieldStorage(
            fp=self.rfile,
            headers=self.headers,
            environ={'REQUEST_METHOD': 'POST',
                'CONTENT_TYPE': self.headers['Content-Type']}
        )
        # check for missing audioFile and/or sequenceNumber
        if 'audioFile' not in form or 'sequenceNumber' not in form:
            self.send_response(400, 'Bad Request')
            self._send_cors_headers()
            self.end_headers()
        
            msg="Missing file or sequence number"

            self.wfile.write(f'{msg}'.encode())
            LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": f'{msg}'})
            return

        file_item = form['audioFile']
        sequence_number = form['sequenceNumber'].value.strip()

        # check sequence number
        if not sequence_number.isdigit():
            self.send_response(400, 'Bad Request')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write(json.dumps({"message":"Sequence number must be a positive integer"}).encode())
            LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": "Sequence number must be a positive integer"})
            return
        
        # advanced
        #bit_rate = form['frameRate']
        #channels = form['channels']
        #width = form['sampleWidth']
        
        #if not bit_rate.isDigit() or not channels.isDigit() or not width.isDigit();
            #self.send_response(400, 'Bad Request')
            #self._send_cors_headers()
            #self.end_headers()
            #self.wfile(json.dumps({"message": "Frame rate, channels, sample width must be a positive integers"}).encode())
            #LOGS.append({"time": f'{datetime.now().strftime("%H:%M")}', "entry": "Frame rate, channels, sample width must be a positive integers"})


        #if channels != 1 or channels !=2:
            #self.send_response(400, 'Bad Request')
            #self._send_cors_headers()
            #self.end_headers()
            #self.wfile(json.dumps({"message": "Channel value can be only mono (1) or stereo (2)"}).encode())
            #LOGS.append({"time": f'{datetime.now().strftime("%H:%M")}', "entry": "Channel value can be only mono (1) or stereo (2)"})

        # check if correct format (and create upload folder if not exist)
        if file_item.filename:
            filename = os.path.basename(file_item.filename)
            if allowed_file(filename):
                if not os.path.exists(UPLOAD_FOLDER):
                    os.makedirs(UPLOAD_FOLDER)
                    
                # file name change to sequence + datetime
                wav_filename = f"{sequence_number}_{datetime.now().strftime('%Y-%m-%d_%H')}.wav"
                wav_path = os.path.join(UPLOAD_FOLDER, wav_filename)
                
                # check for duplicates
                if os.path.exists(wav_path):
                    print(f"File {wav_path} already exists.")
                    feedback_message = f"File with this number already exists."
                    self.send_response(400, 'Bad Request')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps(
                        {'message': feedback_message}).encode())
                    LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": '400 Bad Request'})
                    return

                try:
                    # Attempt to convert or save the uploaded file, handling potential corruption
                    if not convert_audio(file_item.file, wav_path):
                        LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": "Failed to convert audio file. The file may be corrupted."})
                        raise ValueError("Failed to convert audio file. The file may be corrupted.")
                except Exception as error:
                    self.send_response(400, 'Bad Request')
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(json.dumps({'message': f'Error processing the file: {error}'}).encode())
                    LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": 'Error processing the file'})
                    return


                # Debugging: Log the uploaded file path
                print("Uploaded file path:", wav_path)
                LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": 'Uploaded file path'})
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
                LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": "Invalid file format"})
        else:
            self.send_response(400, 'Bad Request')
            self._send_cors_headers()
            self.end_headers()
            self.wfile.write("No selected file".encode())
            LOGS.append({"time":f'{datetime.now().strftime("%H:%M")}', "entry": "No selected file"})

def run(server_class=HTTPServer, handler_class=SimpleHTTPRequestHandler, port=8000):
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    print(f"Starting port {port}...")
    httpd.serve_forever()

if __name__ == "__main__":
    run()
