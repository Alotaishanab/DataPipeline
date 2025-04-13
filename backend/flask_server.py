from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = '/mnt/data_volume/uploads'
USER_DATASETS_FOLDER = '/mnt/data_volume/datasets/user_chunks'
INTERNAL_DATASETS_FOLDER = '/mnt/data_volume/datasets/internal_chunks'
RESULTS_FOLDER = '/mnt/data_volume/results'

SPLIT_SCRIPT = './scripts/split_uploaded_fasta.py'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    email = request.form.get('email')

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400

    if file and (file.filename.endswith('.fasta') or file.filename.endswith('.fasta.gz')):
        filename = secure_filename(file.filename)
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(local_path)

        with open(f"{local_path}.email", "w") as f:
            f.write(email)

        split_command = f"python3 {SPLIT_SCRIPT} {local_path}"
        result = subprocess.run(split_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            return jsonify({'status': 'error', 'message': result.stderr.decode()}), 500
        else:
            return jsonify({'status': 'success', 'message': f'File processed. We\'ll email you at {email}'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Only .fasta or .fasta.gz files are allowed'}), 400

@app.route('/api/datasets', methods=['GET'])
def list_datasets():
    try:
        def list_files(folder, label):
            return [{'name': f, 'type': label} for f in sorted(os.listdir(folder))
                    if os.path.isfile(os.path.join(folder, f))]
        internal = list_files(INTERNAL_DATASETS_FOLDER, 'internal')
        user = list_files(USER_DATASETS_FOLDER, 'user')
        return jsonify({'datasets': internal + user})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/datasets/internal/<path:filename>')
def serve_internal_dataset(filename):
    return send_from_directory(INTERNAL_DATASETS_FOLDER, filename)

@app.route('/datasets/user/<path:filename>')
def serve_user_dataset(filename):
    return send_from_directory(USER_DATASETS_FOLDER, filename)

@app.route('/results/internal/<path:filename>')
def serve_internal_result(filename):
    return send_from_directory(os.path.join(RESULTS_FOLDER, 'internal_outputs'), filename)

@app.route('/results/user/<path:filename>')
def serve_user_result(filename):
    return send_from_directory(os.path.join(RESULTS_FOLDER, 'user_outputs'), filename)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
