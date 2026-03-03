'use client';

import { useState, useCallback } from 'react';
import { HiPlay, HiClock, HiChevronDown, HiChevronRight } from 'react-icons/hi';
import endpoints, { EndpointDefinition, getGroupedEndpoints } from '@/lib/endpoints';
import api from '@/lib/api';

const METHOD_COLORS: Record<string, string> = {
  GET: 'bg-green-100 text-green-800',
  POST: 'bg-blue-100 text-blue-800',
  PUT: 'bg-yellow-100 text-yellow-800',
  DELETE: 'bg-red-100 text-red-800',
  PATCH: 'bg-purple-100 text-purple-800',
};

interface ResponseData {
  status: number;
  statusText: string;
  data: unknown;
  headers: Record<string, string>;
  time: number;
}

export default function ApiExplorer() {
  const [selectedEndpoint, setSelectedEndpoint] = useState<EndpointDefinition>(endpoints[0]);
  const [pathParamValues, setPathParamValues] = useState<Record<string, string>>({});
  const [queryParamValues, setQueryParamValues] = useState<Record<string, string>>({});
  const [requestBody, setRequestBody] = useState<string>('');
  const [response, setResponse] = useState<ResponseData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [expandedGroups, setExpandedGroups] = useState<Record<string, boolean>>(() => {
    const groups = getGroupedEndpoints();
    const initial: Record<string, boolean> = {};
    Object.keys(groups).forEach((g) => (initial[g] = true));
    return initial;
  });

  const grouped = getGroupedEndpoints();

  const selectEndpoint = useCallback((ep: EndpointDefinition) => {
    setSelectedEndpoint(ep);
    setPathParamValues({});
    setQueryParamValues({});
    setRequestBody(ep.bodySchema ? JSON.stringify(ep.bodySchema, null, 2) : '');
    setResponse(null);
    setError(null);
  }, []);

  const toggleGroup = (group: string) => {
    setExpandedGroups((prev) => ({ ...prev, [group]: !prev[group] }));
  };

  const buildUrl = (): string => {
    let url = selectedEndpoint.path;
    // Replace path parameters
    if (selectedEndpoint.pathParams) {
      selectedEndpoint.pathParams.forEach((param) => {
        url = url.replace(`{${param.name}}`, pathParamValues[param.name] || `{${param.name}}`);
      });
    }
    // Add query parameters
    const queryParts: string[] = [];
    if (selectedEndpoint.queryParams) {
      selectedEndpoint.queryParams.forEach((param) => {
        const val = queryParamValues[param.name];
        if (val) {
          queryParts.push(`${encodeURIComponent(param.name)}=${encodeURIComponent(val)}`);
        }
      });
    }
    if (queryParts.length > 0) {
      url += '?' + queryParts.join('&');
    }
    return url;
  };

  const sendRequest = async () => {
    setLoading(true);
    setError(null);
    setResponse(null);

    const url = buildUrl();
    const startTime = performance.now();

    try {
      let body: unknown = undefined;
      if (['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method) && requestBody.trim()) {
        body = JSON.parse(requestBody);
      }

      const res = await api.request({
        method: selectedEndpoint.method,
        url,
        data: body,
      });

      const endTime = performance.now();

      setResponse({
        status: res.status,
        statusText: res.statusText,
        data: res.data,
        headers: Object.fromEntries(
          Object.entries(res.headers).filter(([, v]) => typeof v === 'string') as [string, string][]
        ),
        time: Math.round(endTime - startTime),
      });
    } catch (err: unknown) {
      const endTime = performance.now();
      if (err && typeof err === 'object' && 'response' in err) {
        const axiosErr = err as { response: { status: number; statusText: string; data: unknown; headers: Record<string, string> } };
        setResponse({
          status: axiosErr.response.status,
          statusText: axiosErr.response.statusText,
          data: axiosErr.response.data,
          headers: axiosErr.response.headers || {},
          time: Math.round(endTime - startTime),
        });
      } else {
        setError(err instanceof Error ? err.message : 'Request failed');
      }
    } finally {
      setLoading(false);
    }
  };

  const getStatusColor = (status: number) => {
    if (status >= 200 && status < 300) return 'text-green-600';
    if (status >= 400 && status < 500) return 'text-yellow-600';
    return 'text-red-600';
  };

  return (
    <div className="flex h-[calc(100vh-130px)] gap-4">
      {/* Left panel - Endpoint tree */}
      <div className="w-80 flex-shrink-0 overflow-y-auto rounded-lg border border-gray-200 bg-white">
        <div className="border-b border-gray-200 px-4 py-3">
          <h3 className="text-sm font-semibold text-gray-700">API Endpoints</h3>
          <p className="text-xs text-gray-500">{endpoints.length} endpoints</p>
        </div>
        <div className="p-2">
          {Object.entries(grouped).map(([group, eps]) => (
            <div key={group} className="mb-1">
              <button
                onClick={() => toggleGroup(group)}
                className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium text-gray-700 hover:bg-gray-100"
              >
                {expandedGroups[group] ? (
                  <HiChevronDown className="h-4 w-4" />
                ) : (
                  <HiChevronRight className="h-4 w-4" />
                )}
                {group}
                <span className="ml-auto text-xs text-gray-400">{eps.length}</span>
              </button>
              {expandedGroups[group] && (
                <div className="ml-2 space-y-0.5">
                  {eps.map((ep, idx) => (
                    <button
                      key={`${ep.method}-${ep.path}-${idx}`}
                      onClick={() => selectEndpoint(ep)}
                      className={`flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left text-xs transition-colors ${
                        selectedEndpoint === ep
                          ? 'bg-blue-50 text-blue-700'
                          : 'text-gray-600 hover:bg-gray-50'
                      }`}
                    >
                      <span
                        className={`inline-flex min-w-[42px] items-center justify-center rounded px-1.5 py-0.5 text-[10px] font-bold ${
                          METHOD_COLORS[ep.method]
                        }`}
                      >
                        {ep.method}
                      </span>
                      <span className="truncate">{ep.path.replace('/api/', '/')}</span>
                    </button>
                  ))}
                </div>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Right panel - Request/Response */}
      <div className="flex flex-1 flex-col gap-4 overflow-y-auto">
        {/* Request section */}
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="mb-4">
            <p className="text-sm font-medium text-gray-700">{selectedEndpoint.description}</p>
          </div>

          {/* URL bar */}
          <div className="flex gap-2">
            <span
              className={`flex items-center rounded-lg px-3 py-2 text-sm font-bold ${
                METHOD_COLORS[selectedEndpoint.method]
              }`}
            >
              {selectedEndpoint.method}
            </span>
            <input
              type="text"
              readOnly
              value={buildUrl()}
              className="flex-1 rounded-lg border border-gray-300 bg-gray-50 px-3 py-2 font-mono text-sm"
            />
            <button
              onClick={sendRequest}
              disabled={loading}
              className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
            >
              {loading ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
              ) : (
                <HiPlay className="h-4 w-4" />
              )}
              Send
            </button>
          </div>

          {/* Path Parameters */}
          {selectedEndpoint.pathParams && selectedEndpoint.pathParams.length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-medium text-gray-700">Path Parameters</h4>
              <div className="grid grid-cols-2 gap-2">
                {selectedEndpoint.pathParams.map((param) => (
                  <div key={param.name}>
                    <label className="text-xs text-gray-500">
                      {param.name} {param.required && <span className="text-red-500">*</span>}
                    </label>
                    <input
                      type={param.type === 'number' ? 'number' : 'text'}
                      value={pathParamValues[param.name] || ''}
                      onChange={(e) =>
                        setPathParamValues((prev) => ({
                          ...prev,
                          [param.name]: e.target.value,
                        }))
                      }
                      placeholder={param.description}
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Query Parameters */}
          {selectedEndpoint.queryParams && selectedEndpoint.queryParams.length > 0 && (
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-medium text-gray-700">Query Parameters</h4>
              <div className="grid grid-cols-2 gap-2">
                {selectedEndpoint.queryParams.map((param) => (
                  <div key={param.name}>
                    <label className="text-xs text-gray-500">
                      {param.name}
                      {param.defaultValue && (
                        <span className="text-gray-400"> (default: {param.defaultValue})</span>
                      )}
                    </label>
                    <input
                      type={param.type === 'number' ? 'number' : 'text'}
                      value={queryParamValues[param.name] || ''}
                      onChange={(e) =>
                        setQueryParamValues((prev) => ({
                          ...prev,
                          [param.name]: e.target.value,
                        }))
                      }
                      placeholder={param.description}
                      className="w-full rounded-md border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                    />
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Request Body */}
          {['POST', 'PUT', 'PATCH'].includes(selectedEndpoint.method) && (
            <div className="mt-4">
              <h4 className="mb-2 text-sm font-medium text-gray-700">Request Body (JSON)</h4>
              <textarea
                value={requestBody}
                onChange={(e) => setRequestBody(e.target.value)}
                rows={10}
                className="w-full rounded-md border border-gray-300 bg-gray-900 px-3 py-2 font-mono text-sm text-green-400 focus:border-blue-500 focus:outline-none focus:ring-1 focus:ring-blue-500"
                spellCheck={false}
              />
            </div>
          )}
        </div>

        {/* Response section */}
        {(response || error) && (
          <div className="rounded-lg border border-gray-200 bg-white p-4">
            <h4 className="mb-2 text-sm font-medium text-gray-700">Response</h4>

            {error && (
              <div className="rounded-md bg-red-50 p-3 text-sm text-red-700">{error}</div>
            )}

            {response && (
              <>
                <div className="mb-3 flex items-center gap-4">
                  <span className={`text-sm font-bold ${getStatusColor(response.status)}`}>
                    {response.status} {response.statusText}
                  </span>
                  <span className="flex items-center gap-1 text-xs text-gray-500">
                    <HiClock className="h-3 w-3" />
                    {response.time}ms
                  </span>
                </div>
                <div className="max-h-96 overflow-auto rounded-md bg-gray-900 p-4">
                  <pre className="font-mono text-xs text-green-400 whitespace-pre-wrap">
                    {JSON.stringify(response.data, null, 2)}
                  </pre>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
