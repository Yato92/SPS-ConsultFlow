import { useQuery } from '@tanstack/react-query';
import {
  fetchBotUsers,
  fetchClients,
  fetchDashboard,
  fetchManagers,
  fetchNotifications,
  fetchOrder,
  fetchOrders,
  fetchPricing,
} from '@/api/client';
import type { DashboardParams, OrdersParams } from '@/api/client';

export function useDashboard(params: DashboardParams) {
  return useQuery({
    queryKey: ['dashboard', params],
    queryFn: () => fetchDashboard(params),
    staleTime: 30_000,
    // Заявка из VK появляется без ручного обновления страницы.
    refetchInterval: 15_000,
    refetchOnWindowFocus: true,
  });
}

export function useOrders(params: OrdersParams) {
  return useQuery({
    queryKey: ['orders', params],
    queryFn: () => fetchOrders(params),
    placeholderData: (previous) => previous,
    refetchInterval: 15_000,
    refetchOnWindowFocus: true,
  });
}

export function useOrder(id: number | null) {
  return useQuery({
    queryKey: ['order', id],
    queryFn: () => fetchOrder(id as number),
    enabled: id !== null,
  });
}

export function useClients(search: string) {
  return useQuery({
    queryKey: ['clients', search],
    queryFn: () => fetchClients(search),
  });
}

export function useManagers() {
  return useQuery({
    queryKey: ['users', 'manager'],
    queryFn: fetchManagers,
    staleTime: 300_000,
  });
}

export function useBotUsers() {
  return useQuery({
    queryKey: ['telegram', 'users'],
    queryFn: fetchBotUsers,
  });
}

export function useNotifications() {
  return useQuery({
    queryKey: ['telegram', 'notifications'],
    queryFn: fetchNotifications,
    refetchInterval: 20_000,
  });
}

export function usePricing() {
  return useQuery({
    queryKey: ['pricing'],
    queryFn: fetchPricing,
    staleTime: 300_000,
  });
}
