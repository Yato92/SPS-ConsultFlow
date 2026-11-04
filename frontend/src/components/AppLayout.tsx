import { Avatar, Dropdown, Grid, Layout, Menu } from 'antd';
import type { MenuProps } from 'antd';
import {
  AppstoreOutlined,
  LogoutOutlined,
  MenuOutlined,
  MessageOutlined,
  ShoppingOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import { useMemo, useState } from 'react';
import { Outlet, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '@/auth/AuthContext';
import { ROLE_LABELS } from '@/constants';
import { Brand } from './Brand';

const { Header, Sider, Content } = Layout;

const NAV_ITEMS: MenuProps['items'] = [
  { key: '/', icon: <AppstoreOutlined />, label: 'Обзор' },
  { key: '/orders', icon: <ShoppingOutlined />, label: 'Заказы' },
  { key: '/clients', icon: <TeamOutlined />, label: 'Клиенты' },
  { key: '/telegram', icon: <MessageOutlined />, label: 'Telegram-бот' },
];

const PAGE_TITLES: Record<string, string> = {
  '/': 'Обзор',
  '/orders': 'Заказы',
  '/clients': 'Клиенты',
  '/telegram': 'Telegram-бот',
};

export function AppLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const screens = Grid.useBreakpoint();
  const [collapsed, setCollapsed] = useState(false);

  const selectedKey = useMemo(() => {
    const match = Object.keys(PAGE_TITLES)
      .filter((key) => key !== '/')
      .find((key) => location.pathname.startsWith(key));
    return match ?? '/';
  }, [location.pathname]);

  const dropdownItems: MenuProps['items'] = [
    {
      key: 'profile',
      icon: <UserOutlined />,
      label: (
        <div style={{ lineHeight: 1.35 }}>
          <div style={{ fontWeight: 600 }}>{user?.full_name}</div>
          <div style={{ fontSize: 11.5, color: '#8a90a2' }}>
            {ROLE_LABELS[user?.role ?? ''] ?? user?.role}
          </div>
        </div>
      ),
      disabled: true,
    },
    { type: 'divider' },
    { key: 'logout', icon: <LogoutOutlined />, label: 'Выйти', danger: true },
  ];

  return (
    <Layout style={{ minHeight: '100vh' }}>
      <Sider
        width={252}
        breakpoint="lg"
        collapsedWidth={0}
        trigger={null}
        collapsible
        collapsed={collapsed}
        onBreakpoint={(broken) => setCollapsed(broken)}
        className="cf-sider"
      >
        <div className="cf-sider__inner">
          <Brand />
          <Menu
            mode="inline"
            selectedKeys={[selectedKey]}
            items={NAV_ITEMS}
            className="cf-menu"
            onClick={({ key }) => {
              navigate(key);
              if (!screens.lg) setCollapsed(true);
            }}
          />
          <div className="cf-sider-footer">
            <div className="cf-user-card">
              <Avatar
                size={34}
                style={{
                  background: 'linear-gradient(135deg, #6068F8, #8B7CF8)',
                  flex: 'none',
                  fontSize: 12,
                  fontWeight: 700,
                }}
              >
                {user?.full_name?.slice(0, 1) ?? 'U'}
              </Avatar>
              <div className="cf-user-card__meta">
                <div className="cf-user-card__name">{user?.full_name}</div>
                <div className="cf-user-card__role">
                  {ROLE_LABELS[user?.role ?? ''] ?? user?.role}
                </div>
              </div>
              <LogoutOutlined
                style={{ color: '#9aa0ae', cursor: 'pointer' }}
                onClick={logout}
              />
            </div>
          </div>
        </div>
      </Sider>

      <Layout>
        <Header className="cf-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            {!screens.lg && (
              <MenuOutlined
                style={{ fontSize: 17, cursor: 'pointer' }}
                onClick={() => setCollapsed((value) => !value)}
              />
            )}
            <div>
              <div className="cf-header__title">{PAGE_TITLES[selectedKey]}</div>
              <div className="cf-header__sub">
                {dayjs().format('dddd, D MMMM YYYY')} · ConsultFlow
              </div>
            </div>
          </div>

          <div className="cf-header__actions">
            <span className="cf-chip">
              <span className="cf-chip__dot" />
              Демо-стенд
            </span>
            <Dropdown
              menu={{
                items: dropdownItems,
                onClick: ({ key }) => {
                  if (key === 'logout') logout();
                },
              }}
              trigger={['click']}
              placement="bottomRight"
            >
              <Avatar
                size={36}
                style={{
                  background: 'linear-gradient(135deg, #6068F8, #8B7CF8)',
                  cursor: 'pointer',
                  fontSize: 13,
                  fontWeight: 700,
                }}
              >
                {user?.full_name?.slice(0, 1) ?? 'U'}
              </Avatar>
            </Dropdown>
          </div>
        </Header>

        <Content className="cf-content">
          <div className="cf-page fade-in">
            <Outlet />
          </div>
        </Content>
      </Layout>
    </Layout>
  );
}
