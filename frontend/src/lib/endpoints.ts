export interface EndpointParam {
  name: string;
  type: 'string' | 'number' | 'boolean';
  required?: boolean;
  description?: string;
  defaultValue?: string;
}

export interface EndpointDefinition {
  group: string;
  method: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  path: string;
  description: string;
  pathParams?: EndpointParam[];
  queryParams?: EndpointParam[];
  bodySchema?: Record<string, unknown>;
}

const endpoints: EndpointDefinition[] = [
  // ==================== Properties ====================
  {
    group: 'Properties',
    method: 'GET',
    path: '/api/properties',
    description: 'List all properties (paginated)',
    queryParams: [
      { name: 'page', type: 'number', description: 'Page number (0-based)', defaultValue: '0' },
      { name: 'size', type: 'number', description: 'Page size', defaultValue: '20' },
      { name: 'sort', type: 'string', description: 'Sort field' },
    ],
  },
  {
    group: 'Properties',
    method: 'GET',
    path: '/api/properties/{id}',
    description: 'Get property by ID',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Property ID' }],
  },
  {
    group: 'Properties',
    method: 'POST',
    path: '/api/properties',
    description: 'Create a new property',
    bodySchema: {
      address: '123 Main St',
      city: 'Springfield',
      state: 'IL',
      zipCode: '62701',
      county: 'Sangamon',
      propertyType: 'SINGLE_FAMILY',
      yearBuilt: 2020,
      squareFeet: 2000,
      lotSize: 0.25,
      bedrooms: 3,
      bathrooms: 2,
      garage: true,
      garageSpaces: 2,
      pool: false,
      description: 'Beautiful home',
    },
  },
  {
    group: 'Properties',
    method: 'PUT',
    path: '/api/properties/{id}',
    description: 'Update a property',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Property ID' }],
    bodySchema: {
      address: '123 Main St',
      city: 'Springfield',
      state: 'IL',
      zipCode: '62701',
      propertyType: 'SINGLE_FAMILY',
      bedrooms: 4,
      bathrooms: 3,
    },
  },
  {
    group: 'Properties',
    method: 'DELETE',
    path: '/api/properties/{id}',
    description: 'Delete a property',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Property ID' }],
  },
  {
    group: 'Properties',
    method: 'GET',
    path: '/api/properties/search',
    description: 'Search properties by criteria',
    queryParams: [
      { name: 'city', type: 'string', description: 'City name' },
      { name: 'state', type: 'string', description: 'State code' },
      { name: 'propertyType', type: 'string', description: 'Property type' },
      { name: 'minBedrooms', type: 'number', description: 'Minimum bedrooms' },
      { name: 'maxPrice', type: 'number', description: 'Maximum price' },
      { name: 'minPrice', type: 'number', description: 'Minimum price' },
    ],
  },
  {
    group: 'Properties',
    method: 'GET',
    path: '/api/properties/{id}/images',
    description: 'Get images for a property',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Property ID' }],
  },
  {
    group: 'Properties',
    method: 'POST',
    path: '/api/properties/{id}/images',
    description: 'Add image to a property',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Property ID' }],
    bodySchema: {
      imageUrl: 'https://example.com/image.jpg',
      caption: 'Front of house',
      isPrimary: true,
      displayOrder: 1,
    },
  },
  {
    group: 'Properties',
    method: 'GET',
    path: '/api/properties/{id}/tax-records',
    description: 'Get tax records for a property',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Property ID' }],
  },

  // ==================== Listings ====================
  {
    group: 'Listings',
    method: 'GET',
    path: '/api/listings',
    description: 'List all listings (paginated)',
    queryParams: [
      { name: 'page', type: 'number', description: 'Page number', defaultValue: '0' },
      { name: 'size', type: 'number', description: 'Page size', defaultValue: '20' },
    ],
  },
  {
    group: 'Listings',
    method: 'GET',
    path: '/api/listings/{id}',
    description: 'Get listing by ID',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Listing ID' }],
  },
  {
    group: 'Listings',
    method: 'POST',
    path: '/api/listings',
    description: 'Create a new listing',
    bodySchema: {
      propertyId: 1,
      agentId: 1,
      listPrice: 450000,
      status: 'ACTIVE',
      listingType: 'SALE',
      description: 'Beautiful property for sale',
    },
  },
  {
    group: 'Listings',
    method: 'PUT',
    path: '/api/listings/{id}',
    description: 'Update a listing',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Listing ID' }],
    bodySchema: {
      listPrice: 460000,
      status: 'PENDING',
    },
  },
  {
    group: 'Listings',
    method: 'DELETE',
    path: '/api/listings/{id}',
    description: 'Delete a listing',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Listing ID' }],
  },
  {
    group: 'Listings',
    method: 'GET',
    path: '/api/listings/status/{status}',
    description: 'Get listings by status',
    pathParams: [{ name: 'status', type: 'string', required: true, description: 'Listing status (ACTIVE, PENDING, SOLD, etc.)' }],
  },
  {
    group: 'Listings',
    method: 'GET',
    path: '/api/listings/agent/{agentId}',
    description: 'Get listings by agent',
    pathParams: [{ name: 'agentId', type: 'number', required: true, description: 'Agent ID' }],
  },

  // ==================== Agents ====================
  {
    group: 'Agents',
    method: 'GET',
    path: '/api/agents',
    description: 'List all agents (paginated)',
    queryParams: [
      { name: 'page', type: 'number', description: 'Page number', defaultValue: '0' },
      { name: 'size', type: 'number', description: 'Page size', defaultValue: '20' },
    ],
  },
  {
    group: 'Agents',
    method: 'GET',
    path: '/api/agents/{id}',
    description: 'Get agent by ID',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Agent ID' }],
  },
  {
    group: 'Agents',
    method: 'POST',
    path: '/api/agents',
    description: 'Create a new agent',
    bodySchema: {
      firstName: 'John',
      lastName: 'Smith',
      email: 'john.smith@realty.com',
      phone: '555-0100',
      licenseNumber: 'RE-12345',
      licenseState: 'CA',
      brokerageId: 1,
      commissionRate: 3.0,
    },
  },
  {
    group: 'Agents',
    method: 'PUT',
    path: '/api/agents/{id}',
    description: 'Update an agent',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Agent ID' }],
    bodySchema: {
      phone: '555-0101',
      commissionRate: 3.5,
    },
  },
  {
    group: 'Agents',
    method: 'DELETE',
    path: '/api/agents/{id}',
    description: 'Delete an agent',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Agent ID' }],
  },
  {
    group: 'Agents',
    method: 'GET',
    path: '/api/agents/{id}/commissions',
    description: 'Get commission history for agent',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Agent ID' }],
  },
  {
    group: 'Agents',
    method: 'GET',
    path: '/api/agents/{id}/listings',
    description: 'Get listings for agent',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Agent ID' }],
  },

  // ==================== Brokerages ====================
  {
    group: 'Agents',
    method: 'GET',
    path: '/api/brokerages',
    description: 'List all brokerages',
  },
  {
    group: 'Agents',
    method: 'GET',
    path: '/api/brokerages/{id}',
    description: 'Get brokerage by ID',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Brokerage ID' }],
  },
  {
    group: 'Agents',
    method: 'POST',
    path: '/api/brokerages',
    description: 'Create a new brokerage',
    bodySchema: {
      name: 'Premier Realty',
      address: '456 Broker Ave',
      city: 'Los Angeles',
      state: 'CA',
      zipCode: '90001',
      phone: '555-0200',
      email: 'info@premierrealty.com',
    },
  },

  // ==================== Clients ====================
  {
    group: 'Clients',
    method: 'GET',
    path: '/api/clients',
    description: 'List all clients (paginated)',
    queryParams: [
      { name: 'page', type: 'number', description: 'Page number', defaultValue: '0' },
      { name: 'size', type: 'number', description: 'Page size', defaultValue: '20' },
    ],
  },
  {
    group: 'Clients',
    method: 'GET',
    path: '/api/clients/{id}',
    description: 'Get client by ID',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Client ID' }],
  },
  {
    group: 'Clients',
    method: 'POST',
    path: '/api/clients',
    description: 'Create a new client',
    bodySchema: {
      firstName: 'Jane',
      lastName: 'Doe',
      email: 'jane.doe@email.com',
      phone: '555-0300',
      clientType: 'BUYER',
      annualIncome: 85000,
      creditScore: 720,
    },
  },
  {
    group: 'Clients',
    method: 'PUT',
    path: '/api/clients/{id}',
    description: 'Update a client',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Client ID' }],
    bodySchema: {
      phone: '555-0301',
      annualIncome: 90000,
    },
  },
  {
    group: 'Clients',
    method: 'DELETE',
    path: '/api/clients/{id}',
    description: 'Delete a client',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Client ID' }],
  },
  {
    group: 'Clients',
    method: 'GET',
    path: '/api/clients/type/{clientType}',
    description: 'Get clients by type',
    pathParams: [{ name: 'clientType', type: 'string', required: true, description: 'Client type (BUYER, SELLER, BORROWER, INVESTOR)' }],
  },

  // ==================== Leads ====================
  {
    group: 'Clients',
    method: 'GET',
    path: '/api/leads',
    description: 'List all leads',
  },
  {
    group: 'Clients',
    method: 'POST',
    path: '/api/leads',
    description: 'Create a new lead',
    bodySchema: {
      firstName: 'Bob',
      lastName: 'Wilson',
      email: 'bob@email.com',
      phone: '555-0400',
      source: 'WEBSITE',
      agentId: 1,
    },
  },

  // ==================== Showings ====================
  {
    group: 'Clients',
    method: 'GET',
    path: '/api/showings',
    description: 'List all showings',
  },
  {
    group: 'Clients',
    method: 'POST',
    path: '/api/showings',
    description: 'Schedule a showing',
    bodySchema: {
      listingId: 1,
      agentId: 1,
      clientId: 1,
      showingDate: '2025-02-01',
      startTime: '10:00',
      endTime: '11:00',
    },
  },

  // ==================== Offers ====================
  {
    group: 'Clients',
    method: 'GET',
    path: '/api/offers',
    description: 'List all offers',
  },
  {
    group: 'Clients',
    method: 'POST',
    path: '/api/offers',
    description: 'Submit an offer',
    bodySchema: {
      listingId: 1,
      buyerId: 1,
      agentId: 1,
      offerAmount: 440000,
      earnestMoney: 10000,
      downPayment: 88000,
      financingType: 'CONVENTIONAL',
    },
  },
  {
    group: 'Clients',
    method: 'PUT',
    path: '/api/offers/{id}/status',
    description: 'Update offer status',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Offer ID' }],
    queryParams: [{ name: 'status', type: 'string', required: true, description: 'New status' }],
  },

  // ==================== Loans ====================
  {
    group: 'Loans',
    method: 'GET',
    path: '/api/loans',
    description: 'List all loan applications (paginated)',
    queryParams: [
      { name: 'page', type: 'number', description: 'Page number', defaultValue: '0' },
      { name: 'size', type: 'number', description: 'Page size', defaultValue: '20' },
    ],
  },
  {
    group: 'Loans',
    method: 'GET',
    path: '/api/loans/{id}',
    description: 'Get loan application by ID',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
  },
  {
    group: 'Loans',
    method: 'POST',
    path: '/api/loans',
    description: 'Create a new loan application',
    bodySchema: {
      borrowerId: 1,
      propertyId: 1,
      loanType: 'CONVENTIONAL',
      loanPurpose: 'PURCHASE',
      loanAmount: 360000,
      interestRate: 6.5,
      loanTerm: 30,
      downPayment: 90000,
    },
  },
  {
    group: 'Loans',
    method: 'PUT',
    path: '/api/loans/{id}',
    description: 'Update a loan application',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
    bodySchema: {
      loanAmount: 350000,
      interestRate: 6.25,
    },
  },
  {
    group: 'Loans',
    method: 'DELETE',
    path: '/api/loans/{id}',
    description: 'Delete a loan application',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
  },
  {
    group: 'Loans',
    method: 'PUT',
    path: '/api/loans/{id}/status',
    description: 'Update loan status',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
    queryParams: [{ name: 'status', type: 'string', required: true, description: 'New status (STARTED, SUBMITTED, PROCESSING, etc.)' }],
  },
  {
    group: 'Loans',
    method: 'GET',
    path: '/api/loans/status/{status}',
    description: 'Get loans by status',
    pathParams: [{ name: 'status', type: 'string', required: true, description: 'Loan status' }],
  },
  {
    group: 'Loans',
    method: 'GET',
    path: '/api/loans/{id}/employment',
    description: 'Get employment history for loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
  },
  {
    group: 'Loans',
    method: 'POST',
    path: '/api/loans/{id}/employment',
    description: 'Add employment record to loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
    bodySchema: {
      employerName: 'Acme Corp',
      position: 'Software Engineer',
      monthlyIncome: 8500,
      startDate: '2020-01-15',
      currentEmployer: true,
    },
  },
  {
    group: 'Loans',
    method: 'GET',
    path: '/api/loans/{id}/assets',
    description: 'Get assets for loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
  },
  {
    group: 'Loans',
    method: 'POST',
    path: '/api/loans/{id}/assets',
    description: 'Add asset to loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
    bodySchema: {
      assetType: 'CHECKING',
      institution: 'Chase Bank',
      accountNumber: '****1234',
      currentBalance: 45000,
    },
  },

  // ==================== Underwriting ====================
  {
    group: 'Underwriting',
    method: 'GET',
    path: '/api/loans/{id}/credit-report',
    description: 'Get credit report for loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
  },
  {
    group: 'Underwriting',
    method: 'POST',
    path: '/api/loans/{id}/credit-report',
    description: 'Order credit report for loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
    bodySchema: {
      creditBureau: 'EXPERIAN',
    },
  },
  {
    group: 'Underwriting',
    method: 'GET',
    path: '/api/loans/{id}/underwriting',
    description: 'Get underwriting decision for loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
  },
  {
    group: 'Underwriting',
    method: 'POST',
    path: '/api/loans/{id}/underwriting',
    description: 'Submit underwriting decision',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
    bodySchema: {
      underwriter: 'Jane Underwriter',
      decision: 'APPROVED',
      conditions: 'None',
      ltvRatio: 80,
      dtiRatio: 35,
      riskScore: 720,
    },
  },
  {
    group: 'Underwriting',
    method: 'GET',
    path: '/api/loans/{id}/appraisal',
    description: 'Get appraisal order for loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
  },
  {
    group: 'Underwriting',
    method: 'POST',
    path: '/api/loans/{id}/appraisal',
    description: 'Order appraisal for loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
    bodySchema: {
      appraiser: 'Bob Appraiser',
      appraiserLicense: 'AP-98765',
    },
  },

  // ==================== Closings ====================
  {
    group: 'Closings',
    method: 'GET',
    path: '/api/closings',
    description: 'List all closings (paginated)',
    queryParams: [
      { name: 'page', type: 'number', description: 'Page number', defaultValue: '0' },
      { name: 'size', type: 'number', description: 'Page size', defaultValue: '20' },
    ],
  },
  {
    group: 'Closings',
    method: 'GET',
    path: '/api/closings/{id}',
    description: 'Get closing by ID',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Closing ID' }],
  },
  {
    group: 'Closings',
    method: 'POST',
    path: '/api/closings',
    description: 'Create a new closing',
    bodySchema: {
      loanApplicationId: 1,
      listingId: 1,
      closingDate: '2025-03-15',
      closingLocation: '123 Title Office',
      escrowCompany: 'First Escrow',
      titleCompany: 'Fidelity Title',
      closingCosts: 8500,
    },
  },
  {
    group: 'Closings',
    method: 'PUT',
    path: '/api/closings/{id}',
    description: 'Update a closing',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Closing ID' }],
    bodySchema: {
      status: 'IN_PROGRESS',
      closingCosts: 9000,
    },
  },
  {
    group: 'Closings',
    method: 'GET',
    path: '/api/closings/{id}/documents',
    description: 'Get documents for a closing',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Closing ID' }],
  },
  {
    group: 'Closings',
    method: 'POST',
    path: '/api/closings/{id}/documents',
    description: 'Add document to a closing',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Closing ID' }],
    bodySchema: {
      documentType: 'DEED',
      documentName: 'Warranty Deed',
      status: 'PENDING',
    },
  },

  // ==================== Admin ====================
  {
    group: 'Admin',
    method: 'GET',
    path: '/api/loans/{id}/payments',
    description: 'Get payments for a loan',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
  },
  {
    group: 'Admin',
    method: 'POST',
    path: '/api/loans/{id}/payments',
    description: 'Record a loan payment',
    pathParams: [{ name: 'id', type: 'number', required: true, description: 'Loan ID' }],
    bodySchema: {
      paymentDate: '2025-02-01',
      principalAmount: 800,
      interestAmount: 1200,
      escrowAmount: 350,
      totalAmount: 2350,
    },
  },
];

export default endpoints;

/**
 * Group endpoints by their group name
 */
export function getGroupedEndpoints(): Record<string, EndpointDefinition[]> {
  return endpoints.reduce((groups, endpoint) => {
    if (!groups[endpoint.group]) {
      groups[endpoint.group] = [];
    }
    groups[endpoint.group].push(endpoint);
    return groups;
  }, {} as Record<string, EndpointDefinition[]>);
}
