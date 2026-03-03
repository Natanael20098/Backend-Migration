'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { HiArrowLeft } from 'react-icons/hi';
import Header from '@/components/Header';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import api from '@/lib/api';
import {
  LoanApplication,
  Employment,
  Asset,
  CreditReport,
  UnderwritingDecision,
  AppraisalOrder,
  ClosingDetail,
} from '@/lib/types';
import {
  formatCurrency,
  formatCurrencyDetailed,
  formatDate,
  formatEnumValue,
  formatPercent,
} from '@/lib/utils';

type TabKey = 'application' | 'employment' | 'assets' | 'credit' | 'underwriting' | 'appraisal' | 'closing';

const TABS: { key: TabKey; label: string }[] = [
  { key: 'application', label: 'Application' },
  { key: 'employment', label: 'Employment' },
  { key: 'assets', label: 'Assets' },
  { key: 'credit', label: 'Credit' },
  { key: 'underwriting', label: 'Underwriting' },
  { key: 'appraisal', label: 'Appraisal' },
  { key: 'closing', label: 'Closing' },
];

const STATUS_FLOW = [
  'STARTED',
  'SUBMITTED',
  'PROCESSING',
  'UNDERWRITING',
  'APPROVED',
  'CLOSING',
  'FUNDED',
];

export default function LoanDetailPage() {
  const params = useParams();
  const id = params.id;

  const [loan, setLoan] = useState<LoanApplication | null>(null);
  const [employment, setEmployment] = useState<Employment[]>([]);
  const [assets, setAssets] = useState<Asset[]>([]);
  const [creditReport, setCreditReport] = useState<CreditReport | null>(null);
  const [underwriting, setUnderwriting] = useState<UnderwritingDecision | null>(null);
  const [appraisal, setAppraisal] = useState<AppraisalOrder | null>(null);
  const [closing, setClosing] = useState<ClosingDetail | null>(null);
  const [activeTab, setActiveTab] = useState<TabKey>('application');
  const [loading, setLoading] = useState(true);

  const fetchLoan = async () => {
    try {
      const [loanRes, empRes, assetRes, creditRes, uwRes, appRes] = await Promise.allSettled([
        api.get(`/api/loans/${id}`),
        api.get(`/api/loans/${id}/employment`),
        api.get(`/api/loans/${id}/assets`),
        api.get(`/api/loans/${id}/credit-report`),
        api.get(`/api/loans/${id}/underwriting`),
        api.get(`/api/loans/${id}/appraisal`),
      ]);

      if (loanRes.status === 'fulfilled') setLoan(loanRes.value.data);
      if (empRes.status === 'fulfilled') {
        setEmployment(Array.isArray(empRes.value.data) ? empRes.value.data : []);
      }
      if (assetRes.status === 'fulfilled') {
        setAssets(Array.isArray(assetRes.value.data) ? assetRes.value.data : []);
      }
      if (creditRes.status === 'fulfilled') setCreditReport(creditRes.value.data);
      if (uwRes.status === 'fulfilled') setUnderwriting(uwRes.value.data);
      if (appRes.status === 'fulfilled') setAppraisal(appRes.value.data);

      // Try to fetch closing info
      try {
        const closingsRes = await api.get('/api/closings', { params: { size: 100 } });
        const allClosings = closingsRes.data.content || closingsRes.data || [];
        const loanClosing = allClosings.find(
          (c: ClosingDetail) => c.loanApplication?.id === Number(id)
        );
        if (loanClosing) setClosing(loanClosing);
      } catch {
        // No closing info
      }
    } catch {
      // Loan fetch failed
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (id) fetchLoan();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const handleStatusChange = async (newStatus: string) => {
    try {
      await api.put(`/api/loans/${id}/status`, null, { params: { status: newStatus } });
      fetchLoan();
    } catch {
      alert('Failed to update loan status');
    }
  };

  if (loading) {
    return (
      <div>
        <Header title="Loan Detail" />
        <div className="p-6">
          <LoadingSpinner message="Loading loan application..." />
        </div>
      </div>
    );
  }

  if (!loan) {
    return (
      <div>
        <Header title="Loan Not Found" />
        <div className="p-6">
          <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
            <p className="text-gray-500">Loan application not found.</p>
            <Link href="/loans" className="mt-4 inline-block text-blue-600 hover:underline">
              Back to Loan Pipeline
            </Link>
          </div>
        </div>
      </div>
    );
  }

  const currentStatusIdx = STATUS_FLOW.indexOf(loan.status);

  return (
    <div>
      <Header
        title={`Loan #${loan.id}`}
        subtitle={`${formatEnumValue(loan.loanType)} - ${formatCurrency(loan.loanAmount)}`}
        actions={
          <Link
            href="/loans"
            className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <HiArrowLeft className="h-4 w-4" />
            Back
          </Link>
        }
      />
      <div className="p-6">
        {/* Status Pipeline */}
        <div className="mb-6 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-lg font-semibold text-gray-900">Status Pipeline</h3>
            <StatusBadge status={loan.status} type="loan" size="md" />
          </div>
          <div className="flex items-center gap-1">
            {STATUS_FLOW.map((status, idx) => {
              const isCurrent = loan.status === status;
              const isPast = currentStatusIdx >= 0 && idx < currentStatusIdx;
              const isDenied = loan.status === 'DENIED' || loan.status === 'WITHDRAWN';
              return (
                <div key={status} className="flex-1">
                  <div
                    className={`h-2 rounded-full ${
                      isCurrent
                        ? 'bg-blue-600'
                        : isPast
                        ? 'bg-green-500'
                        : isDenied && idx === 0
                        ? 'bg-red-500'
                        : 'bg-gray-200'
                    }`}
                  />
                  <p className={`mt-1 text-center text-[10px] ${
                    isCurrent ? 'font-bold text-blue-600' : 'text-gray-400'
                  }`}>
                    {formatEnumValue(status)}
                  </p>
                </div>
              );
            })}
          </div>
          {/* Status Change Actions */}
          <div className="mt-4 flex flex-wrap gap-2">
            {STATUS_FLOW.filter((s) => s !== loan.status).map((status) => (
              <button
                key={status}
                onClick={() => handleStatusChange(status)}
                className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50"
              >
                Move to {formatEnumValue(status)}
              </button>
            ))}
            {!['DENIED', 'WITHDRAWN'].includes(loan.status) && (
              <>
                <button
                  onClick={() => handleStatusChange('DENIED')}
                  className="rounded-md border border-red-300 px-3 py-1.5 text-xs font-medium text-red-700 hover:bg-red-50"
                >
                  Deny
                </button>
                <button
                  onClick={() => handleStatusChange('WITHDRAWN')}
                  className="rounded-md border border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-500 hover:bg-gray-50"
                >
                  Withdraw
                </button>
              </>
            )}
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6 border-b border-gray-200">
          <div className="flex gap-0">
            {TABS.map((tab) => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`border-b-2 px-4 py-2.5 text-sm font-medium transition-colors ${
                  activeTab === tab.key
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:border-gray-300 hover:text-gray-700'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>

        {/* Tab Content */}
        {activeTab === 'application' && (
          <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
            {/* Loan Details */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">Loan Details</h3>
              <div className="space-y-3">
                <InfoRow label="Loan Type" value={formatEnumValue(loan.loanType)} />
                <InfoRow label="Loan Purpose" value={formatEnumValue(loan.loanPurpose)} />
                <InfoRow label="Loan Amount" value={formatCurrency(loan.loanAmount)} />
                <InfoRow label="Interest Rate" value={`${loan.interestRate}%`} />
                <InfoRow label="Loan Term" value={`${loan.loanTerm} years`} />
                <InfoRow label="Down Payment" value={formatCurrency(loan.downPayment)} />
                <InfoRow label="Down Payment %" value={formatPercent(loan.downPaymentPercent)} />
                <InfoRow label="Monthly Payment" value={formatCurrencyDetailed(loan.monthlyPayment)} />
                <InfoRow label="Application Date" value={formatDate(loan.applicationDate)} />
                <InfoRow label="Est. Closing Date" value={formatDate(loan.estimatedClosingDate)} />
                <InfoRow label="Loan Officer" value={loan.loanOfficer || 'Unassigned'} />
              </div>
            </div>

            {/* Borrower Info */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">Borrower Information</h3>
              {loan.borrower ? (
                <div className="space-y-3">
                  <InfoRow
                    label="Name"
                    value={`${loan.borrower.firstName} ${loan.borrower.lastName}`}
                  />
                  <InfoRow label="Email" value={loan.borrower.email} />
                  <InfoRow label="Phone" value={loan.borrower.phone} />
                  <InfoRow label="Annual Income" value={formatCurrency(loan.borrower.annualIncome)} />
                  <InfoRow label="Credit Score" value={String(loan.borrower.creditScore || 'N/A')} />
                  <InfoRow
                    label="Address"
                    value={
                      loan.borrower.address
                        ? `${loan.borrower.address}, ${loan.borrower.city}, ${loan.borrower.state} ${loan.borrower.zipCode}`
                        : 'N/A'
                    }
                  />
                </div>
              ) : (
                <p className="text-sm text-gray-500">No borrower information available.</p>
              )}

              <h3 className="mb-4 mt-6 border-t border-gray-200 pt-4 text-lg font-semibold text-gray-900">
                Property
              </h3>
              {loan.property ? (
                <div className="space-y-3">
                  <InfoRow label="Address" value={loan.property.address} />
                  <InfoRow
                    label="Location"
                    value={`${loan.property.city}, ${loan.property.state} ${loan.property.zipCode}`}
                  />
                  <InfoRow label="Type" value={formatEnumValue(loan.property.propertyType)} />
                  <InfoRow label="Year Built" value={String(loan.property.yearBuilt)} />
                  <InfoRow label="Sq Ft" value={String(loan.property.squareFeet)} />
                </div>
              ) : (
                <p className="text-sm text-gray-500">No property information available.</p>
              )}
            </div>

            {loan.notes && (
              <div className="lg:col-span-2 rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="mb-2 text-lg font-semibold text-gray-900">Notes</h3>
                <p className="text-sm text-gray-700 whitespace-pre-wrap">{loan.notes}</p>
              </div>
            )}
          </div>
        )}

        {activeTab === 'employment' && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">Employment History</h3>
            {employment.length === 0 ? (
              <p className="text-sm text-gray-500">No employment records found.</p>
            ) : (
              <div className="space-y-4">
                {employment.map((emp) => (
                  <div key={emp.id} className="rounded-lg border border-gray-100 p-4">
                    <div className="flex items-center justify-between">
                      <h4 className="font-medium text-gray-900">{emp.employerName}</h4>
                      {emp.currentEmployer && (
                        <span className="rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-800">
                          Current
                        </span>
                      )}
                    </div>
                    <div className="mt-2 grid grid-cols-2 gap-2 text-sm">
                      <InfoRow label="Position" value={emp.position} />
                      <InfoRow label="Monthly Income" value={formatCurrency(emp.monthlyIncome)} />
                      <InfoRow label="Start Date" value={formatDate(emp.startDate)} />
                      <InfoRow label="End Date" value={emp.endDate ? formatDate(emp.endDate) : 'Present'} />
                      <InfoRow label="Type" value={emp.employmentType || 'N/A'} />
                      <InfoRow label="Verification" value={emp.verificationStatus || 'Pending'} />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {activeTab === 'assets' && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">Assets</h3>
            {assets.length === 0 ? (
              <p className="text-sm text-gray-500">No asset records found.</p>
            ) : (
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Type</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Institution</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Account</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Balance</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Verified</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-gray-200">
                    {assets.map((asset) => (
                      <tr key={asset.id}>
                        <td className="px-4 py-3 text-sm">{formatEnumValue(asset.assetType)}</td>
                        <td className="px-4 py-3 text-sm">{asset.institution}</td>
                        <td className="px-4 py-3 text-sm font-mono">{asset.accountNumber}</td>
                        <td className="px-4 py-3 text-sm font-medium text-green-600">
                          {formatCurrency(asset.currentBalance)}
                        </td>
                        <td className="px-4 py-3">
                          <StatusBadge status={asset.verificationStatus || 'PENDING'} />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="mt-4 border-t border-gray-200 pt-3">
                  <p className="text-sm font-medium text-gray-900">
                    Total Assets: {formatCurrency(assets.reduce((sum, a) => sum + (a.currentBalance || 0), 0))}
                  </p>
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'credit' && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">Credit Report</h3>
            {!creditReport ? (
              <p className="text-sm text-gray-500">No credit report available.</p>
            ) : (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <div className="space-y-3">
                  <InfoRow label="Credit Bureau" value={creditReport.creditBureau} />
                  <InfoRow
                    label="Credit Score"
                    value={String(creditReport.creditScore)}
                  />
                  <InfoRow label="Report Date" value={formatDate(creditReport.reportDate)} />
                  <InfoRow label="Expiration" value={formatDate(creditReport.expirationDate)} />
                  <InfoRow label="Status" value={creditReport.status || 'N/A'} />
                </div>
                <div className="space-y-3">
                  <InfoRow label="Monthly Debt" value={formatCurrency(creditReport.monthlyDebt)} />
                  <InfoRow label="DTI Ratio" value={formatPercent(creditReport.debtToIncomeRatio)} />
                  <InfoRow label="Open Accounts" value={String(creditReport.openAccounts)} />
                  <InfoRow label="Delinquent Accounts" value={String(creditReport.delinquentAccounts)} />
                  <InfoRow label="Public Records" value={String(creditReport.publicRecords)} />
                  <InfoRow label="Inquiries" value={String(creditReport.inquiries)} />
                </div>
              </div>
            )}
          </div>
        )}

        {activeTab === 'underwriting' && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">Underwriting Decision</h3>
            {!underwriting ? (
              <p className="text-sm text-gray-500">No underwriting decision available.</p>
            ) : (
              <div className="space-y-3">
                <InfoRow label="Underwriter" value={underwriting.underwriter} />
                <InfoRow label="Decision" value={formatEnumValue(underwriting.decision)} />
                <InfoRow label="Decision Date" value={formatDate(underwriting.decisionDate)} />
                <InfoRow label="LTV Ratio" value={formatPercent(underwriting.ltvRatio)} />
                <InfoRow label="DTI Ratio" value={formatPercent(underwriting.dtiRatio)} />
                <InfoRow label="Risk Score" value={String(underwriting.riskScore)} />
                <InfoRow label="Review Level" value={underwriting.reviewLevel || 'N/A'} />
                {underwriting.conditions && (
                  <div>
                    <span className="text-sm font-medium text-gray-500">Conditions:</span>
                    <p className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">{underwriting.conditions}</p>
                  </div>
                )}
                {underwriting.notes && (
                  <div>
                    <span className="text-sm font-medium text-gray-500">Notes:</span>
                    <p className="mt-1 text-sm text-gray-700 whitespace-pre-wrap">{underwriting.notes}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'appraisal' && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">Appraisal</h3>
            {!appraisal ? (
              <p className="text-sm text-gray-500">No appraisal order available.</p>
            ) : (
              <div className="space-y-3">
                <InfoRow label="Appraiser" value={appraisal.appraiser} />
                <InfoRow label="Appraiser License" value={appraisal.appraiserLicense} />
                <InfoRow label="Order Date" value={formatDate(appraisal.orderDate)} />
                <InfoRow label="Inspection Date" value={formatDate(appraisal.inspectionDate)} />
                <InfoRow label="Completion Date" value={formatDate(appraisal.completionDate)} />
                <InfoRow
                  label="Appraised Value"
                  value={formatCurrency(appraisal.appraisedValue)}
                />
                <InfoRow label="Property Condition" value={appraisal.propertyCondition || 'N/A'} />
                <InfoRow label="Approach Used" value={appraisal.approachUsed || 'N/A'} />
                <InfoRow label="Status" value={formatEnumValue(appraisal.status)} />
                {appraisal.notes && (
                  <div>
                    <span className="text-sm font-medium text-gray-500">Notes:</span>
                    <p className="mt-1 text-sm text-gray-700">{appraisal.notes}</p>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        {activeTab === 'closing' && (
          <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
            <h3 className="mb-4 text-lg font-semibold text-gray-900">Closing Details</h3>
            {!closing ? (
              <p className="text-sm text-gray-500">No closing details available.</p>
            ) : (
              <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
                <div className="space-y-3">
                  <InfoRow label="Closing Date" value={formatDate(closing.closingDate)} />
                  <InfoRow label="Location" value={closing.closingLocation} />
                  <InfoRow label="Status" value={formatEnumValue(closing.status)} />
                  <InfoRow label="Escrow Company" value={closing.escrowCompany} />
                  <InfoRow label="Escrow Officer" value={closing.escrowOfficer} />
                  <InfoRow label="Title Company" value={closing.titleCompany} />
                </div>
                <div className="space-y-3">
                  <InfoRow label="Closing Costs" value={formatCurrency(closing.closingCosts)} />
                  <InfoRow label="Prepaid Items" value={formatCurrency(closing.prepaidItems)} />
                  <InfoRow label="Prorations" value={formatCurrency(closing.prorations)} />
                  <InfoRow label="Seller Credits" value={formatCurrency(closing.sellerCredits)} />
                  <InfoRow
                    label="Earnest Money Applied"
                    value={formatCurrency(closing.earnestMoneyApplied)}
                  />
                  <InfoRow
                    label="Cash to Close"
                    value={formatCurrency(closing.cashToClose)}
                  />
                  <InfoRow label="Funding Date" value={formatDate(closing.fundingDate)} />
                  <InfoRow label="Recording Date" value={formatDate(closing.recordingDate)} />
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="text-sm text-gray-500">{label}</span>
      <span className="text-sm font-medium text-gray-900">{value || 'N/A'}</span>
    </div>
  );
}
