# test_api.py

import os
import io
import pytest
import tempfile
from flask_server import app

@pytest.fixture
def client():
    app.config['TESTING'] = True
    client = app.test_client()
    yield client


def test_upload_invalid_file(client):
    data = {
        'email': 'test@example.com',
        'file': (io.BytesIO(b'invalid content'), 'test.txt')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'Only .fasta or .fasta.gz files are allowed' in response.get_data(as_text=True)


def test_upload_missing_email(client):
    data = {
        'file': (io.BytesIO(b'>seq\nATCG'), 'test.fasta')
    }
    response = client.post('/upload', data=data, content_type='multipart/form-data')
    assert response.status_code == 400
    assert 'Email is required' in response.get_data(as_text=True)


def test_datasets_endpoint(client):
    response = client.get('/api/datasets')
    assert response.status_code == 200
    assert 'datasets' in response.get_json()


def test_static_file_serving(client):
    # Simulate a file in the internal datasets directory
    internal_path = '/mnt/data_volume/datasets/internal_chunks'
    user_path = '/mnt/data_volume/datasets/user_chunks'
    results_internal = '/mnt/data_volume/results/internal_outputs'
    results_user = '/mnt/data_volume/results/user_outputs'

    os.makedirs(internal_path, exist_ok=True)
    os.makedirs(user_path, exist_ok=True)
    os.makedirs(results_internal, exist_ok=True)
    os.makedirs(results_user, exist_ok=True)

    for folder, route in [
        (internal_path, '/datasets/internal/test.txt'),
        (user_path, '/datasets/user/test.txt'),
        (results_internal, '/results/internal/test.txt'),
        (results_user, '/results/user/test.txt')
    ]:
        file_path = os.path.join(folder, 'test.txt')
        with open(file_path, 'w') as f:
            f.write('content')
        res = client.get(route)
        assert res.status_code == 200
        assert res.data == b'content'
