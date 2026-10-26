import { routeLine, type Route } from "@/lib/case";

/* The route in one plain sentence. Nothing to tap. */
export function RouteLine({ route }: { route: Route | null }) {
  const text = route ? routeLine(route) : "Working out which program governs this service.";
  return (
    <p className="mt-6 border-t border-hairline pt-4 text-[18px] leading-relaxed font-semibold lg:text-[17px]" data-route={route?.program ?? ""}>
      {text}
    </p>
  );
}
