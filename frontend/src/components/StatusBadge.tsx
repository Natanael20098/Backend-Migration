import { formatEnumValue, getListingStatusColor, getLoanStatusColor, getClosingStatusColor } from '@/lib/utils';

interface StatusBadgeProps {
  status: string;
  type?: 'listing' | 'loan' | 'closing' | 'generic';
  size?: 'sm' | 'md';
}

const genericColors: Record<string, string> = {
  ACTIVE: 'bg-green-100 text-green-800',
  INACTIVE: 'bg-gray-100 text-gray-800',
  PENDING: 'bg-yellow-100 text-yellow-800',
  COMPLETED: 'bg-blue-100 text-blue-800',
  CANCELLED: 'bg-red-100 text-red-800',
  APPROVED: 'bg-green-100 text-green-800',
  DENIED: 'bg-red-100 text-red-800',
  NEW: 'bg-blue-100 text-blue-800',
  VERIFIED: 'bg-green-100 text-green-800',
  SCHEDULED: 'bg-indigo-100 text-indigo-800',
  CONFIRMED: 'bg-cyan-100 text-cyan-800',
  SUBMITTED: 'bg-blue-100 text-blue-800',
  ACCEPTED: 'bg-green-100 text-green-800',
  REJECTED: 'bg-red-100 text-red-800',
  COUNTERED: 'bg-orange-100 text-orange-800',
  ORDERED: 'bg-blue-100 text-blue-800',
  FUNDED: 'bg-emerald-100 text-emerald-800',
};

export default function StatusBadge({
  status,
  type = 'generic',
  size = 'sm',
}: StatusBadgeProps) {
  let colorClass: string;

  switch (type) {
    case 'listing':
      colorClass = getListingStatusColor(status);
      break;
    case 'loan':
      colorClass = getLoanStatusColor(status);
      break;
    case 'closing':
      colorClass = getClosingStatusColor(status);
      break;
    default:
      colorClass = genericColors[status] || 'bg-gray-100 text-gray-800';
  }

  const sizeClass = size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-3 py-1 text-sm';

  return (
    <span
      className={`inline-flex items-center rounded-full font-medium ${colorClass} ${sizeClass}`}
    >
      {formatEnumValue(status)}
    </span>
  );
}
