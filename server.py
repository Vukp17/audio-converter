from flask import Flask, request, jsonify
import os
from datetime import datetime
from pydub import AudioSegment

app = Flask(__name__)

UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'wav', 'flac'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def convert_audio(input_file, output_file):
    audio = AudioSegment.from_file(input_file)
    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
    audio.export(output_file, format='wav')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'audioFile' not in request.files:
        return jsonify({'message': 'No file part'}), 400

    file = request.files['audioFile']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        file_number = request.form['fileNumber']
        file_name = request.form['fileName']
        filename = f"{file_number}_{file_name}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.wav"
        file.save(os.path.join(UPLOAD_FOLDER, filename))

        # Perform conversion if necessary
        if file.filename.lower().endswith('.flac'):
            input_file = os.path.join(UPLOAD_FOLDER, filename)
            output_file = os.path.join(UPLOAD_FOLDER, filename.replace('.flac', '.wav'))
            convert_audio(input_file, output_file)
            os.remove(input_file)  # Remove original FLAC file
            filename = filename.replace('.flac', '.wav')

        return jsonify({
            'message': 'File uploaded successfully',
            'filename': filename,
            'format': '16-bit PCM, 16 KSPS, MONO'
        }), 200

    return jsonify({'message': 'Invalid file format'}), 400

if __name__ == '__main__':
    app.run(debug=True)
