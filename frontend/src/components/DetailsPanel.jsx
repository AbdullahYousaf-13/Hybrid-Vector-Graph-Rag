import { useState } from "react";
import { ChevronDown, Code2, FileText } from "lucide-react";
import { cleanChunk } from "../utils/formatAnswer.js";
import { cx } from "../utils/cx.js";

/**
 * Shows what the retriever actually did: the generated Cypher (graph) and/or
 * the retrieved chunks (vector). Hybrid answers can carry both. Collapsed by
 * default so the answer stays the focus.
 */
export default function DetailsPanel({ details }) {
  const [open, setOpen] = useState(false);

  const cypher = details?.cypher_query ?? details?.graph_cypher_query ?? null;
  const chunks = details?.chunks ?? details?.vector_chunks ?? null;

  if (!cypher && !(Array.isArray(chunks) && chunks.length > 0)) return null;

  return (
    <div className="mt-5 border-t border-parchment-300 pt-4">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-lg px-2 py-1 -ml-2 font-display text-xs tracking-wide text-ink-600 uppercase transition hover:text-ink-900 focus-visible:ring-2 focus-visible:ring-gold-400 focus-visible:outline-none"
      >
        <ChevronDown
          className={cx("size-4 transition-transform", open && "rotate-180")}
          aria-hidden="true"
        />
        {open ? "Hide details" : "Show details"}
      </button>

      {open && (
        <div className="mt-3 space-y-4">
          {cypher && (
            <section>
              <h3 className="mb-1.5 flex items-center gap-1.5 text-xs tracking-wide text-ink-400 uppercase">
                <Code2 className="size-3.5" aria-hidden="true" />
                Generated Cypher
              </h3>
              <pre className="thin-scroll overflow-x-auto overflow-y-hidden rounded-lg border border-parchment-300 bg-ink-900 p-3 font-mono text-xs leading-relaxed text-parchment-200">
                {cypher}
              </pre>
            </section>
          )}

          {Array.isArray(chunks) && chunks.length > 0 && (
            <section>
              <h3 className="mb-1.5 flex items-center gap-1.5 text-xs tracking-wide text-ink-400 uppercase">
                <FileText className="size-3.5" aria-hidden="true" />
                Retrieved chunks ({chunks.length})
              </h3>
              <ol className="thin-scroll max-h-80 space-y-2 overflow-y-auto pr-1">
                {chunks.map((chunk, index) => (
                  <li
                    key={index}
                    className="rounded-lg border border-parchment-300 bg-parchment-50/80 p-3"
                  >
                    <span className="mb-1 inline-block rounded bg-parchment-200 px-1.5 py-0.5 font-mono text-[10px] text-ink-600">
                      #{index + 1}
                    </span>
                    <p className="text-sm leading-relaxed whitespace-pre-wrap text-ink-600">
                      {cleanChunk(chunk)}
                    </p>
                  </li>
                ))}
              </ol>
            </section>
          )}
        </div>
      )}
    </div>
  );
}
