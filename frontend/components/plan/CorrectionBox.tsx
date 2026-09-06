"use client";

// Free text, deliberately. No per-section edit buttons and no field-level form:
// the system classifies and the user writes English, and that is the thing this
// milestone tests. A structured correction UI would test something else.

import { useState } from "react";

export function CorrectionBox({
  onSubmit,
  onApprove,
  pending,
  disabled,
  hideApprove = false,
  label = "Anything wrong? Say it however you like.",
}: {
  onSubmit: (text: string) => void;
  onApprove: () => void;
  pending: boolean;
  disabled: boolean;
  hideApprove?: boolean;
  label?: string;
}) {
  const [text, setText] = useState("");

  function send() {
    if (!text.trim() || pending) return;
    onSubmit(text.trim());
    setText("");
  }

  return (
    <div className="sticky bottom-0 border-t border-[color:var(--line)] bg-[color:var(--canvas)]/95 pb-6 pt-5 backdrop-blur">
      <label className="text-sm text-[color:var(--muted)]">{label}</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send();
        }}
        rows={2}
        disabled={pending || disabled}
        placeholder="i only have four days · you've missed X entirely · go deeper on Y"
        className="mt-2 w-full resize-none rounded-2xl border border-[color:var(--line)] bg-[color:var(--panel)] p-4 text-sm leading-6 text-[color:var(--ink)] outline-none placeholder:text-[color:var(--muted)]/60 focus:border-[color:var(--line-strong)] disabled:opacity-60"
      />
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          onClick={send}
          disabled={pending || disabled || !text.trim()}
          className="rounded-full border border-[color:var(--line-strong)] px-5 py-2.5 text-sm font-medium text-[color:var(--ink)] disabled:opacity-40"
        >
          {pending ? "Revising…" : "Send correction"}
        </button>
        {!hideApprove && (
        <button
          onClick={onApprove}
          disabled={pending || disabled}
          className="rounded-full bg-[color:var(--ink)] px-5 py-2.5 text-sm font-medium text-white disabled:opacity-40"
        >
          This is right — approve
        </button>
        )}
        {pending && (
          <span className="text-sm text-[color:var(--muted)]">
            Working out what this changes. Up to a minute.
          </span>
        )}
      </div>
    </div>
  );
}
