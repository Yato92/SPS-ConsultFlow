export type UserRole = 'admin' | 'manager' | 'consultant' | 'lawyer' | 'finance';
export type OrderStatus =
  | 'new'
  | 'clarification'
  | 'qualified'
  | 'proposal'
  | 'revision'
  | 'approved'
  | 'contract'
  | 'in_progress'
  | 'done'
  | 'closed'
  | 'cancelled';
export type Practice = 'management' | 'finance' | 'legal' | 'it';

export interface UserBrief {
  id: number;
  full_name: string;
  role: string;
}

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  telegram_id: number | null;
  is_active: boolean;
}

export interface Client {
  id: number;
  name: string;
  inn: string | null;
  contact_person: string | null;
  email: string | null;
  phone: string | null;
  telegram_id: number | null;
  created_at: string;
  orders_count?: number;
  paid_total?: number;
  profit?: number;
}

export interface Order {
  id: number;
  number: string;
  title: string;
  description: string | null;
  practice: Practice;
  status: OrderStatus;
  amount: number;
  paid_amount: number;
  expenses: number;
  deadline: string | null;
  sla_due_at: string | null;
  source: string;
  created_at: string;
  updated_at: string;
  closed_at: string | null;
  is_overdue: boolean;
  is_deleted: boolean;
  deleted_at: string | null;
  client: Client;
  manager: UserBrief | null;
}

export interface OrderEvent {
  id: number;
  from_status: OrderStatus | null;
  to_status: OrderStatus;
  comment: string | null;
  actor_type: string;
  actor_id: number | null;
  created_at: string;
}

export interface DocumentPayload {
  title: string;
  number: string;
  body: string;
  meta: Record<string, string>;
}

export interface OrderDocument {
  id: number;
  doc_type: string;
  number: string;
  status: string;
  payload: DocumentPayload;
  created_at: string;
}

export interface OrderDetail extends Order {
  events: OrderEvent[];
  documents: OrderDocument[];
}

export interface OrderList {
  items: Order[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface Summary {
  orders_total: number;
  active_orders: number;
  closed_orders: number;
  amount_total: number;
  paid_total: number;
  expenses_total: number;
  profit: number;
  avg_check: number;
  conversion: number;
  overdue_count: number;
  avg_cycle_days: number;
}

export interface MonthlyPoint {
  month: string;
  label: string;
  orders: number;
  paid: number;
  expenses: number;
  profit: number;
}

export interface PracticeStat {
  practice: Practice;
  label: string;
  orders: number;
  amount: number;
  paid: number;
  expenses: number;
  profit: number;
}

export interface StatusStat {
  status: OrderStatus;
  label: string;
  count: number;
  amount: number;
}

export interface ManagerStat {
  manager_id: number | null;
  name: string;
  orders: number;
  paid: number;
  profit: number;
}

export interface Dashboard {
  summary: Summary;
  monthly: MonthlyPoint[];
  by_practice: PracticeStat[];
  by_status: StatusStat[];
  managers: ManagerStat[];
  recent_orders: Order[];
  overdue_orders: Order[];
  generated_at: string;
}

export interface BotUser {
  id: number;
  telegram_id: number;
  username: string | null;
  full_name: string;
  role: string;
  user_id: number | null;
}

export interface BotUserRow extends BotUser {
  orders_count: number;
  created_at: string;
}

export interface Notification {
  id: number;
  order_id: number | null;
  recipient: string;
  text: string;
  created_at: string;
}

export interface PricingInfo {
  practices: { value: string; label: string; rate: number; sla_hours: number }[];
  complexities: { value: string; label: string; multiplier: number }[];
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface ClientPortalDocument {
  id: number;
  type: string;
  name: string;
  status: string;
  created_at: string;
}

export interface ClientPortalOrder {
  id: number;
  number: string;
  title: string;
  description: string | null;
  status: string;
  status_label: string;
  practice: string;
  practice_label: string;
  amount: number;
  paid_amount: number;
  created_at: string;
  sla_due_at: string | null;
  is_overdue: boolean;
  documents: ClientPortalDocument[];
}

export interface ClientPortal {
  client_name: string;
  contact_person: string | null;
  orders: ClientPortalOrder[];
}
