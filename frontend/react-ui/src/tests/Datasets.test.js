// frontend/react-ui/src/__tests__/Datasets.test.js
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import Datasets from '../pages/Datasets';

beforeEach(() => {
  global.fetch = jest.fn(() =>
    Promise.resolve({
      json: () =>
        Promise.resolve({
          datasets: [{ name: 'chunk_001.fasta.gz', type: 'internal' }],
        }),
    })
  );
});

describe('Datasets Page', () => {
  test('renders dataset list on successful fetch', async () => {
    render(<Datasets />);
    await waitFor(() => screen.getByText(/chunk_001\.fasta\.gz/i));
    expect(screen.getByText(/chunk_001\.fasta\.gz/i)).toBeInTheDocument();
  });

  test('shows no‑items message if none are returned', async () => {
    fetch.mockImplementationOnce(() =>
      Promise.resolve({
        json: () => Promise.resolve({ datasets: [] }),
      })
    );
    render(<Datasets />);
    await waitFor(() => screen.getByText(/🚫 No items found\./i));
    expect(screen.getByText(/🚫 No items found\./i)).toBeInTheDocument();
  });
});
