import { cx } from "../utils/cx.js";

/** The four house colours, in one thin band. Used at the page's top and foot. */
export default function HouseStripe({ className }) {
  return (
    <div className={cx("flex w-full overflow-hidden", className)} aria-hidden="true">
      <div className="flex-1 bg-gryffindor" />
      <div className="flex-1 bg-slytherin" />
      <div className="flex-1 bg-ravenclaw" />
      <div className="flex-1 bg-hufflepuff" />
    </div>
  );
}
