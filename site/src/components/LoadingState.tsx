export function LoadingState() {
  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4 animate-fade-in">
        <div className="relative w-20 h-20 mx-auto">
          <div className="absolute inset-0 rounded-full border-4 border-slate-200"></div>
          <div className="absolute inset-0 rounded-full border-4 border-t-blue-500 border-r-indigo-500 animate-spin"></div>
        </div>
        <h2 className="text-xl font-semibold gradient-text">Loading inventory...</h2>
        <p className="text-slate-500 text-sm">Fetching latest vehicle data</p>
      </div>
    </div>
  );
}

export function DealershipSkeleton() {
  return (
    <div className="card p-3 space-y-2 animate-pulse">
      <div className="flex items-start gap-2">
        <div className="skeleton w-4 h-4 rounded mt-1"></div>
        <div className="flex-1 space-y-2">
          <div className="skeleton h-4 w-3/4 rounded"></div>
          <div className="skeleton h-3 w-16 rounded-full"></div>
        </div>
      </div>
      <div className="pl-6 space-y-1">
        <div className="skeleton h-3 w-32 rounded"></div>
        <div className="skeleton h-3 w-24 rounded"></div>
      </div>
    </div>
  );
}

export function TableSkeleton() {
  return (
    <div className="card p-6 space-y-4">
      <div className="skeleton h-8 w-48 rounded"></div>
      <div className="space-y-3">
        {[...Array(5)].map((_, i) => (
          <div key={i} className="flex gap-4">
            <div className="skeleton h-12 flex-1 rounded"></div>
            <div className="skeleton h-12 w-20 rounded"></div>
            <div className="skeleton h-12 w-24 rounded"></div>
            <div className="skeleton h-12 w-28 rounded"></div>
          </div>
        ))}
      </div>
    </div>
  );
}
