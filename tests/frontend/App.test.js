// App.test.js
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../../frontend/react-ui/src/App';

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
    expect(screen.getByText(/Internal Results/i)).toBeInTheDocument();
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
