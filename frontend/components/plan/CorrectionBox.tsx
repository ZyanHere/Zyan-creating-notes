"use client";

// Free text, deliberately. No per-section edit buttons and no field-level form:
// the system classifies and the user writes English, and that is the thing this
// milestone tests. A structured correction UI would test something else.

import { useState } from "react";
import { Spinner } from "@/components/ui/Spinner";

export function CorrectionBox({
  onSubmit,
  onApprove,
  pending,
  disabled,
  hideApprove = false,
  embedded = false,
  label = "Anything wrong? Say it however you like.",
}: {
  onSubmit: (text: string) => void;
  onApprove: () => void;
  pending: boolean;
  disabled: boolean;
  hideApprove?: boolean;
  /** Inside a panel rather than pinned to the page.
   *
   *  The two uses need opposite chrome. Pinned, it is a bar over the document
   *  and needs its own ground and a top edge to sit against; inside a panel,
   *  that same ground and edge draw a seam across the card it lives in. */
  embedded?: boolean;
  label?: string;
}) {
  const [text, setText] = useState("");

  function send() {
    if (!text.trim() || pending) return;
    onSubmit(text.trim());
    setText("");
  }

  return (
    <div
      className={
        embedded
          ? ""
          : "sticky bottom-0 z-10 border-t border-[color:var(--line-strong)] bg-[color:var(--canvas)]/90 pb-6 pt-5 backdrop-blur-xl"
      }
    >
      <label className="eyebrow">{label}</label>
      <textarea
        value={text}
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) send();
        }}
        rows={2}
        disabled={pending || disabled}
        placeholder="i only have four days · you've missed X entirely · go deeper on Y"
        className="ruled mt-2 px-0 py-2 font-[family-name:var(--font-serif)] text-[0.9375rem] leading-7 placeholder:text-[color:var(--soft)] placeholder:italic"
      />
      <div className="mt-3 flex flex-wrap items-center gap-3">
        <button
          onClick={send}
          disabled={pending || disabled || !text.trim()}
          className="btn btn-ghost"
        >
          {pending ? (
            <>
              <Spinner />
              Revising…
            </>
          ) : (
            "Send correction"
          )}
        </button>
        {!hideApprove && (
        <button
          onClick={onApprove}
          disabled={pending || disabled}
          className="btn btn-primary"
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
