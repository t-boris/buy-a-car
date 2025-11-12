import { useEffect, useState } from 'react';
import type { Car, Inventory, SortConfig } from './types/inventory';
import { fetchInventory, fetchDealerships, formatPrice, formatMonthly, formatMileage } from './api/inventory';
import { LoadingState } from './components/LoadingState';

// Extended dealership info combining data from both sources
interface DealershipInfo {
  name: string;
  website: string;
  snippet?: string;
  found_at?: string;
  vehicleCount: number;
  phone: string | null;
  inventoryUrl: string | null;
}

// Filter state
interface Filters {
  makes: Set<string>;
  priceRange: [number, number];
  yearRange: [number, number];
  maxMileage: number;
}

function App() {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [dealershipInfos, setDealershipInfos] = useState<DealershipInfo[]>([]);
  const [filteredCars, setFilteredCars] = useState<Car[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ field: 'price', direction: 'asc' });
  const [selectedDealerships, setSelectedDealerships] = useState<Set<string>>(new Set());
  const [view, setView] = useState<'cars' | 'dealers'>('cars');
  const [aiQuery, setAiQuery] = useState('');
  const [aiLoading, setAiLoading] = useState(false);
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>({
    makes: new Set(),
    priceRange: [0, 100000],
    yearRange: [2000, 2025],
    maxMileage: 200000
  });

  const [availableMakes, setAvailableMakes] = useState<string[]>([]);

  // Load inventory and dealerships on mount
  useEffect(() => {
    loadData();
  }, []);

  // Apply filtering and sorting when data, sort config, or filters change
  useEffect(() => {
    if (inventory) {
      let filtered = inventory.items;

      // Filter out aggregators and mock dealers
      const aggregators = ['autotrader.com', 'cars.com', 'carfax.com', 'cargurus.com', 'edmunds.com', 'truecar.com', 'kbb.com'];
      const mockKeywords = ['mock', 'test', 'example', 'sample'];

      filtered = filtered.filter(car => {
        const dealerName = car.dealer.name.toLowerCase();
        const dealerUrl = (car.dealer.url || '').toLowerCase();

        // Skip if it's an aggregator
        if (aggregators.some(agg => dealerUrl.includes(agg))) {
          return false;
        }

        // Skip if it's a mock/test dealer
        if (mockKeywords.some(keyword => dealerName.includes(keyword))) {
          return false;
        }

        return true;
      });

      // Apply dealership filter
      if (selectedDealerships.size > 0) {
        filtered = filtered.filter(car => selectedDealerships.has(car.dealer.name));
      }

      // Apply make filter
      if (filters.makes.size > 0) {
        filtered = filtered.filter(car => filters.makes.has(car.make));
      }

      // Apply price range
      filtered = filtered.filter(car =>
        car.price >= filters.priceRange[0] && car.price <= filters.priceRange[1]
      );

      // Apply year range
      filtered = filtered.filter(car =>
        car.year >= filters.yearRange[0] && car.year <= filters.yearRange[1]
      );

      // Apply mileage filter
      filtered = filtered.filter(car => car.mileage <= filters.maxMileage);

      // Apply sorting
      const sorted = [...filtered].sort((a, b) => {
        const { field, direction } = sortConfig;
        let aVal: number, bVal: number;

        switch (field) {
          case 'price': aVal = a.price; bVal = b.price; break;
          case 'monthly': aVal = a.finance.est_monthly; bVal = b.finance.est_monthly; break;
          case 'year': aVal = a.year; bVal = b.year; break;
          case 'mileage': aVal = a.mileage; bVal = b.mileage; break;
          case 'trend': aVal = a.price_trend.delta; bVal = b.price_trend.delta; break;
          default: aVal = 0; bVal = 0;
        }

        return direction === 'asc' ? aVal - bVal : bVal - aVal;
      });
      setFilteredCars(sorted);
    }
  }, [inventory, sortConfig, selectedDealerships, filters]);

  async function loadData() {
    try {
      setLoading(true);
      setError(null);
      const [inventoryData, dealershipsData] = await Promise.all([
        fetchInventory(),
        fetchDealerships()
      ]);
      setInventory(inventoryData);

      // Get unique makes
      const makes = new Set(inventoryData.items.map(car => car.make));
      setAvailableMakes(Array.from(makes).sort());

      // Combine dealership data with inventory stats
      const dealershipMap = new Map<string, DealershipInfo>();

      // Aggregator domains and keywords to filter out
      const aggregators = ['autotrader.com', 'cars.com', 'carfax.com', 'cargurus.com', 'edmunds.com', 'truecar.com', 'kbb.com'];
      const mockKeywords = ['mock', 'test', 'example', 'sample'];

      function isAggregatorOrMock(name: string, url: string): boolean {
        const nameLower = name.toLowerCase();
        const urlLower = url.toLowerCase();

        // Check if it's an aggregator
        if (aggregators.some(agg => urlLower.includes(agg))) {
          return true;
        }

        // Check if it's a mock/test dealer
        if (mockKeywords.some(keyword => nameLower.includes(keyword))) {
          return true;
        }

        return false;
      }

      // First, add all dealerships from dealerships.json (excluding aggregators and mocks)
      dealershipsData.forEach(dealer => {
        // Skip aggregators and mocks
        if (isAggregatorOrMock(dealer.name, dealer.website)) {
          return;
        }

        dealershipMap.set(dealer.name, {
          ...dealer,
          vehicleCount: 0,
          phone: null,
          inventoryUrl: null
        });
      });

      // Then, update with vehicle counts and contact info from inventory
      inventoryData.items.forEach(car => {
        const dealerName = car.dealer.name;
        const dealerUrl = car.dealer.url || '';

        // Skip aggregators and mocks
        if (isAggregatorOrMock(dealerName, dealerUrl)) {
          return;
        }

        const existing = dealershipMap.get(dealerName);

        if (existing) {
          existing.vehicleCount++;
          if (!existing.phone && car.dealer.phone) {
            existing.phone = car.dealer.phone;
          }
          if (!existing.inventoryUrl && car.dealer.url) {
            existing.inventoryUrl = car.dealer.url;
          }
        } else {
          dealershipMap.set(dealerName, {
            name: dealerName,
            website: dealerUrl,
            vehicleCount: 1,
            phone: car.dealer.phone || null,
            inventoryUrl: dealerUrl
          });
        }
      });

      const sorted = Array.from(dealershipMap.values()).sort((a, b) => {
        if (a.vehicleCount !== b.vehicleCount) {
          return b.vehicleCount - a.vehicleCount;
        }
        return a.name.localeCompare(b.name);
      });

      setDealershipInfos(sorted);
    } catch (err: any) {
      setError(`Failed to load inventory: ${err.message}`);
    } finally {
      setLoading(false);
    }
  }

  function handleSort(field: SortConfig['field']) {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc'
    }));
  }

  function getTrendSymbol(direction: string) {
    switch (direction) {
      case 'down': return '▼';
      case 'up': return '▲';
      case 'new': return '●';
      default: return '–';
    }
  }

  function getTrendColor(direction: string) {
    switch (direction) {
      case 'down': return 'text-green-400';
      case 'up': return 'text-red-400';
      case 'new': return 'text-blue-400';
      default: return 'text-slate-400';
    }
  }

  function toggleMake(make: string) {
    setFilters(prev => {
      const next = new Set(prev.makes);
      if (next.has(make)) {
        next.delete(make);
      } else {
        next.add(make);
      }
      return { ...prev, makes: next };
    });
  }

  function clearFilters() {
    setFilters({
      makes: new Set(),
      priceRange: [0, 100000],
      yearRange: [2000, 2025],
      maxMileage: 200000
    });
    setSelectedDealerships(new Set());
  }

  async function handleAISearch() {
    if (!aiQuery.trim() || !inventory) return;

    setAiLoading(true);
    try {
      const apiKey = (import.meta as any).env?.VITE_GEMINI_API_KEY || '';

      if (!apiKey || apiKey === 'your-gemini-api-key-here') {
        alert('Please set VITE_GEMINI_API_KEY in .env file');
        setAiLoading(false);
        return;
      }

      console.log('🤖 AI Filter query:', aiQuery);
      console.log('📊 Total cars available:', inventory.items.length);

      const response = await fetch('https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-pro:generateContent?key=' + apiKey, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          contents: [{
            parts: [{
              text: `You are a car search assistant. Analyze the user's query and return matching car IDs with an explanation.

User query: "${aiQuery}"

Available cars (JSON):
${JSON.stringify(inventory.items.map(car => ({
  id: car.id,
  title: car.title,
  make: car.make,
  model: car.model,
  year: car.year,
  price: car.price,
  mileage: car.mileage,
  condition: car.condition
})))}

IMPORTANT: The user may write in Russian or English. Understand their intent.
Common Russian terms:
- "дешевая" or "недорогая" = cheap, affordable (look for lower prices)
- "надежная" = reliable (look for brands like Toyota, Honda, Mazda, Lexus)
- "дочка" = daughter (look for safe, reliable, affordable cars)

Return ONLY a valid JSON object in this exact format:
{
  "ids": ["id1", "id2"],
  "explanation": "I selected these cars because they are affordable and reliable. Toyota and Honda are known for their dependability, making them perfect for a young driver."
}

The explanation should be 1-2 sentences explaining WHY these cars match the user's criteria. Write in the same language as the user's query.
If no cars match, return: {"ids": [], "explanation": "No cars match your criteria."}`
            }]
          }]
        })
      });

      if (!response.ok) {
        const errorData = await response.json();
        console.error('❌ API Error:', errorData);
        alert(`Gemini API error: ${errorData.error?.message || 'Unknown error'}`);
        setAiLoading(false);
        return;
      }

      const data = await response.json();
      console.log('📥 Gemini response:', data);

      const resultText = data.candidates?.[0]?.content?.parts?.[0]?.text || '{"ids": [], "explanation": "No response"}';
      console.log('📝 Extracted text:', resultText);

      // Remove markdown code blocks and parse
      const cleanText = resultText.replace(/```json\n?|\n?```/g, '').trim();
      const result = JSON.parse(cleanText);

      console.log('🎯 Parsed result:', result);

      if (!result.ids || !Array.isArray(result.ids)) {
        console.error('❌ Invalid format:', result);
        alert('AI returned invalid format. Please try again.');
        setAiLoading(false);
        return;
      }

      const matched = inventory.items.filter(car => result.ids.includes(car.id));
      console.log('✅ Filtered cars:', matched.length);
      console.log('💬 AI Explanation:', result.explanation);

      setFilteredCars(matched);
      setAiExplanation(result.explanation || null);

      if (matched.length === 0) {
        setAiExplanation(result.explanation || 'No cars match your criteria.');
      }
    } catch (err: any) {
      console.error('❌ AI search failed:', err);
      alert(`AI search failed: ${err.message}`);
    } finally {
      setAiLoading(false);
    }
  }

  if (loading) {
    return <LoadingState />;
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="card max-w-md w-full p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gradient-to-br from-red-400 to-pink-500 flex items-center justify-center">
            <span className="text-2xl text-white">✗</span>
          </div>
          <h2 className="text-2xl font-bold text-slate-200 mb-2">Error Loading Inventory</h2>
          <p className="text-slate-400 mb-6">{error}</p>
          <button
            onClick={loadData}
            className="px-6 py-3 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white font-semibold rounded-lg transition-all duration-300"
          >
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!inventory || inventory.items.length === 0) {
    return (
      <div className="min-h-screen flex items-center justify-center p-8">
        <div className="card max-w-md w-full p-8 text-center">
          <h2 className="text-2xl font-bold text-slate-200 mb-2">No Vehicles Found</h2>
          <p className="text-slate-400">Check back later for new inventory</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen">
      {/* Header */}
      <header className="card sticky" style={{ top: 0, zIndex: 50, borderRadius: 0 }}>
        <div className="container mx-auto px-6 py-4">
          <div className="flex justify-between items-center">
            <div>
              <h1 className="text-3xl font-bold gradient-text">AutoFinder</h1>
              <p className="text-lg font-semibold mt-2">
                <span className="text-blue-400 text-2xl">{filteredCars.length}</span>
                <span className="text-slate-300"> vehicles</span>
                <span className="text-slate-500"> • </span>
                <span className="text-slate-400">{dealershipInfos.length} dealerships</span>
              </p>
            </div>
            <div className="flex gap-6 border-b border-slate-600">
              <button
                onClick={() => setView('cars')}
                className={`px-4 pb-3 font-medium transition relative ${
                  view === 'cars'
                    ? 'text-blue-400'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                Cars
                {view === 'cars' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-400"></div>
                )}
              </button>
              <button
                onClick={() => setView('dealers')}
                className={`px-4 pb-3 font-medium transition relative ${
                  view === 'dealers'
                    ? 'text-blue-400'
                    : 'text-slate-400 hover:text-slate-300'
                }`}
              >
                Dealers
                {view === 'dealers' && (
                  <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-blue-400"></div>
                )}
              </button>
            </div>
          </div>
        </div>
      </header>

      <div className="container mx-auto px-6 py-8">
        {view === 'cars' ? (
          <div className="flex gap-6">
            {/* Sidebar Filters */}
            <aside className="w-80 flex-shrink-0">
              <div className="sticky" style={{ top: '100px' }}>
                {/* AI Filter */}
                <div className="card p-4 mb-4">
                  <h3 className="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
                    <span>🤖</span> AI Filter
                  </h3>
                  <input
                    type="text"
                    value={aiQuery}
                    onChange={(e) => setAiQuery(e.target.value)}
                    onKeyPress={(e) => e.key === 'Enter' && handleAISearch()}
                    placeholder="e.g., reliable SUV under $15k..."
                    className="ai-input mb-2"
                    disabled={aiLoading}
                  />
                  <button
                    onClick={handleAISearch}
                    disabled={aiLoading || !aiQuery.trim()}
                    className="w-full px-4 py-2 bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {aiLoading ? 'Filtering...' : 'Filter'}
                  </button>
                  <p className="text-xs text-slate-500 mt-2">
                    Powered by Gemini AI
                  </p>
                </div>

                {/* Make Filter */}
                <div className="card p-4 mb-4">
                  <h3 className="text-sm font-semibold text-slate-200 mb-3">Make</h3>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {availableMakes.map(make => (
                      <label key={make} className="flex items-center gap-2 cursor-pointer hover:bg-slate-700/30 p-1 rounded">
                        <input
                          type="checkbox"
                          checked={filters.makes.has(make)}
                          onChange={() => toggleMake(make)}
                          className="rounded"
                        />
                        <span className="text-sm text-slate-300">{make}</span>
                      </label>
                    ))}
                  </div>
                </div>

                {/* Price Range */}
                <div className="card p-4 mb-4">
                  <h3 className="text-sm font-semibold text-slate-200 mb-3">
                    Price: ${filters.priceRange[0].toLocaleString()} - ${filters.priceRange[1].toLocaleString()}
                  </h3>
                  <input
                    type="range"
                    min="0"
                    max="100000"
                    step="1000"
                    value={filters.priceRange[1]}
                    onChange={(e) => setFilters(prev => ({ ...prev, priceRange: [0, parseInt(e.target.value)] }))}
                    className="w-full"
                  />
                </div>

                {/* Year Range */}
                <div className="card p-4 mb-4">
                  <h3 className="text-sm font-semibold text-slate-200 mb-3">
                    Year: {filters.yearRange[0]} - {filters.yearRange[1]}
                  </h3>
                  <div className="flex gap-2">
                    <input
                      type="number"
                      min="2000"
                      max="2025"
                      value={filters.yearRange[0]}
                      onChange={(e) => setFilters(prev => ({ ...prev, yearRange: [parseInt(e.target.value), prev.yearRange[1]] }))}
                      className="ai-input w-1/2"
                    />
                    <input
                      type="number"
                      min="2000"
                      max="2025"
                      value={filters.yearRange[1]}
                      onChange={(e) => setFilters(prev => ({ ...prev, yearRange: [prev.yearRange[0], parseInt(e.target.value)] }))}
                      className="ai-input w-1/2"
                    />
                  </div>
                </div>

                {/* Mileage */}
                <div className="card p-4 mb-4">
                  <h3 className="text-sm font-semibold text-slate-200 mb-3">
                    Max Mileage: {filters.maxMileage.toLocaleString()} mi
                  </h3>
                  <input
                    type="range"
                    min="0"
                    max="200000"
                    step="5000"
                    value={filters.maxMileage}
                    onChange={(e) => setFilters(prev => ({ ...prev, maxMileage: parseInt(e.target.value) }))}
                    className="w-full"
                  />
                </div>

                <button
                  onClick={clearFilters}
                  className="w-full px-4 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 font-medium rounded-lg transition"
                >
                  Clear All Filters
                </button>
              </div>
            </aside>

            {/* Main Table */}
            <main className="flex-1">
              {/* AI Loading Indicator */}
              {aiLoading && (
                <div className="card p-6 mb-6 flex items-center gap-4">
                  <div className="flex-shrink-0">
                    <div className="w-12 h-12 rounded-full border-4 border-purple-500/30 border-t-purple-500 animate-spin"></div>
                  </div>
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-purple-400 mb-1">AI is analyzing...</h3>
                    <p className="text-sm text-slate-400">Gemini 2.5 Pro is finding the best matches for you</p>
                  </div>
                </div>
              )}

              {/* AI Explanation */}
              {aiExplanation && !aiLoading && (
                <div className="card p-6 mb-6 bg-gradient-to-r from-purple-500/10 to-pink-500/10 border-l-4 border-purple-500">
                  <div className="flex items-start gap-3">
                    <div className="flex-shrink-0 text-2xl">🤖</div>
                    <div className="flex-1">
                      <h3 className="text-sm font-semibold text-purple-400 mb-2">Why AI selected these cars:</h3>
                      <p className="text-slate-300">{aiExplanation}</p>
                    </div>
                    <button
                      onClick={() => setAiExplanation(null)}
                      className="flex-shrink-0 text-slate-500 hover:text-slate-300 transition"
                      title="Close"
                    >
                      ✕
                    </button>
                  </div>
                </div>
              )}

              <div className="card overflow-hidden">
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-slate-700/50 border-b border-slate-600">
                      <tr>
                        <SortHeader label="Year" field="year" currentSort={sortConfig} onSort={handleSort} />
                        <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Vehicle</th>
                        <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Condition</th>
                        <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase">VIN</th>
                        <SortHeader label="Price" field="price" currentSort={sortConfig} onSort={handleSort} />
                        <SortHeader label="Monthly" field="monthly" currentSort={sortConfig} onSort={handleSort} />
                        <SortHeader label="Mileage" field="mileage" currentSort={sortConfig} onSort={handleSort} />
                        <SortHeader label="Trend" field="trend" currentSort={sortConfig} onSort={handleSort} />
                        <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase">First Seen</th>
                        <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Dealer</th>
                        <th className="px-3 py-3 text-left text-xs font-semibold text-slate-400 uppercase">Link</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-slate-700/50">
                      {filteredCars.map((car) => (
                        <tr key={car.id} className="hover:bg-slate-700/20 transition">
                          <td className="px-3 py-3 text-slate-200 font-semibold">{car.year}</td>
                          <td className="px-3 py-3">
                            <div className="font-medium text-slate-200">{car.make} {car.model}</div>
                            {car.trim && (
                              <div className="text-xs text-slate-500 mt-0.5">{car.trim}</div>
                            )}
                          </td>
                          <td className="px-3 py-3">
                            <span className={`px-2 py-1 rounded text-xs font-medium ${
                              car.condition === 'new' ? 'bg-green-500/20 text-green-300' :
                              car.condition === 'certified' ? 'bg-blue-500/20 text-blue-300' :
                              'bg-slate-500/20 text-slate-300'
                            }`}>
                              {car.condition}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-slate-400 text-xs font-mono">
                            {car.vin ? car.vin.slice(-8) : 'N/A'}
                          </td>
                          <td className="px-3 py-3">
                            <div className="font-semibold text-slate-200">{formatPrice(car.price)}</div>
                          </td>
                          <td className="px-3 py-3">
                            <div className="font-medium text-slate-300">{formatMonthly(car.finance.est_monthly)}</div>
                            <div className="text-xs text-slate-500">{formatPrice(car.finance.est_down)} down</div>
                          </td>
                          <td className="px-3 py-3 text-slate-300">{formatMileage(car.mileage)}</td>
                          <td className="px-3 py-3">
                            <span className={`font-medium ${getTrendColor(car.price_trend.direction)}`}>
                              {getTrendSymbol(car.price_trend.direction)} {formatPrice(Math.abs(car.price_trend.delta))}
                            </span>
                          </td>
                          <td className="px-3 py-3 text-slate-400 text-xs">
                            {new Date(car.timestamps.first_seen).toLocaleDateString()}
                          </td>
                          <td className="px-3 py-3">
                            <div className="text-xs text-slate-300 max-w-[150px] truncate" title={car.dealer.name}>
                              {car.dealer.name}
                            </div>
                            {car.dealer.phone && (
                              <a href={`tel:${car.dealer.phone}`} className="text-xs text-blue-400 hover:text-blue-300">
                                {car.dealer.phone}
                              </a>
                            )}
                          </td>
                          <td className="px-3 py-3">
                            <a
                              href={car.dealer.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="inline-block px-3 py-1.5 bg-gradient-to-r from-blue-500 to-indigo-600 hover:from-blue-600 hover:to-indigo-700 text-white text-xs font-semibold rounded transition-all duration-300"
                              title="Visit dealer website (listing URL not available)"
                            >
                              Dealer
                            </a>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {filteredCars.length === 0 && (
                  <div className="text-center py-12 text-slate-400">
                    No vehicles match your filters
                  </div>
                )}
              </div>

              <div className="text-center mt-6 card p-4 inline-block mx-auto">
                <span className="text-slate-400">Showing </span>
                <span className="text-blue-400 text-xl font-bold">{filteredCars.length}</span>
                <span className="text-slate-400"> of </span>
                <span className="text-slate-300 font-semibold">{inventory.items.length}</span>
                <span className="text-slate-400"> vehicles</span>
              </div>
            </main>
          </div>
        ) : (
          /* Dealer Cards View */
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {dealershipInfos.map((dealer, idx) => (
              <div key={dealer.name} className="dealer-card">
                <div className="flex items-start justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white font-bold">
                      #{idx + 1}
                    </div>
                    <div>
                      <h3 className="font-semibold text-slate-200 line-clamp-2">{dealer.name}</h3>
                      <p className="text-xs text-slate-500">{dealer.website}</p>
                    </div>
                  </div>
                </div>

                {dealer.snippet && (
                  <p className="text-sm text-slate-400 mb-3 line-clamp-2">{dealer.snippet}</p>
                )}

                <div className="space-y-2 mb-4">
                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-blue-400">🚗</span>
                    <span className="text-slate-300">{dealer.vehicleCount} vehicles</span>
                  </div>

                  {dealer.phone && (
                    <div className="flex items-center gap-2 text-sm">
                      <span className="text-green-400">📞</span>
                      <a href={`tel:${dealer.phone}`} className="text-slate-300 hover:text-blue-400 transition">
                        {dealer.phone}
                      </a>
                    </div>
                  )}

                  <div className="flex items-center gap-2 text-sm">
                    <span className="text-purple-400">🌐</span>
                    <a
                      href={`https://${dealer.website}`}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-slate-300 hover:text-blue-400 transition truncate"
                    >
                      {dealer.website}
                    </a>
                  </div>
                </div>

                <div className="flex gap-2">
                  <button
                    onClick={() => {
                      setView('cars');
                      setSelectedDealerships(new Set([dealer.name]));
                    }}
                    className="flex-1 px-3 py-2 bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium rounded transition"
                  >
                    View Inventory
                  </button>
                  {dealer.inventoryUrl && (
                    <a
                      href={dealer.inventoryUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="px-3 py-2 bg-slate-700 hover:bg-slate-600 text-slate-300 text-sm font-medium rounded transition"
                    >
                      🔗
                    </a>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Sort header component
interface SortHeaderProps {
  label: string;
  field: SortConfig['field'];
  currentSort: SortConfig;
  onSort: (field: SortConfig['field']) => void;
}

function SortHeader({ label, field, currentSort, onSort }: SortHeaderProps) {
  const isActive = currentSort.field === field;
  const arrow = isActive ? (currentSort.direction === 'asc' ? '↑' : '↓') : '';

  return (
    <th
      onClick={() => onSort(field)}
      className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase cursor-pointer hover:bg-slate-600/30 transition select-none"
    >
      {label} {arrow && <span className="text-blue-400 ml-1">{arrow}</span>}
    </th>
  );
}

export default App;
