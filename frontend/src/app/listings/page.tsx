'use client';

import { useEffect, useState, useCallback } from 'react';
import { useRouter } from 'next/navigation';
import Header from '@/components/Header';
import DataTable, { Column } from '@/components/DataTable';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import api from '@/lib/api';
import { Listing } from '@/lib/types';
import { formatCurrency, formatDate } from '@/lib/utils';

const STATUSES = ['', 'ACTIVE', 'PENDING', 'SOLD', 'EXPIRED', 'WITHDRAWN', 'COMING_SOON'];

export default function ListingsPage() {
  const router = useRouter();
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');

  const fetchListings = useCallback(async () => {
    setLoading(true);
    try {
      let res;
      if (statusFilter) {
        res = await api.get(`/api/listings/status/${statusFilter}`);
        const data = Array.isArray(res.data) ? res.data : res.data.content || [];
        setListings(data);
        setTotalPages(1);
      } else {
        res = await api.get('/api/listings', { params: { page, size: 20 } });
        if (res.data.content) {
          setListings(res.data.content);
          setTotalPages(res.data.totalPages || 1);
        } else if (Array.isArray(res.data)) {
          setListings(res.data);
          setTotalPages(1);
        }
      }
    } catch {
      setListings([]);
    } finally {
      setLoading(false);
    }
  }, [page, statusFilter]);

  useEffect(() => {
    fetchListings();
  }, [fetchListings]);

  const handleStatusChange = async (listingId: number, newStatus: string) => {
    try {
      await api.put(`/api/listings/${listingId}`, { status: newStatus });
      fetchListings();
    } catch {
      alert('Failed to update listing status');
    }
  };

  const columns: Column<Listing>[] = [
    {
      key: 'id',
      header: 'ID',
      render: (item) => <span className="font-mono text-xs">#{item.id}</span>,
    },
    {
      key: 'property',
      header: 'Property',
      render: (item) => (
        <div>
          <p className="font-medium">{item.property?.address || 'N/A'}</p>
          <p className="text-xs text-gray-500">
            {item.property?.city}, {item.property?.state}
          </p>
        </div>
      ),
    },
    {
      key: 'listPrice',
      header: 'List Price',
      render: (item) => (
        <span className="font-semibold text-blue-600">{formatCurrency(item.listPrice)}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: (item) => <StatusBadge status={item.status} type="listing" />,
    },
    {
      key: 'agent',
      header: 'Agent',
      render: (item) =>
        item.agent ? `${item.agent.firstName} ${item.agent.lastName}` : 'N/A',
    },
    {
      key: 'mlsNumber',
      header: 'MLS #',
      render: (item) => <span className="font-mono text-xs">{item.mlsNumber || 'N/A'}</span>,
    },
    {
      key: 'listDate',
      header: 'List Date',
      render: (item) => formatDate(item.listDate),
    },
    {
      key: 'daysOnMarket',
      header: 'DOM',
      render: (item) => <span>{item.daysOnMarket ?? '-'}</span>,
    },
    {
      key: 'actions',
      header: 'Actions',
      render: (item) => (
        <select
          onClick={(e) => e.stopPropagation()}
          onChange={(e) => {
            if (e.target.value) {
              handleStatusChange(item.id, e.target.value);
              e.target.value = '';
            }
          }}
          defaultValue=""
          className="rounded border border-gray-300 px-2 py-1 text-xs focus:border-blue-500 focus:outline-none"
        >
          <option value="">Change Status</option>
          {STATUSES.filter((s) => s && s !== item.status).map((s) => (
            <option key={s} value={s}>
              {s}
            </option>
          ))}
        </select>
      ),
    },
  ];

  if (loading) {
    return (
      <div>
        <Header title="Listings" subtitle="Manage active and past property listings" />
        <div className="p-6">
          <LoadingSpinner message="Loading listings..." />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Listings" subtitle="Manage active and past property listings" />
      <div className="p-6">
        {/* Filters */}
        <div className="mb-4 flex items-center gap-4">
          <div>
            <label className="mr-2 text-sm font-medium text-gray-700">Status:</label>
            <select
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value);
                setPage(0);
              }}
              className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            >
              <option value="">All Statuses</option>
              {STATUSES.filter(Boolean).map((s) => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          </div>
          <p className="text-sm text-gray-500">
            {listings.length} listing{listings.length !== 1 ? 's' : ''} found
          </p>
        </div>

        <DataTable
          columns={columns}
          data={listings}
          keyExtractor={(item) => item.id}
          onRowClick={(item) => router.push(`/properties/${item.property?.id}`)}
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
          emptyMessage="No listings found. Ensure the backend API is running."
        />
      </div>
    </div>
  );
}
