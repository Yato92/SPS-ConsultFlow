import {
  ArrowRightOutlined,
  DollarOutlined,
  SearchOutlined,
  ShoppingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Avatar, Card, Input, Table, Tag } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useClients } from '@/api/queries';
import type { Client } from '@/api/types';
import { KpiCard } from '@/components/KpiCard';
import { PageHeader } from '@/components/PageHeader';
import { date, initials, money, num } from '@/utils/format';

export function ClientsPage() {
  const navigate = useNavigate();
  const [search, setSearch] = useState('');
  const { data, isLoading } = useClients(search);

  const items = data?.items ?? [];

  const stats = useMemo(() => {
    const paid = items.reduce((sum, item) => sum + (item.paid_total ?? 0), 0);
    const orders = items.reduce((sum, item) => sum + (item.orders_count ?? 0), 0);
    return {
      paid,
      orders,
      avg: orders ? paid / orders : 0,
    };
  }, [items]);

  const columns: ColumnsType<Client> = [
    {
      title: 'Клиент',
      dataIndex: 'name',
      render: (value: string, row) => (
        <div style={{ display: 'flex', alignItems: 'center', gap: 11 }}>
          <Avatar
            size={34}
            style={{
              background: '#EEF0FF',
              color: '#4C55E8',
              fontWeight: 700,
              fontSize: 12,
              flex: 'none',
            }}
          >
            {initials(value)}
          </Avatar>
          <div style={{ minWidth: 0 }}>
            <div className="cell-strong" style={{ whiteSpace: 'normal' }}>
              {value}
            </div>
            <div className="cell-muted">{row.contact_person ?? '—'}</div>
          </div>
        </div>
      ),
    },
    {
      title: 'Контакты',
      key: 'contacts',
      render: (_, row) => (
        <div style={{ lineHeight: 1.5 }}>
          <div style={{ fontSize: 12.5 }}>{row.phone ?? '—'}</div>
          <div className="cell-muted">{row.email ?? '—'}</div>
        </div>
      ),
    },
    {
      title: 'Заказов',
      dataIndex: 'orders_count',
      align: 'center',
      width: 100,
      render: (value: number) => <Tag bordered={false}>{value ?? 0}</Tag>,
    },
    {
      title: 'Оплачено',
      dataIndex: 'paid_total',
      align: 'right',
      width: 150,
      render: (value: number) => <span className="mono cell-strong">{money(value)}</span>,
    },
    {
      title: 'Результат',
      dataIndex: 'profit',
      align: 'right',
      width: 150,
      render: (value: number) => (
        <span className="mono" style={{ color: value >= 0 ? '#1F9D3A' : '#E03A3A' }}>
          {money(value)}
        </span>
      ),
    },
    {
      title: 'В базе',
      dataIndex: 'created_at',
      align: 'right',
      width: 110,
      render: (value: string) => <span className="cell-muted">{date(value)}</span>,
    },
    {
      title: '',
      key: 'open',
      width: 46,
      render: () => <ArrowRightOutlined style={{ color: '#b6bac7' }} />,
    },
  ];

  return (
    <>
      <PageHeader
        title="Клиенты"
        subtitle="База компаний, история заказов и финансовый результат по каждому клиенту."
        actions={
          <Input
            allowClear
            prefix={<SearchOutlined style={{ color: '#a5aab8' }} />}
            placeholder="Поиск по названию, контакту, телефону"
            style={{ width: 320 }}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
          />
        }
      />

      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
        <KpiCard
          label="Клиентов"
          value={num(items.length)}
          hint="в активной базе"
          icon={<TeamOutlined />}
          tone="primary"
        />
        <KpiCard
          label="Заказов"
          value={num(stats.orders)}
          hint="за всё время"
          icon={<ShoppingOutlined />}
          tone="violet"
        />
        <KpiCard
          label="Оплачено"
          value={money(stats.paid)}
          hint="суммарно по клиентам"
          icon={<DollarOutlined />}
          tone="success"
        />
        <KpiCard
          label="Средний чек"
          value={money(stats.avg)}
          hint="на один заказ"
          icon={<UserOutlined />}
          tone="cyan"
        />
      </div>

      <Card className="cf-card" style={{ marginTop: 16 }} bodyStyle={{ padding: 6 }}>
        <Table<Client>
          className="cf-table"
          rowKey="id"
          loading={isLoading}
          dataSource={items}
          columns={columns}
          pagination={{ pageSize: 12, showSizeChanger: false }}
          onRow={(row) => ({
            onClick: () => navigate(`/orders?q=${encodeURIComponent(row.name)}`),
          })}
        />
      </Card>
    </>
  );
}
