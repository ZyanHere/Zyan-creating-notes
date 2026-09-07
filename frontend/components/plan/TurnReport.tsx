// What the last correction did, in the reader's words.
//
// The decision names never appear. "Deferred" is not an error state: it is the
// system correctly declining a request that belongs to a stage which does not
// exist yet. Drift stays visible — "we changed something you didn't ask about"
// is the user's concern, not a system-quality metric — while the inverse signal
// (routed to but unchanged) is ours, and lives in provenance.

import type { Turn } from "@/lib/api";
import { decisionName } from "@/lib/compose";

const list = (kinds: string[]) => kinds.map(decisionName).join(" · ");

export function TurnReport({ turn }: { turn: Turn }) {
  const changed = turn.actual.filter((k) => k !== "intake_strategy");
  const unchanged = turn.unchanged.filter((k) => k !== "intake_strategy");

  return (
    <div className="rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel-strong)] p-5">
      <p className="text-sm leading-6 text-[color:var(--ink)]">
        <span className="text-[color:var(--muted)]">We read that as: </span>
        {turn.reading}
      </p>

      {turn.out_of_scope && (
        <p className="mt-3 rounded-xl border border-sky-200 bg-sky-50 p-3 text-sm leading-6 text-sky-900">
          That&apos;s about how it will look rather than what it says, so nothing
          in the plan changed — {turn.out_of_scope}
        </p>
      )}

      {turn.not_understood && (
        <p className="mt-3 rounded-xl border border-amber-300 bg-amber-50 p-3 text-sm leading-6 text-amber-900">
          That didn&apos;t land anywhere. Try naming what feels wrong about the
          plan above — what&apos;s missing, too deep, in the wrong order.
        </p>
      )}

      {changed.length > 0 && (
        <>
          <p className="mt-3 text-sm leading-6 text-[color:var(--ink)]">
            <span className="text-[color:var(--muted)]">Updated: </span>
            {list(changed)}
          </p>
          {unchanged.length > 0 && (
            <p className="mt-0.5 text-sm leading-6 text-[color:var(--muted)]">
              Left alone: {list(unchanged)}
            </p>
          )}
        </>
      )}

      {turn.unclaimed_drift.length > 0 && (
        <p className="mt-3 text-sm leading-6 text-amber-800">
          We also changed {list(turn.unclaimed_drift)} without being asked — check
          that above.
        </p>
      )}
    </div>
  );
}
