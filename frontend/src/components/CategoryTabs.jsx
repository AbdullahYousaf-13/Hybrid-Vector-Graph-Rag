import { useState } from "react";
import { CATEGORIES, MODES } from "../constants.js";
import { cx } from "../utils/cx.js";

export default function CategoryTabs({ onPick, disabled }) {
  const [activeId, setActiveId] = useState(CATEGORIES[0].id);
  const active = CATEGORIES.find((category) => category.id === activeId) ?? CATEGORIES[0];

  return (
    <section className="min-w-0">
      <div
        role="tablist"
        aria-label="Question categories"
        className="swipe-x flex gap-1 border-b border-gold-400/20"
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
                "-mb-px flex shrink-0 items-center gap-1.5 border-b-2 px-2.5 py-2 font-display text-[11px] font-semibold tracking-[0.06em] whitespace-nowrap uppercase transition",
                "focus-visible:ring-2 focus-visible:ring-gold-400 focus-visible:outline-none",
                isActive
                  ? "border-gold-400 text-gold-300"
                  : "border-transparent text-mist/80 hover:text-parchment-100"
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
          <p className="py-1 text-mist italic">{active.hint}</p>
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
                      "flex items-center gap-2 rounded-full border border-gold-400/25 bg-white/[0.04] px-3 py-1.5 text-[15px] text-parchment-100 transition",
                      "shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]",
                      "hover:border-gold-400/70 hover:bg-white/[0.08] hover:shadow-[0_0_0_1px_rgba(211,166,37,0.25),0_0_18px_-6px_rgba(211,166,37,0.5)]",
                      "focus-visible:ring-2 focus-visible:ring-gold-400 focus-visible:outline-none",
                      disabled && "cursor-not-allowed opacity-50 hover:border-gold-400/25 hover:bg-white/[0.04] hover:shadow-none"
                    )}
                  >
                    {question.text}
                    <span
                      className={cx(
                        "rounded-full border px-1.5 py-px font-display text-[9px] font-semibold tracking-wider uppercase",
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
