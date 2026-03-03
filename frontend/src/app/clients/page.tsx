'use client';

import { useEffect, useState, useCallback } from 'react';
import Header from '@/components/Header';
import DataTable, { Column } from '@/components/DataTable';
import StatusBadge from '@/components/StatusBadge';
import Modal from '@/components/Modal';
import LoadingSpinner from '@/components/LoadingSpinner';
import api from '@/lib/api';
import { Client } from '@/lib/types';
import { formatCurrency, formatDate } from '@/lib/utils';

const CLIENT_TYPES = ['', 'BUYER', 'SELLER', 'BORROWER', 'INVESTOR'];

export default function ClientsPage() {
  const [clients, setClients] = useState<Client[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [typeFilter, setTypeFilter] = useState('');
  const [searchTerm, setSearchTerm] = useState('');
  const [showAddModal, setShowAddModal] = useState(false);
  const [newClient, setNewClient] = useState({
    firstName: '',
    lastName: '',
    email: '',
    phone: '',
    clientType: 'BUYER',
    annualIncome: '',
    creditScore: '',
  });

  const fetchClients = useCallback(async () => {
    setLoading(true);
    try {
      let res;
      if (typeFilter) {
        res = await api.get(`/api/clients/type/${typeFilter}`);
        const data = Array.isArray(res.data) ? res.data : res.data.content || [];
        setClients(data);
        setTotalPages(1);
      } else {
        res = await api.get('/api/clients', { params: { page, size: 20 } });
        if (res.data.content) {
          setClients(res.data.content);
          setTotalPages(res.data.totalPages || 1);
        } else if (Array.isArray(res.data)) {
          setClients(res.data);
          setTotalPages(1);
        }
      }
    } catch {
      setClients([]);
    } finally {
      setLoading(false);
    }
  }, [page, typeFilter]);

  useEffect(() => {
    fetchClients();
  }, [fetchClients]);

  const filteredClients = searchTerm
    ? clients.filter(
        (c) =>
          `${c.firstName} ${c.lastName}`.toLowerCase().includes(searchTerm.toLowerCase()) ||
          c.email?.toLowerCase().includes(searchTerm.toLowerCase())
      )
    : clients;

  const handleAddClient = async () => {
    try {
      await api.post('/api/clients', {
        ...newClient,
        annualIncome: newClient.annualIncome ? Number(newClient.annualIncome) : undefined,
        creditScore: newClient.creditScore ? Number(newClient.creditScore) : undefined,
      });
      setShowAddModal(false);
      setNewClient({
        firstName: '',
        lastName: '',
        email: '',
        phone: '',
        clientType: 'BUYER',
        annualIncome: '',
        creditScore: '',
      });
      fetchClients();
    } catch {
      alert('Failed to create client');
    }
  };

  const columns: Column<Client>[] = [
    {
      key: 'id',
      header: 'ID',
      render: (item) => <span className="font-mono text-xs">#{item.id}</span>,
    },
    {
      key: 'name',
      header: 'Name',
      render: (item) => (
        <div>
          <p className="font-medium">
            {item.firstName} {item.lastName}
          </p>
          <p className="text-xs text-gray-500">{item.email}</p>
        </div>
      ),
    },
    {
      key: 'phone',
      header: 'Phone',
      render: (item) => item.phone || 'N/A',
    },
    {
      key: 'clientType',
      header: 'Type',
      render: (item) => <StatusBadge status={item.clientType || 'BUYER'} />,
    },
    {
      key: 'creditScore',
      header: 'Credit Score',
      render: (item) => (
        <span
          className={`font-medium ${
            (item.creditScore || 0) >= 700
              ? 'text-green-600'
              : (item.creditScore || 0) >= 640
              ? 'text-yellow-600'
              : 'text-red-600'
          }`}
        >
          {item.creditScore || 'N/A'}
        </span>
      ),
    },
    {
      key: 'annualIncome',
      header: 'Annual Income',
      render: (item) => (item.annualIncome ? formatCurrency(item.annualIncome) : 'N/A'),
    },
    {
      key: 'preApproved',
      header: 'Pre-Approved',
      render: (item) =>
        item.preApproved ? (
          <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
            Yes - {formatCurrency(item.preApprovalAmount)}
          </span>
        ) : (
          <span className="text-xs text-gray-500">No</span>
        ),
    },
    {
      key: 'createdAt',
      header: 'Created',
      render: (item) => formatDate(item.createdAt),
    },
  ];

  if (loading) {
    return (
      <div>
        <Header title="Clients" subtitle="Client management and CRM" />
        <div className="p-6">
          <LoadingSpinner message="Loading clients..." />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header
        title="Clients"
        subtitle="Client management and CRM"
        actions={
          <button
            onClick={() => setShowAddModal(true)}
            className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
          >
            + Add Client
          </button>
        }
      />
      <div className="p-6">
        {/* Filters */}
        <div className="mb-4 flex flex-wrap items-center gap-4">
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search by name or email..."
            className="w-64 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          />
          <select
            value={typeFilter}
            onChange={(e) => {
              setTypeFilter(e.target.value);
              setPage(0);
            }}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
          >
            <option value="">All Types</option>
            {CLIENT_TYPES.filter(Boolean).map((t) => (
              <option key={t} value={t}>
                {t}
              </option>
            ))}
          </select>
          <span className="text-sm text-gray-500">
            {filteredClients.length} client{filteredClients.length !== 1 ? 's' : ''}
          </span>
        </div>

        <DataTable
          columns={columns}
          data={filteredClients}
          keyExtractor={(item) => item.id}
          currentPage={page}
          totalPages={totalPages}
          onPageChange={setPage}
          emptyMessage="No clients found. Ensure the backend API is running."
        />
      </div>

      {/* Add Client Modal */}
      <Modal isOpen={showAddModal} onClose={() => setShowAddModal(false)} title="Add New Client">
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">First Name *</label>
              <input
                type="text"
                value={newClient.firstName}
                onChange={(e) => setNewClient({ ...newClient, firstName: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Last Name *</label>
              <input
                type="text"
                value={newClient.lastName}
                onChange={(e) => setNewClient({ ...newClient, lastName: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          <div>
            <label className="mb-1 block text-sm font-medium text-gray-700">Email *</label>
            <input
              type="email"
              value={newClient.email}
              onChange={(e) => setNewClient({ ...newClient, email: e.target.value })}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
            />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Phone</label>
              <input
                type="text"
                value={newClient.phone}
                onChange={(e) => setNewClient({ ...newClient, phone: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Client Type</label>
              <select
                value={newClient.clientType}
                onChange={(e) => setNewClient({ ...newClient, clientType: e.target.value })}
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              >
                {CLIENT_TYPES.filter(Boolean).map((t) => (
                  <option key={t} value={t}>
                    {t}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Annual Income</label>
              <input
                type="number"
                value={newClient.annualIncome}
                onChange={(e) => setNewClient({ ...newClient, annualIncome: e.target.value })}
                placeholder="85000"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-sm font-medium text-gray-700">Credit Score</label>
              <input
                type="number"
                value={newClient.creditScore}
                onChange={(e) => setNewClient({ ...newClient, creditScore: e.target.value })}
                placeholder="720"
                min="300"
                max="850"
                className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
          </div>
          <div className="flex justify-end gap-3 pt-4">
            <button
              onClick={() => setShowAddModal(false)}
              className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              onClick={handleAddClient}
              disabled={!newClient.firstName || !newClient.lastName || !newClient.email}
              className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Create Client
            </button>
          </div>
        </div>
      </Modal>
    </div>
  );
}
