'use client';

import { useEffect, useState } from 'react';
import {
  HiOfficeBuilding,
  HiClipboardList,
  HiCurrencyDollar,
  HiDocumentText,
} from 'react-icons/hi';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  Legend,
} from 'recharts';
import Header from '@/components/Header';
import StatsCard from '@/components/StatsCard';
import LoadingSpinner from '@/components/LoadingSpinner';
import api from '@/lib/api';

interface DashboardStats {
  totalProperties: number;
  activeListings: number;
  loansInPipeline: number;
  pendingClosings: number;
}

interface LoanStatusCount {
  status: string;
  count: number;
}

interface ListingStatusCount {
  status: string;
  count: number;
}

const LOAN_STATUS_COLORS = [
  '#6b7280', '#3b82f6', '#06b6d4', '#6366f1',
  '#22c55e', '#eab308', '#ef4444', '#f97316',
  '#a855f7', '#10b981', '#64748b',
];

const LISTING_STATUS_COLORS = [
  '#22c55e', '#eab308', '#3b82f6', '#6b7280', '#ef4444', '#a855f7',
];

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats>({
    totalProperties: 0,
    activeListings: 0,
    loansInPipeline: 0,
    pendingClosings: 0,
  });
  const [loanStatusData, setLoanStatusData] = useState<LoanStatusCount[]>([]);
  const [listingStatusData, setListingStatusData] = useState<ListingStatusCount[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchDashboardData() {
      try {
        const [propertiesRes, listingsRes, loansRes, closingsRes] = await Promise.allSettled([
          api.get('/api/properties', { params: { size: 1 } }),
          api.get('/api/listings', { params: { size: 1 } }),
          api.get('/api/loans', { params: { size: 1 } }),
          api.get('/api/closings', { params: { size: 1 } }),
        ]);

        const totalProperties =
          propertiesRes.status === 'fulfilled'
            ? propertiesRes.value.data.totalElements ?? (Array.isArray(propertiesRes.value.data) ? propertiesRes.value.data.length : 0)
            : 0;
        const activeListings =
          listingsRes.status === 'fulfilled'
            ? listingsRes.value.data.totalElements ?? (Array.isArray(listingsRes.value.data) ? listingsRes.value.data.length : 0)
            : 0;
        const loansInPipeline =
          loansRes.status === 'fulfilled'
            ? loansRes.value.data.totalElements ?? (Array.isArray(loansRes.value.data) ? loansRes.value.data.length : 0)
            : 0;
        const pendingClosings =
          closingsRes.status === 'fulfilled'
            ? closingsRes.value.data.totalElements ?? (Array.isArray(closingsRes.value.data) ? closingsRes.value.data.length : 0)
            : 0;

        setStats({ totalProperties, activeListings, loansInPipeline, pendingClosings });

        // Fetch loan status breakdown
        const loanStatuses = ['STARTED', 'SUBMITTED', 'PROCESSING', 'UNDERWRITING', 'APPROVED', 'CLOSING', 'FUNDED'];
        const loanCounts: LoanStatusCount[] = [];
        for (const status of loanStatuses) {
          try {
            const res = await api.get(`/api/loans/status/${status}`);
            const count = Array.isArray(res.data)
              ? res.data.length
              : res.data.totalElements ?? 0;
            if (count > 0) {
              loanCounts.push({ status, count });
            }
          } catch {
            // Status might not exist, skip
          }
        }
        setLoanStatusData(loanCounts);

        // Fetch listing status breakdown
        const listingStatuses = ['ACTIVE', 'PENDING', 'SOLD', 'EXPIRED', 'WITHDRAWN', 'COMING_SOON'];
        const listingCounts: ListingStatusCount[] = [];
        for (const status of listingStatuses) {
          try {
            const res = await api.get(`/api/listings/status/${status}`);
            const count = Array.isArray(res.data)
              ? res.data.length
              : res.data.totalElements ?? 0;
            if (count > 0) {
              listingCounts.push({ status, count });
            }
          } catch {
            // Status might not exist, skip
          }
        }
        setListingStatusData(listingCounts);
      } catch {
        // Dashboard is best-effort
      } finally {
        setLoading(false);
      }
    }

    fetchDashboardData();
  }, []);

  if (loading) {
    return (
      <div>
        <Header title="Dashboard" subtitle="Overview of your real estate and mortgage operations" />
        <div className="p-6">
          <LoadingSpinner message="Loading dashboard..." />
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header title="Dashboard" subtitle="Overview of your real estate and mortgage operations" />
      <div className="p-6">
        {/* Stats Grid */}
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-4">
          <StatsCard
            title="Total Properties"
            value={stats.totalProperties}
            icon={HiOfficeBuilding}
            iconColor="text-blue-600"
            iconBg="bg-blue-50"
          />
          <StatsCard
            title="Active Listings"
            value={stats.activeListings}
            icon={HiClipboardList}
            iconColor="text-green-600"
            iconBg="bg-green-50"
          />
          <StatsCard
            title="Loans in Pipeline"
            value={stats.loansInPipeline}
            icon={HiCurrencyDollar}
            iconColor="text-purple-600"
            iconBg="bg-purple-50"
          />
          <StatsCard
            title="Pending Closings"
            value={stats.pendingClosings}
            icon={HiDocumentText}
            iconColor="text-orange-600"
            iconBg="bg-orange-50"
          />
        </div>

        {/* Charts */}
        <div className="mt-8 grid grid-cols-1 gap-6 lg:grid-cols-2">
          {/* Loan Pipeline by Status */}
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">Loan Pipeline by Status</h3>
            {loanStatusData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <BarChart data={loanStatusData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis
                    dataKey="status"
                    tick={{ fontSize: 11 }}
                    angle={-30}
                    textAnchor="end"
                    height={60}
                  />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Bar dataKey="count" fill="#3b82f6" radius={[4, 4, 0, 0]}>
                    {loanStatusData.map((_, index) => (
                      <Cell key={`cell-${index}`} fill={LOAN_STATUS_COLORS[index % LOAN_STATUS_COLORS.length]} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-[300px] items-center justify-center text-sm text-gray-500">
                No loan data available. Start the backend API to see loan pipeline.
              </div>
            )}
          </div>

          {/* Listings by Status */}
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">Listings by Status</h3>
            {listingStatusData.length > 0 ? (
              <ResponsiveContainer width="100%" height={300}>
                <PieChart>
                  <Pie
                    data={listingStatusData}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    label={({ payload }: { payload?: ListingStatusCount }) => payload ? `${payload.status}: ${payload.count}` : ''}
                    outerRadius={100}
                    fill="#8884d8"
                    dataKey="count"
                  >
                    {listingStatusData.map((_, index) => (
                      <Cell
                        key={`cell-${index}`}
                        fill={LISTING_STATUS_COLORS[index % LISTING_STATUS_COLORS.length]}
                      />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex h-[300px] items-center justify-center text-sm text-gray-500">
                No listing data available. Start the backend API to see listing breakdown.
              </div>
            )}
          </div>
        </div>

        {/* Quick Info */}
        <div className="mt-8 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <h3 className="mb-4 text-lg font-semibold text-gray-900">Getting Started</h3>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <div className="rounded-lg bg-blue-50 p-4">
              <h4 className="font-medium text-blue-900">Real Estate Management</h4>
              <p className="mt-1 text-sm text-blue-700">
                Browse properties, manage listings, track agents, and coordinate showings.
              </p>
            </div>
            <div className="rounded-lg bg-purple-50 p-4">
              <h4 className="font-medium text-purple-900">Mortgage Pipeline</h4>
              <p className="mt-1 text-sm text-purple-700">
                Process loan applications, manage underwriting, and track closings.
              </p>
            </div>
            <div className="rounded-lg bg-green-50 p-4">
              <h4 className="font-medium text-green-900">API Explorer</h4>
              <p className="mt-1 text-sm text-green-700">
                Test all 59 API endpoints with the built-in Postman-like explorer.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
