import { cx } from "../utils/cx.js";

const HOUSES = [
  "via-gryffindor-ribbon",
  "via-slytherin-ribbon",
  "via-ravenclaw-ribbon",
  "via-hufflepuff-ribbon",
];

export default function HouseRibbon({ className }) {
  return (
    <div aria-hidden="true" className={cx("w-full", className)}>
      <div className="flex h-[3px] gap-3 px-6 sm:px-16">
        {HOUSES.map((house) => (
          <div
            key={house}
            className={cx("h-full flex-1 rounded-full bg-gradient-to-r from-transparent to-transparent", house)}
          />
        ))}
      </div>
      <div className="mt-1.5 h-px w-full bg-gradient-to-r from-transparent via-gold-600/60 to-transparent" />
    </div>
  );
}
