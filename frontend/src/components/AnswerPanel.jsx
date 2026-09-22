import { AlertTriangle, Clock, Gauge, Loader2, Sparkles } from "lucide-react";
import { MODES } from "../constants.js";
import { parseAnswer, parseInline } from "../utils/formatAnswer.js";
import { cx } from "../utils/cx.js";
import DetailsPanel from "./DetailsPanel.jsx";

export default function AnswerPanel({ status, result, error, asked, elapsed }) {
  if (status === "idle") return <IdleState />;
  if (status === "loading") return <LoadingState elapsed={elapsed} asked={asked} />;
  if (status === "error") return <ErrorState error={error} />;
  if (status === "success" && result) return <AnswerCard result={result} asked={asked} />;
  return null;
}

function Shell({ className, children }) {
  return (
    <div
      className={cx(
        "rounded-2xl border border-parchment-300 bg-parchment-50/85 p-5 shadow-sm backdrop-blur-[1px] sm:p-6",
        className
      )}
    >
      {children}
    </div>
  );
}

function IdleState() {
  return (
    <Shell className="border-dashed bg-parchment-50/50 text-center">
      <Sparkles className="mx-auto size-6 text-gold-400" aria-hidden="true" />
      <p className="mt-2 font-display text-sm tracking-wide text-ink-600 uppercase">
        The archive is listening
      </p>
      <p className="mt-1 text-ink-400">
        Pick a suggestion or write your own question, then press Ask.
      </p>
    </Shell>
  );
}

function LoadingState({ elapsed, asked }) {
  return (
    <Shell>
      <div className="flex items-center gap-2 text-ink-600">
        <Loader2 className="size-4 animate-spin text-gold-600" aria-hidden="true" />
        <span className="font-display text-sm tracking-wide uppercase">
          Consulting the archive… {elapsed.toFixed(1)}s
        </span>
      </div>

      {asked?.question && (
        <p className="mt-3 text-ink-400 italic">“{asked.question}”</p>
      )}

      <div className="mt-4 space-y-2" aria-hidden="true">
        <div className="h-3 w-full animate-pulse rounded bg-parchment-200" />
        <div className="h-3 w-11/12 animate-pulse rounded bg-parchment-200" />
        <div className="h-3 w-8/12 animate-pulse rounded bg-parchment-200" />
      </div>
    </Shell>
  );
}

function ErrorState({ error }) {
  const status = error?.status;
  const hint =
    status === 429
      ? "The shared daily request quota is used up. It resets tomorrow."
      : status === 400
        ? "Adjust the question and try again."
        : status === 0
          ? "The API isn't reachable — check that the backend process is running."
          : "Try again, or check the backend logs for details.";

  return (
    <Shell className="border-gryffindor/40 bg-gryffindor/5">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 size-5 shrink-0 text-gryffindor" aria-hidden="true" />
        <div className="min-w-0">
          <p className="font-display text-sm font-semibold tracking-wide text-gryffindor uppercase">
            {status ? `Request failed (${status})` : "Request failed"}
          </p>
          <p className="mt-1 break-words text-ink-800">{error?.message}</p>
          <p className="mt-2 text-sm text-ink-400">{hint}</p>
        </div>
      </div>
    </Shell>
  );
}

function AnswerCard({ result, asked }) {
  const mode = MODES.find((m) => m.id === asked?.mode);
  const blocks = parseAnswer(result.answer);
  const quota = result.quota;
  const quotaPercent = quota?.max ? Math.min(100, (quota.used / quota.max) * 100) : 0;

  return (
    <Shell>
      <div className="flex flex-wrap items-center gap-2">
        {mode && (
          <span
            className={cx(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-display text-[11px] tracking-wide uppercase",
              mode.badge
            )}
          >
            <mode.icon className="size-3.5" aria-hidden="true" />
            {mode.label}
          </span>
        )}
        <p className="min-w-0 flex-1 text-ink-400 italic">“{asked?.question}”</p>
      </div>

      <div className="mt-4 space-y-3 text-lg leading-relaxed text-ink-900">
        {blocks.map((block, index) =>
          block.type === "list" ? (
            <ul key={index} className="space-y-1.5 pl-1">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex} className="flex gap-2">
                  <span className="mt-2.5 size-1.5 shrink-0 rotate-45 bg-gold-400" aria-hidden="true" />
                  <span>
                    <RichText text={item} />
                  </span>
                </li>
              ))}
            </ul>
          ) : (
            <p key={index}>
              <RichText text={block.text} />
            </p>
          )
        )}
      </div>

      <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2 border-t border-parchment-300 pt-3 text-xs text-ink-400">
        <span className="inline-flex items-center gap-1.5">
          <Clock className="size-3.5" aria-hidden="true" />
          Answered in {result.time_seconds}s
        </span>

        {quota && (
          <span className="inline-flex items-center gap-1.5">
            <Gauge className="size-3.5" aria-hidden="true" />
            {quota.used}/{quota.max} requests used today
            <span className="ml-1 h-1 w-16 overflow-hidden rounded-full bg-parchment-300">
              <span
                className="block h-full bg-gold-400"
                style={{ width: `${quotaPercent}%` }}
              />
            </span>
          </span>
        )}
      </div>

      <DetailsPanel details={result.details} />
    </Shell>
  );
}

function RichText({ text }) {
  return parseInline(text).map((part, index) =>
    part.bold ? (
      <strong key={index} className="font-semibold text-ink-900">
        {part.text}
      </strong>
    ) : (
      <span key={index}>{part.text}</span>
    )
  );
}
