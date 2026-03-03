'use client';

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import { HiArrowLeft, HiArrowRight, HiCheck } from 'react-icons/hi';
import Header from '@/components/Header';
import api from '@/lib/api';

const STEPS = [
  { key: 'borrower', label: 'Borrower Info' },
  { key: 'property', label: 'Property' },
  { key: 'loan', label: 'Loan Details' },
  { key: 'employment', label: 'Employment' },
  { key: 'assets', label: 'Assets' },
];

const LOAN_TYPES = ['CONVENTIONAL', 'FHA', 'VA', 'USDA', 'JUMBO', 'ARM', 'FIXED'];
const LOAN_PURPOSES = ['PURCHASE', 'REFINANCE', 'CASH_OUT', 'HOME_EQUITY'];

export default function NewLoanPage() {
  const router = useRouter();
  const [currentStep, setCurrentStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Form state
  const [formData, setFormData] = useState({
    // Borrower
    borrowerId: '',
    // Property
    propertyId: '',
    // Loan details
    loanType: 'CONVENTIONAL',
    loanPurpose: 'PURCHASE',
    loanAmount: '',
    interestRate: '',
    loanTerm: '30',
    downPayment: '',
    // Employment
    employerName: '',
    position: '',
    monthlyIncome: '',
    startDate: '',
    currentEmployer: true,
    // Assets
    assetType: 'CHECKING',
    institution: '',
    accountNumber: '',
    currentBalance: '',
  });

  const updateField = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0:
        return !!formData.borrowerId;
      case 1:
        return !!formData.propertyId;
      case 2:
        return !!formData.loanAmount && !!formData.interestRate;
      default:
        return true;
    }
  };

  const handleSubmit = async () => {
    setSubmitting(true);
    setError(null);

    try {
      // Create the loan application
      const loanRes = await api.post('/api/loans', {
        borrowerId: Number(formData.borrowerId),
        propertyId: Number(formData.propertyId),
        loanType: formData.loanType,
        loanPurpose: formData.loanPurpose,
        loanAmount: Number(formData.loanAmount),
        interestRate: Number(formData.interestRate),
        loanTerm: Number(formData.loanTerm),
        downPayment: formData.downPayment ? Number(formData.downPayment) : 0,
      });

      const loanId = loanRes.data.id;

      // Add employment record if provided
      if (formData.employerName && formData.monthlyIncome) {
        try {
          await api.post(`/api/loans/${loanId}/employment`, {
            employerName: formData.employerName,
            position: formData.position,
            monthlyIncome: Number(formData.monthlyIncome),
            startDate: formData.startDate || undefined,
            currentEmployer: formData.currentEmployer,
          });
        } catch {
          // Employment is optional
        }
      }

      // Add asset record if provided
      if (formData.institution && formData.currentBalance) {
        try {
          await api.post(`/api/loans/${loanId}/assets`, {
            assetType: formData.assetType,
            institution: formData.institution,
            accountNumber: formData.accountNumber,
            currentBalance: Number(formData.currentBalance),
          });
        } catch {
          // Assets are optional
        }
      }

      router.push(`/loans/${loanId}`);
    } catch (err: unknown) {
      const message =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response: { data: { message?: string } } }).response?.data?.message || 'Failed to create loan application'
          : 'Failed to create loan application';
      setError(message);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div>
      <Header
        title="New Loan Application"
        subtitle="Create a new mortgage application"
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
        {/* Step Indicator */}
        <div className="mb-8">
          <div className="flex items-center justify-between">
            {STEPS.map((step, idx) => (
              <div key={step.key} className="flex flex-1 items-center">
                <div className="flex flex-col items-center">
                  <div
                    className={`flex h-10 w-10 items-center justify-center rounded-full text-sm font-medium ${
                      idx < currentStep
                        ? 'bg-green-600 text-white'
                        : idx === currentStep
                        ? 'bg-blue-600 text-white'
                        : 'bg-gray-200 text-gray-500'
                    }`}
                  >
                    {idx < currentStep ? <HiCheck className="h-5 w-5" /> : idx + 1}
                  </div>
                  <p
                    className={`mt-2 text-xs font-medium ${
                      idx === currentStep ? 'text-blue-600' : 'text-gray-500'
                    }`}
                  >
                    {step.label}
                  </p>
                </div>
                {idx < STEPS.length - 1 && (
                  <div
                    className={`mx-2 h-0.5 flex-1 ${
                      idx < currentStep ? 'bg-green-600' : 'bg-gray-200'
                    }`}
                  />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Form */}
        <div className="mx-auto max-w-2xl rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
          {error && (
            <div className="mb-4 rounded-lg bg-red-50 p-3 text-sm text-red-700">{error}</div>
          )}

          {/* Step 0: Borrower Info */}
          {currentStep === 0 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Borrower Information</h3>
              <p className="text-sm text-gray-500">
                Enter the borrower&apos;s client ID. You can find this on the Clients page.
              </p>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Borrower Client ID *
                </label>
                <input
                  type="number"
                  value={formData.borrowerId}
                  onChange={(e) => updateField('borrowerId', e.target.value)}
                  placeholder="Enter client ID (e.g., 1)"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
          )}

          {/* Step 1: Property */}
          {currentStep === 1 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Property Information</h3>
              <p className="text-sm text-gray-500">
                Enter the property ID for this loan. You can find this on the Properties page.
              </p>
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700">
                  Property ID *
                </label>
                <input
                  type="number"
                  value={formData.propertyId}
                  onChange={(e) => updateField('propertyId', e.target.value)}
                  placeholder="Enter property ID (e.g., 1)"
                  className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                />
              </div>
            </div>
          )}

          {/* Step 2: Loan Details */}
          {currentStep === 2 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Loan Details</h3>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Loan Type *</label>
                  <select
                    value={formData.loanType}
                    onChange={(e) => updateField('loanType', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  >
                    {LOAN_TYPES.map((t) => (
                      <option key={t} value={t}>
                        {t}
                      </option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Loan Purpose *
                  </label>
                  <select
                    value={formData.loanPurpose}
                    onChange={(e) => updateField('loanPurpose', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  >
                    {LOAN_PURPOSES.map((p) => (
                      <option key={p} value={p}>
                        {p}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Loan Amount ($) *
                  </label>
                  <input
                    type="number"
                    value={formData.loanAmount}
                    onChange={(e) => updateField('loanAmount', e.target.value)}
                    placeholder="360000"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Interest Rate (%) *
                  </label>
                  <input
                    type="number"
                    step="0.125"
                    value={formData.interestRate}
                    onChange={(e) => updateField('interestRate', e.target.value)}
                    placeholder="6.5"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Loan Term (years)
                  </label>
                  <select
                    value={formData.loanTerm}
                    onChange={(e) => updateField('loanTerm', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  >
                    <option value="15">15 years</option>
                    <option value="20">20 years</option>
                    <option value="30">30 years</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Down Payment ($)
                  </label>
                  <input
                    type="number"
                    value={formData.downPayment}
                    onChange={(e) => updateField('downPayment', e.target.value)}
                    placeholder="90000"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Step 3: Employment */}
          {currentStep === 3 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Employment Information</h3>
              <p className="text-sm text-gray-500">Optional: Add current employment details.</p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Employer Name
                  </label>
                  <input
                    type="text"
                    value={formData.employerName}
                    onChange={(e) => updateField('employerName', e.target.value)}
                    placeholder="Acme Corp"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Position</label>
                  <input
                    type="text"
                    value={formData.position}
                    onChange={(e) => updateField('position', e.target.value)}
                    placeholder="Software Engineer"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Monthly Income ($)
                  </label>
                  <input
                    type="number"
                    value={formData.monthlyIncome}
                    onChange={(e) => updateField('monthlyIncome', e.target.value)}
                    placeholder="8500"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Start Date</label>
                  <input
                    type="date"
                    value={formData.startDate}
                    onChange={(e) => updateField('startDate', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="currentEmployer"
                  checked={formData.currentEmployer as boolean}
                  onChange={(e) => updateField('currentEmployer', e.target.checked)}
                  className="rounded border-gray-300"
                />
                <label htmlFor="currentEmployer" className="text-sm text-gray-700">
                  This is my current employer
                </label>
              </div>
            </div>
          )}

          {/* Step 4: Assets */}
          {currentStep === 4 && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-gray-900">Assets</h3>
              <p className="text-sm text-gray-500">
                Optional: Add an asset to verify funds for closing.
              </p>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Asset Type</label>
                  <select
                    value={formData.assetType}
                    onChange={(e) => updateField('assetType', e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  >
                    <option value="CHECKING">Checking Account</option>
                    <option value="SAVINGS">Savings Account</option>
                    <option value="INVESTMENT">Investment Account</option>
                    <option value="RETIREMENT">Retirement Account</option>
                    <option value="OTHER">Other</option>
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">Institution</label>
                  <input
                    type="text"
                    value={formData.institution}
                    onChange={(e) => updateField('institution', e.target.value)}
                    placeholder="Chase Bank"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Account Number
                  </label>
                  <input
                    type="text"
                    value={formData.accountNumber}
                    onChange={(e) => updateField('accountNumber', e.target.value)}
                    placeholder="****1234"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700">
                    Current Balance ($)
                  </label>
                  <input
                    type="number"
                    value={formData.currentBalance}
                    onChange={(e) => updateField('currentBalance', e.target.value)}
                    placeholder="45000"
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none"
                  />
                </div>
              </div>
            </div>
          )}

          {/* Navigation */}
          <div className="mt-8 flex items-center justify-between border-t border-gray-200 pt-4">
            <button
              onClick={() => setCurrentStep(Math.max(0, currentStep - 1))}
              disabled={currentStep === 0}
              className="flex items-center gap-1 rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
            >
              <HiArrowLeft className="h-4 w-4" />
              Previous
            </button>
            {currentStep < STEPS.length - 1 ? (
              <button
                onClick={() => setCurrentStep(currentStep + 1)}
                disabled={!canProceed()}
                className="flex items-center gap-1 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                Next
                <HiArrowRight className="h-4 w-4" />
              </button>
            ) : (
              <button
                onClick={handleSubmit}
                disabled={submitting}
                className="flex items-center gap-1 rounded-lg bg-green-600 px-4 py-2 text-sm font-medium text-white hover:bg-green-700 disabled:opacity-50"
              >
                {submitting ? (
                  <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
                ) : (
                  <HiCheck className="h-4 w-4" />
                )}
                Submit Application
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
