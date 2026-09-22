import { useState } from "react";
import { CATEGORIES, MODES } from "../constants.js";
import { cx } from "../utils/cx.js";

/**
 * Tabs of suggested questions. The first tab ("Ask Away") intentionally has no
 * presets — it's the free-form path. Picking a suggestion only fills the
 * question box and switches the mode; it never sends the request.
 */
export default function CategoryTabs({ onPick, disabled }) {
  const [activeId, setActiveId] = useState(CATEGORIES[0].id);
  const active = CATEGORIES.find((category) => category.id === activeId) ?? CATEGORIES[0];

  return (
    <section className="min-w-0">
      <div
        role="tablist"
        aria-label="Question categories"
        className="swipe-x flex gap-1 border-b border-parchment-300"
      >
        {CATEGORIES.map((category) => {
          const Icon = category.icon;
          const isActive = category.id === active.id;

          return (
            <button
              key={category.id}
              type="button"
              role="tab"
              aria-selected={isActive}
              onClick={() => setActiveId(category.id)}
              className={cx(
                "-mb-px flex shrink-0 items-center gap-1.5 border-b-2 px-3 py-2 font-display text-xs tracking-wide whitespace-nowrap uppercase transition",
                "focus-visible:ring-2 focus-visible:ring-gold-400 focus-visible:outline-none",
                isActive
                  ? "border-gold-400 text-ink-900"
                  : "border-transparent text-ink-400 hover:text-ink-600"
              )}
            >
              <Icon className="size-3.5" aria-hidden="true" />
              {category.label}
            </button>
          );
        })}
      </div>

      <div className="pt-3">
        {active.questions.length === 0 ? (
          <p className="py-1 text-sm text-ink-400 italic">{active.hint}</p>
        ) : (
          <ul className="flex flex-wrap gap-2">
            {active.questions.map((question) => {
              const mode = MODES.find((m) => m.id === question.mode);

              return (
                <li key={question.text}>
                  <button
                    type="button"
                    disabled={disabled}
                    onClick={() => onPick(question)}
                    className={cx(
                      "flex items-center gap-2 rounded-full border border-parchment-300 bg-parchment-50/70 px-3 py-1.5 text-sm text-ink-800 transition",
                      "hover:border-gold-400 hover:bg-parchment-50",
                      "focus-visible:ring-2 focus-visible:ring-gold-400 focus-visible:outline-none",
                      disabled && "cursor-not-allowed opacity-50 hover:border-parchment-300"
                    )}
                  >
                    {question.text}
                    <span
                      className={cx(
                        "rounded-full border px-1.5 py-px text-[10px] tracking-wide uppercase",
                        mode?.badge
                      )}
                    >
                      {mode?.label}
                    </span>
                  </button>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </section>
  );
}
