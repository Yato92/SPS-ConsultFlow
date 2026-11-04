import { Button, Card, Empty, Result, Space, Spin, Tag, Typography } from 'antd';
import dayjs from 'dayjs';
import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { clientPortalRequest, getApiError } from '@/api/client';
import type { ClientPortal, ClientPortalOrder } from '@/api/types';

const { Title, Text, Paragraph } = Typography;

const STATUS_COLORS: Record<string, string> = {
  new: 'blue',
  clarification: 'gold',
  qualified: 'cyan',
  proposal: 'geekblue',
  revision: 'orange',
  approved: 'green',
  contract: 'purple',
  in_progress: 'processing',
  done: 'success',
  closed: 'default',
  cancelled: 'default',
};

const money = (value: number) =>
  new Intl.NumberFormat('ru-RU', {
    style: 'currency',
    currency: 'RUB',
    maximumFractionDigits: 0,
  }).format(value);

function OrderCard({ order }: { order: ClientPortalOrder }) {
  return (
    <Card
      style={{ marginBottom: 16, borderRadius: 14 }}
      title={
        <Space wrap>
          <span>Заявка №{order.number}</span>
          <Tag color={STATUS_COLORS[order.status] ?? 'default'}>{order.status_label}</Tag>
          {order.is_overdue && <Tag color="red">Просрочено</Tag>}
        </Space>
      }
    >
      <Title level={5} style={{ marginTop: 0 }}>
        {order.title}
      </Title>
      <Paragraph type="secondary" style={{ whiteSpace: 'pre-wrap' }}>
        {order.description || 'Описание не указано.'}
      </Paragraph>
      <Space size="large" wrap>
        <Text>
          Направление: <b>{order.practice_label}</b>
        </Text>
        <Text>
          Стоимость: <b>{money(order.amount)}</b>
        </Text>
        <Text>
          Оплачено: <b>{money(order.paid_amount)}</b>
        </Text>
        <Text type="secondary">Создана: {dayjs(order.created_at).format('DD.MM.YYYY HH:mm')}</Text>
        {order.sla_due_at && (
          <Text type={order.is_overdue ? 'danger' : 'secondary'}>
            Срок ответа: {dayjs(order.sla_due_at).format('DD.MM.YYYY')}
          </Text>
        )}
      </Space>
      <div style={{ marginTop: 16 }}>
        <Text strong>Документы</Text>
        {order.documents.length ? (
          <ul style={{ margin: '8px 0 0', paddingLeft: 20 }}>
            {order.documents.map((document) => (
              <li key={document.id}>
                {document.name} · {document.status} ·{' '}
                {dayjs(document.created_at).format('DD.MM.YYYY')}
              </li>
            ))}
          </ul>
        ) : (
          <Paragraph type="secondary" style={{ margin: '8px 0 0' }}>
            Документы появятся после согласования.
          </Paragraph>
        )}
      </div>
    </Card>
  );
}

export function ClientPortalPage() {
  const [params] = useSearchParams();
  const token = params.get('token');
  const [data, setData] = useState<ClientPortal | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(Boolean(token));

  useEffect(() => {
    if (!token) {
      setError('В ссылке нет токена. Откройте кабинет через кнопку «Кабинет» в VK-боте.');
      setLoading(false);
      return;
    }
    let cancelled = false;
    setLoading(true);
    clientPortalRequest(token)
      .then((payload) => {
        if (!cancelled) setData(payload);
      })
      .catch((err) => {
        if (!cancelled) setError(getApiError(err));
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [token]);

  if (loading) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center' }}>
        <Spin size="large" tip="Загружаем ваши заявки…" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={{ minHeight: '100vh', display: 'grid', placeItems: 'center', padding: 20 }}>
        <Result
          status="warning"
          title="Кабинет недоступен"
          subTitle={error ?? 'Ссылка недействительна или устарела.'}
          extra={
            <Button type="primary" onClick={() => window.location.reload()}>
              Попробовать снова
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div style={{ minHeight: '100vh', background: '#f5f7fb', padding: '32px 16px' }}>
      <div style={{ maxWidth: 900, margin: '0 auto' }}>
        <Title level={2} style={{ marginTop: 0 }}>
          Личный кабинет
        </Title>
        <Paragraph type="secondary">
          {data.client_name}
          {data.contact_person ? ` · ${data.contact_person}` : ''}
        </Paragraph>
        <Paragraph type="secondary" style={{ marginTop: -8 }}>
          Это персональная ссылка: не пересылайте её другим людям.
        </Paragraph>
        {data.orders.length ? (
          data.orders.map((order) => <OrderCard key={order.id} order={order} />)
        ) : (
          <Card style={{ borderRadius: 14 }}>
            <Empty description="Заявок пока нет. Оставьте заявку в VK-боте." />
          </Card>
        )}
      </div>
    </div>
  );
}
