import { useEffect, useState } from 'react';
import type { Car, Inventory, SortConfig } from './types/inventory';
import { fetchInventory, formatPrice, formatMonthly, formatMileage, formatDistance, formatRelativeTime } from './api/inventory';

function App() {
  const [inventory, setInventory] = useState<Inventory | null>(null);
  const [filteredCars, setFilteredCars] = useState<Car[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [sortConfig, setSortConfig] = useState<SortConfig>({ field: 'price', direction: 'asc' });

  // Load inventory on mount
  useEffect(() => {
    loadInventory();
  }, []);

  // Apply sorting when data or sort config changes
  useEffect(() => {
    if (inventory) {
      const sorted = [...inventory.items].sort((a, b) => {
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
  }, [inventory, sortConfig]);

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
                {inventory.items.length} vehicles near {inventory.zip} ({inventory.radius_miles} mi)
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
    </>
  );
}

export default App;
