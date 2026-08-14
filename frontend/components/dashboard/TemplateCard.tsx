import type { Template } from "@/lib/mock-data";

type TemplateCardProps = {
  template: Template;
};

export function TemplateCard({ template }: TemplateCardProps) {
  return (
    <article className="rounded-[24px] border border-[color:var(--line)] bg-white p-5 shadow-[0_16px_36px_rgba(27,40,56,0.05)]">
      <div className="flex items-center justify-between gap-4">
        <h3 className="text-base font-semibold text-[color:var(--ink)]">
          {template.name}
        </h3>
        <span className="rounded-full bg-[color:var(--canvas)] px-3 py-1 text-xs font-medium text-[color:var(--muted)]">
          Preview
        </span>
      </div>
      <p className="mt-3 text-sm leading-6 text-[color:var(--muted)]">
        {template.description}
      </p>
      <p className="mt-4 text-sm font-medium text-[color:var(--ink)]">
        {template.emphasis}
      </p>
    </article>
  );
}
