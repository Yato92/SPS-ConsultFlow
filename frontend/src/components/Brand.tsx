export function Brand({ light = false }: { light?: boolean }) {
  return (
    <div className="cf-brand">
      <div
        className="cf-brand__logo"
        style={light ? { background: 'rgba(255,255,255,0.18)', boxShadow: 'none' } : undefined}
      >
        CF
      </div>
      <div>
        <div className="cf-brand__title" style={light ? { color: '#fff' } : undefined}>
          ConsultFlow
        </div>
        <div
          className="cf-brand__subtitle"
          style={light ? { color: 'rgba(255,255,255,0.7)' } : undefined}
        >
          От заявки до акта — один процесс
        </div>
      </div>
    </div>
  );
}
