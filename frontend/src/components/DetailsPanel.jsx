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
    <div className="mt-5 border-t border-gold-400/20 pt-4">
      <button
        type="button"
        onClick={() => setOpen((value) => !value)}
        aria-expanded={open}
        className="inline-flex items-center gap-1.5 rounded-sm px-2 py-1 -ml-2 font-display text-[11px] font-semibold tracking-[0.2em] text-gold-400/85 uppercase transition hover:text-gold-300 focus-visible:ring-2 focus-visible:ring-gold-400 focus-visible:outline-none"
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
              <h3 className="mb-1.5 flex items-center gap-1.5 font-display text-[10px] font-semibold tracking-[0.18em] text-mist uppercase">
                <Code2 className="size-3.5" aria-hidden="true" />
                Generated Cypher
              </h3>
              <pre className="thin-scroll overflow-x-auto overflow-y-hidden rounded-sm border border-gold-400/15 bg-night-950/70 p-3.5 font-mono text-xs leading-relaxed text-parchment-200 shadow-[inset_0_2px_10px_rgba(0,0,0,0.6)]">
                {cypher}
              </pre>
            </section>
          )}

          {Array.isArray(chunks) && chunks.length > 0 && (
            <section>
              <h3 className="mb-1.5 flex items-center gap-1.5 font-display text-[10px] font-semibold tracking-[0.18em] text-mist uppercase">
                <FileText className="size-3.5" aria-hidden="true" />
                Retrieved chunks ({chunks.length})
              </h3>
              <ol className="thin-scroll max-h-80 space-y-2 overflow-y-auto pr-1">
                {chunks.map((chunk, index) => (
                  <li
                    key={index}
                    className="rounded-sm border border-gold-400/15 bg-white/[0.04] p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.04)]"
                  >
                    <span className="mb-1 inline-block rounded-sm border border-gold-400/25 bg-white/[0.06] px-1.5 py-0.5 font-display text-[10px] font-semibold text-gold-300">
                      #{index + 1}
                    </span>
                    <p className="text-[15px] leading-relaxed whitespace-pre-wrap text-parchment-200/85">
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
