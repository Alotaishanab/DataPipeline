// frontend/react-ui/src/__tests__/App.test.js
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

describe('App routing', () => {
  test('renders Home component on root route', () => {
    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByText(/UniRef50 Dataset Processor/i)).toBeInTheDocument();
  });

  test('renders Results page on /results route', () => {
    render(
      <MemoryRouter initialEntries={['/results']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByText(/Processed Dataset Chunks/i)).toBeInTheDocument();
  });

  test('renders Datasets page on /datasets route', () => {
    render(
      <MemoryRouter initialEntries={['/datasets']}>
        <App />
      </MemoryRouter>
    );
    expect(screen.getByText(/Available Datasets/i)).toBeInTheDocument();
  });
});
