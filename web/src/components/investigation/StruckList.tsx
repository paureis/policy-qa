import { struckSource, type StruckCitation } from "@/lib/case";
import { Strike } from "./Strike";

/*
  The citations the verifier struck, shown on any finding that has them:
  each quote struck through, where it was claimed from, and the reason.
  Struck citations are shown, never hidden. The strike draws left to right
  when the citation arrives (Strike), unless reduced motion is set.
*/
export function StruckList({ struck, className = "" }: { struck: StruckCitation[]; className?: string }) {
  if (struck.length === 0) return null;
  const n = struck.length;
  return (
    <div className={`mt-4 ${className}`} data-struck={n}>
      <p className="text-[15px] font-semibold text-ink">{n === 1 ? "1 citation was struck:" : `${n} citations were struck:`}</p>
      <ul className="mt-2 space-y-3" aria-label="Citations the verifier struck">
        {struck.map((s, i) => (
          <li key={`${s.doc_id ?? "none"}-${s.page ?? "none"}-${i}`} className="border-l border-ink/40 pl-4">
            <p className="text-[16px] leading-relaxed">
              <Strike className="decoration-ink decoration-2">“{s.quote}”</Strike>
            </p>
            <p className="mt-1 text-[15px] text-muted">{struckSource(s)}</p>
            <p className="mt-1 text-[15px] font-semibold text-ink">Reason: {s.reason}.</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
