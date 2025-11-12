import { useEffect, useState } from 'react';
import type { Car, Inventory, SortConfig } from './types/inventory';
import { fetchInventory, formatPrice, formatMonthly, formatMileage, formatDistance, formatRelativeTime } from './api/inventory';

function App() {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [filteredCars, setFilteredCars] = useState<Car[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ field: 'price', direction: 'asc' });
  const [selectedDealerships, setSelectedDealerships] = useState<Set<string>>(new Set());

  // Load inventory on mount
  useEffect(() => {
    loadInventory();
  }, []);

  // Apply filtering and sorting when data, sort config, or dealership filter changes
  useEffect(() => {
    if (inventory) {
      let filtered = inventory.items;

      // Apply dealership filter
      if (selectedDealerships.size > 0) {
        filtered = filtered.filter(car => selectedDealerships.has(car.dealer.name));
      }

      // Apply sorting
      const sorted = [...filtered].sort((a, b) => {
        const { field, direction } = sortConfig;
        let aVal: number, bVal: number;

        switch (field) {
          case 'price': aVal = a.price; bVal = b.price; break;
          case 'monthly': aVal = a.finance.est_monthly; bVal = b.finance.est_monthly; break;
          case 'year': aVal = a.year; bVal = b.year; break;
          case 'mileage': aVal = a.mileage; bVal = b.mileage; break;
          case 'distance': aVal = a.distance_miles; bVal = b.distance_miles; break;
          case 'trend': aVal = a.price_trend.delta; bVal = b.price_trend.delta; break;
          default: aVal = 0; bVal = 0;
        }

        return direction === 'asc' ? aVal - bVal : bVal - aVal;
      });
      setFilteredCars(sorted);
    }
  }, [inventory, sortConfig, selectedDealerships]);

  async function loadInventory() {
    try {
      setLoading(true);
      setError(null);
      const data = await fetchInventory();
      setInventory(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load inventory');
    } finally {
      setLoading(false);
    }
  }

  function handleSort(field: SortConfig['field']) {
    setSortConfig(prev => ({
      field,
      direction: prev.field === field && prev.direction === 'asc' ? 'desc' : 'asc',
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

  function getTrendClass(direction: string) {
    return `trend trend-${direction}`;
  }

  function getDealershipStats() {
    if (!inventory) return [];

    const stats = new Map<string, number>();
    inventory.items.forEach(car => {
      const name = car.dealer.name;
      stats.set(name, (stats.get(name) || 0) + 1);
    });

    return Array.from(stats.entries())
      .map(([name, count]) => ({ name, count }))
      .sort((a, b) => b.count - a.count);
  }

  function toggleDealership(dealerName: string) {
    setSelectedDealerships(prev => {
      const next = new Set(prev);
      if (next.has(dealerName)) {
        next.delete(dealerName);
      } else {
        next.add(dealerName);
      }
      return next;
    });
  }

  function clearDealershipFilter() {
    setSelectedDealerships(new Set());
  }

  if (loading) {
    return (
      <div className="loading">
        <h2>Loading inventory...</h2>
        <p className="text-muted mt-2">Fetching latest vehicle data</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="error">
        <h2>Error Loading Inventory</h2>
        <p>{error}</p>
        <button className="btn btn-primary mt-4" onClick={loadInventory}>
          Retry
        </button>
      </div>
    );
  }

  if (!inventory || inventory.items.length === 0) {
    return (
      <div className="loading">
        <h2>No Vehicles Found</h2>
        <p className="text-muted">Check back later for new inventory</p>
      </div>
    );
  }

  return (
    <>
      {/* Header */}
      <header className="header">
        <div className="container">
          <div className="header-content">
            <div>
              <h1>AutoFinder</h1>
              <div className="header-info">
                {filteredCars.length} {selectedDealerships.size > 0 ? `of ${inventory.items.length}` : ''} vehicles near {inventory.zip} ({inventory.radius_miles} mi)
                {selectedDealerships.size > 0 && (
                  <span style={{ marginLeft: '8px', color: '#007bff' }}>
                    • {selectedDealerships.size} dealer{selectedDealerships.size !== 1 ? 's' : ''} selected
                  </span>
                )}
              </div>
            </div>
            <div className="header-info">
              Last updated: {formatRelativeTime(inventory.generated_at)}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <div className="container">
        <div style={{ display: 'flex', gap: '24px' }}>
          {/* Sidebar */}
          <aside style={{
            width: '280px',
            flexShrink: 0,
            position: 'sticky',
            top: '80px',
            height: 'fit-content',
            maxHeight: 'calc(100vh - 100px)',
            overflowY: 'auto',
          }}>
            {/* Cities Section */}
            <div style={{
              background: '#f8f9fa',
              borderRadius: '8px',
              padding: '16px',
              marginBottom: '16px'
            }}>
              <h3 style={{ margin: '0 0 12px 0', fontSize: '14px', fontWeight: 600 }}>
                Search Areas
              </h3>
              <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                gap: '6px'
              }}>
                {['Gurnee', 'Waukegan', 'Libertyville', 'Vernon Hills', 'Mundelein', 'Grayslake', 'Lake Forest'].map(city => (
                  <span
                    key={city}
                    style={{
                      background: '#fff',
                      border: '1px solid #dee2e6',
                      borderRadius: '12px',
                      padding: '4px 10px',
                      fontSize: '12px',
                      color: '#495057',
                    }}
                  >
                    {city}
                  </span>
                ))}
              </div>
            </div>

            {/* Dealerships Section */}
            <div style={{
              background: '#f8f9fa',
              borderRadius: '8px',
              padding: '16px'
            }}>
              <div style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '12px'
              }}>
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600 }}>
                  Dealerships
                </h3>
                {selectedDealerships.size > 0 && (
                  <button
                    onClick={clearDealershipFilter}
                    style={{
                      background: 'none',
                      border: 'none',
                      color: '#007bff',
                      fontSize: '12px',
                      cursor: 'pointer',
                      padding: 0,
                    }}
                  >
                    Clear
                  </button>
                )}
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                {getDealershipStats().map(dealer => (
                  <label
                    key={dealer.name}
                    style={{
                      display: 'flex',
                      alignItems: 'center',
                      gap: '8px',
                      cursor: 'pointer',
                      padding: '8px',
                      borderRadius: '4px',
                      background: selectedDealerships.has(dealer.name) ? '#e7f3ff' : '#fff',
                      border: '1px solid',
                      borderColor: selectedDealerships.has(dealer.name) ? '#007bff' : '#dee2e6',
                      transition: 'all 0.2s',
                    }}
                  >
                    <input
                      type="checkbox"
                      checked={selectedDealerships.has(dealer.name)}
                      onChange={() => toggleDealership(dealer.name)}
                      style={{ cursor: 'pointer' }}
                    />
                    <span style={{
                      flex: 1,
                      fontSize: '13px',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      whiteSpace: 'nowrap',
                    }}>
                      {dealer.name}
                    </span>
                    <span style={{
                      background: selectedDealerships.has(dealer.name) ? '#007bff' : '#6c757d',
                      color: '#fff',
                      borderRadius: '10px',
                      padding: '2px 8px',
                      fontSize: '11px',
                      fontWeight: 600,
                    }}>
                      {dealer.count}
                    </span>
                  </label>
                ))}
              </div>
            </div>
          </aside>

          {/* Main Table */}
          <div style={{ flex: 1, minWidth: 0 }}>
            <div className="table-container">
          <table>
            <thead>
              <tr>
                <th>Vehicle</th>
                <th onClick={() => handleSort('year')} style={{ cursor: 'pointer' }}>
                  Year {sortConfig.field === 'year' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('mileage')} style={{ cursor: 'pointer' }}>
                  Mileage {sortConfig.field === 'mileage' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('price')} style={{ cursor: 'pointer' }}>
                  Price {sortConfig.field === 'price' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                </th>
                <th>Trend</th>
                <th onClick={() => handleSort('monthly')} style={{ cursor: 'pointer' }}>
                  Monthly {sortConfig.field === 'monthly' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                </th>
                <th onClick={() => handleSort('distance')} style={{ cursor: 'pointer' }}>
                  Distance {sortConfig.field === 'distance' && (sortConfig.direction === 'asc' ? '↑' : '↓')}
                </th>
                <th>Dealer</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredCars.map(car => (
                <tr key={car.id}>
                  <td>
                    <strong>{car.title}</strong>
                    <div className="text-muted" style={{ fontSize: '13px' }}>
                      {car.condition}
                      {car.vin && ` • VIN: ${car.vin.slice(-6)}`}
                    </div>
                  </td>
                  <td>{car.year}</td>
                  <td>{formatMileage(car.mileage)} mi</td>
                  <td><strong>{formatPrice(car.price)}</strong></td>
                  <td>
                    <span className={getTrendClass(car.price_trend.direction)}>
                      {getTrendSymbol(car.price_trend.direction)}
                      {car.price_trend.delta > 0 && ` $${car.price_trend.delta.toFixed(0)}`}
                    </span>
                  </td>
                  <td>{formatMonthly(car.finance.est_monthly)}/mo</td>
                  <td>{formatDistance(car.distance_miles)}</td>
                  <td>
                    <div style={{ fontSize: '13px' }}>
                      {car.dealer.name}
                      {car.dealer.phone && (
                        <div className="text-muted">{car.dealer.phone}</div>
                      )}
                    </div>
                  </td>
                  <td>
                    <a
                      href={car.dealer.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="btn btn-primary"
                      style={{ fontSize: '13px', padding: '6px 12px' }}
                    >
                      View
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

            {/* Stats Footer */}
            <div className="text-center text-muted mt-4" style={{ fontSize: '14px' }}>
              <p>
                Showing {filteredCars.length} vehicles •{' '}
                Avg price: {formatPrice(filteredCars.reduce((sum, c) => sum + c.price, 0) / filteredCars.length)} •{' '}
                Avg monthly: {formatMonthly(filteredCars.reduce((sum, c) => sum + c.finance.est_monthly, 0) / filteredCars.length)}
              </p>
              <p style={{ marginTop: '8px' }}>
                Finance assumes {inventory.items[0]?.finance.assumptions.apr_percent}% APR,{' '}
                {inventory.items[0]?.finance.assumptions.term_months} months,{' '}
                ${inventory.items[0]?.finance.assumptions.doc_fees} doc fees
              </p>
            </div>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
