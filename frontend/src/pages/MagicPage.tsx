import { Button, Result, Spin } from 'antd';
import { useEffect, useRef, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { getApiError } from '@/api/client';
import { useAuth } from '@/auth/AuthContext';

export function MagicPage() {
  const [params] = useSearchParams();
  const { loginWithMagic } = useAuth();
  const navigate = useNavigate();
  const [error, setError] = useState<string | null>(null);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;

    const token = params.get('token');
    if (!token) {
      setError('В ссылке отсутствует токен авторизации.');
      return;
    }

    loginWithMagic(token)
      .then(() => navigate('/', { replace: true }))
      .catch((err) => setError(getApiError(err)));
  }, [params, loginWithMagic, navigate]);

  return (
    <div className="magic-page">
      {error ? (
        <Result
          status="warning"
          title="Ссылка недействительна"
          subTitle={error}
          extra={
            <Button type="primary" onClick={() => navigate('/login', { replace: true })}>
              Войти по паролю
            </Button>
          }
        />
      ) : (
        <div style={{ textAlign: 'center' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16, color: '#6b7280', fontSize: 13 }}>
            Проверяем одноразовую ссылку…
          </div>
        </div>
      )}
    </div>
  );
}
