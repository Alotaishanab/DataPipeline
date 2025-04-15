from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import subprocess
import uuid

app = Flask(__name__)

UPLOAD_FOLDER = '/mnt/data_volume/uploads'
USER_DATASETS_FOLDER = '/mnt/data_volume/datasets/user_chunks'
INTERNAL_DATASETS_FOLDER = '/mnt/data_volume/datasets/internal_chunks'
RESULTS_FOLDER = '/mnt/data_volume/results'

SPLIT_SCRIPT = './split_uploaded_fasta.py'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')

    if not file or not (file.filename.endswith('.fasta') or file.filename.endswith('.fasta.gz')):
        return jsonify({'status': 'error', 'message': 'Only .fasta or .fasta.gz files are allowed'}), 400

    job_id = str(uuid.uuid4())
    job_dir = os.path.join(app.config['UPLOAD_FOLDER'], job_id)
    os.makedirs(job_dir, exist_ok=True)

    filename = secure_filename(file.filename)
    local_path = os.path.join(job_dir, filename)
    file.save(local_path)

    split_command = f"python3 {SPLIT_SCRIPT} {local_path} {job_id}"
    result = subprocess.run(split_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        return jsonify({
            'status': 'error',
            'message': result.stderr.decode(),
            'job_id': job_id
        }), 500

    return jsonify({
        'status': 'success',
        'message': 'File uploaded and processing started.',
        'job_id': job_id
    }), 200

@app.route('/api/datasets', methods=['GET'])
def list_datasets():
    try:
        def list_files(folder, label):
            dataset_entries = []

            # Internal datasets are stored flat (not in subfolders)
            if label == 'internal':
                for f in sorted(os.listdir(folder)):
                    full_path = os.path.join(folder, f)
                    if os.path.isfile(full_path) and f.endswith('.gz'):
                        dataset_entries.append({'name': f, 'type': label})
            else:
                # User datasets are stored in job_id subfolders
                for subdir in sorted(os.listdir(folder)):
                    subpath = os.path.join(folder, subdir)
                    if os.path.isdir(subpath):
                        for f in os.listdir(subpath):
                            if f.endswith('.gz'):
                                dataset_entries.append({'name': f, 'type': label, 'job_id': subdir})
            return dataset_entries

        internal = list_files(INTERNAL_DATASETS_FOLDER, 'internal')
        user = list_files(USER_DATASETS_FOLDER, 'user')
        return jsonify({'datasets': internal + user})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/datasets/internal/<path:filename>')
def serve_internal_dataset(filename):
    return send_from_directory(INTERNAL_DATASETS_FOLDER, filename)

@app.route('/datasets/user/<job_id>/<path:filename>')
def serve_user_dataset(job_id, filename):
    return send_from_directory(os.path.join(USER_DATASETS_FOLDER, job_id), filename)

@app.route('/results/internal/<path:filename>')
def serve_internal_result(filename):
    return send_from_directory(os.path.join(RESULTS_FOLDER, 'internal_outputs'), filename)

@app.route('/results/user/<path:filename>')
def serve_user_result(filename):
    return send_from_directory(os.path.join(RESULTS_FOLDER, 'user_outputs'), filename)

@app.route('/results/internal/')
def list_internal_results():
    try:
        files = sorted(os.listdir(os.path.join(RESULTS_FOLDER, 'internal_outputs')))
        files = [f for f in files if f.endswith('.json')]
        return "\n".join(f'<a href="/results/internal/{f}">{f}</a><br>' for f in files)
    except Exception as e:
        return f"<p>Error: {e}</p>", 500

@app.route('/results/user/')
def list_user_results():
    try:
        files = sorted(os.listdir(os.path.join(RESULTS_FOLDER, 'user_outputs')))
        files = [f for f in files if f.endswith('.json')]
        return "\n".join(f'<a href="/results/user/{f}">{f}</a><br>' for f in files)
    except Exception as e:
        return f"<p>Error: {e}</p>", 500

@app.route('/results/user/manifest/<job_id>')
def get_user_manifest(job_id):
    manifest_path = os.path.join(USER_DATASETS_FOLDER, job_id, "manifest.json")
    if not os.path.isfile(manifest_path):
        return jsonify({'error': 'Manifest not found'}), 404
    with open(manifest_path) as f:
        return f.read()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
