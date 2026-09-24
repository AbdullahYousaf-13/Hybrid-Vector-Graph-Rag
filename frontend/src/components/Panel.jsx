import { CornerFlourish } from "./Ornament.jsx";
import { cx } from "../utils/cx.js";

export default function Panel({ className, children, ...rest }) {
  const corner = "pointer-events-none absolute hidden size-7 text-gold-400/55 sm:block";

  return (
    <div className={cx("panel rounded-sm p-6 sm:p-9", className)} {...rest}>
      <CornerFlourish className={cx(corner, "top-2 left-2")} />
      <CornerFlourish className={cx(corner, "top-2 right-2 rotate-90")} />
      <CornerFlourish className={cx(corner, "right-2 bottom-2 rotate-180")} />
      <CornerFlourish className={cx(corner, "bottom-2 left-2 -rotate-90")} />
      {children}
    </div>
  );
}
