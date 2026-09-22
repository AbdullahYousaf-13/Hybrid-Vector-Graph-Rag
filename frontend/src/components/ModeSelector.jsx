import { Check } from "lucide-react";
import { MODES } from "../constants.js";
import { cx } from "../utils/cx.js";

/**
 * The native radio is visually hidden (`sr-only`) and the card itself is the
 * one selection indicator — there is deliberately no second dot competing
 * with it. Keyboard and screen-reader behaviour stays native.
 */
export default function ModeSelector({ value, onChange, disabled }) {
  return (
    <fieldset className="min-w-0">
      <legend className="mb-2 font-display text-xs tracking-widest text-ink-600 uppercase">
        Retrieval mode
      </legend>

      <div className="grid gap-2.5 sm:grid-cols-3">
        {MODES.map((mode) => {
          const selected = value === mode.id;
          const Icon = mode.icon;

          return (
            <label
              key={mode.id}
              title={mode.blurb}
              className={cx(
                "group relative flex cursor-pointer flex-col gap-1 rounded-xl border p-3 transition",
                "focus-within:ring-2 focus-within:ring-gold-400 focus-within:ring-offset-1 focus-within:ring-offset-parchment-100",
                disabled && "cursor-not-allowed opacity-60",
                selected
                  ? mode.card
                  : "border-parchment-300 bg-parchment-50/60 hover:border-parchment-400 hover:bg-parchment-50"
              )}
            >
              <input
                type="radio"
                name="mode"
                value={mode.id}
                checked={selected}
                disabled={disabled}
                onChange={() => onChange(mode.id)}
                className="sr-only"
              />

              <div className="flex items-center gap-2">
                <span
                  className={cx(
                    "grid size-7 shrink-0 place-items-center rounded-lg transition",
                    selected ? mode.iconWrap : "bg-parchment-200 text-ink-400"
                  )}
                >
                  <Icon className="size-4" aria-hidden="true" />
                </span>

                <span
                  className={cx(
                    "font-display text-sm font-semibold",
                    selected ? mode.accentText : "text-ink-800"
                  )}
                >
                  {mode.label}
                </span>

                {selected && (
                  <Check
                    className={cx("ml-auto size-4 shrink-0", mode.accentText)}
                    aria-hidden="true"
                  />
                )}
              </div>

              <span className="text-sm leading-snug text-ink-600">{mode.tagline}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
