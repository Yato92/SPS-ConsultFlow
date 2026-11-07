import axios from 'axios';
import type {
  Client,
  ClientPortal,
  Dashboard,
  BotUserRow,
  Notification,
  OrderDetail,
  OrderList,
  PricingInfo,
  TokenResponse,
  User,
  UserBrief,
} from './types';

export const TOKEN_KEY = 'consultflow_token';

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL ?? '/api',
  timeout: 25000,
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    const path = window.location.pathname;
    if (status === 401 && !['/login', '/magic', '/client'].includes(path)) {
      localStorage.removeItem(TOKEN_KEY);
      window.location.href = '/login';
    }
    return Promise.reject(error);
  },
);

export function getApiError(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((item) => item?.msg ?? String(item))
        .filter(Boolean)
        .join('; ');
    }
    if (error.code === 'ERR_NETWORK') {
      return 'Сервер недоступен. Проверьте, что backend запущен на порту 8000.';
    }
    if (error.response?.status === 403) return 'Недостаточно прав для этой операции';
  }
  return 'Не удалось выполнить запрос. Попробуйте ещё раз.';
}

const clean = <T extends object>(params: T): Record<string, unknown> =>
  Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== undefined && value !== null && value !== '',
    ),
  );

export async function loginRequest(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/login', { email, password });
  return data;
}

export async function magicRequest(token: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>('/auth/magic', { token });
  return data;
}

export async function clientPortalRequest(token: string): Promise<ClientPortal> {
  const { data } = await api.get<ClientPortal>('/client/portal', { params: { token } });
  return data;
}

export async function meRequest(): Promise<User> {
  const { data } = await api.get<User>('/auth/me');
  return data;
}

export interface DashboardParams {
  date_from?: string;
  date_to?: string;
  practice?: string;
}

export async function fetchDashboard(params: DashboardParams): Promise<Dashboard> {
  const { data } = await api.get<Dashboard>('/dashboard', { params: clean(params) });
  return data;
}

export interface OrdersParams {
  q?: string;
  status?: string;
  practice?: string;
  manager_id?: number;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
  sort_by?: string;
  sort_dir?: 'asc' | 'desc';
  include_deleted?: boolean;
}

export async function fetchOrders(params: OrdersParams): Promise<OrderList> {
  const { data } = await api.get<OrderList>('/orders', { params: clean(params) });
  return data;
}

export async function fetchOrder(id: number): Promise<OrderDetail> {
  const { data } = await api.get<OrderDetail>(`/orders/${id}`);
  return data;
}

export async function fetchClients(search?: string): Promise<{ items: Client[]; total: number }> {
  const { data } = await api.get<{ items: Client[]; total: number }>('/clients', {
    params: clean({ search, limit: 500 }),
  });
  return data;
}

export async function fetchManagers(): Promise<UserBrief[]> {
  const { data } = await api.get<UserBrief[]>('/users', { params: { role: 'manager' } });
  return data;
}

export async function fetchBotUsers(): Promise<BotUserRow[]> {
  const { data } = await api.get<BotUserRow[]>('/telegram/users');
  return data;
}

export async function fetchNotifications(): Promise<Notification[]> {
  const { data } = await api.get<Notification[]>('/telegram/notifications', {
    params: { limit: 50 },
  });
  return data;
}

export async function fetchPricing(): Promise<PricingInfo> {
  const { data } = await api.get<PricingInfo>('/dashboard/pricing');
  return data;
}

export async function changeOrderStatus(
  id: number,
  status: string,
  comment?: string,
): Promise<OrderDetail> {
  const { data } = await api.post<OrderDetail>(`/orders/${id}/status`, { status, comment });
  return data;
}

export async function updateOrder(
  id: number,
  payload: Record<string, unknown>,
): Promise<unknown> {
  const { data } = await api.patch(`/orders/${id}`, payload);
  return data;
}

export async function generateDocument(
  orderId: number,
  docType: string,
): Promise<{ id: number }> {
  const { data } = await api.post(`/orders/${orderId}/documents`, { doc_type: docType });
  return data;
}

export async function deleteOrder(id: number): Promise<OrderDetail> {
  const { data } = await api.delete<OrderDetail>(`/orders/${id}`);
  return data;
}

export async function restoreOrder(id: number): Promise<OrderDetail> {
  const { data } = await api.post<OrderDetail>(`/orders/${id}/restore`);
  return data;
}

export async function signDocument(orderId: number, documentId: number): Promise<unknown> {
  const { data } = await api.post(`/orders/${orderId}/documents/${documentId}/sign`);
  return data;
}

export async function downloadOrdersCsv(): Promise<void> {
  const response = await api.get('/orders/export/csv', { responseType: 'blob' });
  const url = URL.createObjectURL(response.data as Blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = 'consultflow-orders.csv';
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
