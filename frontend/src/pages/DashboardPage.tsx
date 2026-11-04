import {
  AimOutlined,
  ArrowRightOutlined,
  CalculatorOutlined,
  ClockCircleOutlined,
  ReloadOutlined,
  RiseOutlined,
  ShoppingOutlined,
  WalletOutlined,
} from '@ant-design/icons';
import { App, Button, Empty, Segmented, Select, Skeleton, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Area,
  CartesianGrid,
  Cell,
  ComposedChart,
  Line,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import { useDashboard } from '@/api/queries';
import type { Order, PracticeStat } from '@/api/types';
import { KpiCard } from '@/components/KpiCard';
import { ChartCard, PageHeader } from '@/components/PageHeader';
import { PracticePill, StatusPill } from '@/components/StatusPill';
import {
  CHART_COLORS,
  PRACTICE_META,
  PRACTICE_OPTIONS,
  PERIODS,
  STATUS_META,
} from '@/constants';
import { date, money, moneyCompact, num, overdueDays, percent } from '@/utils/format';

function ChartTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div
      style={{
        background: '#fff',
        border: '1px solid #E9EBF3',
        borderRadius: 12,
        padding: '10px 12px',
        boxShadow: '0 10px 30px rgba(16,24,40,0.12)',
        fontSize: 12,
      }}
    >
      <div style={{ fontWeight: 650, marginBottom: 6 }}>{label}</div>
      {payload.map((item: any) => (
        <div
          key={item.dataKey}
          style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 2 }}
        >
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: 3,
              background: item.color ?? item.stroke,
            }}
          />
          <span style={{ color: '#6b7280' }}>{item.name}</span>
          <span style={{ marginLeft: 'auto', fontWeight: 600 }}>{money(item.value)}</span>
        </div>
      ))}
    </div>
  );
}

function MonthlyChart({ data }: { data: { label: string; paid: number; expenses: number; profit: number }[] }) {
  return (
    <div className="chart-wrap" style={{ height: 290 }}>
      <ResponsiveContainer width="100%" height="100%">
        <ComposedChart data={data} margin={{ top: 8, right: 6, left: -14, bottom: 0 }}>
          <defs>
            <linearGradient id="paidFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS.paid} stopOpacity={0.28} />
              <stop offset="100%" stopColor={CHART_COLORS.paid} stopOpacity={0.02} />
            </linearGradient>
            <linearGradient id="expensesFill" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={CHART_COLORS.expenses} stopOpacity={0.18} />
              <stop offset="100%" stopColor={CHART_COLORS.expenses} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="4 4" vertical={false} stroke={CHART_COLORS.grid} />
          <XAxis
            dataKey="label"
            tickLine={false}
            axisLine={false}
            tick={{ fill: '#9aa0ae', fontSize: 11 }}
            dy={6}
          />
          <YAxis
            tickLine={false}
            axisLine={false}
            tick={{ fill: '#9aa0ae', fontSize: 11 }}
            tickFormatter={(value) => moneyCompact(value)}
            width={72}
          />
          <Tooltip content={<ChartTooltip />} cursor={{ stroke: '#dfe3f0', strokeWidth: 1 }} />
          <Area
            type="monotone"
            dataKey="paid"
            name="Оплачено"
            stroke={CHART_COLORS.paid}
            strokeWidth={2.4}
            fill="url(#paidFill)"
          />
          <Area
            type="monotone"
            dataKey="expenses"
            name="Расходы"
            stroke={CHART_COLORS.expenses}
            strokeWidth={2}
            fill="url(#expensesFill)"
          />
          <Line
            type="monotone"
            dataKey="profit"
            name="Результат"
            stroke={CHART_COLORS.profit}
            strokeWidth={2.2}
            dot={false}
          />
        </ComposedChart>
      </ResponsiveContainer>
    </div>
  );
}

function PracticeDonut({ items }: { items: PracticeStat[] }) {
  const data = items
    .filter((item) => item.paid > 0)
    .map((item) => ({
      name: PRACTICE_META[item.practice]?.label ?? item.label,
      value: item.paid,
      color: PRACTICE_META[item.practice]?.color ?? '#6068F8',
    }));
  const total = data.reduce((sum, item) => sum + item.value, 0);

  if (!data.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Нет оплат" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      <div className="chart-wrap" style={{ height: 190 }}>
        <ResponsiveContainer width="100%" height="100%">
          <PieChart>
            <Pie
              data={data}
              dataKey="value"
              nameKey="name"
              innerRadius={58}
              outerRadius={84}
              paddingAngle={3}
              stroke="none"
            >
              {data.map((item) => (
                <Cell key={item.name} fill={item.color} />
              ))}
            </Pie>
            <Tooltip
              formatter={(value: any) => money(Number(value))}
              contentStyle={{
                borderRadius: 12,
                border: '1px solid #E9EBF3',
                boxShadow: '0 10px 30px rgba(16,24,40,0.12)',
                fontSize: 12,
              }}
            />
          </PieChart>
        </ResponsiveContainer>
        <div className="donut-center">
          <div className="donut-center__value">{moneyCompact(total)}</div>
          <div className="donut-center__label">оплачено</div>
        </div>
      </div>
      <div className="legend-list">
        {data.map((item) => (
          <div className="legend-row" key={item.name}>
            <span className="legend-row__dot" style={{ background: item.color }} />
            <span className="legend-row__name">{item.name}</span>
            <span className="legend-row__value">
              {Math.round((item.value / total) * 100)}%
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}

function StatusBreakdown({ data }: { data: { status: string; label: string; count: number; amount: number }[] }) {
  const total = data.reduce((sum, item) => sum + item.count, 0);
  if (!data.length) return <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Нет данных" />;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
      {data.map((item) => {
        const meta = STATUS_META[item.status as keyof typeof STATUS_META];
        const share = total ? Math.round((item.count / total) * 100) : 0;
        return (
          <div key={item.status}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 5 }}>
              <span
                style={{
                  width: 8,
                  height: 8,
                  borderRadius: 3,
                  background: meta?.color ?? '#8c8c8c',
                }}
              />
              <span style={{ fontSize: 12.5, color: '#4b5163', flex: 1 }}>
                {meta?.label ?? item.label}
              </span>
              <span style={{ fontSize: 12, color: '#8a90a2' }}>
                {item.count} · {moneyCompact(item.amount)}
              </span>
            </div>
            <div style={{ height: 6, borderRadius: 6, background: '#F2F3FA' }}>
              <div
                style={{
                  width: `${share}%`,
                  minWidth: item.count ? 6 : 0,
                  height: '100%',
                  borderRadius: 6,
                  background: meta?.color ?? '#8c8c8c',
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

function PracticePerformance({ items }: { items: PracticeStat[] }) {
  const max = Math.max(...items.map((item) => item.paid), 1);
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {items.map((item) => {
        const meta = PRACTICE_META[item.practice];
        return (
          <div key={item.practice}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
              <PracticePill practice={item.practice} />
              <span style={{ fontSize: 11.5, color: '#8a90a2' }}>{item.orders} заказов</span>
              <span
                style={{
                  marginLeft: 'auto',
                  fontSize: 12.5,
                  fontWeight: 650,
                  fontVariantNumeric: 'tabular-nums',
                }}
              >
                {money(item.paid)}
              </span>
            </div>
            <div style={{ height: 7, borderRadius: 6, background: '#F2F3FA' }}>
              <div
                style={{
                  width: `${Math.max((item.paid / max) * 100, item.paid ? 4 : 0)}%`,
                  height: '100%',
                  borderRadius: 6,
                  background: meta?.color ?? '#6068F8',
                  opacity: 0.85,
                }}
              />
            </div>
          </div>
        );
      })}
    </div>
  );
}

export function DashboardPage() {
  const navigate = useNavigate();
  const [period, setPeriod] = useState<string>('all');
  const [practice, setPractice] = useState<string | undefined>(undefined);

  const params = useMemo(() => {
    if (period === 'all') return { practice };
    return {
      practice,
      date_from: dayjs().subtract(Number(period), 'day').format('YYYY-MM-DD'),
      date_to: dayjs().format('YYYY-MM-DD'),
    };
  }, [period, practice]);

  const { data, isLoading, isError, refetch, isFetching } = useDashboard(params);

  const orderColumns: ColumnsType<Order> = [
    {
      title: 'Заказ',
      dataIndex: 'number',
      render: (value: string, row) => (
        <div>
          <div className="cell-strong">{value}</div>
          <div className="cell-muted" style={{ maxWidth: 260, overflow: 'hidden', textOverflow: 'ellipsis' }}>
            {row.title}
          </div>
        </div>
      ),
    },
    {
      title: 'Клиент',
      dataIndex: ['client', 'name'],
      responsive: ['lg'],
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      render: (value) => <StatusPill status={value} />,
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      align: 'right',
      render: (value: number) => <span className="mono cell-strong">{money(value)}</span>,
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      align: 'right',
      responsive: ['md'],
      render: (value: string) => <span className="cell-muted">{date(value)}</span>,
    },
  ];

  if (isLoading) {
    return (
      <>
        <PageHeader title="Обзор" subtitle="Загрузка показателей…" />
        <div className="kpi-grid">
          {Array.from({ length: 6 }).map((_, index) => (
            <div className="kpi-card" key={index}>
              <Skeleton active paragraph={{ rows: 1 }} title={{ width: '70%' }} />
            </div>
          ))}
        </div>
        <div style={{ marginTop: 16 }}>
          <Skeleton active paragraph={{ rows: 8 }} />
        </div>
      </>
    );
  }

  if (isError || !data) {
    return (
      <>
        <PageHeader title="Обзор" />
        <ChartCard title="Не удалось загрузить данные">
          <Empty description="Проверьте соединение с API и повторите попытку.">
            <Button type="primary" icon={<ReloadOutlined />} onClick={() => refetch()}>
              Повторить
            </Button>
          </Empty>
        </ChartCard>
      </>
    );
  }

  const { summary } = data;
  const margin = summary.paid_total
    ? Math.round((summary.profit / summary.paid_total) * 100)
    : 0;
  const expensesShare = summary.paid_total
    ? Math.round((summary.expenses_total / summary.paid_total) * 100)
    : 0;

  return (
    <>
      <PageHeader
        title="Обзор"
        subtitle={
          <>
            Ключевые показатели обработки заказов на консалтинговые услуги.
            <span style={{ color: '#a3a8b6' }}>
              {' '}
              Обновлено {dayjs(data.generated_at).format('HH:mm')}
            </span>
          </>
        }
        actions={
          <>
            <Segmented
              options={PERIODS}
              value={period}
              onChange={(value) => setPeriod(String(value))}
            />
            <Select
              allowClear
              placeholder="Все направления"
              options={PRACTICE_OPTIONS}
              value={practice}
              onChange={setPractice}
              style={{ width: 190 }}
            />
            <Button icon={<ReloadOutlined />} loading={isFetching} onClick={() => refetch()}>
              Обновить
            </Button>
          </>
        }
      />

      <div className="kpi-grid">
        <KpiCard
          label="Заказов"
          value={num(summary.orders_total)}
          hint={`${summary.active_orders} в работе · ${summary.closed_orders} закрыто`}
          icon={<ShoppingOutlined />}
          tone="primary"
        />
        <KpiCard
          label="Оплачено"
          value={money(summary.paid_total)}
          hint={`средний чек ${money(summary.avg_check)}`}
          icon={<WalletOutlined />}
          tone="success"
        />
        <KpiCard
          label="Расходы"
          value={money(summary.expenses_total)}
          hint={`${expensesShare}% от оплат`}
          icon={<CalculatorOutlined />}
          tone="warning"
        />
        <KpiCard
          label="Финансовый результат"
          value={money(summary.profit)}
          hint={`маржа ${margin}%`}
          icon={<RiseOutlined />}
          tone="cyan"
        />
        <KpiCard
          label="Конверсия"
          value={percent(summary.conversion)}
          hint={`${summary.closed_orders} из ${summary.orders_total} закрыто`}
          icon={<AimOutlined />}
          tone="violet"
        />
        <KpiCard
          label="Просрочено SLA"
          value={num(summary.overdue_count)}
          hint={summary.overdue_count ? 'требуют внимания' : 'всё в норме'}
          icon={<ClockCircleOutlined />}
          tone={summary.overdue_count ? 'danger' : 'success'}
        />
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.7fr) minmax(0, 1fr)',
          gap: 16,
          marginTop: 16,
        }}
      >
        <ChartCard
          title="Динамика оплат и расходов"
          extra="по месяцам регистрации заказов"
        >
          <MonthlyChart data={data.monthly} />
          <div style={{ display: 'flex', gap: 18, marginTop: 6, paddingLeft: 6 }}>
            {[
              { label: 'Оплачено', color: CHART_COLORS.paid },
              { label: 'Расходы', color: CHART_COLORS.expenses },
              { label: 'Результат', color: CHART_COLORS.profit },
            ].map((item) => (
              <span
                key={item.label}
                style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#6b7280' }}
              >
                <span style={{ width: 8, height: 8, borderRadius: 3, background: item.color }} />
                {item.label}
              </span>
            ))}
          </div>
        </ChartCard>

        <ChartCard title="Структура оплат" extra="по направлениям">
          <PracticeDonut items={data.by_practice} />
        </ChartCard>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)',
          gap: 16,
          marginTop: 16,
        }}
      >
        <ChartCard title="Направления консалтинга" extra="оплачено">
          <PracticePerformance items={data.by_practice} />
        </ChartCard>
        <ChartCard title="Воронка статусов" extra={`${summary.orders_total} заказов`}>
          <StatusBreakdown data={data.by_status} />
        </ChartCard>
      </div>

      <div style={{ marginTop: 16 }}>
        <ChartCard
          title="Последние заказы"
          extra={
            <Button
              type="link"
              size="small"
              icon={<ArrowRightOutlined />}
              iconPosition="end"
              onClick={() => navigate('/orders')}
            >
              Все заказы
            </Button>
          }
        >
          <Table<Order>
            className="cf-table"
            rowKey="id"
            dataSource={data.recent_orders}
            columns={orderColumns}
            pagination={false}
            size="small"
            onRow={(row) => ({ onClick: () => navigate(`/orders?order=${row.id}`) })}
          />
        </ChartCard>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)',
          gap: 16,
          marginTop: 16,
        }}
      >
        <ChartCard title="Менеджеры" extra="по оплатам">
          {data.managers.length === 0 ? (
            <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="Нет данных" />
          ) : (
            <div>
              {data.managers.slice(0, 5).map((manager, index) => (
                <div className="rank-row" key={`${manager.manager_id}-${index}`}>
                  <span className="rank-row__index">{index + 1}</span>
                  <span className="rank-row__name">{manager.name}</span>
                  <span style={{ fontSize: 11.5, color: '#8a90a2' }}>{manager.orders} зак.</span>
                  <span className="rank-row__value">{money(manager.paid)}</span>
                </div>
              ))}
            </div>
          )}
        </ChartCard>

        <ChartCard
          title="Просрочено по SLA"
          extra={
            summary.overdue_count > 0 ? (
              <Tag color="error" bordered={false}>
                {summary.overdue_count}
              </Tag>
            ) : (
              'нет'
            )
          }
        >
          {data.overdue_orders.length === 0 ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Все заявки обрабатываются в срок"
            />
          ) : (
            <div>
              {data.overdue_orders.map((order) => (
                <div
                  className="overdue-item"
                  key={order.id}
                  style={{ cursor: 'pointer' }}
                  onClick={() => navigate(`/orders?order=${order.id}`)}
                >
                  <span className="overdue-item__icon">
                    <ClockCircleOutlined />
                  </span>
                  <div style={{ minWidth: 0, flex: 1 }}>
                    <div className="overdue-item__title">
                      {order.number} · {order.title}
                    </div>
                    <div className="overdue-item__meta">
                      {order.client.name} · просрочка {overdueDays(order.sla_due_at)} дн.
                    </div>
                  </div>
                  <span style={{ fontSize: 11.5, color: '#f03d3d', fontWeight: 600 }}>
                    {overdueDays(order.sla_due_at)} дн.
                  </span>
                </div>
              ))}
            </div>
          )}
        </ChartCard>
      </div>

      <div style={{ marginTop: 14, fontSize: 11.5, color: '#a3a8b6', textAlign: 'right' }}>
        Данные учебные · ConsultFlow · {dayjs().format('YYYY')}
      </div>
    </>
  );
}
