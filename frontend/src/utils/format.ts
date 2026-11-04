import dayjs from 'dayjs';

const rub = new Intl.NumberFormat('ru-RU', {
  style: 'currency',
  currency: 'RUB',
  maximumFractionDigits: 0,
});

const rubCompact = new Intl.NumberFormat('ru-RU', {
  notation: 'compact',
  maximumFractionDigits: 1,
});

const number = new Intl.NumberFormat('ru-RU');

export const money = (value: number | null | undefined): string =>
  rub.format(Number(value ?? 0));

export const moneyCompact = (value: number | null | undefined): string =>
  `${rubCompact.format(Number(value ?? 0))} ₽`;

export const num = (value: number | null | undefined): string =>
  number.format(Number(value ?? 0));

export const date = (value: string | null | undefined): string =>
  value ? dayjs(value).format('DD.MM.YYYY') : '—';

export const dateTime = (value: string | null | undefined): string =>
  value ? dayjs(value).format('DD.MM.YYYY HH:mm') : '—';

export const percent = (value: number | null | undefined, digits = 0): string =>
  `${(Number(value ?? 0) * 100).toFixed(digits)} %`;

export const initials = (name: string): string =>
  name
    .split(' ')
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase())
    .join('');

export const overdueDays = (value: string | null): number => {
  if (!value) return 0;
  const diff = dayjs().diff(dayjs(value), 'day');
  return diff > 0 ? diff : 0;
};
