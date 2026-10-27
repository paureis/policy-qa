"use client";

import { useId } from "react";
import type { EvidenceItem } from "@/lib/case";
import { CitationChips } from "@/components/investigation/CitationChip";
import { PHONE_SHEET } from "@/components/investigation/SectionTitle";

/*
  What to include with the appeal. Each row is a real checkbox the person can
  tick as they gather papers; the tick lives only on this screen. The reason
  sits under each item, and the chip when the policy is the reason.
  register: part of section 3 at desktop ("What to send and where to file"),
  under the letter sheet, as an h3 without the section rule and overline.
*/
export function EvidenceChecklist({ items, register = false }: { items: EvidenceItem[]; register?: boolean }) {
  if (!items || items.length === 0) return null;
  const Heading = register ? "h3" : "h2";
  return (
    <section
      aria-labelledby="evidence-heading"
      className={register ? "" : `land mt-10 ${PHONE_SHEET}`}
      data-checklist={items.length}
      data-register={register ? "true" : undefined}
    >
      <Heading id="evidence-heading" className={register ? "text-[20px] leading-tight font-semibold" : "mt-1 text-[22px] leading-tight font-bold"}>
        What to include with your appeal
      </Heading>
      <p className="mt-2 text-[16px] text-muted">Tick each one as you put it with the letter. The ticks stay on this screen only.</p>
      <ul className="mt-4 divide-y divide-hairline border-y border-hairline">
        {items.map((item, i) => (
          <ChecklistRow key={i} item={item} />
        ))}
      </ul>
    </section>
  );
}

function ChecklistRow({ item }: { item: EvidenceItem }) {
  const id = useId();
  return (
    <li className="py-3">
      <label htmlFor={id} className="flex min-h-11 cursor-pointer items-start gap-3">
        <span className="relative mt-[2px] grid h-7 w-7 shrink-0 place-items-center">
          <input
            id={id}
            type="checkbox"
            aria-describedby={`${id}-why`}
            className="peer absolute inset-0 h-7 w-7 cursor-pointer appearance-none border-2 border-ink bg-bond checked:bg-ink lg:-inset-2 lg:h-11 lg:w-11 lg:border-0 lg:bg-transparent lg:checked:bg-transparent"
          />
          {/* At desktop the input is a 44 px target and this draws the 28 px box inside it. */}
          <span aria-hidden="true" className="pointer-events-none absolute inset-0 hidden border-2 border-ink bg-bond peer-checked:bg-ink lg:block" />
          <svg
            viewBox="0 0 20 20"
            aria-hidden="true"
            className="tick-step pointer-events-none relative hidden h-5 w-5 text-white peer-checked:block"
          >
            <path d="M4 10.5l4 4 8-9" fill="none" stroke="currentColor" strokeWidth="2.6" strokeLinecap="square" />
          </svg>
        </span>
        <span className="min-w-0">
          <span className="block text-[18px] leading-snug font-semibold lg:text-[17px]">{item.item}</span>
          <span id={`${id}-why`} className="mt-1 block text-[16px] leading-relaxed text-muted">
            {item.why}
          </span>
        </span>
      </label>
      {item.citation ? (
        <div className="pl-10">
          <CitationChips citations={[item.citation]} label="Why the policy asks for this" />
        </div>
      ) : null}
    </li>
  );
}
