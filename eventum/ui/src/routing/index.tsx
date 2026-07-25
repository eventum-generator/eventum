import { createBrowserRouter } from 'react-router-dom';

import { RootBoundary, RouteError } from './boundaries';
import { routes } from './config';

export const router = createBrowserRouter([
  {
    element: <RootBoundary />,
    errorElement: <RouteError />,
    children: routes,
  },
]);
