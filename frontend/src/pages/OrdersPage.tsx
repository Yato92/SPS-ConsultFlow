import {
  DeleteOutlined,
  DownloadOutlined,
  FilterOutlined,
  PlusOutlined,
  ReloadOutlined,
  SearchOutlined,
  UndoOutlined,
} from '@ant-design/icons';
import {
  App,
  Button,
  Card,
  DatePicker,
  Form,
  Input,
  InputNumber,
  Modal,
  Popconfirm,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  Tooltip,
} from 'antd';
import type { ColumnsType } from 'antd/es/table';
import dayjs from 'dayjs';
import type { Dayjs } from 'dayjs';
import { useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import {
  api,
  deleteOrder,
  downloadOrdersCsv,
  getApiError,
  restoreOrder,
} from '@/api/client';
import { useClients, useManagers, useOrders } from '@/api/queries';
import type { Order } from '@/api/types';
import { useAuth } from '@/auth/AuthContext';
import { PageHeader } from '@/components/PageHeader';
import { PracticePill, StatusPill } from '@/components/StatusPill';
import {
  PRACTICE_OPTIONS,
  STATUS_OPTIONS,
} from '@/constants';
import { date, money, overdueDays } from '@/utils/format';
import { OrderDrawer } from './OrderDrawer';

interface CreateFormValues {
  client_id: number;
  practice: string;
  title: string;
  amount: number;
  manager_id?: number;
  deadline?: Dayjs;
}

export function OrdersPage() {
  const { message } = App.useApp();
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const canManage = user?.role === 'admin' || user?.role === 'manager';
  const [searchParams, setSearchParams] = useSearchParams();
  const orderParam = Number(searchParams.get('order')) || null;

  const [search, setSearch] = useState('');
  const [statuses, setStatuses] = useState<string[]>([]);
  const [practice, setPractice] = useState<string | undefined>();
  const [managerId, setManagerId] = useState<number | undefined>();
  const [range, setRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [createOpen, setCreateOpen] = useState(false);
  const [creating, setCreating] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [showDeleted, setShowDeleted] = useState(false);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [form] = Form.useForm<CreateFormValues>();

  const { data: managers } = useManagers();
  const { data: clients } = useClients('');

  useEffect(() => {
    const preset = searchParams.get('q');
    if (preset) setSearch(preset);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const params = useMemo(
    () => ({
      q: search || undefined,
      status: statuses.length ? statuses.join(',') : undefined,
      practice,
      manager_id: managerId,
      date_from: range?.[0].format('YYYY-MM-DD'),
      date_to: range?.[1].format('YYYY-MM-DD'),
      page,
      page_size: pageSize,
      sort_by: 'created_at',
      sort_dir: 'desc' as const,
      include_deleted: showDeleted || undefined,
    }),
    [search, statuses, practice, managerId, range, page, pageSize, showDeleted],
  );
  const { data, isFetching, refetch } = useOrders(params);

  const resetFilters = () => {
    setSearch('');
    setStatuses([]);
    setPractice(undefined);
    setManagerId(undefined);
    setRange(null);
    setPage(1);
  };

  const openOrder = (id: number) => {
    const next = new URLSearchParams(searchParams);
    next.set('order', String(id));
    setSearchParams(next);
  };

  const closeOrder = () => {
    const next = new URLSearchParams(searchParams);
    next.delete('order');
    setSearchParams(next);
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      await downloadOrdersCsv();
      message.success('CSV-файл сформирован');
    } catch (error) {
      message.error(getApiError(error));
    } finally {
      setExporting(false);
    }
  };

  const handleCreate = async (values: CreateFormValues) => {
    setCreating(true);
    try {
      const { data: created } = await api.post('/orders', {
        client_id: values.client_id,
        practice: values.practice,
        title: values.title,
        amount: values.amount,
        manager_id: values.manager_id,
        deadline: values.deadline?.format('YYYY-MM-DD') ?? null,
      });
      message.success(`Заказ ${created.number} создан`);
      setCreateOpen(false);
      form.resetFields();
      await queryClient.invalidateQueries({ queryKey: ['orders'] });
      await queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      openOrder(created.id);
    } catch (error) {
      message.error(getApiError(error));
    } finally {
      setCreating(false);
    }
  };

  const refreshLists = async () => {
    await queryClient.invalidateQueries({ queryKey: ['orders'] });
    await queryClient.invalidateQueries({ queryKey: ['dashboard'] });
  };

  const handleDelete = async (row: Order) => {
    setBusyId(row.id);
    try {
      await deleteOrder(row.id);
      message.success(
        `Заказ ${row.number} убран из списка. Запись сохранена в базе данных.`,
      );
      if (orderParam === row.id) closeOrder();
      await refreshLists();
    } catch (error) {
      message.error(getApiError(error));
    } finally {
      setBusyId(null);
    }
  };

  const handleRestore = async (row: Order) => {
    setBusyId(row.id);
    try {
      await restoreOrder(row.id);
      message.success(`Заказ ${row.number} возвращён из архива`);
      await refreshLists();
    } catch (error) {
      message.error(getApiError(error));
    } finally {
      setBusyId(null);
    }
  };

  const columns: ColumnsType<Order> = [
    {
      title: 'Заказ',
      dataIndex: 'number',
      width: 270,
      render: (value: string, row) => (
        <div>
          <div className="cell-strong">
            {value}
            {row.is_deleted && (
              <Tag color="default" bordered={false} style={{ marginLeft: 8 }}>
                в архиве
              </Tag>
            )}
          </div>
          <div
            className="cell-muted"
            style={{ maxWidth: 250, overflow: 'hidden', textOverflow: 'ellipsis' }}
          >
            {row.title}
          </div>
        </div>
      ),
    },
    {
      title: 'Клиент',
      dataIndex: ['client', 'name'],
      width: 210,
      ellipsis: true,
    },
    {
      title: 'Направление',
      dataIndex: 'practice',
      width: 160,
      render: (value) => <PracticePill practice={value} />,
    },
    {
      title: 'Статус',
      dataIndex: 'status',
      width: 175,
      render: (value) => <StatusPill status={value} />,
    },
    {
      title: 'Сумма',
      dataIndex: 'amount',
      width: 130,
      align: 'right',
      render: (value: number) => <span className="mono cell-strong">{money(value)}</span>,
    },
    {
      title: 'Оплачено',
      dataIndex: 'paid_amount',
      width: 130,
      align: 'right',
      render: (value: number) => <span className="mono">{money(value)}</span>,
    },
    {
      title: 'Менеджер',
      dataIndex: ['manager', 'full_name'],
      width: 170,
      ellipsis: true,
      render: (value: string | undefined) => value ?? <span className="cell-muted">—</span>,
    },
    {
      title: 'Создан',
      dataIndex: 'created_at',
      width: 105,
      render: (value: string) => <span className="cell-muted">{date(value)}</span>,
    },
    {
      title: 'SLA',
      key: 'sla',
      width: 100,
      render: (_, row) =>
        row.is_overdue ? (
          <Tooltip title={`Срок был ${date(row.sla_due_at)}`}>
            <Tag color="error" bordered={false}>
              {overdueDays(row.sla_due_at)} дн.
            </Tag>
          </Tooltip>
        ) : (
          <span className="cell-muted">{row.sla_due_at ? date(row.sla_due_at) : '—'}</span>
        ),
    },
  ];

  if (canManage) {
    columns.push({
      title: '',
      key: 'actions',
      width: 130,
      fixed: 'right',
      render: (_, row) => (
        <div onClick={(event) => event.stopPropagation()}>
          {row.is_deleted ? (
            <Button
              size="small"
              icon={<UndoOutlined />}
              loading={busyId === row.id}
              onClick={() => handleRestore(row)}
            >
              Вернуть
            </Button>
          ) : (
            <Popconfirm
              title="Удалить заказ?"
              description="Он исчезнет из списка и отчётов, но останется в базе данных."
              okText="Удалить"
              cancelText="Отмена"
              okButtonProps={{ danger: true }}
              onConfirm={() => handleDelete(row)}
            >
              <Button
                danger
                size="small"
                icon={<DeleteOutlined />}
                loading={busyId === row.id}
              >
                Удалить
              </Button>
            </Popconfirm>
          )}
        </div>
      ),
    });
  }

  return (
    <>
      <PageHeader
        title="Заказы"
        subtitle="Единый реестр заявок и заказов: фильтры, статусы, документы и SLA."
        actions={
          <>
            <Button icon={<ReloadOutlined />} loading={isFetching} onClick={() => refetch()}>
              Обновить
            </Button>
            <Button icon={<DownloadOutlined />} loading={exporting} onClick={handleExport}>
              Экспорт CSV
            </Button>
            {canManage && (
              <Button
                type="primary"
                icon={<PlusOutlined />}
                onClick={() => setCreateOpen(true)}
              >
                Новый заказ
              </Button>
            )}
          </>
        }
      />

      <Card className="cf-card" bodyStyle={{ padding: 16 }}>
        <Space wrap size={10} style={{ width: '100%' }}>
          <Input
            allowClear
            prefix={<SearchOutlined style={{ color: '#a5aab8' }} />}
            placeholder="Номер, клиент или тема"
            style={{ width: 260 }}
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            onPressEnter={() => setPage(1)}
          />
          <Select
            mode="multiple"
            allowClear
            maxTagCount={1}
            placeholder="Статусы"
            options={STATUS_OPTIONS}
            style={{ minWidth: 210 }}
            value={statuses}
            onChange={(value) => {
              setStatuses(value);
              setPage(1);
            }}
          />
          <Select
            allowClear
            placeholder="Направление"
            options={PRACTICE_OPTIONS}
            style={{ width: 185 }}
            value={practice}
            onChange={(value) => {
              setPractice(value);
              setPage(1);
            }}
          />
          <Select
            allowClear
            showSearch
            optionFilterProp="label"
            placeholder="Менеджер"
            style={{ width: 200 }}
            value={managerId}
            onChange={(value) => {
              setManagerId(value);
              setPage(1);
            }}
            options={(managers ?? []).map((item) => ({
              value: item.id,
              label: item.full_name,
            }))}
          />
          <DatePicker.RangePicker
            value={range}
            onChange={(value) => {
              setRange(value as [Dayjs, Dayjs] | null);
              setPage(1);
            }}
            format="DD.MM.YYYY"
            placeholder={['С даты', 'По дату']}
          />
          <Button icon={<FilterOutlined />} onClick={resetFilters}>
            Сбросить
          </Button>
          {canManage && (
            <Space size={6}>
              <Switch
                checked={showDeleted}
                onChange={(checked) => {
                  setShowDeleted(checked);
                  setPage(1);
                }}
              />
              <span style={{ fontSize: 12, color: '#8a90a2' }}>
                Показать удалённые
              </span>
            </Space>
          )}
          {data && (
            <span style={{ marginLeft: 'auto', fontSize: 12, color: '#8a90a2' }}>
              Найдено: <b style={{ color: '#1D2130' }}>{data.total}</b>
            </span>
          )}
        </Space>
      </Card>

      <Card className="cf-card" style={{ marginTop: 16 }} bodyStyle={{ padding: 6 }}>
        <Table<Order>
          className="cf-table"
          rowKey="id"
          loading={isFetching}
          dataSource={data?.items ?? []}
          columns={columns}
          scroll={{ x: 1300 }}
          onRow={(row) => ({ onClick: () => openOrder(row.id) })}
          pagination={{
            current: data?.page ?? page,
            pageSize: data?.page_size ?? pageSize,
            total: data?.total ?? 0,
            showSizeChanger: true,
            pageSizeOptions: [10, 20, 50, 100],
            showTotal: (total, rangeNumbers) =>
              `${rangeNumbers[0]}–${rangeNumbers[1]} из ${total}`,
            onChange: (nextPage, nextSize) => {
              setPage(nextPage);
              setPageSize(nextSize);
            },
          }}
        />
      </Card>

      <OrderDrawer orderId={orderParam} open={orderParam !== null} onClose={closeOrder} />

      <Modal
        title="Новый заказ"
        open={createOpen}
        onCancel={() => setCreateOpen(false)}
        onOk={() => form.submit()}
        okText="Создать заказ"
        cancelText="Отмена"
        confirmLoading={creating}
        destroyOnClose
      >
        <Form form={form} layout="vertical" onFinish={handleCreate} requiredMark={false}>
          <Form.Item
            name="client_id"
            label="Клиент"
            rules={[{ required: true, message: 'Выберите клиента' }]}
          >
            <Select
              showSearch
              optionFilterProp="label"
              placeholder="Начните вводить название"
              options={(clients?.items ?? []).map((item) => ({
                value: item.id,
                label: item.name,
              }))}
            />
          </Form.Item>
          <Form.Item
            name="title"
            label="Тема заказа"
            rules={[{ required: true, min: 3, message: 'Опишите тему заказа' }]}
          >
            <Input placeholder="Например: аудит ИТ-инфраструктуры" />
          </Form.Item>
          <Space size={12} style={{ display: 'flex' }}>
            <Form.Item
              name="practice"
              label="Направление"
              rules={[{ required: true, message: 'Выберите направление' }]}
              style={{ flex: 1 }}
            >
              <Select options={PRACTICE_OPTIONS} placeholder="Направление" />
            </Form.Item>
            <Form.Item
              name="manager_id"
              label="Менеджер"
              style={{ flex: 1 }}
            >
              <Select
                allowClear
                placeholder="Я (по умолчанию)"
                options={(managers ?? []).map((item) => ({
                  value: item.id,
                  label: item.full_name,
                }))}
              />
            </Form.Item>
          </Space>
          <Space size={12} style={{ display: 'flex' }}>
            <Form.Item name="amount" label="Стоимость, ₽" style={{ flex: 1 }}>
              <InputNumber
                min={0}
                step={1000}
                style={{ width: '100%' }}
                placeholder="0"
                formatter={(value) =>
                  value ? `${value}`.replace(/\B(?=(\d{3})+(?!\d))/g, ' ') : ''
                }
              />
            </Form.Item>
            <Form.Item name="deadline" label="Срок" style={{ flex: 1 }}>
              <DatePicker style={{ width: '100%' }} format="DD.MM.YYYY" />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </>
  );
}
