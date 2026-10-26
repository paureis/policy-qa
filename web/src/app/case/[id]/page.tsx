import type { Metadata } from "next";
import { Suspense } from "react";
import { InvestigationView } from "@/components/investigation/InvestigationView";

export const metadata: Metadata = {
  title: "Case",
  description: "The case's investigation: each question asked of the written rules, the answer, and the verified citations.",
};

/*
  Server shell for /case/[id]. The id is a request-time param, so it is
  awaited inside a Suspense boundary (cacheComponents is on); the loading
  line doubles as the prerendered fallback. Everything else is the client
  InvestigationView.
*/
export default function CasePage({ params }: { params: Promise<{ id: string }> }) {
  return (
    <Suspense fallback={<LoadingLine />}>
      <CaseById params={params} />
    </Suspense>
  );
}

async function CaseById({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  return <InvestigationView caseId={id} />;
}

function LoadingLine() {
  return (
    <main className="mx-auto w-full max-w-[640px] flex-1 px-4 pt-6 pb-16">
      <p className="text-[18px] lg:text-[17px]">Loading the case…</p>
    </main>
  );
}
