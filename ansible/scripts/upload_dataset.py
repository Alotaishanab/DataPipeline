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
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>Upload Dataset</title>
  <style>
    * { box-sizing: border-box; }

    body {
      margin: 0;
      padding: 0;
      font-family: "Inter", -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: #f5f7fa;
    }

    .container {
      max-width: 500px;
      margin: 80px auto;
      background: white;
      padding: 40px;
      border-radius: 20px;
      box-shadow: 0 10px 30px rgba(0, 0, 0, 0.06);
    }

    h1 {
      font-size: 26px;
      font-weight: 600;
      margin-bottom: 10px;
      color: #1b1f2b;
    }

    p.instructions {
      font-size: 14px;
      color: #6a707c;
      margin-bottom: 20px;
    }

    input[type="file"] {
      display: block;
      width: 100%;
      padding: 10px;
      margin-top: 10px;
      border: 2px dashed #d5d9e0;
      border-radius: 12px;
      background-color: #fafbfc;
      transition: border-color 0.2s;
    }

    input[type="file"]:hover {
      border-color: #0070f3;
    }

    input[type="submit"] {
      width: 100%;
      margin-top: 20px;
      background-color: #0070f3;
      color: white;
      font-weight: 600;
      font-size: 15px;
      padding: 12px;
      border: none;
      border-radius: 12px;
      cursor: pointer;
      transition: background-color 0.2s;
    }

    input[type="submit"]:hover {
      background-color: #0058d3;
    }

    .message {
      margin-top: 20px;
      font-weight: 500;
      padding: 12px;
      border-radius: 8px;
    }

    .success {
      color: #0a883e;
      background-color: #e4f6ea;
    }

    .error {
      color: #c82c2c;
      background-color: #ffe5e5;
    }

    footer {
      margin-top: 30px;
      font-size: 13px;
      color: #a1a7b3;
      text-align: center;
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>Upload Your Dataset</h1>
    <p class="instructions">
      Only <strong>CSV (.csv)</strong> files are accepted.<br/>
      Make sure your dataset is formatted properly to avoid pipeline errors.
    </p>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file" required />
      <input type="submit" value="Upload & Run Pipeline"/>
    </form>

    {% if message %}
      <div class="message {{ status }}">{{ message }}</div>
    {% endif %}

    <footer>© {{ year }} Data Pipeline UI</footer>
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
