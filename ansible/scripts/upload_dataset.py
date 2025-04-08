from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
import os
import subprocess

app = Flask(__name__)

UPLOAD_FOLDER = '/mnt/uploads'
SPLIT_SCRIPT = './scripts/split_uploaded_fasta.py'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

@app.route('/upload', methods=['POST'])
def upload():
    file = request.files.get('file')
    email = request.form.get('email')

    if not email:
        return jsonify({'status': 'error', 'message': 'Email is required'}), 400

    if file and file.filename.endswith('.fasta'):
        filename = secure_filename(file.filename)
        local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(local_path)

        # Optionally store the email for notification
        with open(f"{local_path}.email", "w") as f:
            f.write(email)

        split_command = f"python3 {SPLIT_SCRIPT} {local_path}"
        result = subprocess.run(split_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        if result.returncode != 0:
            return jsonify({'status': 'error', 'message': result.stderr.decode()}), 500
        else:
            return jsonify({'status': 'success', 'message': f'File processed. We\'ll email you at {email}'}), 200
    else:
        return jsonify({'status': 'error', 'message': 'Only .fasta files are allowed'}), 400


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
