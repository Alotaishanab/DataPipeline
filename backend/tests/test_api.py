import io
import pytest
from flask_server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    return app.test_client()

# Test invalid upload: wrong file extension
@pytest.mark.parametrize('filename, content', [
    ('test.txt', b'invalid content'),
    ('test.fa', b'invalid content')
])
def test_upload_invalid_file(client, filename, content):
    data = {'file': (io.BytesIO(content), filename)}
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'Only .fasta or .fasta.gz files are allowed' in response.get_data(as_text=True)

# Prevent actual subprocess calls in upload
@pytest.fixture(autouse=True)
def no_op_split(monkeypatch):
    monkeypatch.setattr('flask_server.subprocess.run',
                        lambda *args, **kwargs: type('R', (), {'returncode': 0, 'stderr': b''})())

# Test successful upload entry point
@pytest.mark.parametrize('filename', ['file.fasta', 'file.fasta.gz'])
def test_upload_success_start_processing(client, filename):
    data = {'file': (io.BytesIO(b'>seq\nATCG'), filename)}
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data['status'] == 'success'
    assert 'job_id' in json_data

# Test datasets listing endpoint
def test_datasets_endpoint(client):
    response = client.get('/api/datasets')
    assert response.status_code == 200
    data = response.get_json()
    assert 'datasets' in data and isinstance(data['datasets'], list)
