import type { Metadata } from "next";
import { IntakeFlow } from "@/components/intake/IntakeFlow";

export const metadata: Metadata = {
  title: "New case",
  description: "Read a coverage denial letter into a case card, check the details, and open the case.",
};

export default function NewCasePage() {
  return <IntakeFlow />;
}
