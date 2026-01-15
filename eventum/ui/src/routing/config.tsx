import { lazy } from 'react';
import { RouteObject } from 'react-router-dom';

import { PrivateRoute, SignInRoute } from './guards';
import { ROUTE_PATHS } from './paths';
import AppLayout from '@/components/layout/AppLayout';
import BlankLayout from '@/components/layout/BlankLayout';
import FooterOnlyLayout from '@/components/layout/FooterOnlyLayout';

const SignInPage = lazy(
  () =>
    import('@/pages/SignInPage') as Promise<{
      default: React.ComponentType;
    }>
);
const OverviewPage = lazy(
  () =>
    import('@/pages/OverviewPage') as Promise<{
      default: React.ComponentType;
    }>
);
const InstancesPage = lazy(
  () =>
    import('@/pages/InstancesPage') as Promise<{
      default: React.ComponentType;
    }>
);
const InstancePage = lazy(
  () =>
    import('@/pages/InstancePage') as Promise<{
      default: React.ComponentType;
    }>
);
const ProjectsPage = lazy(
  () =>
    import('@/pages/ProjectsPage') as Promise<{
      default: React.ComponentType;
    }>
);
const ProjectPage = lazy(
  () =>
    import('@/pages/ProjectPage') as Promise<{
      default: React.ComponentType;
    }>
);
const SecretsPage = lazy(
  () =>
    import('@/pages/SecretsPage') as Promise<{
      default: React.ComponentType;
    }>
);
const SettingsPage = lazy(
  () =>
    import('@/pages/SettingsPage') as Promise<{
      default: React.ComponentType;
    }>
);
const ManagementPage = lazy(
  () =>
    import('@/pages/ManagementPage') as Promise<{
      default: React.ComponentType;
    }>
);
const NotFoundPage = lazy(
  () =>
    import('@/pages/NotFoundPage') as Promise<{
      default: React.ComponentType;
    }>
);

export const routes: RouteObject[] = [
  {
    path: ROUTE_PATHS.SIGNIN,
    element: (
      <SignInRoute>
        <FooterOnlyLayout>
          <SignInPage />
        </FooterOnlyLayout>
      </SignInRoute>
    ),
  },
  {
    path: ROUTE_PATHS.ROOT,
    element: (
      <PrivateRoute>
        <AppLayout />
      </PrivateRoute>
    ),
    children: [
      { index: true, element: <OverviewPage /> },
      { path: ROUTE_PATHS.INSTANCES, element: <InstancesPage /> },
      { path: ROUTE_PATHS.INSTANCE, element: <InstancePage /> },
      { path: ROUTE_PATHS.PROJECTS, element: <ProjectsPage /> },
      { path: ROUTE_PATHS.PROJECT, element: <ProjectPage /> },
      { path: ROUTE_PATHS.SECRETS, element: <SecretsPage /> },
      { path: ROUTE_PATHS.SETTINGS, element: <SettingsPage /> },
      { path: ROUTE_PATHS.MANAGEMENT, element: <ManagementPage /> },
    ],
  },
  {
    path: '*',
    element: (
      <BlankLayout>
        <NotFoundPage />
      </BlankLayout>
    ),
  },
];
