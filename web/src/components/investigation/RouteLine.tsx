import { routeLine, type Route } from "@/lib/case";

/* The route in one plain sentence. Nothing to tap. "lead" sits under a section heading, without its own rule. */
export function RouteLine({ route, lead = false }: { route: Route | null; lead?: boolean }) {
  const text = route ? routeLine(route) : "Working out which program governs this service.";
  return (
    <p
      className={`${lead ? "mt-3" : "mt-6 border-t border-hairline pt-4"} text-[18px] leading-relaxed font-semibold lg:text-[17px]`}
      data-route={route?.program ?? ""}
    >
      {text}
    </p>
  );
}
