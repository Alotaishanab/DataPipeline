from flask import Flask, request, render_template_string
from werkzeug.utils import secure_filename
import os
import subprocess
import datetime

app = Flask(__name__)

# Configurations
UPLOAD_FOLDER = '/mnt/uploads'
SPLIT_SCRIPT = './scripts/split_uploaded_fasta.py'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Minimal, clean HTML template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Upload FASTA Dataset</title>
  <style>
    body {
      font-family: Arial, sans-serif;
      background-color: #202124;
      color: #fff;
      display: flex;
      height: 100vh;
      justify-content: center;
      align-items: center;
    }
    .container {
      background: #2d2e32;
      padding: 30px;
      border-radius: 12px;
      box-shadow: 0 0 10px rgba(0,0,0,0.5);
      width: 400px;
      text-align: center;
    }
    input[type="file"] {
      display: block;
      margin: 20px auto;
    }
    input[type="submit"] {
      padding: 10px 20px;
      background-color: #00e676;
      color: #202124;
      border: none;
      border-radius: 8px;
      font-weight: bold;
      cursor: pointer;
    }
    .message {
      margin-top: 20px;
      padding: 10px;
      border-radius: 6px;
    }
    .success {
      background-color: #1b5e20;
    }
    .error {
      background-color: #b71c1c;
    }
  </style>
</head>
<body>
  <div class="container">
    <h2>Upload Your FASTA Dataset</h2>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file" accept=".fasta" required>
      <input type="submit" value="Upload & Process">
    </form>
    {% if message %}
    <div class="message {{ status }}">{{ message }}</div>
    {% endif %}
  </div>
</body>
</html>
'''

@app.route('/', methods=['GET', 'POST'])
def upload():
    message = ''
    status = ''
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.fasta'):
            filename = secure_filename(file.filename)
            local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(local_path)

            # Trigger your split script
            split_command = f"python3 {SPLIT_SCRIPT} {local_path}"
            result = subprocess.run(split_command, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if result.returncode != 0:
                message = "❌ Error processing file: " + result.stderr.decode()
                status = "error"
            else:
                message = "✅ File uploaded and sent for processing."
                status = "success"
        else:
            message = "❌ Only .fasta files are allowed."
            status = "error"

    return render_template_string(HTML_TEMPLATE, message=message, status=status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
