// Results.test.js
import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import Results from '../../src/pages/Results';

beforeEach(() => {
  global.fetch = jest.fn((path) => {
    const data = path.includes('internal')
      ? 'href="result1.json"'
      : 'href="user_result1.json"';
    return Promise.resolve({
      text: () => Promise.resolve(data),
    });
  });
});

describe('Results Page', () => {
  test('renders internal results', async () => {
    render(<Results />);
    await waitFor(() => screen.getByText(/result1.json/i));
    expect(screen.getByText(/result1.json/i)).toBeInTheDocument();
  });

  test('renders user results', async () => {
    render(<Results />);
    await waitFor(() => screen.getByText(/user_result1.json/i));
    expect(screen.getByText(/user_result1.json/i)).toBeInTheDocument();
  });
});
