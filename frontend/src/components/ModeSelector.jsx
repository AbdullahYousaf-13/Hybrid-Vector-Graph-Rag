import { Check } from "lucide-react";
import { MODES } from "../constants.js";
import { cx } from "../utils/cx.js";

/**
 * The native radio is visually hidden (`sr-only`) and the card itself is the
 * one selection indicator; there is deliberately no second dot competing
 * with it. Keyboard and screen-reader behaviour stays native.
 */
export default function ModeSelector({ value, onChange, disabled }) {
  return (
    <fieldset className="min-w-0">
      <legend className="mb-2.5 font-display text-[11px] font-semibold tracking-[0.2em] text-gold-400/85 uppercase">
        Retrieval mode
      </legend>

      <div className="grid gap-3 sm:grid-cols-3">
        {MODES.map((mode) => {
          const selected = value === mode.id;
          const Icon = mode.icon;

          return (
            <label
              key={mode.id}
              title={mode.blurb}
              className={cx(
                "group relative flex cursor-pointer flex-col gap-1.5 rounded-sm border p-3.5 transition",
                "shadow-[inset_0_1px_0_rgba(255,255,255,0.05)]",
                "focus-within:ring-2 focus-within:ring-gold-400 focus-within:ring-offset-2 focus-within:ring-offset-night-900",
                disabled && "cursor-not-allowed opacity-60",
                selected
                  ? mode.card
                  : "border-gold-400/20 bg-white/[0.03] hover:border-gold-400/50 hover:bg-white/[0.06]"
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

              <div className="flex items-center gap-2.5">
                <span
                  className={cx(
                    "grid size-8 shrink-0 place-items-center rounded-sm border transition",
                    selected ? mode.iconWrap : "border-gold-400/20 bg-white/[0.05] text-mist"
                  )}
                >
                  <Icon className="size-4" aria-hidden="true" />
                </span>

                <span
                  className={cx(
                    "font-display text-[13px] font-bold tracking-[0.08em] uppercase",
                    selected ? mode.accentText : "text-parchment-100"
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

              <span className="text-[15px] leading-snug text-mist">{mode.tagline}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}
