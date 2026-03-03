/**
 * Format a number as US currency
 */
export function formatCurrency(amount: number | undefined | null): string {
  if (amount == null) return '$0';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Format a number as US currency with cents
 */
export function formatCurrencyDetailed(amount: number | undefined | null): string {
  if (amount == null) return '$0.00';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format a date string to a readable format
 */
export function formatDate(dateString: string | undefined | null): string {
  if (!dateString) return 'N/A';
  try {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(date);
  } catch {
    return dateString;
  }
}

/**
 * Format a date with time
 */
export function formatDateTime(dateString: string | undefined | null): string {
  if (!dateString) return 'N/A';
  try {
    const date = new Date(dateString);
    return new Intl.DateTimeFormat('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    }).format(date);
  } catch {
    return dateString;
  }
}

/**
 * Format a number with commas
 */
export function formatNumber(num: number | undefined | null): string {
  if (num == null) return '0';
  return new Intl.NumberFormat('en-US').format(num);
}

/**
 * Format square feet
 */
export function formatSqft(sqft: number | undefined | null): string {
  if (sqft == null) return '0 sqft';
  return `${formatNumber(sqft)} sqft`;
}

/**
 * Format percentage
 */
export function formatPercent(value: number | undefined | null, decimals: number = 2): string {
  if (value == null) return '0%';
  return `${value.toFixed(decimals)}%`;
}

/**
 * Get initials from a name
 */
export function getInitials(firstName?: string, lastName?: string): string {
  const first = firstName?.charAt(0)?.toUpperCase() || '';
  const last = lastName?.charAt(0)?.toUpperCase() || '';
  return `${first}${last}`;
}

/**
 * Capitalize first letter of a string
 */
export function capitalize(str: string): string {
  if (!str) return '';
  return str.charAt(0).toUpperCase() + str.slice(1).toLowerCase();
}

/**
 * Format an enum value (SNAKE_CASE to Title Case)
 */
export function formatEnumValue(value: string | undefined | null): string {
  if (!value) return '';
  return value
    .split('_')
    .map((word) => capitalize(word))
    .join(' ');
}

/**
 * Get color class for listing status
 */
export function getListingStatusColor(status: string): string {
  const colors: Record<string, string> = {
    ACTIVE: 'bg-green-100 text-green-800',
    PENDING: 'bg-yellow-100 text-yellow-800',
    SOLD: 'bg-blue-100 text-blue-800',
    EXPIRED: 'bg-gray-100 text-gray-800',
    WITHDRAWN: 'bg-red-100 text-red-800',
    COMING_SOON: 'bg-purple-100 text-purple-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

/**
 * Get color class for loan status
 */
export function getLoanStatusColor(status: string): string {
  const colors: Record<string, string> = {
    STARTED: 'bg-gray-100 text-gray-800',
    SUBMITTED: 'bg-blue-100 text-blue-800',
    PROCESSING: 'bg-cyan-100 text-cyan-800',
    UNDERWRITING: 'bg-indigo-100 text-indigo-800',
    APPROVED: 'bg-green-100 text-green-800',
    CONDITIONAL_APPROVAL: 'bg-yellow-100 text-yellow-800',
    DENIED: 'bg-red-100 text-red-800',
    SUSPENDED: 'bg-orange-100 text-orange-800',
    CLOSING: 'bg-purple-100 text-purple-800',
    FUNDED: 'bg-emerald-100 text-emerald-800',
    WITHDRAWN: 'bg-slate-100 text-slate-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

/**
 * Get color class for closing status
 */
export function getClosingStatusColor(status: string): string {
  const colors: Record<string, string> = {
    SCHEDULED: 'bg-blue-100 text-blue-800',
    IN_PROGRESS: 'bg-yellow-100 text-yellow-800',
    DOCUMENTS_SIGNED: 'bg-indigo-100 text-indigo-800',
    FUNDED: 'bg-green-100 text-green-800',
    RECORDED: 'bg-emerald-100 text-emerald-800',
    COMPLETED: 'bg-teal-100 text-teal-800',
    CANCELLED: 'bg-red-100 text-red-800',
  };
  return colors[status] || 'bg-gray-100 text-gray-800';
}

/**
 * Truncate text to a maximum length
 */
export function truncate(text: string | undefined | null, maxLength: number = 100): string {
  if (!text) return '';
  if (text.length <= maxLength) return text;
  return text.slice(0, maxLength) + '...';
}

/**
 * Build query string from an object
 */
export function buildQueryString(params: Record<string, string | number | boolean | undefined>): string {
  const filtered = Object.entries(params)
    .filter(([, value]) => value !== undefined && value !== '' && value !== null)
    .map(([key, value]) => `${encodeURIComponent(key)}=${encodeURIComponent(String(value))}`);
  return filtered.length > 0 ? `?${filtered.join('&')}` : '';
}

/**
 * Get property type display name
 */
export function getPropertyTypeDisplay(type: string): string {
  const types: Record<string, string> = {
    SINGLE_FAMILY: 'Single Family',
    CONDO: 'Condo',
    TOWNHOUSE: 'Townhouse',
    MULTI_FAMILY: 'Multi Family',
    LAND: 'Land',
    COMMERCIAL: 'Commercial',
  };
  return types[type] || type;
}
