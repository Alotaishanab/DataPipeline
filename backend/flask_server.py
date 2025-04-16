from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
import subprocess
import uuid

app = Flask(__name__)

# ────────────────────────────────────────────────
# Allow uploads up to 2 GB (adjust value if needed)
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 * 1024  # 2 GB
# ────────────────────────────────────────────────

UPLOAD_FOLDER              = '/mnt/data_volume/uploads'
USER_DATASETS_FOLDER       = '/mnt/data_volume/datasets/user_chunks'
INTERNAL_DATASETS_FOLDER   = '/mnt/data_volume/datasets/internal_chunks'
RESULTS_FOLDER             = '/mnt/data_volume/results'

SPLIT_SCRIPT = './split_uploaded_fasta.py'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ─────────────────────────── Upload endpoint ────────────────────────────────
@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    if not file or not (file.filename.endswith('.fasta') or file.filename.endswith('.fasta.gz')):
        return jsonify({'status': 'error',
                        'message': 'Only .fasta or .fasta.gz files are allowed'}), 400

    job_id  = str(uuid.uuid4())
    job_dir = os.path.join(UPLOAD_FOLDER, job_id)
    os.makedirs(job_dir, exist_ok=True)

    filename   = secure_filename(file.filename)
    local_path = os.path.join(job_dir, filename)
    file.save(local_path)

    cmd    = f"python3 {SPLIT_SCRIPT} {local_path} {job_id}"
    result = subprocess.run(cmd, shell=True,
                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        return jsonify({'status': 'error',
                        'message': result.stderr.decode(),
                        'job_id': job_id}), 500

    return jsonify({'status':  'success',
                    'message': 'File uploaded and processing started.',
                    'job_id':  job_id}), 200

# ─────────────────────────── Dataset listing APIs ───────────────────────────
@app.route('/api/datasets', methods=['GET'])
def list_datasets():
    try:
        def list_internal(folder, limit=20):
            files = sorted(
                f for f in os.listdir(folder)
                if f.endswith('.gz') and os.path.isfile(os.path.join(folder, f))
            )
            return [{'name': f, 'type': 'internal'} for f in files[:limit]]

        def list_user(folder):
            folders = sorted(
                f for f in os.listdir(folder)
                if os.path.isdir(os.path.join(folder, f))
            )
            return [{'name': f, 'type': 'user_folder'} for f in folders]

        return jsonify({'datasets': list_internal(INTERNAL_DATASETS_FOLDER) +
                                   list_user(USER_DATASETS_FOLDER)})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/datasets/user/<job_id>', methods=['GET'])
def list_files_in_user_folder(job_id):
    try:
        folder = os.path.join(USER_DATASETS_FOLDER, job_id)
        if not os.path.exists(folder):
            return jsonify({'error': 'Job ID not found'}), 404
        files = sorted(
            f for f in os.listdir(folder)
            if f.endswith('.gz') and os.path.isfile(os.path.join(folder, f))
        )
        return jsonify({'job_id': job_id, 'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────── Results listing APIs ───────────────────────────
@app.route('/api/results', methods=['GET'])
def list_results():
    try:
        internal_dir = os.path.join(RESULTS_FOLDER, 'internal_outputs')
        user_dir     = os.path.join(RESULTS_FOLDER, 'user_outputs')

        internal = sorted(
            f for f in os.listdir(internal_dir)
            if f.endswith('.json') and os.path.isfile(os.path.join(internal_dir, f))
        )
        user_folders = sorted(
            f for f in os.listdir(user_dir)
            if os.path.isdir(os.path.join(user_dir, f))
        )
        return jsonify({'internal': internal, 'user_folders': user_folders})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/results/user/<job_id>', methods=['GET'])
def list_user_results_by_job(job_id):
    try:
        folder = os.path.join(RESULTS_FOLDER, 'user_outputs', job_id)
        if not os.path.isdir(folder):
            return jsonify({'error': 'Job folder not found'}), 404
        files = sorted(
            f for f in os.listdir(folder)
            if f.endswith('.json') and os.path.isfile(os.path.join(folder, f))
        )
        return jsonify({'job_id': job_id, 'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ─────────────────────────── Static file serving ────────────────────────────
@app.route('/datasets/internal/<path:filename>')
def serve_internal_dataset(filename):
    return send_from_directory(INTERNAL_DATASETS_FOLDER, filename)

@app.route('/datasets/user/<job_id>/<path:filename>')
def serve_user_dataset(job_id, filename):
    return send_from_directory(os.path.join(USER_DATASETS_FOLDER, job_id), filename)

@app.route('/results/internal/<path:filename>')
def serve_internal_result(filename):
    return send_from_directory(os.path.join(RESULTS_FOLDER, 'internal_outputs'), filename)

@app.route('/results/user/<job_id>/<path:filename>')
def serve_user_result_file(job_id, filename):
    return send_from_directory(os.path.join(RESULTS_FOLDER, 'user_outputs', job_id), filename)

# ─────────────────────────── Legacy / HTML listings ─────────────────────────
@app.route('/results/internal/')
def list_internal_results():
    try:
        files = [f for f in sorted(os.listdir(
                os.path.join(RESULTS_FOLDER, 'internal_outputs'))) if f.endswith('.json')]
        return "\n".join(f'<a href="/results/internal/{f}">{f}</a><br>' for f in files)
    except Exception as e:
        return f"<p>Error: {e}</p>", 500

@app.route('/results/user/')
def list_user_results_legacy():
    try:
        base = os.path.join(RESULTS_FOLDER, 'user_outputs')
        links = []
        for job_id in sorted(os.listdir(base)):
            folder = os.path.join(base, job_id)
            if os.path.isdir(folder):
                links += [f'<a href="/results/user/{job_id}/{f}">{job_id}/{f}</a><br>'
                          for f in os.listdir(folder) if f.endswith('.json')]
        return "\n".join(links)
    except Exception as e:
        return f"<p>Error: {e}</p>", 500

@app.route('/results/user/manifest/<job_id>')
def get_user_manifest(job_id):
    manifest = os.path.join(USER_DATASETS_FOLDER, job_id, "manifest.json")
    if not os.path.isfile(manifest):
        return jsonify({'error': 'Manifest not found'}), 404
    with open(manifest) as f:
        return f.read()

# ─────────────────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
