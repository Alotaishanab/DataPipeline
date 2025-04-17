// frontend/react-ui/src/__tests__/Results.test.js
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import Results from '../pages/Results';

beforeEach(() => {
  global.fetch = jest.fn((url) => {
    if (url === '/api/results') {
      return Promise.resolve({
        json: () =>
          Promise.resolve({
            internal: ['result1.json'],
            user_folders: ['job123'],
          }),
      });
    }
    if (url.startsWith('/api/results/user/')) {
      return Promise.resolve({
        json: () => Promise.resolve({ files: ['user_result1.json'] }),
      });
    }
    return Promise.resolve({ json: () => Promise.resolve({}) });
  });
});

describe('Results Page', () => {
  test('renders internal results', async () => {
    render(<Results />);
    await waitFor(() => screen.getByText(/result1\.json/i));
    expect(screen.getByText(/result1\.json/i)).toBeInTheDocument();
  });

  test('renders user results', async () => {
    render(<Results />);
    await waitFor(() => screen.getByText(/user_result1\.json/i));
    expect(screen.getByText(/user_result1\.json/i)).toBeInTheDocument();
  });
});
