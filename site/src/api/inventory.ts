/**
 * API module for fetching inventory data.
 *
 * Loads data from the static inventory.json file generated
 * by the backend fetcher script.
 */

import type { Inventory } from '../types/inventory';

/**
 * Fetch the latest vehicle inventory from data/inventory.json.
 *
 * @returns Promise resolving to Inventory data
 * @throws Error if fetch fails or data is invalid
 */
export async function fetchInventory(): Promise<Inventory> {
  try {
    // Fetch with cache bypass to ensure fresh data
    const response = await fetch('/inventory.json', {
      cache: 'no-store',
      headers: {
        'Cache-Control': 'no-cache',
      },
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    const data: Inventory = await response.json();

    // Basic validation
    if (!data.items || !Array.isArray(data.items)) {
      throw new Error('Invalid inventory data structure');
    }

    return data;
  } catch (error) {
    console.error('Failed to fetch inventory:', error);
    throw new Error(
      error instanceof Error
        ? `Failed to load inventory: ${error.message}`
        : 'Failed to load inventory'
    );
  }
}

/**
 * Format a price as currency string.
 */
export function formatPrice(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(amount);
}

/**
 * Format a monthly payment as currency string.
 */
export function formatMonthly(amount: number): string {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(amount);
}

/**
 * Format mileage with thousands separator.
 */
export function formatMileage(miles: number): string {
  return new Intl.NumberFormat('en-US').format(miles);
}

/**
 * Format distance with one decimal place.
 */
export function formatDistance(miles: number): string {
  return `${miles.toFixed(1)} mi`;
}

/**
 * Format date/time from ISO string to human-readable format.
 */
export function formatDateTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    return new Intl.DateTimeFormat('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      timeZoneName: 'short',
    }).format(date);
  } catch {
    return isoString;
  }
}

/**
 * Format relative time (e.g., "2 hours ago").
 */
export function formatRelativeTime(isoString: string): string {
  try {
    const date = new Date(isoString);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMins / 60);
    const diffDays = Math.floor(diffHours / 24);

    if (diffMins < 1) return 'just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;

    return formatDateTime(isoString);
  } catch {
    return isoString;
  }
}
