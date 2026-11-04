import { Navigate, Outlet } from 'react-router-dom';
import { useAuth } from '@/auth/AuthContext';
import { FullScreenLoader } from './PageHeader';

export function ProtectedRoute() {
  const { user, loading } = useAuth();

  if (loading) return <FullScreenLoader />;
  if (!user) return <Navigate to="/login" replace />;
  return <Outlet />;
}
