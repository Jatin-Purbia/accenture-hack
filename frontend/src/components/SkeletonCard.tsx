/** Matches KpiCard's shape exactly so the grid "loads in" as a recognizable
 * pattern rather than a blank screen with a spinner. */
export function SkeletonCard() {
  return (
    <div className="panel" style={{ display: "flex", flexDirection: "column", gap: 12 }}>
      <div className="skeleton" style={{ width: 34, height: 34, borderRadius: 10 }} />
      <div>
        <div className="skeleton" style={{ width: "70%", height: 14, marginBottom: 6 }} />
        <div className="skeleton" style={{ width: "45%", height: 11 }} />
      </div>
      <div className="skeleton" style={{ width: "40%", height: 26 }} />
      <div className="skeleton" style={{ width: "100%", height: 44 }} />
    </div>
  );
}
