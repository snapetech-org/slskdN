// <copyright file="PrimaryNavigation.test.jsx" company="slskdN Team">
// Copyright (c) slskdN Team. All rights reserved.
// </copyright>

import PrimaryNavigation from './PrimaryNavigation';
import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';

describe('PrimaryNavigation', () => {
  it('links the Overview entry to the default dashboard route', () => {
    render(
      <MemoryRouter>
        <PrimaryNavigation
          isAgent={false}
          navActivity={{ chat: false, rooms: false }}
          version={{ isCanary: false }}
        />
      </MemoryRouter>,
    );

    expect(screen.getByTestId('nav-dashboard')).toHaveTextContent('Overview');
    expect(screen.getByTestId('nav-dashboard').closest('a')).toHaveAttribute(
      'href',
      '/dashboard',
    );
    expect(screen.getByTestId('nav-dashboard').closest('a')).toHaveAttribute(
      'aria-label',
      'Overview',
    );
    expect(screen.getByTestId('nav-uploads').closest('a')).toHaveAttribute(
      'aria-label',
      'Uploads',
    );
    expect(screen.getByTestId('nav-group-discover')).toHaveAttribute(
      'aria-label',
      'Discover',
    );
  });
});
