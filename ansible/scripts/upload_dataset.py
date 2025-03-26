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
  <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@400;600;700&display=swap" rel="stylesheet">
  <style>
    /* Global Reset & Styles */
    * { box-sizing: border-box; }
    body {
      margin: 0;
      padding: 0;
      font-family: 'Montserrat', sans-serif;
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
    /* Headings & Instructions */
    h1 {
      margin: 0 0 15px;
      font-size: 2em;
      font-weight: 700;
      color: #ffffff;
    }
    p.instructions {
      font-size: 14px;
      color: #c4c4c4;
      margin-bottom: 30px;
    }
    /* Form & Custom File Input */
    form {
      display: flex;
      flex-direction: column;
      gap: 20px;
    }
    /* Hide the default file input */
    #fileInput {
      display: none;
    }
    /* Custom File Button with dashed style */
    #customFileButton {
      padding: 15px;
      background-color: transparent;
      border: 2px dashed #00e676;
      border-radius: 10px;
      font-size: 16px;
      font-weight: 600;
      cursor: pointer;
      color: #00e676;
      transition: background-color 0.3s, color 0.3s;
    }
    #customFileButton:hover {
      background-color: #00e676;
      color: #2b2b3d;
    }
    #fileName {
      font-size: 14px;
      color: #c4c4c4;
      margin-top: 5px;
    }
    /* Submit Button */
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
    /* Progress Bar */
    #progressContainer {
      width: 100%;
      background-color: #3a3a4d;
      border-radius: 10px;
      overflow: hidden;
      margin-top: 20px;
      display: none;
    }
    #progressBar {
      height: 20px;
      width: 0%;
      background-color: #00e676;
      transition: width 0.4s ease;
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
    <form id="uploadForm" method="POST" enctype="multipart/form-data">
      <input type="file" id="fileInput" name="file" accept=".csv" required>
      <button type="button" id="customFileButton">Choose File</button>
      <div id="fileName"></div>
      <input type="submit" value="Upload & Run Pipeline">
      <div id="progressContainer">
        <div id="progressBar"></div>
      </div>
    </form>
    {% if message %}
      <div class="message {{ status }}">{{ message }}</div>
    {% endif %}
    <footer>
      © {{ year }} Data Pipeline UI – Made with <span>UCABBAA</span>
    </footer>
  </div>
  <script>
    // Trigger hidden file input when custom button is clicked
    document.getElementById('customFileButton').addEventListener('click', function() {
      document.getElementById('fileInput').click();
    });
    
    // Display selected file name
    document.getElementById('fileInput').addEventListener('change', function(){
      var file = document.getElementById('fileInput').files[0];
      document.getElementById('fileName').textContent = file ? file.name : '';
    });
    
    // Intercept form submission to implement AJAX file upload with progress bar
    document.getElementById('uploadForm').addEventListener('submit', function(e) {
      e.preventDefault();
      var fileInput = document.getElementById('fileInput');
      if (!fileInput.files[0]) {
        alert("Please select a CSV file.");
        return;
      }
      var formData = new FormData();
      formData.append('file', fileInput.files[0]);
      
      var xhr = new XMLHttpRequest();
      xhr.open('POST', '/', true);
      
      // Update progress bar
      xhr.upload.addEventListener('progress', function(e) {
        if (e.lengthComputable) {
          var percent = (e.loaded / e.total) * 100;
          document.getElementById('progressContainer').style.display = 'block';
          document.getElementById('progressBar').style.width = percent + '%';
        }
      });
      
      xhr.onload = function() {
        if (xhr.status === 200) {
          // Replace the document with the updated response (includes message notifications)
          document.open();
          document.write(xhr.responseText);
          document.close();
        } else {
          alert("Upload failed. Please try again.");
        }
      };
      
      xhr.send(formData);
    });
  </script>
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
