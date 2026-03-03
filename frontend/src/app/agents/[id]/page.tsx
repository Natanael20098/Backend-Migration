'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { HiArrowLeft, HiPhone, HiMail, HiIdentification, HiOfficeBuilding } from 'react-icons/hi';
import Header from '@/components/Header';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import api from '@/lib/api';
import { Agent, Commission, Listing } from '@/lib/types';
import { getInitials, formatCurrency, formatDate, formatPercent } from '@/lib/utils';

export default function AgentDetailPage() {
  const params = useParams();
  const id = params.id;

  const [agent, setAgent] = useState<Agent | null>(null);
  const [commissions, setCommissions] = useState<Commission[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchAgent() {
      try {
        const [agentRes, commRes, listingsRes] = await Promise.allSettled([
          api.get(`/api/agents/${id}`),
          api.get(`/api/agents/${id}/commissions`),
          api.get(`/api/agents/${id}/listings`),
        ]);

        if (agentRes.status === 'fulfilled') setAgent(agentRes.value.data);
        if (commRes.status === 'fulfilled') {
          setCommissions(Array.isArray(commRes.value.data) ? commRes.value.data : []);
        }
        if (listingsRes.status === 'fulfilled') {
          const data = listingsRes.value.data;
          setListings(Array.isArray(data) ? data : data.content || []);
        }
      } catch {
        // Agent not found
      } finally {
        setLoading(false);
      }
    }
    if (id) fetchAgent();
  }, [id]);

  if (loading) {
    return (
      <div>
        <Header title="Agent Detail" />
        <div className="p-6">
          <LoadingSpinner message="Loading agent..." />
        </div>
      </div>
    );
  }

  if (!agent) {
    return (
      <div>
        <Header title="Agent Not Found" />
        <div className="p-6">
          <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
            <p className="text-gray-500">Agent not found.</p>
            <Link href="/agents" className="mt-4 inline-block text-blue-600 hover:underline">
              Back to Agents
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const totalCommissions = commissions.reduce((sum, c) => sum + (c.amount || 0), 0);

  return (
    <div>
      <Header
        title={`${agent.firstName} ${agent.lastName}`}
        subtitle={agent.brokerage?.name || 'Independent Agent'}
        actions={
          <Link
            href="/agents"
            className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <HiArrowLeft className="h-4 w-4" />
            Back
          </Link>
        }
      />
      <div className="p-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Profile */}
          <div className="space-y-6">
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <div className="flex flex-col items-center text-center">
                {agent.photoUrl ? (
                  <div
                    className="h-24 w-24 rounded-full bg-cover bg-center"
                    style={{ backgroundImage: `url(${agent.photoUrl})` }}
                  />
                ) : (
                  <div className="flex h-24 w-24 items-center justify-center rounded-full bg-blue-100 text-2xl font-bold text-blue-600">
                    {getInitials(agent.firstName, agent.lastName)}
                  </div>
                )}
                <h2 className="mt-4 text-xl font-bold text-gray-900">
                  {agent.firstName} {agent.lastName}
                </h2>
                <span
                  className={`mt-2 rounded-full px-3 py-1 text-xs font-medium ${
                    agent.active !== false
                      ? 'bg-green-100 text-green-800'
                      : 'bg-red-100 text-red-800'
                  }`}
                >
                  {agent.active !== false ? 'Active' : 'Inactive'}
                </span>
              </div>

              <div className="mt-6 space-y-3">
                <div className="flex items-center gap-3 text-sm">
                  <HiMail className="h-5 w-5 text-gray-400" />
                  <span className="text-gray-700">{agent.email}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <HiPhone className="h-5 w-5 text-gray-400" />
                  <span className="text-gray-700">{agent.phone}</span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <HiIdentification className="h-5 w-5 text-gray-400" />
                  <span className="text-gray-700">
                    {agent.licenseNumber} ({agent.licenseState})
                  </span>
                </div>
                <div className="flex items-center gap-3 text-sm">
                  <HiOfficeBuilding className="h-5 w-5 text-gray-400" />
                  <span className="text-gray-700">{agent.brokerage?.name || 'N/A'}</span>
                </div>
              </div>
            </div>

            {/* Stats */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">Performance</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Commission Rate</span>
                  <span className="font-medium">{formatPercent(agent.commissionRate)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Active Listings</span>
                  <span className="font-medium">{listings.length}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Total Commissions</span>
                  <span className="font-medium text-green-600">{formatCurrency(totalCommissions)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">License Expires</span>
                  <span className="font-medium">{formatDate(agent.licenseExpiration)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Years in Business</span>
                  <span className="font-medium">
                    {agent.yearStarted ? new Date().getFullYear() - agent.yearStarted : 'N/A'}
                  </span>
                </div>
              </div>
            </div>

            {agent.bio && (
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="mb-2 text-lg font-semibold text-gray-900">Bio</h3>
                <p className="text-sm text-gray-700">{agent.bio}</p>
              </div>
            )}
          </div>

          {/* Listings & Commissions */}
          <div className="lg:col-span-2 space-y-6">
            {/* Active Listings */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">
                Listings ({listings.length})
              </h3>
              {listings.length === 0 ? (
                <p className="text-sm text-gray-500">No listings found for this agent.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Property</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Price</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">List Date</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {listings.map((listing) => (
                        <tr key={listing.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm">
                            <Link href={`/properties/${listing.property?.id}`} className="text-blue-600 hover:underline">
                              {listing.property?.address || 'N/A'}
                            </Link>
                          </td>
                          <td className="px-4 py-3 text-sm font-medium">{formatCurrency(listing.listPrice)}</td>
                          <td className="px-4 py-3"><StatusBadge status={listing.status} type="listing" /></td>
                          <td className="px-4 py-3 text-sm text-gray-500">{formatDate(listing.listDate)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>

            {/* Commission History */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">
                Commission History ({commissions.length})
              </h3>
              {commissions.length === 0 ? (
                <p className="text-sm text-gray-500">No commission records found.</p>
              ) : (
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Listing</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Amount</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Rate</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Type</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Paid</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {commissions.map((comm) => (
                        <tr key={comm.id} className="hover:bg-gray-50">
                          <td className="px-4 py-3 text-sm">#{comm.listingId}</td>
                          <td className="px-4 py-3 text-sm font-medium text-green-600">{formatCurrency(comm.amount)}</td>
                          <td className="px-4 py-3 text-sm">{formatPercent(comm.rate)}</td>
                          <td className="px-4 py-3 text-sm">{comm.type || 'N/A'}</td>
                          <td className="px-4 py-3"><StatusBadge status={comm.status || 'PENDING'} /></td>
                          <td className="px-4 py-3 text-sm text-gray-500">{formatDate(comm.paidDate)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
