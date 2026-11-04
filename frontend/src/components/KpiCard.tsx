import type { ReactNode } from 'react';

const TONES: Record<string, { bg: string; color: string }> = {
  primary: { bg: '#EEF0FF', color: '#4C55E8' },
  success: { bg: '#E9F8EC', color: '#1F9D3A' },
  warning: { bg: '#FFF6E6', color: '#C57C05' },
  danger: { bg: '#FFEFEF', color: '#E03A3A' },
  violet: { bg: '#F3EDFF', color: '#7A45D6' },
  cyan: { bg: '#E6FAF9', color: '#0E9C95' },
};

export function KpiCard({
  label,
  value,
  hint,
  icon,
  tone = 'primary',
}: {
  label: string;
  value: string;
  hint?: string;
  icon: ReactNode;
  tone?: keyof typeof TONES;
}) {
  const palette = TONES[tone] ?? TONES.primary;
  return (
    <div className="kpi-card">
      <div className="kpi-card__top">
        <span className="kpi-card__label">{label}</span>
        <span
          className="kpi-card__icon"
          style={{ background: palette.bg, color: palette.color }}
        >
          {icon}
        </span>
      </div>
      <div className="kpi-card__value">{value}</div>
      {hint && <div className="kpi-card__hint">{hint}</div>}
    </div>
  );
}
