import type { CSSProperties, ReactNode } from 'react';
import { Card, Spin } from 'antd';

export function PageHeader({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="cf-page-head">
      <div>
        <h1 className="cf-page-head__title">{title}</h1>
        {subtitle && <div className="cf-page-head__sub">{subtitle}</div>}
      </div>
      {actions && <div className="cf-page-head__actions">{actions}</div>}
    </div>
  );
}

export function ChartCard({
  title,
  extra,
  children,
  className,
  bodyStyle,
}: {
  title: ReactNode;
  extra?: ReactNode;
  children: ReactNode;
  className?: string;
  bodyStyle?: CSSProperties;
}) {
  return (
    <Card
      className={`cf-card ${className ?? ''}`}
      title={title}
      extra={extra}
      bodyStyle={bodyStyle}
    >
      {children}
    </Card>
  );
}

export function FullScreenLoader({ text = 'Загружаем данные…' }: { text?: string }) {
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        flexDirection: 'column',
        gap: 14,
        background: '#f4f5fa',
      }}
    >
      <Spin size="large" />
      <div style={{ color: '#6b7280', fontSize: 13 }}>{text}</div>
    </div>
  );
}
