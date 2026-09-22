import { BookOpen } from "lucide-react";
import HouseStripe from "./HouseStripe.jsx";

export default function Header() {
  return (
    <header>
      <HouseStripe className="h-1.5" />

      <div className="mx-auto max-w-3xl px-4 pt-8 pb-6 text-center sm:px-6 sm:pt-12">
        <div className="mb-3 inline-flex items-center gap-2 rounded-full border border-parchment-300 bg-parchment-50/70 px-3 py-1 text-xs tracking-wide text-ink-600 uppercase">
          <BookOpen className="size-3.5 text-gold-600" aria-hidden="true" />
          All seven books
        </div>

        <h1 className="font-display text-3xl leading-tight font-bold text-ink-900 sm:text-4xl">
          The Hogwarts Archive
        </h1>

        <div className="my-4 flex items-center justify-center gap-3" aria-hidden="true">
          <span className="h-px w-16 bg-gradient-to-r from-transparent to-gold-400 sm:w-24" />
          <span className="size-1.5 rotate-45 bg-gold-400" />
          <span className="h-px w-16 bg-gradient-to-l from-transparent to-gold-400 sm:w-24" />
        </div>

        <p className="mx-auto max-w-xl text-lg text-ink-600">
          A hybrid <span className="text-ink-900">vector + graph</span> retrieval system over the
          Harry Potter corpus. Ask a question, choose how it should be answered, and see exactly
          what the retriever found.
        </p>
      </div>
    </header>
  );
}
