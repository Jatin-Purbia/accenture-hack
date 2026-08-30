import { useEffect, useMemo, useState, type ReactNode } from "react";
import { AlertTriangle, ArrowDown, ArrowRight, ArrowUp, CheckCircle2, ChevronRight, Clock3, Minus, ScanSearch } from "lucide-react";
import { api } from "../api/client";
import { formatKpiValue } from "../lib/format";
import { kpiIcon } from "../lib/icons";
import { movementStatus, STATUS_COLOR, STATUS_LABEL, STATUS_WASH, type Status } from "../lib/status";
import type { EvidencePacket, ScenarioDef } from "../types";
import { Sparkline } from "./Sparkline";
import { StatusDot } from "./StatusDot";

interface Props {
  scenarios: ScenarioDef[];
  personaId: string;
  onSelect: (scenarioId: string) => void;
}

interface BriefingItem {
  scenario: ScenarioDef;
  evidence: EvidencePacket | null;
  status: Status | null;
}

const RANK: Record<Status, number> = { critical: 0, warning: 1, unknown: 2, good: 3 };

export function HomeView({ scenarios, personaId, onSelect }: Props) {
  const [evidenceMap, setEvidenceMap] = useState<Record<string, EvidencePacket>>({});
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();
    setEvidenceMap({});
    setIsLoading(true);

    if (scenarios.length === 0) return () => controller.abort();

    Promise.all(
      scenarios.map(async (scenario) => {
        try {
          const evidence = await api.getScenarioEvidence(scenario.id, personaId, controller.signal);
          return [scenario.id, evidence] as const;
        } catch {
          return null;
        }
      })
    ).then((results) => {
      if (controller.signal.aborted) return;
      const loaded = results.filter((result): result is readonly [string, EvidencePacket] => result !== null);
      setEvidenceMap(Object.fromEntries(loaded));
      setIsLoading(false);
    });

    return () => controller.abort();
  }, [scenarios, personaId]);

  const items = useMemo<BriefingItem[]>(
    () =>
      scenarios
        .map((scenario) => {
          const evidence = evidenceMap[scenario.id] ?? null;
          const status = evidence
            ? movementStatus({
                isMaterial: evidence.movement.is_material,
                relativeChangePct: evidence.movement.relative_change_pct,
                abstained: evidence.abstained,
              })
            : null;
          return { scenario, evidence, status };
        })
        .sort((a, b) => (a.status ? RANK[a.status] : 4) - (b.status ? RANK[b.status] : 4)),
    [scenarios, evidenceMap]
  );

  if (isLoading) return <HomeSkeleton />;

  const primary = items.find((item) => item.status === "critical") ?? items.find((item) => item.status === "warning") ?? items.find((item) => item.evidence) ?? null;
  const actionCount = items.filter((item) => item.status === "critical").length;
  const watchCount = items.filter((item) => item.status === "warning" || item.status === "unknown").length;
  const onTrackCount = items.filter((item) => item.status === "good").length;
  const generatedAt = items.find((item) => item.evidence)?.evidence?.generated_at;

  return (
    <div className="home-view fade-in">
      <section className="home-heading">
        <div>
          <div className="eyebrow">Performance briefing</div>
          <h1>Start with what matters</h1>
          <p className="secondary">Signals are ranked by business impact, with the clearest next decision first.</p>
        </div>
        {generatedAt && (
          <div className="home-updated" title={new Date(generatedAt).toLocaleString()}>
            <Clock3 size={14} /> Updated {formatUpdateTime(generatedAt)}
          </div>
        )}
      </section>

      <section className="portfolio-summary" aria-label="Portfolio summary">
        <SummaryItem icon={<AlertTriangle size={17} />} value={actionCount} label="Need action" tone="critical" />
        <SummaryItem icon={<ScanSearch size={17} />} value={watchCount} label="Watch closely" tone="warning" />
        <SummaryItem icon={<CheckCircle2 size={17} />} value={onTrackCount} label="On track" tone="good" />
      </section>

      <div className="briefing-layout">
        {primary ? <PriorityBrief item={primary} onSelect={onSelect} /> : <EmptyBrief />}
        <section className="signal-list panel" aria-labelledby="signal-list-title">
          <div className="signal-list-header">
            <div>
              <div className="eyebrow">All signals</div>
              <h2 id="signal-list-title">KPI pulse</h2>
            </div>
            <span className="signal-count">{items.length} monitored</span>
          </div>
          <div className="signal-rows">
            {items.map((item) => (
              <SignalRow key={item.scenario.id} item={item} onClick={() => onSelect(item.scenario.id)} />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

function SummaryItem({ icon, value, label, tone }: { icon: ReactNode; value: number; label: string; tone: Status }) {
  return (
    <div className="summary-item" style={{ color: STATUS_COLOR[tone] }}>
      <span className="summary-icon" style={{ background: STATUS_WASH[tone] }}>{icon}</span>
      <strong>{value}</strong>
      <span>{label}</span>
    </div>
  );
}

function PriorityBrief({ item, onSelect }: { item: BriefingItem; onSelect: (scenarioId: string) => void }) {
  const { scenario, evidence } = item;
  if (!evidence || !item.status) return <EmptyBrief />;

  const status = item.status;
  const movement = evidence.movement;
  const Icon = kpiIcon(scenario.kpi_id);
  const Direction = movement.relative_change_pct > 0.5 ? ArrowUp : movement.relative_change_pct < -0.5 ? ArrowDown : Minus;
  const hypothesis = evidence.hypotheses.find((candidate) => candidate.id === evidence.top_hypothesis_id) ?? evidence.hypotheses[0];
  const explanation = evidence.abstained
    ? evidence.abstention_reason
    : hypothesis?.drivers.slice(0, 2).map((driver) => driver.description).join(" ") || hypothesis?.summary || scenario.description;

  return (
    <section className="priority-brief panel" style={{ borderTopColor: STATUS_COLOR[status] }} aria-labelledby="priority-title">
      <div className="priority-kicker">
        <span><StatusDot status={status} pulse={status === "critical"} size={10} /> Priority signal</span>
        <span style={{ color: STATUS_COLOR[status], background: STATUS_WASH[status] }}>{STATUS_LABEL[status]}</span>
      </div>
      <div className="priority-title-row">
        <span className="icon-badge priority-icon"><Icon size={20} /></span>
        <div>
          <div className="muted priority-dimension">{movement.dimension_label}</div>
          <h2 id="priority-title">{scenario.label}</h2>
        </div>
      </div>
      <div className="priority-movement" style={{ color: STATUS_COLOR[status] }}>
        <Direction size={26} strokeWidth={2.4} />
        <strong>{Math.abs(movement.relative_change_pct).toFixed(0)}%</strong>
        <span>vs expected</span>
      </div>
      <p className="priority-explanation">{explanation}</p>
      <div className="priority-footer">
        <span><span className="muted">Current</span> {formatKpiValue(scenario.kpi_id, movement.actual_value)}</span>
        <button className="btn btn-primary" onClick={() => onSelect(scenario.id)}>
          Review story <ArrowRight size={16} />
        </button>
      </div>
    </section>
  );
}

function SignalRow({ item, onClick }: { item: BriefingItem; onClick: () => void }) {
  const Icon = kpiIcon(item.scenario.kpi_id);
  const movement = item.evidence?.movement;
  const status = item.status ?? "unknown";
  const Direction = movement && movement.relative_change_pct > 0.5 ? ArrowUp : movement && movement.relative_change_pct < -0.5 ? ArrowDown : Minus;

  return (
    <button className="signal-row" onClick={onClick}>
      <span className="icon-badge signal-icon"><Icon size={17} /></span>
      <span className="signal-name">
        <strong>{item.scenario.label}</strong>
        <span>{movement?.dimension_label ?? "Data unavailable"}</span>
      </span>
      {item.evidence && movement ? (
        <>
          <span className="signal-trend" aria-hidden="true"><Sparkline trend={item.evidence.trend} status={status} height={34} /></span>
          <span className="signal-change" style={{ color: STATUS_COLOR[status] }}>
            <Direction size={15} strokeWidth={2.5} /> {Math.abs(movement.relative_change_pct).toFixed(0)}%
          </span>
          <span className="signal-status"><StatusDot status={status} size={8} /> {STATUS_LABEL[status]}</span>
        </>
      ) : (
        <span className="signal-unavailable muted">Unavailable</span>
      )}
      <ChevronRight className="signal-chevron" size={17} />
    </button>
  );
}

function EmptyBrief() {
  return (
    <section className="priority-brief panel empty-brief">
      <ScanSearch size={28} />
      <h2>No briefing available</h2>
      <p className="muted">The signal service did not return data for this view.</p>
    </section>
  );
}

function HomeSkeleton() {
  return (
    <div className="home-view" aria-label="Loading performance briefing">
      <section className="home-heading">
        <div>
          <div className="skeleton" style={{ width: 130, height: 12, marginBottom: 10 }} />
          <div className="skeleton" style={{ width: 280, height: 30, marginBottom: 8 }} />
          <div className="skeleton" style={{ width: 390, maxWidth: "80vw", height: 15 }} />
        </div>
      </section>
      <section className="portfolio-summary">
        {[0, 1, 2].map((key) => <div key={key} className="skeleton" style={{ width: 120, height: 30 }} />)}
      </section>
      <div className="briefing-layout">
        <div className="panel home-panel-skeleton"><div className="skeleton" /></div>
        <div className="panel home-panel-skeleton"><div className="skeleton" /></div>
      </div>
    </div>
  );
}

function formatUpdateTime(value: string): string {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "recently";
  return new Intl.DateTimeFormat(undefined, { hour: "numeric", minute: "2-digit" }).format(date);
}
