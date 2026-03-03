import Link from 'next/link';
import { HiLocationMarker } from 'react-icons/hi';
import { IoBedOutline } from 'react-icons/io5';
import { LuBath, LuRuler } from 'react-icons/lu';
import { Property } from '@/lib/types';
import { formatCurrency, formatNumber, getPropertyTypeDisplay } from '@/lib/utils';

interface PropertyCardProps {
  property: Property;
  listPrice?: number;
}

export default function PropertyCard({ property, listPrice }: PropertyCardProps) {
  const primaryImage = property.images?.find((img) => img.isPrimary);
  const imageUrl = primaryImage?.imageUrl || '/placeholder-property.jpg';

  return (
    <Link href={`/properties/${property.id}`}>
      <div className="group overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm transition-shadow hover:shadow-md">
        <div className="relative h-48 overflow-hidden bg-gray-200">
          <div
            className="h-full w-full bg-cover bg-center transition-transform group-hover:scale-105"
            style={{
              backgroundImage: `url(${imageUrl})`,
              backgroundColor: '#e5e7eb',
            }}
          >
            {!primaryImage && (
              <div className="flex h-full items-center justify-center text-gray-400">
                <HiLocationMarker className="h-12 w-12" />
              </div>
            )}
          </div>
          <div className="absolute left-3 top-3">
            <span className="rounded-full bg-blue-600 px-3 py-1 text-xs font-medium text-white">
              {getPropertyTypeDisplay(property.propertyType)}
            </span>
          </div>
        </div>
        <div className="p-4">
          {listPrice !== undefined && (
            <p className="text-xl font-bold text-blue-600">
              {formatCurrency(listPrice)}
            </p>
          )}
          <p className="mt-1 font-medium text-gray-900">{property.address}</p>
          <p className="text-sm text-gray-500">
            {property.city}, {property.state} {property.zipCode}
          </p>
          <div className="mt-3 flex items-center gap-4 text-sm text-gray-600">
            <span className="flex items-center gap-1">
              <IoBedOutline className="h-4 w-4" />
              {property.bedrooms} bd
            </span>
            <span className="flex items-center gap-1">
              <LuBath className="h-4 w-4" />
              {property.bathrooms} ba
            </span>
            <span className="flex items-center gap-1">
              <LuRuler className="h-4 w-4" />
              {formatNumber(property.squareFeet)} sqft
            </span>
          </div>
        </div>
      </div>
    </Link>
  );
}
