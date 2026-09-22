import { cx } from "../utils/cx.js";

const HOUSES = [
  "from-transparent via-gryffindor-light/90 to-transparent shadow-[0_0_14px_rgba(232,112,108,0.45)]",
  "from-transparent via-slytherin-light/90 to-transparent shadow-[0_0_14px_rgba(127,207,154,0.4)]",
  "from-transparent via-ravenclaw-light/90 to-transparent shadow-[0_0_14px_rgba(142,165,230,0.4)]",
  "from-transparent via-hufflepuff/95 to-transparent shadow-[0_0_14px_rgba(236,185,57,0.45)]",
];

/**
 * The four house colours as soft glowing ribbons, each fading at its ends,
 * held together by a single gold hairline beneath.
 */
export default function HouseRibbon({ className }) {
  return (
    <div aria-hidden="true" className={cx("w-full", className)}>
      <div className="flex h-[3px] gap-3 px-6 sm:px-16">
        {HOUSES.map((house) => (
          <div key={house} className={cx("h-full flex-1 rounded-full bg-gradient-to-r", house)} />
        ))}
      </div>
      <div className="mt-1.5 h-px w-full bg-gradient-to-r from-transparent via-gold-400/70 to-transparent" />
    </div>
  );
}
