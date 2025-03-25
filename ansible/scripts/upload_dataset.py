from flask import Flask, request, render_template_string
from werkzeug.utils import secure_filename
import os
import subprocess

app = Flask(__name__)

# Configurations
UPLOAD_FOLDER = '/mnt/uploads'
HDFS_INPUT_DIR = '/user/input_data'
HDFS_OUTPUT_DIR = '/user/output_data'
PIPELINE_SCRIPT = '/home/almalinux/scripts/run_pipeline.py'

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# HTML UI Template
HTML_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
  <title>Upload Dataset</title>
  <style>
    body { font-family: sans-serif; background: #f0f2f5; }
    .container {
      max-width: 600px;
      margin: 80px auto;
      background: white;
      padding: 40px;
      border-radius: 12px;
      box-shadow: 0 0 12px rgba(0, 0, 0, 0.1);
    }
    h2 { color: #222; margin-bottom: 20px; }
    input[type="file"] {
      width: 100%;
      padding: 10px;
    }
    input[type="submit"] {
      margin-top: 20px;
      background: #007bff;
      color: white;
      border: none;
      padding: 12px 20px;
      border-radius: 6px;
      cursor: pointer;
      font-weight: bold;
    }
    .message { margin-top: 20px; font-weight: bold; }
    .success { color: green; }
    .error { color: red; }
  </style>
</head>
<body>
  <div class="container">
    <h2>Upload Your CSV Dataset</h2>
    <form method="POST" enctype="multipart/form-data">
      <input type="file" name="file" required>
      <input type="submit" value="Upload & Run Pipeline">
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
                    message = f"Success! Results saved to: {hdfs_output_path}"
                    status = "success"
                else:
                    message = "Pipeline execution failed: " + spark_result.stderr.decode()
                    status = "error"
        else:
            message = "Only .csv files are allowed."
            status = "error"

    return render_template_string(HTML_TEMPLATE, message=message, status=status)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)