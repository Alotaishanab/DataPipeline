from flask import Flask, request, render_template_string
from werkzeug.utils import secure_filename
import os
import subprocess
import datetime

app = Flask(__name__)

# Configurations
UPLOAD_FOLDER = '/mnt/uploads'
HDFS_INPUT_DIR = '/user/input_data'
HDFS_OUTPUT_DIR = '/user/output_data'
PIPELINE_SCRIPT = '/home/almalinux/scripts/run_pipeline.py'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# HTML UI Template (Revolut-inspired)
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Upload Dataset</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap" rel="stylesheet">
  <style>
    /* Reset & Global Styles */
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 0;
      font-family: 'Inter', sans-serif;
      background: linear-gradient(135deg, #1f1c2c, #928dab);
      color: #e0e0e0;
      height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
    }
    /* Container */
    .container {
      width: 100%;
      max-width: 500px;
      background-color: #2b2b3d;
      padding: 40px;
      border-radius: 15px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.6);
      text-align: center;
    }
    /* Headings & Text */
    h1 {
      margin: 0 0 15px;
      font-size: 2em;
      font-weight: 600;
      color: #ffffff;
    }
    p.instructions {
      font-size: 14px;
      color: #c4c4c4;
      margin-bottom: 30px;
    }
    /* Form Elements */
    form {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    input[type="file"] {
      padding: 20px;
      background-color: #3a3a4d;
      border: 2px dashed #555;
      border-radius: 10px;
      color: #e0e0e0;
      transition: border-color 0.3s;
    }
    input[type="file"]:hover {
      border-color: #00e676;
    }
    input[type="submit"] {
      padding: 15px;
      background-color: #00e676;
      border: none;
      border-radius: 10px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      color: #2b2b3d;
      transition: background-color 0.3s;
    }
    input[type="submit"]:hover {
      background-color: #00c853;
    }
    /* Message Styles */
    .message {
      margin-top: 20px;
      padding: 15px;
      border-radius: 10px;
      font-size: 14px;
    }
    .success {
      background-color: #1b5e20;
      color: #a5d6a7;
    }
    .error {
      background-color: #b71c1c;
      color: #ffcdd2;
    }
    /* Footer */
    footer {
      margin-top: 30px;
      font-size: 12px;
      color: #888;
    }
    footer span {
      font-weight: 600;
      color: #00e676;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Upload Your Dataset</h1>
    <p class="instructions">
      Only <strong>CSV (.csv)</strong> files are accepted.<br>
      Ensure your dataset is formatted properly to avoid pipeline errors.
    </p>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file" required>
      <input type="submit" value="Upload & Run Pipeline">
    </form>
    {% if message %}
      <div class="message {{ status }}">{{ message }}</div>
    {% endif %}
    <footer>
      © {{ year }} Data Pipeline UI – Made with <span>UCABBAA</span>
    </footer>
  </div>
</body>
</html>
'''.replace('{{ year }}', str(datetime.datetime.now().year))


@app.route('/', methods=['GET', 'POST'])
def upload():
    message = ''
    status = ''
    if request.method == 'POST':
        file = request.files.get('file')
        if file and file.filename.endswith('.csv'):
            filename = secure_filename(file.filename)
            local_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(local_path)

            # Push to HDFS
            hdfs_put = f"hdfs dfs -mkdir -p {HDFS_INPUT_DIR} && hdfs dfs -put -f {local_path} {HDFS_INPUT_DIR}/"
            hdfs_result = subprocess.run(hdfs_put, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            if hdfs_result.returncode != 0:
                message = "Failed to upload to HDFS: " + hdfs_result.stderr.decode()
                status = "error"
            else:
                # Run Spark pipeline
                hdfs_input_path = f"{HDFS_INPUT_DIR}/{filename}"
                hdfs_output_path = f"{HDFS_OUTPUT_DIR}/{filename}.out"
                spark_submit = f"spark-submit {PIPELINE_SCRIPT} {hdfs_input_path} {hdfs_output_path}"
                spark_result = subprocess.run(spark_submit, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                if spark_result.returncode == 0:
                    message = f"✅ Success! Results saved to: {hdfs_output_path}"
                    status = "success"
                else:
                    message = "⚠️ Pipeline execution failed: " + spark_result.stderr.decode()
                    status = "error"
        else:
            message = "❌ Only .csv files are allowed."
            status = "error"

    return render_template_string(HTML_TEMPLATE, message=message, status=status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
