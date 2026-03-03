// ==================== Property Types ====================

export interface Property {
  id: number;
  address: string;
  city: string;
  state: string;
  zipCode: string;
  county: string;
  propertyType: PropertyType;
  yearBuilt: number;
  squareFeet: number;
  lotSize: number;
  bedrooms: number;
  bathrooms: number;
  garage: boolean;
  garageSpaces: number;
  pool: boolean;
  description: string;
  latitude: number;
  longitude: number;
  zoning: string;
  parcelNumber: string;
  createdAt: string;
  updatedAt: string;
  images?: PropertyImage[];
  taxRecords?: TaxRecord[];
}

export type PropertyType =
  | 'SINGLE_FAMILY'
  | 'CONDO'
  | 'TOWNHOUSE'
  | 'MULTI_FAMILY'
  | 'LAND'
  | 'COMMERCIAL';

export interface PropertyImage {
  id: number;
  propertyId: number;
  imageUrl: string;
  caption: string;
  isPrimary: boolean;
  displayOrder: number;
  uploadedAt: string;
}

export interface TaxRecord {
  id: number;
  propertyId: number;
  taxYear: number;
  assessedValue: number;
  taxAmount: number;
  taxRate: number;
  exemptions: string;
  paidDate: string;
  status: string;
}

// ==================== Listing Types ====================

export interface Listing {
  id: number;
  property: Property;
  agent: Agent;
  listPrice: number;
  status: ListingStatus;
  listingType: ListingType;
  mlsNumber: string;
  listDate: string;
  expirationDate: string;
  daysOnMarket: number;
  description: string;
  virtualTourUrl: string;
  createdAt: string;
  updatedAt: string;
}

export type ListingStatus =
  | 'ACTIVE'
  | 'PENDING'
  | 'SOLD'
  | 'EXPIRED'
  | 'WITHDRAWN'
  | 'COMING_SOON';

export type ListingType = 'SALE' | 'RENT' | 'LEASE' | 'AUCTION';

// ==================== Agent Types ====================

export interface Agent {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  licenseNumber: string;
  licenseState: string;
  licenseExpiration: string;
  brokerage: Brokerage;
  photoUrl: string;
  bio: string;
  specializations: string;
  yearStarted: number;
  commissionRate: number;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface Brokerage {
  id: number;
  name: string;
  address: string;
  city: string;
  state: string;
  zipCode: string;
  phone: string;
  email: string;
  licenseNumber: string;
  website: string;
  active: boolean;
}

export interface Commission {
  id: number;
  agentId: number;
  listingId: number;
  amount: number;
  rate: number;
  type: string;
  status: string;
  paidDate: string;
}

// ==================== Client Types ====================

export interface Client {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  clientType: ClientType;
  address: string;
  city: string;
  state: string;
  zipCode: string;
  dateOfBirth: string;
  ssn: string;
  annualIncome: number;
  creditScore: number;
  preApproved: boolean;
  preApprovalAmount: number;
  notes: string;
  agent: Agent;
  createdAt: string;
  updatedAt: string;
}

export type ClientType = 'BUYER' | 'SELLER' | 'BORROWER' | 'INVESTOR';

// ==================== Lead Types ====================

export interface Lead {
  id: number;
  firstName: string;
  lastName: string;
  email: string;
  phone: string;
  source: string;
  status: LeadStatus;
  agent: Agent;
  property: Property;
  notes: string;
  createdAt: string;
  updatedAt: string;
}

export type LeadStatus =
  | 'NEW'
  | 'CONTACTED'
  | 'QUALIFIED'
  | 'SHOWING_SCHEDULED'
  | 'OFFER_MADE'
  | 'CONVERTED'
  | 'LOST';

// ==================== Showing Types ====================

export interface Showing {
  id: number;
  listing: Listing;
  agent: Agent;
  client: Client;
  showingDate: string;
  startTime: string;
  endTime: string;
  status: ShowingStatus;
  feedback: string;
  rating: number;
  notes: string;
}

export type ShowingStatus =
  | 'SCHEDULED'
  | 'CONFIRMED'
  | 'COMPLETED'
  | 'CANCELLED'
  | 'NO_SHOW';

// ==================== Offer Types ====================

export interface Offer {
  id: number;
  listing: Listing;
  buyer: Client;
  agent: Agent;
  offerAmount: number;
  earnestMoney: number;
  downPayment: number;
  financingType: string;
  contingencies: string;
  closingDate: string;
  expirationDate: string;
  status: OfferStatus;
  counterOfferAmount: number;
  notes: string;
  createdAt: string;
  updatedAt: string;
}

export type OfferStatus =
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'COUNTERED'
  | 'ACCEPTED'
  | 'REJECTED'
  | 'WITHDRAWN'
  | 'EXPIRED';

// ==================== Loan Types ====================

export interface LoanApplication {
  id: number;
  borrower: Client;
  property: Property;
  loanType: LoanType;
  loanPurpose: LoanPurpose;
  loanAmount: number;
  interestRate: number;
  loanTerm: number;
  downPayment: number;
  downPaymentPercent: number;
  monthlyPayment: number;
  status: LoanStatus;
  applicationDate: string;
  estimatedClosingDate: string;
  loanOfficer: string;
  notes: string;
  createdAt: string;
  updatedAt: string;
  employmentHistory?: Employment[];
  assets?: Asset[];
  creditReport?: CreditReport;
  underwritingDecision?: UnderwritingDecision;
  appraisalOrder?: AppraisalOrder;
}

export type LoanType =
  | 'CONVENTIONAL'
  | 'FHA'
  | 'VA'
  | 'USDA'
  | 'JUMBO'
  | 'ARM'
  | 'FIXED';

export type LoanPurpose = 'PURCHASE' | 'REFINANCE' | 'CASH_OUT' | 'HOME_EQUITY';

export type LoanStatus =
  | 'STARTED'
  | 'SUBMITTED'
  | 'PROCESSING'
  | 'UNDERWRITING'
  | 'APPROVED'
  | 'CONDITIONAL_APPROVAL'
  | 'DENIED'
  | 'SUSPENDED'
  | 'CLOSING'
  | 'FUNDED'
  | 'WITHDRAWN';

// ==================== Employment Types ====================

export interface Employment {
  id: number;
  loanApplicationId: number;
  employerName: string;
  employerAddress: string;
  employerPhone: string;
  position: string;
  startDate: string;
  endDate: string;
  currentEmployer: boolean;
  monthlyIncome: number;
  employmentType: string;
  verificationStatus: string;
  verifiedDate: string;
}

// ==================== Asset Types ====================

export interface Asset {
  id: number;
  loanApplicationId: number;
  assetType: string;
  institution: string;
  accountNumber: string;
  currentBalance: number;
  verificationStatus: string;
  verifiedDate: string;
  notes: string;
}

// ==================== Credit Types ====================

export interface CreditReport {
  id: number;
  loanApplicationId: number;
  creditBureau: string;
  creditScore: number;
  reportDate: string;
  expirationDate: string;
  monthlyDebt: number;
  debtToIncomeRatio: number;
  openAccounts: number;
  delinquentAccounts: number;
  publicRecords: number;
  inquiries: number;
  status: string;
}

// ==================== Underwriting Types ====================

export interface UnderwritingDecision {
  id: number;
  loanApplicationId: number;
  underwriter: string;
  decision: UnderwritingDecisionType;
  decisionDate: string;
  conditions: string;
  notes: string;
  ltvRatio: number;
  dtiRatio: number;
  riskScore: number;
  reviewLevel: string;
}

export type UnderwritingDecisionType =
  | 'APPROVED'
  | 'APPROVED_WITH_CONDITIONS'
  | 'SUSPENDED'
  | 'DENIED'
  | 'REFERRED';

// ==================== Appraisal Types ====================

export interface AppraisalOrder {
  id: number;
  loanApplicationId: number;
  appraiser: string;
  appraiserLicense: string;
  orderDate: string;
  inspectionDate: string;
  completionDate: string;
  appraisedValue: number;
  propertyCondition: string;
  approachUsed: string;
  status: AppraisalStatus;
  notes: string;
}

export type AppraisalStatus =
  | 'ORDERED'
  | 'SCHEDULED'
  | 'INSPECTED'
  | 'COMPLETED'
  | 'UNDER_REVIEW'
  | 'ACCEPTED'
  | 'DISPUTED';

// ==================== Closing Types ====================

export interface ClosingDetail {
  id: number;
  loanApplication: LoanApplication;
  listing: Listing;
  closingDate: string;
  closingLocation: string;
  escrowCompany: string;
  escrowOfficer: string;
  escrowNumber: string;
  titleCompany: string;
  titlePolicyNumber: string;
  titleInsuranceAmount: number;
  closingCosts: number;
  prepaidItems: number;
  prorations: number;
  sellerCredits: number;
  earnestMoneyApplied: number;
  cashToClose: number;
  fundingDate: string;
  recordingDate: string;
  status: ClosingStatus;
  notes: string;
  createdAt: string;
  updatedAt: string;
  documents?: ClosingDocument[];
}

export type ClosingStatus =
  | 'SCHEDULED'
  | 'IN_PROGRESS'
  | 'DOCUMENTS_SIGNED'
  | 'FUNDED'
  | 'RECORDED'
  | 'COMPLETED'
  | 'CANCELLED';

export interface ClosingDocument {
  id: number;
  closingDetailId: number;
  documentType: string;
  documentName: string;
  status: string;
  uploadedAt: string;
  signedAt: string;
}

// ==================== Loan Payment Types ====================

export interface LoanPayment {
  id: number;
  loanApplicationId: number;
  paymentNumber: number;
  paymentDate: string;
  dueDate: string;
  principalAmount: number;
  interestAmount: number;
  escrowAmount: number;
  totalAmount: number;
  lateFee: number;
  status: string;
}

// ==================== API Response Types ====================

export interface PageResponse<T> {
  content: T[];
  totalElements: number;
  totalPages: number;
  size: number;
  number: number;
  first: boolean;
  last: boolean;
}

export interface ApiError {
  status: number;
  message: string;
  timestamp: string;
}
