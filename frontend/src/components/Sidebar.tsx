'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  HiHome,
  HiOfficeBuilding,
  HiClipboardList,
  HiUserGroup,
  HiUsers,
  HiCurrencyDollar,
  HiDocumentText,
  HiCode,
} from 'react-icons/hi';

const navItems = [
  { name: 'Dashboard', href: '/', icon: HiHome },
  { name: 'Properties', href: '/properties', icon: HiOfficeBuilding },
  { name: 'Listings', href: '/listings', icon: HiClipboardList },
  { name: 'Agents', href: '/agents', icon: HiUserGroup },
  { name: 'Clients', href: '/clients', icon: HiUsers },
  { name: 'Loans', href: '/loans', icon: HiCurrencyDollar },
  { name: 'Closings', href: '/closings', icon: HiDocumentText },
  { name: 'API Explorer', href: '/api-explorer', icon: HiCode },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 bg-gray-900 text-white">
      <div className="flex h-16 items-center border-b border-gray-700 px-6">
        <div className="flex items-center gap-2">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-blue-600 font-bold text-white text-sm">
            HL
          </div>
          <div>
            <h1 className="text-lg font-bold leading-tight">HomeLend Pro</h1>
            <p className="text-xs text-gray-400">Real Estate & Mortgage</p>
          </div>
        </div>
      </div>
      <nav className="mt-4 px-3">
        <ul className="space-y-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== '/' && pathname.startsWith(item.href));
            return (
              <li key={item.name}>
                <Link
                  href={item.href}
                  className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                    isActive
                      ? 'bg-blue-600 text-white'
                      : 'text-gray-300 hover:bg-gray-800 hover:text-white'
                  }`}
                >
                  <item.icon className="h-5 w-5 flex-shrink-0" />
                  {item.name}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
      <div className="absolute bottom-0 left-0 right-0 border-t border-gray-700 p-4">
        <div className="text-xs text-gray-500">
          <p>API: localhost:8080</p>
          <p className="mt-1">v1.0.0</p>
        </div>
      </div>
    </aside>
  );
}
