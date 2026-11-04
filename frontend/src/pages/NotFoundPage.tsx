import { Button, Result } from 'antd';
import { useNavigate } from 'react-router-dom';

export function NotFoundPage() {
  const navigate = useNavigate();
  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'grid',
        placeItems: 'center',
        background: '#f4f5fa',
      }}
    >
      <Result
        status="404"
        title="Страница не найдена"
        subTitle="Возможно, ссылка устарела или раздел был перемещён."
        extra={
          <Button type="primary" onClick={() => navigate('/')}>
            На главную
          </Button>
        }
      />
    </div>
  );
}
