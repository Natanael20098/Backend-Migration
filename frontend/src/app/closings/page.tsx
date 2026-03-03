'use client';

import { useEffect, useState, useCallback } from 'react';
import Header from '@/components/Header';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import api from '@/lib/api';
import { ClosingDetail, ClosingDocument } from '@/lib/types';
import { formatCurrency, formatDate, formatEnumValue } from '@/lib/utils';

export default function ClosingsPage() {
  const [closings, setClosings] = useState<ClosingDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [expandedId, setExpandedId] = useState<number | null>(null);
  const [documents, setDocuments] = useState<Record<number, ClosingDocument[]>>({});

  const fetchClosings = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get('/api/closings', { params: { page, size: 20 } });
      if (res.data.content) {
        setClosings(res.data.content);
        setTotalPages(res.data.totalPages || 1);
      } else if (Array.isArray(res.data)) {
        setClosings(res.data);
        setTotalPages(1);
      }
    } catch {
      setClosings([]);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchClosings();
  }, [fetchClosings]);

  const toggleExpand = async (closingId: number) => {
    if (expandedId === closingId) {
      setExpandedId(null);
      return;
    }
    setExpandedId(closingId);

    // Fetch documents if not already loaded
    if (!documents[closingId]) {
      try {
        const res = await api.get(`/api/closings/${closingId}/documents`);
        const docs = Array.isArray(res.data) ? res.data : [];
        setDocuments((prev) => ({ ...prev, [closingId]: docs }));
      } catch {
        setDocuments((prev) => ({ ...prev, [closingId]: [] }));
      }
    }
  };

  if (loading) {
    return (
      <div>
        <Header title="Closings" subtitle="Track closing pipeline and document management" />
        <div className="p-6">
          <LoadingSpinner message="Loading closings..." />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Closings" subtitle="Track closing pipeline and document management" />
      <div className="p-6">
        {closings.length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
            <p className="text-gray-500">No closings found. Ensure the backend API is running.</p>
          </div>
        ) : (
          <div className="space-y-4">
            {closings.map((closing) => (
              <div
                key={closing.id}
                className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden"
              >
                {/* Main row */}
                <div
                  onClick={() => toggleExpand(closing.id)}
                  className="flex cursor-pointer items-center gap-6 px-6 py-4 hover:bg-gray-50"
                >
                  <div className="flex-shrink-0">
                    <span className="font-mono text-sm text-gray-500">#{closing.id}</span>
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="font-medium text-gray-900">
                      {closing.loanApplication?.property?.address ||
                        closing.listing?.property?.address ||
                        'N/A'}
                    </p>
                    <p className="text-xs text-gray-500">
                      Borrower:{' '}
                      {closing.loanApplication?.borrower
                        ? `${closing.loanApplication.borrower.firstName} ${closing.loanApplication.borrower.lastName}`
                        : 'N/A'}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-semibold text-blue-600">
                      {formatCurrency(closing.cashToClose)}
                    </p>
                    <p className="text-xs text-gray-500">Cash to Close</p>
                  </div>
                  <div className="text-center">
                    <p className="text-sm text-gray-900">{formatDate(closing.closingDate)}</p>
                    <p className="text-xs text-gray-500">Closing Date</p>
                  </div>
                  <div>
                    <StatusBadge status={closing.status} type="closing" />
                  </div>
                </div>

                {/* Expanded details */}
                {expandedId === closing.id && (
                  <div className="border-t border-gray-200 bg-gray-50 px-6 py-4">
                    <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
                      {/* Escrow Info */}
                      <div>
                        <h4 className="mb-3 text-sm font-semibold text-gray-700">Escrow Information</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-500">Company</span>
                            <span className="font-medium">{closing.escrowCompany || 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Officer</span>
                            <span className="font-medium">{closing.escrowOfficer || 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Escrow #</span>
                            <span className="font-medium font-mono">{closing.escrowNumber || 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Location</span>
                            <span className="font-medium">{closing.closingLocation || 'N/A'}</span>
                          </div>
                        </div>
                      </div>

                      {/* Title Info */}
                      <div>
                        <h4 className="mb-3 text-sm font-semibold text-gray-700">Title & Insurance</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-500">Title Company</span>
                            <span className="font-medium">{closing.titleCompany || 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Policy #</span>
                            <span className="font-medium font-mono">{closing.titlePolicyNumber || 'N/A'}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Title Insurance</span>
                            <span className="font-medium">{formatCurrency(closing.titleInsuranceAmount)}</span>
                          </div>
                        </div>
                      </div>

                      {/* Financial Summary */}
                      <div>
                        <h4 className="mb-3 text-sm font-semibold text-gray-700">Financial Summary</h4>
                        <div className="space-y-2 text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-500">Closing Costs</span>
                            <span className="font-medium">{formatCurrency(closing.closingCosts)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Prepaid Items</span>
                            <span className="font-medium">{formatCurrency(closing.prepaidItems)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Prorations</span>
                            <span className="font-medium">{formatCurrency(closing.prorations)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Seller Credits</span>
                            <span className="font-medium text-green-600">{formatCurrency(closing.sellerCredits)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-gray-500">Earnest Money</span>
                            <span className="font-medium text-green-600">{formatCurrency(closing.earnestMoneyApplied)}</span>
                          </div>
                          <div className="flex justify-between border-t border-gray-300 pt-2">
                            <span className="font-semibold text-gray-700">Cash to Close</span>
                            <span className="font-bold text-blue-600">{formatCurrency(closing.cashToClose)}</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Dates */}
                    <div className="mt-4 flex gap-6 border-t border-gray-200 pt-4 text-sm">
                      <div>
                        <span className="text-gray-500">Funding Date: </span>
                        <span className="font-medium">{formatDate(closing.fundingDate)}</span>
                      </div>
                      <div>
                        <span className="text-gray-500">Recording Date: </span>
                        <span className="font-medium">{formatDate(closing.recordingDate)}</span>
                      </div>
                    </div>

                    {/* Documents */}
                    <div className="mt-4 border-t border-gray-200 pt-4">
                      <h4 className="mb-3 text-sm font-semibold text-gray-700">Document Checklist</h4>
                      {documents[closing.id] && documents[closing.id].length > 0 ? (
                        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
                          {documents[closing.id].map((doc) => (
                            <div
                              key={doc.id}
                              className="flex items-center justify-between rounded-lg border border-gray-200 bg-white px-3 py-2"
                            >
                              <div>
                                <p className="text-sm font-medium text-gray-900">{doc.documentName}</p>
                                <p className="text-xs text-gray-500">{formatEnumValue(doc.documentType)}</p>
                              </div>
                              <StatusBadge status={doc.status || 'PENDING'} />
                            </div>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-500">No documents found for this closing.</p>
                      )}
                    </div>

                    {closing.notes && (
                      <div className="mt-4 border-t border-gray-200 pt-4">
                        <h4 className="mb-1 text-sm font-semibold text-gray-700">Notes</h4>
                        <p className="text-sm text-gray-600">{closing.notes}</p>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}

            {/* Pagination */}
            {totalPages > 1 && (
              <div className="flex items-center justify-center gap-2 pt-4">
                <button
                  onClick={() => setPage(Math.max(0, page - 1))}
                  disabled={page === 0}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Previous
                </button>
                <span className="px-4 text-sm text-gray-600">
                  Page {page + 1} of {totalPages}
                </span>
                <button
                  onClick={() => setPage(Math.min(totalPages - 1, page + 1))}
                  disabled={page >= totalPages - 1}
                  className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                >
                  Next
                </button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
