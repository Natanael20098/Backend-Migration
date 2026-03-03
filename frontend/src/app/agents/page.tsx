'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { HiPhone, HiMail, HiIdentification } from 'react-icons/hi';
import Header from '@/components/Header';
import LoadingSpinner from '@/components/LoadingSpinner';
import api from '@/lib/api';
import { Agent } from '@/lib/types';
import { getInitials, formatPercent } from '@/lib/utils';

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);

  useEffect(() => {
    async function fetchAgents() {
      try {
        const res = await api.get('/api/agents', { params: { page, size: 20 } });
        if (res.data.content) {
          setAgents(res.data.content);
          setTotalPages(res.data.totalPages || 1);
        } else if (Array.isArray(res.data)) {
          setAgents(res.data);
          setTotalPages(1);
        }
      } catch {
        setAgents([]);
      } finally {
        setLoading(false);
      }
    }
    fetchAgents();
  }, [page]);

  if (loading) {
    return (
      <div>
        <Header title="Agents" subtitle="Agent directory and management" />
        <div className="p-6">
          <LoadingSpinner message="Loading agents..." />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Agents" subtitle="Agent directory and management" />
      <div className="p-6">
        {agents.length === 0 ? (
          <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
            <p className="text-gray-500">No agents found. Ensure the backend API is running.</p>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
              {agents.map((agent) => (
                <Link key={agent.id} href={`/agents/${agent.id}`}>
                  <div className="group rounded-xl border border-gray-200 bg-white p-6 shadow-sm transition-shadow hover:shadow-md">
                    <div className="flex items-center gap-4">
                      {agent.photoUrl ? (
                        <div
                          className="h-14 w-14 flex-shrink-0 rounded-full bg-cover bg-center"
                          style={{ backgroundImage: `url(${agent.photoUrl})` }}
                        />
                      ) : (
                        <div className="flex h-14 w-14 flex-shrink-0 items-center justify-center rounded-full bg-blue-100 text-lg font-bold text-blue-600">
                          {getInitials(agent.firstName, agent.lastName)}
                        </div>
                      )}
                      <div>
                        <h3 className="font-semibold text-gray-900 group-hover:text-blue-600">
                          {agent.firstName} {agent.lastName}
                        </h3>
                        <p className="text-xs text-gray-500">
                          {agent.brokerage?.name || 'Independent'}
                        </p>
                      </div>
                    </div>
                    <div className="mt-4 space-y-2">
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <HiMail className="h-4 w-4 text-gray-400" />
                        <span className="truncate">{agent.email}</span>
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <HiPhone className="h-4 w-4 text-gray-400" />
                        {agent.phone}
                      </div>
                      <div className="flex items-center gap-2 text-sm text-gray-600">
                        <HiIdentification className="h-4 w-4 text-gray-400" />
                        License: {agent.licenseNumber}
                      </div>
                    </div>
                    <div className="mt-4 flex items-center justify-between border-t border-gray-100 pt-3">
                      <span className="text-xs text-gray-500">
                        Commission: {formatPercent(agent.commissionRate)}
                      </span>
                      <span
                        className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                          agent.active !== false
                            ? 'bg-green-100 text-green-800'
                            : 'bg-red-100 text-red-800'
                        }`}
                      >
                        {agent.active !== false ? 'Active' : 'Inactive'}
                      </span>
                    </div>
                  </div>
                </Link>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="mt-6 flex items-center justify-center gap-2">
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
          </>
        )}
      </div>
    </div>
  );
}
