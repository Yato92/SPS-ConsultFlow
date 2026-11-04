import { PRACTICE_META, STATUS_META } from '@/constants';
import type { OrderStatus, Practice } from '@/api/types';

export function StatusPill({ status }: { status: OrderStatus }) {
  const meta = STATUS_META[status];
  if (!meta) return <span>{status}</span>;
  return (
    <span
      className="status-pill"
      style={{ background: `${meta.color}14`, color: meta.color }}
    >
      <span className="status-pill__dot" style={{ background: meta.color }} />
      {meta.label}
    </span>
  );
}

export function PracticePill({ practice }: { practice: Practice }) {
  const meta = PRACTICE_META[practice];
  if (!meta) return <span>{practice}</span>;
  return (
    <span
      className="practice-pill"
      style={{ background: `${meta.color}12`, color: meta.color }}
    >
      {meta.label}
    </span>
  );
}
