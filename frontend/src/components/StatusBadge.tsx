interface Props {
  status: string;
}

export default function StatusBadge({ status }: Props) {
  const styles: Record<string, string> = {
    running: 'bg-blue-50 text-blue-600',
    complete: 'bg-emerald-50 text-emerald-600',
    failed: 'bg-red-50 text-red-600',
  };

  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${styles[status] ?? 'bg-gray-100 text-text-secondary'}`}>
      {status === 'running' && <span className="w-1.5 h-1.5 rounded-full bg-blue-500 mr-1.5 animate-pulse" />}
      {status}
    </span>
  );
}
