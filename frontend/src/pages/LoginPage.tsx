import {
  ArrowRightOutlined,
  BarChartOutlined,
  CheckCircleFilled,
  LockOutlined,
  MailOutlined,
  RobotOutlined,
  SafetyCertificateOutlined,
  ThunderboltOutlined,
} from '@ant-design/icons';
import { Button, Form, Input, Typography } from 'antd';
import { App } from 'antd';
import { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { getApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthContext';

const FEATURES = [
  { icon: <RobotOutlined />, text: 'Заявки из Telegram попадают в единую воронку' },
  { icon: <ThunderboltOutlined />, text: 'КП, договор и акт формируются автоматически' },
  { icon: <BarChartOutlined />, text: 'SLA, загрузка менеджеров и аналитика в реальном времени' },
  { icon: <SafetyCertificateOutlined />, text: 'Ролевой доступ и журнал действий' },
];

export function LoginPage() {
  const { user, login } = useAuth();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const [form] = Form.useForm();
  const [loading, setLoading] = useState(false);

  if (user) return <Navigate to="/" replace />;

  const onFinish = async (values: { email: string; password: string }) => {
    setLoading(true);
    try {
      await login(values.email, values.password);
      message.success('Добро пожаловать в ConsultFlow');
      navigate('/', { replace: true });
    } catch (error) {
      message.error(getApiError(error));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="login-page">
      <div className="login-hero">
        <div className="login-hero__content">
          <span className="login-hero__badge">
            <span
              style={{
                width: 7,
                height: 7,
                borderRadius: '50%',
                background: '#7CF7A8',
                boxShadow: '0 0 0 3px rgba(124,247,168,0.2)',
              }}
            />
            Цифровой продукт · ConsultFlow
          </span>
          <h1 className="login-hero__title">
            От заявки до акта —<br />
            один процесс
          </h1>
          <p className="login-hero__text">
            Платформа автоматизирует обработку заказов на консалтинговые услуги:
            единая воронка заявок, расчёт стоимости, документы и аналитика — в одном окне.
          </p>

          <div className="login-features">
            {FEATURES.map((feature) => (
              <div className="login-feature" key={feature.text}>
                <span className="login-feature__icon">{feature.icon}</span>
                <span>{feature.text}</span>
              </div>
            ))}
          </div>
        </div>

        <div className="login-hero__footer">
          КнАГУ · группа 5ИТб-1 · «Современные программные средства» · 2026
        </div>
      </div>

      <div className="login-panel">
        <div className="login-card">
          <div className="login-card__brand">
            <div
              style={{
                width: 38,
                height: 38,
                borderRadius: 12,
                background: 'linear-gradient(135deg, #6068F8, #8B7CF8)',
                color: '#fff',
                display: 'grid',
                placeItems: 'center',
                fontWeight: 800,
                fontSize: 12,
                boxShadow: '0 8px 18px rgba(96,104,248,0.25)',
              }}
            >
              CF
            </div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 15 }}>ConsultFlow</div>
              <div style={{ fontSize: 11, color: '#9aa0ae' }}>Панель управления</div>
            </div>
          </div>

          <h2 className="login-card__title">Вход в систему</h2>
          <div className="login-card__sub">
            Используйте рабочую почту или одноразовую ссылку из Telegram-бота.
          </div>

          <Form
            form={form}
            layout="vertical"
            requiredMark={false}
            onFinish={onFinish}
            initialValues={{ email: 'admin@consultflow.ru', password: 'admin12345' }}
            size="large"
          >
            <Form.Item
              name="email"
              label="E-mail"
              rules={[
                { required: true, message: 'Укажите e-mail' },
                { type: 'email', message: 'Некорректный e-mail' },
              ]}
            >
              <Input prefix={<MailOutlined style={{ color: '#a5aab8' }} />} placeholder="you@consultflow.ru" />
            </Form.Item>
            <Form.Item
              name="password"
              label="Пароль"
              rules={[{ required: true, message: 'Введите пароль' }]}
            >
              <Input.Password
                prefix={<LockOutlined style={{ color: '#a5aab8' }} />}
                placeholder="••••••••"
              />
            </Form.Item>
            <Button
              type="primary"
              htmlType="submit"
              block
              loading={loading}
              icon={<ArrowRightOutlined />}
              iconPosition="end"
              style={{ height: 44, marginTop: 4 }}
            >
              Войти в дашборд
            </Button>
          </Form>

          <div className="login-demo">
            <Typography.Text strong style={{ fontSize: 12 }}>
              Демо-доступ
            </Typography.Text>
            <div style={{ marginTop: 4 }}>
              Администратор: <code>admin@consultflow.ru</code> / <code>admin12345</code>
            </div>
            <div>
              Менеджер: <code>manager@consultflow.ru</code> / <code>manager12345</code>
            </div>
            <Button
              size="small"
              type="link"
              style={{ padding: 0, marginTop: 6, fontSize: 12 }}
              onClick={() => form.setFieldsValue({ email: 'admin@consultflow.ru', password: 'admin12345' })}
            >
              Подставить демо-доступ
            </Button>
          </div>

          <div
            style={{
              marginTop: 22,
              fontSize: 12,
              color: '#8a90a2',
              display: 'flex',
              alignItems: 'center',
              gap: 6,
            }}
          >
            <CheckCircleFilled style={{ color: '#2FB344' }} />
            Ссылка из бота открывает дашборд без пароля
          </div>
        </div>
      </div>
    </div>
  );
}
