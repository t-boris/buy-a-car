/**
 * TypeScript type definitions for AutoFinder frontend.
 *
 * These types mirror the Python Pydantic models to ensure
 * type safety when consuming data from inventory.json.
 */

export type VehicleCondition = "new" | "used" | "certified";
export type PriceTrendDirection = "up" | "down" | "flat" | "new";

export interface DealerInfo {
  name: string;
  phone: string | null;
  url: string;
}

export interface MediaInfo {
  thumbnail: string | null;
}

export interface Timestamps {
  first_seen: string;
  last_seen: string;
}

export interface FinanceAssumptions {
  apr_percent: number;
  term_months: number;
  ttl_percent_of_price: number;
  doc_fees: number;
}

export interface FinanceInfo {
  est_down: number;
  est_monthly: number;
  assumptions: FinanceAssumptions;
}

export interface PriceTrend {
  direction: PriceTrendDirection;
  delta: number;
  prev_price: number | null;
  last_change_at: string | null;
}

export interface Car {
  id: string;
  vin: string | null;
  source: string;
  title: string;
  year: number;
  make: string;
  model: string;
  trim: string | null;
  condition: VehicleCondition;
  price: number;
  mileage: number;
  distance_miles: number;
  dealer: DealerInfo;
  media: MediaInfo;
  timestamps: Timestamps;
  finance: FinanceInfo;
  price_trend: PriceTrend;
  days_to_live: number;
  expired_at: string | null;
}

export interface Inventory {
  generated_at: string;
  zip: string;
  radius_miles: number;
  items: Car[];
}

// Filter state interface
export interface FilterState {
  priceRange: [number, number];
  monthlyRange: [number, number];
  yearRange: [number, number];
  maxMileage: number;
  makes: Set<string>;
  models: Set<string>;
  conditions: Set<VehicleCondition>;
  searchQuery: string;
  showSold: boolean;
}

// Sort configuration
export type SortField = "price" | "mileage" | "year" | "monthly" | "trend";
export type SortDirection = "asc" | "desc";

export interface SortConfig {
  field: SortField;
  direction: SortDirection;
}

// Dealership from dealerships.json
export interface Dealership {
  name: string;
  website: string;
  snippet: string;
  found_at: string;
}
