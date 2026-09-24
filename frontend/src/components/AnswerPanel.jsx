import { AlertTriangle, Clock, Gauge, Loader2, Sparkles } from "lucide-react";
import { MODES } from "../constants.js";
import { parseAnswer, parseInline } from "../utils/formatAnswer.js";
import { cx } from "../utils/cx.js";
import DetailsPanel from "./DetailsPanel.jsx";
import Panel from "./Panel.jsx";

export default function AnswerPanel({ status, result, error, asked, elapsed }) {
  if (status === "idle") return <IdleState />;
  if (status === "loading") return <LoadingState elapsed={elapsed} asked={asked} />;
  if (status === "error") return <ErrorState error={error} />;
  if (status === "success" && result) return <AnswerSheet result={result} asked={asked} />;
  return null;
}

const label = "font-display text-[11px] font-semibold tracking-[0.22em] uppercase";

function IdleState() {
  return (
    <Panel className="py-8 text-center sm:py-10">
      <Sparkles className="mx-auto size-7 text-gold-400 drop-shadow-[0_0_10px_rgba(211,166,37,0.55)]" aria-hidden="true" />
      <p className={cx(label, "mt-4 text-gold-300")}>The archive is listening</p>
      <p className="mt-2 text-lg text-mist">
        Pick a suggestion or write your own question, then press Ask.
      </p>
    </Panel>
  );
}

function LoadingState({ elapsed, asked }) {
  return (
    <Panel className="rise-in">
      <div className="flex items-center gap-2.5">
        <Loader2 className="size-4 animate-spin text-gold-400" aria-hidden="true" />
        <span className={cx(label, "text-gold-300")}>
          Consulting the archive… {elapsed.toFixed(1)}s
        </span>
      </div>

      {asked?.question && <p className="mt-3 text-lg text-mist italic">“{asked.question}”</p>}

      <div className="mt-5 space-y-2.5" aria-hidden="true">
        <div className="h-3 w-full animate-pulse rounded-sm bg-white/[0.07]" />
        <div className="h-3 w-11/12 animate-pulse rounded-sm bg-white/[0.07]" />
        <div className="h-3 w-8/12 animate-pulse rounded-sm bg-white/[0.07]" />
      </div>
    </Panel>
  );
}

function ErrorState({ error }) {
  const status = error?.status;
  const hint =
    status === 429
      ? "The shared daily request quota is used up. It resets at midnight UTC."
      : status === 503
        ? "This is temporary on Google's side. Wait a few seconds and ask again."
        : status === 400
        ? "Adjust the question and try again."
        : status === 0
          ? "The API isn't reachable - check that the backend process is running."
          : "Try again, or check the backend logs for details.";

  return (
    <Panel className="rise-in">
      <div className="flex items-start gap-3">
        <AlertTriangle className="mt-0.5 size-5 shrink-0 text-gryffindor-light" aria-hidden="true" />
        <div className="min-w-0">
          <p className={cx(label, "text-gryffindor-light")}>
            {status ? `Request failed (${status})` : "Request failed"}
          </p>
          <p className="mt-1.5 text-lg break-words text-parchment-100">{error?.message}</p>
          <p className="mt-2 text-mist">{hint}</p>
        </div>
      </div>
    </Panel>
  );
}

function AnswerSheet({ result, asked }) {
  const mode = MODES.find((m) => m.id === asked?.mode);
  const allBlocks = parseAnswer(result.answer);
  // Hybrid prefixes degraded answers with a "(... unavailable ...)" status line; show it as a
  // quiet note so the drop cap lands on the real answer instead of "(G".
  const hasNotice = allBlocks[0]?.type === "paragraph" && /^\(.*\)$/.test(allBlocks[0].text);
  const notice = hasNotice ? allBlocks[0].text.slice(1, -1) : null;
  const blocks = hasNotice ? allBlocks.slice(1) : allBlocks;
  const quota = result.quota;
  const quotaPercent = quota?.max ? Math.min(100, (quota.used / quota.max) * 100) : 0;

  return (
    <Panel className="rise-in">
      <div className="flex flex-wrap items-center gap-3">
        {mode && (
          <span
            className={cx(
              "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 font-display text-[10px] font-bold tracking-[0.14em] uppercase",
              mode.badge
            )}
          >
            <mode.icon className="size-3.5" aria-hidden="true" />
            {mode.label}
          </span>
        )}
        <p className="min-w-0 flex-1 text-lg text-mist italic">“{asked?.question}”</p>
      </div>

      <div className="mt-5 space-y-3.5 text-[19px] leading-[1.6] text-parchment-50">
        {notice && <p className="text-base text-mist italic">{notice}</p>}
        {blocks.map((block, index) => {
          if (block.type === "heading") {
            return (
              <h3
                key={index}
                className="pt-2 font-display text-sm font-semibold tracking-[0.14em] text-gold-300 uppercase"
              >
                {block.text}
              </h3>
            );
          }
          if (block.type === "list") {
            const List = block.ordered ? "ol" : "ul";
            return (
              <List key={index} className="space-y-2 pl-1">
                {block.items.map((item, itemIndex) => (
                  <li key={itemIndex} className="flex gap-2.5">
                    {block.ordered ? (
                      <span className="min-w-6 shrink-0 font-semibold text-gold-400" aria-hidden="true">
                        {block.start + itemIndex}.
                      </span>
                    ) : (
                      <span className="mt-3 size-1.5 shrink-0 rotate-45 bg-gold-400" aria-hidden="true" />
                    )}
                    <span>
                      <RichText text={item} />
                    </span>
                  </li>
                ))}
              </List>
            );
          }
          return (
            <p key={index} className={cx(index === 0 && "drop-cap")}>
              <RichText text={block.text} />
            </p>
          );
        })}
      </div>

      <div className="mt-6 flex flex-wrap items-center gap-x-6 gap-y-2 border-t border-gold-400/20 pt-3.5 text-sm text-mist">
        <span className="inline-flex items-center gap-1.5">
          <Clock className="size-3.5" aria-hidden="true" />
          Answered in {result.total_seconds.toFixed(1)}s
        </span>

        {quota?.used != null && (
          <span className="inline-flex items-center gap-1.5">
            <Gauge className="size-3.5" aria-hidden="true" />
            {quota.used}/{quota.max} requests used today
            <span className="ml-1 h-1 w-16 overflow-hidden rounded-full bg-white/10">
              <span className="block h-full bg-gold-400" style={{ width: `${quotaPercent}%` }} />
            </span>
          </span>
        )}
      </div>

      <DetailsPanel details={result.details} />
    </Panel>
  );
}

function RichText({ text }) {
  return parseInline(text).map((part, index) => {
    if (part.style === "bold") {
      return (
        <strong key={index} className="font-semibold text-gold-300">
          {part.text}
        </strong>
      );
    }
    if (part.style === "italic") {
      return (
        <em key={index} className="text-parchment-200">
          {part.text}
        </em>
      );
    }
    return <span key={index}>{part.text}</span>;
  });
}
