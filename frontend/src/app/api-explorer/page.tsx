'use client';

import Header from '@/components/Header';
import ApiExplorer from '@/components/ApiExplorer';

export default function ApiExplorerPage() {
  return (
    <div>
      <Header
        title="API Explorer"
        subtitle="Test all 59 API endpoints — Postman-like developer tool"
      />
      <div className="p-6">
        <ApiExplorer />
      </div>
    </div>
  );
}
