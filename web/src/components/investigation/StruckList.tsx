import { struckSource, type StruckCitation } from "@/lib/case";

/*
  The citations the verifier struck, shown on any finding that has them:
  each quote struck through, where it was claimed from, and the reason.
  Struck citations are shown, never hidden.
*/
export function StruckList({ struck }: { struck: StruckCitation[] }) {
  if (struck.length === 0) return null;
  const n = struck.length;
  return (
    <div className="mt-4" data-struck={n}>
      <p className="text-[15px] font-semibold text-ink">{n === 1 ? "1 citation was struck:" : `${n} citations were struck:`}</p>
      <ul className="mt-2 space-y-3" aria-label="Citations the verifier struck">
        {struck.map((s, i) => (
          <li key={`${s.doc_id ?? "none"}-${s.page ?? "none"}-${i}`} className="border-l-4 border-hairline pl-4">
            <p className="text-[16px] leading-relaxed">
              <s className="decoration-ink decoration-2">“{s.quote}”</s>
            </p>
            <p className="mt-1 text-[15px] text-muted">{struckSource(s)}</p>
            <p className="mt-1 text-[15px] font-semibold text-ink">Reason: {s.reason}.</p>
          </li>
        ))}
      </ul>
    </div>
  );
}
