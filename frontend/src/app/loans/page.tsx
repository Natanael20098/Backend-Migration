'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import Header from '@/components/Header';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import api from '@/lib/api';
import { LoanApplication } from '@/lib/types';
import { formatCurrency, formatDate, formatEnumValue } from '@/lib/utils';

const LOAN_STATUSES = [
  'STARTED',
  'SUBMITTED',
  'PROCESSING',
  'UNDERWRITING',
  'APPROVED',
  'CONDITIONAL_APPROVAL',
  'DENIED',
  'CLOSING',
  'FUNDED',
];

const STATUS_STAGE_ORDER: Record<string, number> = {
  STARTED: 0,
  SUBMITTED: 1,
  PROCESSING: 2,
  UNDERWRITING: 3,
  CONDITIONAL_APPROVAL: 4,
  APPROVED: 5,
  CLOSING: 6,
  FUNDED: 7,
  DENIED: -1,
  SUSPENDED: -2,
  WITHDRAWN: -3,
};

export default function LoansPage() {
  const router = useRouter();
  const [loans, setLoans] = useState<LoanApplication[]>([]);
  const [loading, setLoading] = useState(true);
  const [view, setView] = useState<'table' | 'kanban'>('table');
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');

  useEffect(() => {
    async function fetchLoans() {
      setLoading(true);
      try {
        let res;
        if (statusFilter) {
          res = await api.get(`/api/loans/status/${statusFilter}`);
          const data = Array.isArray(res.data) ? res.data : res.data.content || [];
          setLoans(data);
          setTotalPages(1);
        } else {
          res = await api.get('/api/loans', { params: { page, size: 50 } });
          if (res.data.content) {
            setLoans(res.data.content);
            setTotalPages(res.data.totalPages || 1);
          } else if (Array.isArray(res.data)) {
            setLoans(res.data);
            setTotalPages(1);
          }
        }
      } catch {
        setLoans([]);
      } finally {
        setLoading(false);
      }
    }
    fetchLoans();
  }, [page, statusFilter]);

  // Group loans by status for kanban view
  const groupedLoans = LOAN_STATUSES.reduce((acc, status) => {
    acc[status] = loans.filter((l) => l.status === status);
    return acc;
  }, {} as Record<string, LoanApplication[]>);

  if (loading) {
    return (
      <div>
        <Header title="Loan Pipeline" subtitle="Track and manage mortgage applications" />
        <div className="p-6">
          <LoadingSpinner message="Loading loan pipeline..." />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header
        title="Loan Pipeline"
        subtitle="Track and manage mortgage applications"
        actions={
          <Link
            href="/loans/new"
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + New Loan Application
          </Link>
        }
      />
      <div className="p-6">
        {/* Controls */}
        <div className="mb-4 flex flex-wrap items-center gap-4">
          <div className="flex rounded-lg border border-gray-300 bg-white">
            <button
              onClick={() => setView('table')}
              className={`px-4 py-2 text-sm font-medium ${
                view === 'table'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-700 hover:bg-gray-50'
              } rounded-l-lg`}
            >
              Table
            </button>
            <button
              onClick={() => setView('kanban')}
              className={`px-4 py-2 text-sm font-medium ${
                view === 'kanban'
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-700 hover:bg-gray-50'
              } rounded-r-lg`}
            >
              Kanban
            </button>
          </div>
          {view === 'table' && (
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              {LOAN_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {formatEnumValue(s)}
                </option>
              ))}
            </select>
          )}
          <span className="text-sm text-gray-500">{loans.length} loans</span>
        </div>

        {/* Table View */}
        {view === 'table' && (
          <div className="overflow-hidden rounded-lg border border-gray-200 bg-white shadow-sm">
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">ID</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Borrower</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Property</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Loan Amount</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Type</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Rate</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Status</th>
                    <th className="px-4 py-3 text-left text-xs font-medium uppercase text-gray-500">Applied</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200">
                  {loans.length === 0 ? (
                    <tr>
                      <td colSpan={8} className="px-4 py-12 text-center text-sm text-gray-500">
                        No loan applications found.
                      </td>
                    </tr>
                  ) : (
                    loans
                      .sort((a, b) => (STATUS_STAGE_ORDER[a.status] ?? 0) - (STATUS_STAGE_ORDER[b.status] ?? 0))
                      .map((loan) => (
                        <tr
                          key={loan.id}
                          onClick={() => router.push(`/loans/${loan.id}`)}
                          className="cursor-pointer hover:bg-gray-50"
                        >
                          <td className="px-4 py-3 text-sm font-mono">#{loan.id}</td>
                          <td className="px-4 py-3 text-sm">
                            {loan.borrower
                              ? `${loan.borrower.firstName} ${loan.borrower.lastName}`
                              : 'N/A'}
                          </td>
                          <td className="px-4 py-3 text-sm">{loan.property?.address || 'N/A'}</td>
                          <td className="px-4 py-3 text-sm font-semibold text-blue-600">
                            {formatCurrency(loan.loanAmount)}
                          </td>
                          <td className="px-4 py-3 text-sm">{formatEnumValue(loan.loanType)}</td>
                          <td className="px-4 py-3 text-sm">{loan.interestRate}%</td>
                          <td className="px-4 py-3">
                            <StatusBadge status={loan.status} type="loan" />
                          </td>
                          <td className="px-4 py-3 text-sm text-gray-500">{formatDate(loan.applicationDate)}</td>
                        </tr>
                      ))
                  )}
                </tbody>
              </table>
            </div>
            {totalPages > 1 && (
              <div className="flex items-center justify-between border-t border-gray-200 px-4 py-3">
                <span className="text-sm text-gray-500">Page {page + 1} of {totalPages}</span>
                <div className="flex gap-2">
                  <button
                    onClick={() => setPage(Math.max(0, page - 1))}
                    disabled={page === 0}
                    className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                    disabled={page >= totalPages - 1}
                    className="rounded border border-gray-300 px-3 py-1 text-sm disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Kanban View */}
        {view === 'kanban' && (
          <div className="flex gap-4 overflow-x-auto pb-4">
            {LOAN_STATUSES.map((status) => (
              <div
                key={status}
                className="w-72 flex-shrink-0 rounded-lg border border-gray-200 bg-gray-50"
              >
                <div className="flex items-center justify-between border-b border-gray-200 bg-white px-4 py-3 rounded-t-lg">
                  <div className="flex items-center gap-2">
                    <StatusBadge status={status} type="loan" size="sm" />
                    <span className="text-xs text-gray-500">
                      ({groupedLoans[status]?.length || 0})
                    </span>
                  </div>
                </div>
                <div className="space-y-2 p-3">
                  {(groupedLoans[status] || []).map((loan) => (
                    <div
                      key={loan.id}
                      onClick={() => router.push(`/loans/${loan.id}`)}
                      className="cursor-pointer rounded-lg border border-gray-200 bg-white p-3 shadow-sm hover:shadow-md transition-shadow"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-xs font-mono text-gray-500">#{loan.id}</span>
                        <span className="text-xs text-gray-500">{formatEnumValue(loan.loanType)}</span>
                      </div>
                      <p className="mt-1 text-sm font-semibold text-blue-600">
                        {formatCurrency(loan.loanAmount)}
                      </p>
                      <p className="mt-1 text-xs text-gray-600">
                        {loan.borrower
                          ? `${loan.borrower.firstName} ${loan.borrower.lastName}`
                          : 'N/A'}
                      </p>
                      <p className="text-xs text-gray-400">
                        {loan.property?.address || 'No property'}
                      </p>
                    </div>
                  ))}
                  {(groupedLoans[status] || []).length === 0 && (
                    <p className="py-4 text-center text-xs text-gray-400">No loans</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
