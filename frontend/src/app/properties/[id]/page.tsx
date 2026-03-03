'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { HiArrowLeft, HiLocationMarker } from 'react-icons/hi';
import { IoBedOutline } from 'react-icons/io5';
import { LuBath, LuRuler } from 'react-icons/lu';
import Header from '@/components/Header';
import StatusBadge from '@/components/StatusBadge';
import LoadingSpinner from '@/components/LoadingSpinner';
import api from '@/lib/api';
import { Property, PropertyImage, TaxRecord, Listing } from '@/lib/types';
import {
  formatCurrency,
  formatNumber,
  formatDate,
  getPropertyTypeDisplay,
  formatSqft,
} from '@/lib/utils';

export default function PropertyDetailPage() {
  const params = useParams();
  const id = params.id;

  const [property, setProperty] = useState<Property | null>(null);
  const [images, setImages] = useState<PropertyImage[]>([]);
  const [taxRecords, setTaxRecords] = useState<TaxRecord[]>([]);
  const [listings, setListings] = useState<Listing[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function fetchProperty() {
      try {
        const [propRes, imgRes, taxRes] = await Promise.allSettled([
          api.get(`/api/properties/${id}`),
          api.get(`/api/properties/${id}/images`),
          api.get(`/api/properties/${id}/tax-records`),
        ]);

        if (propRes.status === 'fulfilled') {
          setProperty(propRes.value.data);
        }
        if (imgRes.status === 'fulfilled') {
          setImages(Array.isArray(imgRes.value.data) ? imgRes.value.data : []);
        }
        if (taxRes.status === 'fulfilled') {
          setTaxRecords(Array.isArray(taxRes.value.data) ? taxRes.value.data : []);
        }

        // Try to find listings for this property
        try {
          const listingsRes = await api.get('/api/listings', { params: { size: 100 } });
          const allListings = listingsRes.data.content || listingsRes.data || [];
          const propertyListings = allListings.filter(
            (l: Listing) => l.property?.id === Number(id)
          );
          setListings(propertyListings);
        } catch {
          // Listings fetch is optional
        }
      } catch {
        // Property fetch failed
      } finally {
        setLoading(false);
      }
    }

    if (id) fetchProperty();
  }, [id]);

  if (loading) {
    return (
      <div>
        <Header title="Property Detail" />
        <div className="p-6">
          <LoadingSpinner message="Loading property..." />
        </div>
      </div>
    );
  }

  if (!property) {
    return (
      <div>
        <Header title="Property Not Found" />
        <div className="p-6">
          <div className="rounded-xl border border-gray-200 bg-white p-12 text-center shadow-sm">
            <p className="text-gray-500">Property not found.</p>
            <Link href="/properties" className="mt-4 inline-block text-blue-600 hover:underline">
              Back to Properties
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div>
      <Header
        title={property.address}
        subtitle={`${property.city}, ${property.state} ${property.zipCode}`}
        actions={
          <Link
            href="/properties"
            className="flex items-center gap-1 rounded-lg border border-gray-300 px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
          >
            <HiArrowLeft className="h-4 w-4" />
            Back
          </Link>
        }
      />
      <div className="p-6">
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Image gallery */}
            <div className="rounded-xl border border-gray-200 bg-white shadow-sm overflow-hidden">
              {images.length > 0 ? (
                <div className="grid grid-cols-2 gap-1">
                  {images.map((img) => (
                    <div key={img.id} className="relative h-48 bg-gray-200">
                      <div
                        className="h-full w-full bg-cover bg-center"
                        style={{ backgroundImage: `url(${img.imageUrl})` }}
                      />
                      {img.caption && (
                        <div className="absolute bottom-0 left-0 right-0 bg-black/50 px-2 py-1">
                          <p className="text-xs text-white">{img.caption}</p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex h-64 items-center justify-center bg-gray-100">
                  <div className="text-center text-gray-400">
                    <HiLocationMarker className="mx-auto h-12 w-12" />
                    <p className="mt-2 text-sm">No images available</p>
                  </div>
                </div>
              )}
            </div>

            {/* Property details */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">Property Details</h3>
              <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
                <div>
                  <p className="text-xs font-medium text-gray-500">Property Type</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">
                    {getPropertyTypeDisplay(property.propertyType)}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Year Built</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">{property.yearBuilt}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Square Feet</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">{formatSqft(property.squareFeet)}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Lot Size</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">{property.lotSize} acres</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Bedrooms</p>
                  <p className="mt-1 text-sm font-medium text-gray-900 flex items-center gap-1">
                    <IoBedOutline className="h-4 w-4" /> {property.bedrooms}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Bathrooms</p>
                  <p className="mt-1 text-sm font-medium text-gray-900 flex items-center gap-1">
                    <LuBath className="h-4 w-4" /> {property.bathrooms}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Garage</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">
                    {property.garage ? `Yes (${property.garageSpaces} spaces)` : 'No'}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Pool</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">
                    {property.pool ? 'Yes' : 'No'}
                  </p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">County</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">{property.county}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Zoning</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">{property.zoning || 'N/A'}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-gray-500">Parcel Number</p>
                  <p className="mt-1 text-sm font-medium text-gray-900">{property.parcelNumber || 'N/A'}</p>
                </div>
              </div>
              {property.description && (
                <div className="mt-4 border-t border-gray-200 pt-4">
                  <p className="text-xs font-medium text-gray-500">Description</p>
                  <p className="mt-1 text-sm text-gray-700">{property.description}</p>
                </div>
              )}
            </div>

            {/* Tax Records */}
            {taxRecords.length > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold text-gray-900">Tax Records</h3>
                <div className="overflow-x-auto">
                  <table className="min-w-full divide-y divide-gray-200">
                    <thead className="bg-gray-50">
                      <tr>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Year</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Assessed Value</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Tax Amount</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Rate</th>
                        <th className="px-4 py-2 text-left text-xs font-medium text-gray-500">Status</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-gray-200">
                      {taxRecords.map((tr) => (
                        <tr key={tr.id}>
                          <td className="px-4 py-2 text-sm">{tr.taxYear}</td>
                          <td className="px-4 py-2 text-sm">{formatCurrency(tr.assessedValue)}</td>
                          <td className="px-4 py-2 text-sm">{formatCurrency(tr.taxAmount)}</td>
                          <td className="px-4 py-2 text-sm">{tr.taxRate}%</td>
                          <td className="px-4 py-2 text-sm">
                            <StatusBadge status={tr.status || 'PENDING'} />
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </div>

          {/* Sidebar */}
          <div className="space-y-6">
            {/* Map placeholder */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">Location</h3>
              <div className="flex h-48 items-center justify-center rounded-lg bg-gray-100">
                <div className="text-center text-gray-400">
                  <HiLocationMarker className="mx-auto h-8 w-8" />
                  <p className="mt-2 text-xs">
                    {property.latitude && property.longitude
                      ? `${property.latitude}, ${property.longitude}`
                      : 'Map placeholder'}
                  </p>
                </div>
              </div>
              <div className="mt-4">
                <p className="text-sm text-gray-700">
                  {property.address}<br />
                  {property.city}, {property.state} {property.zipCode}
                </p>
              </div>
            </div>

            {/* Key Stats */}
            <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
              <h3 className="mb-4 text-lg font-semibold text-gray-900">Key Stats</h3>
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Square Feet</span>
                  <span className="text-sm font-medium">{formatNumber(property.squareFeet)}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Beds / Baths</span>
                  <span className="text-sm font-medium flex items-center gap-2">
                    <span className="flex items-center gap-1"><IoBedOutline /> {property.bedrooms}</span>
                    <span className="flex items-center gap-1"><LuBath /> {property.bathrooms}</span>
                    <span className="flex items-center gap-1"><LuRuler /> {formatNumber(property.squareFeet)}</span>
                  </span>
                </div>
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-500">Year Built</span>
                  <span className="text-sm font-medium">{property.yearBuilt}</span>
                </div>
              </div>
            </div>

            {/* Related Listings */}
            {listings.length > 0 && (
              <div className="rounded-xl border border-gray-200 bg-white p-6 shadow-sm">
                <h3 className="mb-4 text-lg font-semibold text-gray-900">Listings</h3>
                <div className="space-y-3">
                  {listings.map((listing) => (
                    <div
                      key={listing.id}
                      className="rounded-lg border border-gray-100 p-3"
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">
                          {formatCurrency(listing.listPrice)}
                        </span>
                        <StatusBadge status={listing.status} type="listing" />
                      </div>
                      <p className="mt-1 text-xs text-gray-500">
                        MLS: {listing.mlsNumber || 'N/A'} | Listed: {formatDate(listing.listDate)}
                      </p>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
