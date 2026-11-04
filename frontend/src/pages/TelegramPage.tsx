import {
  ApiOutlined,
  BellOutlined,
  CheckCircleOutlined,
  LinkOutlined,
  MessageOutlined,
  ReloadOutlined,
  RobotOutlined,
  SendOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { Button, Card, Empty, Space, Table, Tag, Timeline } from 'antd';
import type { ColumnsType } from 'antd/es/table';
import { useBotUsers, useNotifications } from '@/api/queries';
import type { BotUserRow } from '@/api/types';
import { KpiCard } from '@/components/KpiCard';
import { ChartCard, PageHeader } from '@/components/PageHeader';
import { ROLE_LABELS } from '@/constants';
import { dateTime, num } from '@/utils/format';

const SETUP_STEPS = [
  {
    title: 'Получите токен у @BotFather',
    text: 'Создайте бота командой /newbot и скопируйте токен в переменную BOT_TOKEN файла .env.',
  },
  {
    title: 'Укажите свой Telegram ID',
    text: 'Отправьте боту /id, затем добавьте ID в MANAGER_TELEGRAM_IDS — после /start вы получите роль менеджера.',
  },
  {
    title: 'Запустите сервисы',
    text: 'backend: uvicorn app.main:app --reload · bot: python run.py · frontend: pnpm dev.',
  },
  {
    title: 'Откройте дашборд из бота',
    text: 'Команда /link создаёт одноразовую ссылку с автоматической авторизацией в этой панели.',
  },
];

export function TelegramPage() {
  const { data: users, isLoading: usersLoading, refetch: refetchUsers, isFetching } = useBotUsers();
  const { data: notifications, isLoading: notificationsLoading } = useNotifications();

  const botUsers = users ?? [];
  const managers = botUsers.filter((item) => item.role === 'manager');
  const botOrders = botUsers.reduce((sum, item) => sum + item.orders_count, 0);

  const columns: ColumnsType<BotUserRow> = [
    {
      title: 'Пользователь',
      dataIndex: 'full_name',
      render: (value: string, row) => (
        <div>
          <div className="cell-strong">{value || 'Без имени'}</div>
          <div className="cell-muted">
            {row.username ? `@${row.username}` : 'без username'}
          </div>
        </div>
      ),
    },
    {
      title: 'Telegram ID',
      dataIndex: 'telegram_id',
      render: (value: number) => <code style={{ fontSize: 12 }}>{value}</code>,
    },
    {
      title: 'Роль',
      dataIndex: 'role',
      render: (value: string) => (
        <Tag color={value === 'manager' ? 'gold' : 'blue'} bordered={false}>
          {ROLE_LABELS[value] ?? value}
        </Tag>
      ),
    },
    {
      title: 'Заказов',
      dataIndex: 'orders_count',
      align: 'center',
      render: (value: number) => num(value),
    },
    {
      title: 'Дашборд',
      dataIndex: 'user_id',
      render: (value: number | null) =>
        value ? (
          <Tag color="green" bordered={false}>
            связан
          </Tag>
        ) : (
          <span className="cell-muted">—</span>
        ),
    },
  ];

  return (
    <>
      <PageHeader
        title="Telegram-бот"
        subtitle="Пользователи бота, уведомления и связка чат-бота с дашбордом ConsultFlow."
        actions={
          <Button icon={<ReloadOutlined />} loading={isFetching} onClick={() => refetchUsers()}>
            Обновить
          </Button>
        }
      />

      <div className="kpi-grid" style={{ gridTemplateColumns: 'repeat(4, minmax(0, 1fr))' }}>
        <KpiCard
          label="Пользователей бота"
          value={num(botUsers.length)}
          hint="зарегистрировались через /start"
          icon={<TeamOutlined />}
          tone="primary"
        />
        <KpiCard
          label="Менеджеров"
          value={num(managers.length)}
          hint="получают заявки"
          icon={<UserOutlined />}
          tone="violet"
        />
        <KpiCard
          label="Заказов из бота"
          value={num(botOrders)}
          hint="создано в Telegram"
          icon={<SendOutlined />}
          tone="success"
        />
        <KpiCard
          label="Уведомлений"
          value={num(notifications?.length ?? 0)}
          hint="в очереди и доставлено"
          icon={<BellOutlined />}
          tone="warning"
        />
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'minmax(0, 1.55fr) minmax(0, 1fr)',
          gap: 16,
          marginTop: 16,
        }}
      >
        <ChartCard
          title="Пользователи Telegram-бота"
          extra={<span>{botUsers.length} записей</span>}
          bodyStyle={{ padding: 6 }}
        >
          <Table<BotUserRow>
            className="cf-table"
            rowKey="id"
            loading={usersLoading}
            dataSource={botUsers}
            columns={columns}
            pagination={{ pageSize: 8, showSizeChanger: false }}
            locale={{ emptyText: <Empty description="Пока никто не запускал бота" /> }}
          />
        </ChartCard>

        <ChartCard
          title="Лента уведомлений"
          extra={<span>доставка ботом</span>}
          bodyStyle={{ padding: '8px 20px', maxHeight: 520, overflow: 'auto' }}
        >
          {notificationsLoading ? (
            <div className="empty-hint">Загружаем…</div>
          ) : !notifications?.length ? (
            <Empty
              image={Empty.PRESENTED_IMAGE_SIMPLE}
              description="Уведомлений пока нет. Создайте заявку в боте."
            />
          ) : (
            <div>
              {notifications.slice(0, 12).map((item) => (
                <div className="bot-notification" key={item.id}>
                  <span className="bot-notification__icon">
                    <SendOutlined />
                  </span>
                  <div style={{ minWidth: 0 }}>
                    <div
                      className="bot-notification__text"
                      dangerouslySetInnerHTML={{ __html: item.text }}
                    />
                    <div className="bot-notification__meta">
                      получатель {item.recipient} · {dateTime(item.created_at)}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </ChartCard>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1fr) minmax(0, 1fr)', gap: 16, marginTop: 16 }}>
        <ChartCard title="Как подключить бота" extra={<RobotOutlined />}>
          <Timeline
            items={SETUP_STEPS.map((step) => ({
              color: '#6068F8',
              children: (
                <div>
                  <div style={{ fontWeight: 600, fontSize: 13 }}>{step.title}</div>
                  <div style={{ fontSize: 12.5, color: '#6b7280', marginTop: 3, lineHeight: 1.55 }}>
                    {step.text}
                  </div>
                </div>
              ),
            }))}
          />
        </ChartCard>

        <ChartCard title="Команды бота" extra={<MessageOutlined />}>
          <Space direction="vertical" size={12} style={{ width: '100%' }}>
            {[
              { cmd: '/start', desc: 'Регистрация и главное меню' },
              { cmd: '/menu', desc: 'Открыть меню в любой момент' },
              { cmd: '/link', desc: 'Одноразовая ссылка на этот дашборд' },
              { cmd: '/id', desc: 'Показать Telegram ID для настройки роли' },
              { cmd: '/cancel', desc: 'Отменить заполнение заявки' },
            ].map((item) => (
              <div key={item.cmd} style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                <code
                  style={{
                    background: '#EEF0FF',
                    color: '#4C55E8',
                    borderRadius: 7,
                    padding: '2px 8px',
                    fontSize: 12,
                    fontWeight: 600,
                    minWidth: 72,
                    textAlign: 'center',
                  }}
                >
                  {item.cmd}
                </code>
                <span style={{ fontSize: 12.5, color: '#4b5163' }}>{item.desc}</span>
              </div>
            ))}
            <div
              style={{
                marginTop: 4,
                padding: '12px 14px',
                borderRadius: 12,
                background: '#F6F7FD',
                border: '1px dashed #D9DCF5',
                fontSize: 12,
                color: '#5b6172',
                lineHeight: 1.55,
              }}
            >
              <ApiOutlined /> Бот общается с backend по защищённому токену
              <code style={{ margin: '0 4px' }}>X-Bot-Token</code> и получает уведомления
              из очереди — поэтому дашборд и Telegram всегда синхронизированы.
            </div>
            <div style={{ display: 'flex', gap: 14, fontSize: 12, color: '#8a90a2' }}>
              <span>
                <CheckCircleOutlined style={{ color: '#2FB344' }} /> заявки
              </span>
              <span>
                <CheckCircleOutlined style={{ color: '#2FB344' }} /> статусы
              </span>
              <span>
                <CheckCircleOutlined style={{ color: '#2FB344' }} /> документы
              </span>
              <span>
                <LinkOutlined style={{ color: '#2FB344' }} /> magic-link
              </span>
            </div>
          </Space>
        </ChartCard>
      </div>
    </>
  );
}
