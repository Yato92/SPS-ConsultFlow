import type { OrderStatus, Practice } from '@/api/types';

export const STATUS_META: Record<
  OrderStatus,
  { label: string; color: string; short: string }
> = {
  new: { label: 'Новая заявка', color: '#6068F8', short: 'Новая' },
  clarification: { label: 'На уточнении', color: '#FA8C16', short: 'Уточнение' },
  qualified: { label: 'Квалифицирована', color: '#2F54EB', short: 'Квалификация' },
  proposal: { label: 'КП отправлено', color: '#FAAD14', short: 'КП' },
  revision: { label: 'На доработке', color: '#FA541C', short: 'Доработка' },
  approved: { label: 'КП согласовано', color: '#52C41A', short: 'Согласовано' },
  contract: { label: 'Договор подписан', color: '#13C2C2', short: 'Договор' },
  in_progress: { label: 'В работе', color: '#9254DE', short: 'В работе' },
  done: { label: 'Работы выполнены', color: '#389E0D', short: 'Выполнено' },
  closed: { label: 'Закрыт', color: '#8C8C8C', short: 'Закрыт' },
  cancelled: { label: 'Отменён', color: '#FF4D4F', short: 'Отменён' },
};

export const STATUS_ORDER: OrderStatus[] = [
  'new',
  'clarification',
  'qualified',
  'proposal',
  'revision',
  'approved',
  'contract',
  'in_progress',
  'done',
  'closed',
  'cancelled',
];

export const PRACTICE_META: Record<Practice, { label: string; color: string }> = {
  management: { label: 'Управленческий', color: '#6068F8' },
  finance: { label: 'Финансовый', color: '#13C2C2' },
  legal: { label: 'Юридический', color: '#FAAD14' },
  it: { label: 'IT-консалтинг', color: '#9254DE' },
};

export const PRACTICE_OPTIONS = (
  Object.keys(PRACTICE_META) as Practice[]
).map((value) => ({ value, label: PRACTICE_META[value].label }));

export const STATUS_OPTIONS = STATUS_ORDER.map((value) => ({
  value,
  label: STATUS_META[value].label,
}));

export const NEXT_STATUS: Partial<
  Record<OrderStatus, { value: OrderStatus; label: string }>
> = {
  new: { value: 'qualified', label: 'Квалифицировать' },
  clarification: { value: 'proposal', label: 'Отправить КП' },
  qualified: { value: 'proposal', label: 'Отправить КП' },
  proposal: { value: 'approved', label: 'КП согласовано' },
  revision: { value: 'proposal', label: 'Отправить обновлённое КП' },
  approved: { value: 'contract', label: 'Договор подписан' },
  contract: { value: 'in_progress', label: 'Взять в работу' },
  in_progress: { value: 'done', label: 'Работы выполнены' },
  done: { value: 'closed', label: 'Закрыть заказ' },
};

export const DOC_TYPE_META: Record<string, { label: string; color: string }> = {
  request: { label: 'Заявка', color: '#6068F8' },
  proposal: { label: 'Коммерческое предложение', color: '#FAAD14' },
  contract: { label: 'Договор', color: '#13C2C2' },
  act: { label: 'Акт выполненных работ', color: '#52C41A' },
  payment: { label: 'Чек об оплате', color: '#EB2F96' },
};

export const ROLE_LABELS: Record<string, string> = {
  admin: 'Администратор',
  manager: 'Менеджер',
  consultant: 'Консультант',
  lawyer: 'Юрист',
  finance: 'Финансист',
  client: 'Клиент',
};

export const PERIODS = [
  { value: '30', label: '30 дней' },
  { value: '90', label: '90 дней' },
  { value: '365', label: '12 месяцев' },
  { value: 'all', label: 'Всё время' },
];

export const CHART_COLORS = {
  paid: '#6068F8',
  expenses: '#FF9F43',
  profit: '#13C2C2',
  grid: '#ECEEF6',
};
