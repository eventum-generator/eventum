import { useNavigate } from 'react-router-dom';

import { ROUTE_PATHS } from '@/routing/paths';

/**
 * Opens the page secrets are managed on. Only for a caller rendered
 * inside the router: modal content is not, and passes a callback of
 * its own instead.
 */
export function useOpenSecretsPage(): () => void {
  const navigate = useNavigate();

  return () => void navigate(ROUTE_PATHS.SECRETS);
}
