import { redirect } from "next/navigation";

import { isAuthed } from "@/lib/auth";
import { countByStatus, getPendingDeals, getSupersededDeals } from "@/lib/deals";
import LogoutButton from "./LogoutButton";
import ReviewQueue from "./ReviewQueue";
import SupersededList from "./SupersededList";

export const dynamic = "force-dynamic";

export default async function ReviewPage() {
  if (!isAuthed()) {
    redirect("/login");
  }
  const [deals, counts, superseded] = await Promise.all([
    getPendingDeals(),
    countByStatus(),
    getSupersededDeals(),
  ]);
  return (
    <main className="mx-auto max-w-6xl p-6">
      <header className="mb-6 flex items-baseline justify-between">
        <h1 className="text-2xl font-semibold">Deal review queue</h1>
        <div className="flex items-center gap-4 text-sm text-neutral-500">
          <span>
            pending {counts.pending ?? 0} · approved {counts.approved ?? 0} · rejected{" "}
            {counts.rejected ?? 0}
          </span>
          <LogoutButton />
        </div>
      </header>
      <ReviewQueue initialDeals={deals} />
      <SupersededList deals={superseded} />
    </main>
  );
}
