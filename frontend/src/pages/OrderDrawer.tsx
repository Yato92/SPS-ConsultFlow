import {
  CheckCircleOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  EditOutlined,
  FileTextOutlined,
  RightOutlined,
} from '@ant-design/icons';
import {
  App,
  Button,
  DatePicker,
  Descriptions,
  Drawer,
  Dropdown,
  Empty,
  Form,
  Input,
  InputNumber,
  Modal,
  Progress,
  Select,
  Skeleton,
  Space,
  Tabs,
  Timeline,
  Tooltip,
} from 'antd';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import {
  changeOrderStatus,
  generateDocument,
  getApiError,
  signDocument,
  updateOrder,
} from '@/api/client';
import { useManagers, useOrder } from '@/api/queries';
import type { OrderDocument } from '@/api/types';
import { useAuth } from '@/auth/AuthContext';
import { PracticePill, StatusPill } from '@/components/StatusPill';
import {
  DOC_TYPE_META,
  NEXT_STATUS,
  STATUS_META,
  STATUS_OPTIONS,
} from '@/constants';
import { date, dateTime, money, overdueDays } from '@/utils/format';

export function OrderDrawer({
  orderId,
  open,
  onClose,
}: {
  orderId: number | null;
  open: boolean;
  onClose: () => void;
}) {
  const { message } = App.useApp();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const { data: order, isLoading } = useOrder(orderId);
  const { data: managers } = useManagers();
  const [tab, setTab] = useState('overview');
  const [statusOpen, setStatusOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [document, setDocument] = useState<OrderDocument | null>(null);
  const [saving, setSaving] = useState(false);
  const [statusForm] = Form.useForm();
  const [editForm] = Form.useForm();

  const canManage = user?.role === 'admin' || user?.role === 'manager';
  const next = order ? NEXT_STATUS[order.status] : undefined;
  const canCancel = order
    ? !['done', 'closed', 'cancelled'].includes(order.status)
    : false;

  const openStatus = () => {
    statusForm.setFieldsValue({ status: next?.value, comment: '' });
    setStatusOpen(true);
  };

  const openEdit = () => {
    editForm.setFieldsValue({
      amount: order?.amount ?? 0,
      paid_amount: order?.paid_amount ?? 0,
      expenses: order?.expenses ?? 0,
      manager_id: order?.manager?.id,
      deadline: order?.deadline ? dayjs(order.deadline) : undefined,
    });
    setEditOpen(true);
  };

  useEffect(() => {
    if (!open) {
      setTab('overview');
      setDocument(null);
    }
  }, [open]);

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ['order', orderId] });
    await queryClient.invalidateQueries({ queryKey: ['orders'] });
    await queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  };

  const handleStatus = async (status: string, comment?: string) => {
    if (!order) return;
    setSaving(true);
    try {
      await changeOrderStatus(order.id, status, comment);
      message.success('Статус обновлён');
      setStatusOpen(false);
      await invalidate();
    } catch (error) {
      message.error(getApiError(error));
    } finally {
      setSaving(false);
    }
  };

  const handleEdit = async (values: Record<string, unknown>) => {
    if (!order) return;
    setSaving(true);
    try {
      await updateOrder(order.id, {
        amount: values.amount,
        paid_amount: values.paid_amount,
        expenses: values.expenses,
        manager_id: values.manager_id ?? null,
        deadline: values.deadline ? (values.deadline as Dayjs).format('YYYY-MM-DD') : null,
      });
      message.success('Заказ обновлён');
      setEditOpen(false);
      await invalidate();
    } catch (error) {
      message.error(getApiError(error));
    } finally {
      setSaving(false);
    }
  };

  const handleGenerate = async (docType: string) => {
    if (!order) return;
    try {
      await generateDocument(order.id, docType);
      message.success('Документ сформирован');
      await invalidate();
    } catch (error) {
      message.error(getApiError(error));
    }
  };

  const handleSign = async () => {
    if (!order || !document) return;
    try {
      await signDocument(order.id, document.id);
      message.success('Документ отмечен как подписанный');
      setDocument({ ...document, status: 'signed' });
      await invalidate();
    } catch (error) {
      message.error(getApiError(error));
    }
  };

  const downloadDocument = () => {
    if (!document) return;
    const blob = new Blob([document.payload.body], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const link = window.document.createElement("a");
    link.href = url;
    link.download = `${document.number}.md`;
    window.document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const paidShare = useMemo(() => {
    if (!order || !order.amount) return 0;
    return Math.min(100, Math.round((order.paid_amount / order.amount) * 100));
  }, [order]);

  const documentMenu = {
    items: Object.entries(DOC_TYPE_META).map(([key, meta]) => ({
      key,
      label: meta.label,
      icon: <FileTextOutlined />,
    })),
    onClick: ({ key }: { key: string }) => handleGenerate(key),
  };

  return (
    <Drawer
      title={order ? `Заказ ${order.number}` : 'Заказ'}
      open={open}
      onClose={onClose}
      width={760}
      destroyOnClose
      styles={{ body: { padding: 24 } }}
      extra={
        order && canManage ? (
          <Space>
            <Dropdown menu={documentMenu} trigger={['click']}>
              <Button icon={<FileTextOutlined />}>Документ</Button>
            </Dropdown>
            <Button icon={<EditOutlined />} onClick={openEdit}>
              Изменить
            </Button>
            {next && (
              <Button
                type="primary"
                icon={<RightOutlined />}
                onClick={openStatus}
              >
                {next.label}
              </Button>
            )}
          </Space>
        ) : null
      }
    >
      {isLoading || !order ? (
        <Skeleton active paragraph={{ rows: 8 }} />
      ) : (
        <>
          <div className="order-hero">
            <div style={{ minWidth: 0 }}>
              <div className="order-hero__number">{order.number}</div>
              <div className="order-hero__title">{order.title}</div>
              <Space size={8} wrap>
                <StatusPill status={order.status} />
                <PracticePill practice={order.practice} />
                <span className="cell-muted">
                  источник: {order.source === 'telegram' ? 'Telegram-бот' : 'дашборд'}
                </span>
              </Space>
            </div>
            {order.is_overdue && (
              <Tooltip title={`SLA истёк ${dateTime(order.sla_due_at)}`}>
                <span
                  style={{
                    background: '#fff1f0',
                    color: '#f03d3d',
                    borderRadius: 10,
                    padding: '6px 10px',
                    fontSize: 12,
                    fontWeight: 600,
                    whiteSpace: 'nowrap',
                  }}
                >
                  <ClockCircleOutlined /> {overdueDays(order.sla_due_at)} дн.
                </span>
              </Tooltip>
            )}
          </div>

          <Tabs
            activeKey={tab}
            onChange={setTab}
            items={[
              {
                key: 'overview',
                label: 'Обзор',
                children: (
                  <>
                    <div className="fin-grid">
                      <div className="fin-cell">
                        <div className="fin-cell__label">Стоимость</div>
                        <div className="fin-cell__value">{money(order.amount)}</div>
                      </div>
                      <div className="fin-cell">
                        <div className="fin-cell__label">Оплачено</div>
                        <div className="fin-cell__value">{money(order.paid_amount)}</div>
                      </div>
                      <div className="fin-cell">
                        <div className="fin-cell__label">Расходы</div>
                        <div className="fin-cell__value">{money(order.expenses)}</div>
                      </div>
                      <div className="fin-cell">
                        <div className="fin-cell__label">Результат</div>
                        <div
                          className="fin-cell__value"
                          style={{ color: order.paid_amount - order.expenses >= 0 ? '#1F9D3A' : '#E03A3A' }}
                        >
                          {money(order.paid_amount - order.expenses)}
                        </div>
                      </div>
                    </div>

                    <div style={{ margin: '14px 0 20px' }}>
                      <div
                        style={{
                          display: 'flex',
                          justifyContent: 'space-between',
                          fontSize: 12,
                          color: '#6b7280',
                          marginBottom: 6,
                        }}
                      >
                        <span>Оплата заказа</span>
                        <span>{paidShare}%</span>
                      </div>
                      <Progress
                        percent={paidShare}
                        showInfo={false}
                        strokeColor="#6068F8"
                        trailColor="#EEF0F7"
                      />
                    </div>

                    <Descriptions
                      size="small"
                      column={2}
                      bordered
                      items={[
                        { key: 'client', label: 'Клиент', children: order.client.name },
                        {
                          key: 'contact',
                          label: 'Контакт',
                          children: order.client.contact_person ?? '—',
                        },
                        { key: 'phone', label: 'Телефон', children: order.client.phone ?? '—' },
                        { key: 'email', label: 'E-mail', children: order.client.email ?? '—' },
                        {
                          key: 'manager',
                          label: 'Менеджер',
                          children: order.manager?.full_name ?? 'Не назначен',
                        },
                        { key: 'created', label: 'Создан', children: dateTime(order.created_at) },
                        { key: 'deadline', label: 'Срок', children: date(order.deadline) },
                        {
                          key: 'sla',
                          label: 'SLA',
                          children: dateTime(order.sla_due_at),
                        },
                      ]}
                    />

                    {order.description && (
                      <div style={{ marginTop: 18 }}>
                        <div style={{ fontSize: 12, color: '#6b7280', marginBottom: 6 }}>
                          Описание
                        </div>
                        <div
                          style={{
                            background: '#fbfbfe',
                            border: '1px solid #EEF0F6',
                            borderRadius: 12,
                            padding: '12px 14px',
                            fontSize: 13,
                            lineHeight: 1.65,
                            color: '#3d4352',
                          }}
                        >
                          {order.description}
                        </div>
                      </div>
                    )}
                  </>
                ),
              },
              {
                key: 'history',
                label: `История · ${order.events.length}`,
                children: order.events.length ? (
                  <Timeline
                    items={order.events.map((event) => ({
                      color: STATUS_META[event.to_status]?.color ?? '#6068F8',
                      children: (
                        <div>
                          <div style={{ fontWeight: 600, fontSize: 13 }}>
                            {STATUS_META[event.to_status]?.label ?? event.to_status}
                          </div>
                          <div style={{ fontSize: 11.5, color: '#8a90a2', marginTop: 2 }}>
                            {dateTime(event.created_at)} ·{' '}
                            {event.actor_type === 'bot'
                              ? 'Telegram-бот'
                              : event.actor_type === 'user'
                                ? 'Сотрудник'
                                : 'Система'}
                          </div>
                          {event.comment && (
                            <div style={{ fontSize: 12.5, color: '#4b5163', marginTop: 4 }}>
                              {event.comment}
                            </div>
                          )}
                        </div>
                      ),
                    }))}
                  />
                ) : (
                  <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="История пуста" />
                ),
              },
              {
                key: 'documents',
                label: `Документы · ${order.documents.length}`,
                children: order.documents.length ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {order.documents.map((doc) => (
                      <div className="doc-card" key={doc.id}>
                        <div style={{ display: 'flex', gap: 10, alignItems: 'center', minWidth: 0 }}>
                          <span
                            style={{
                              width: 34,
                              height: 34,
                              borderRadius: 10,
                              background: `${DOC_TYPE_META[doc.doc_type]?.color ?? '#6068F8'}14`,
                              color: DOC_TYPE_META[doc.doc_type]?.color ?? '#6068F8',
                              display: 'grid',
                              placeItems: 'center',
                              flex: 'none',
                            }}
                          >
                            <FileTextOutlined />
                          </span>
                          <div style={{ minWidth: 0 }}>
                            <div style={{ fontWeight: 600, fontSize: 13 }}>
                              {doc.payload.title}
                            </div>
                            <div style={{ fontSize: 11.5, color: '#8a90a2' }}>
                              {doc.number} · {date(doc.created_at)}
                            </div>
                          </div>
                        </div>
                        <Space>
                          <span
                            style={{
                              fontSize: 11.5,
                              color: doc.status === 'signed' ? '#1F9D3A' : '#8a90a2',
                            }}
                          >
                            {doc.status === 'signed' ? 'подписан' : 'черновик'}
                          </span>
                          <Button size="small" onClick={() => setDocument(doc)}>
                            Открыть
                          </Button>
                        </Space>
                      </div>
                    ))}
                  </div>
                ) : (
                  <Empty
                    image={Empty.PRESENTED_IMAGE_SIMPLE}
                    description="Документы ещё не сформированы"
                  >
                    {canManage && (
                      <Dropdown menu={documentMenu} trigger={['click']}>
                        <Button type="primary" icon={<FileTextOutlined />}>
                          Сформировать документ
                        </Button>
                      </Dropdown>
                    )}
                  </Empty>
                ),
              },
            ]}
          />

          <Modal
            title="Изменить статус"
            open={statusOpen}
            onCancel={() => setStatusOpen(false)}
            onOk={() => statusForm.submit()}
            okText="Применить"
            cancelText="Отмена"
            confirmLoading={saving}
            destroyOnClose
          >
            <Form
              form={statusForm}
              layout="vertical"
              requiredMark={false}
              initialValues={{ status: next?.value, comment: '' }}
              onFinish={(values) => handleStatus(values.status, values.comment)}
            >
              <Form.Item
                name="status"
                label="Новый статус"
                rules={[{ required: true, message: 'Выберите статус' }]}
              >
                <Select
                  options={STATUS_OPTIONS.filter(
                    (option) =>
                      option.value === next?.value ||
                      (canCancel && option.value === 'cancelled'),
                  )}
                />
              </Form.Item>
              <Form.Item name="comment" label="Комментарий">
                <Input.TextArea rows={3} placeholder="Необязательно" maxLength={500} />
              </Form.Item>
              <div style={{ fontSize: 12, color: '#8a90a2' }}>
                При переходе в статусы «КП отправлено», «Договор подписан» и
                «Работы выполнены» документ формируется автоматически.
              </div>
            </Form>
          </Modal>

          <Modal
            title="Изменить заказ"
            open={editOpen}
            onCancel={() => setEditOpen(false)}
            onOk={() => editForm.submit()}
            okText="Сохранить"
            cancelText="Отмена"
            confirmLoading={saving}
            destroyOnClose
          >
            <Form
              form={editForm}
              layout="vertical"
              requiredMark={false}
              initialValues={{
                amount: order.amount,
                paid_amount: order.paid_amount,
                expenses: order.expenses,
                manager_id: order.manager?.id,
                deadline: order.deadline ? dayjs(order.deadline) : undefined,
              }}
              onFinish={handleEdit}
            >
              <Space size={12} style={{ display: 'flex' }}>
                <Form.Item name="amount" label="Стоимость, ₽" style={{ flex: 1 }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item name="paid_amount" label="Оплачено, ₽" style={{ flex: 1 }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
                <Form.Item name="expenses" label="Расходы, ₽" style={{ flex: 1 }}>
                  <InputNumber min={0} style={{ width: '100%' }} />
                </Form.Item>
              </Space>
              <Space size={12} style={{ display: 'flex' }}>
                <Form.Item name="manager_id" label="Менеджер" style={{ flex: 1 }}>
                  <Select
                    allowClear
                    options={(managers ?? []).map((item) => ({
                      value: item.id,
                      label: item.full_name,
                    }))}
                  />
                </Form.Item>
                <Form.Item name="deadline" label="Срок" style={{ flex: 1 }}>
                  <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
                </Form.Item>
              </Space>
            </Form>
          </Modal>

          <Modal
            title={document?.payload.title ?? 'Документ'}
            open={Boolean(document)}
            onCancel={() => setDocument(null)}
            width={780}
            footer={
              <Space>
                <Button onClick={() => setDocument(null)}>Закрыть</Button>
                {document?.status !== 'signed' && canManage && (
                  <Button type="primary" icon={<CheckCircleOutlined />} onClick={handleSign}>
                    Отметить подписанным
                  </Button>
                )}
                <Button icon={<DownloadOutlined />} onClick={downloadDocument}>
                  В файл
                </Button>
              </Space>
            }
          >
            <pre className="doc-body">{document?.payload.body}</pre>
          </Modal>
        </>
      )}
    </Drawer>
  );
}
