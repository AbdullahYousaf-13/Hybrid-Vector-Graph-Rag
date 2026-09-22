/**
 * The backend runs every answer through Python's `textwrap.fill(..., 60)`, so
 * it arrives hard-wrapped at 60 columns with any bullets flattened into inline
 * " * " markers. Rendering that verbatim looks broken in a wide column, so
 * rebuild the intended structure: blank lines separate paragraphs, single
 * newlines are just the wrap, and " * " starts a list item.
 */
export function parseAnswer(raw) {
  const text = String(raw ?? "").trim();
  if (!text) return [];

  return text
    .split(/\n\s*\n/)
    .map((block) =>
      block
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean)
        .join(" ")
    )
    .filter(Boolean)
    .flatMap(splitBullets);
}

function splitBullets(paragraph) {
  // `**bold**` markers can't match here: they have no space after the asterisk.
  const parts = paragraph.split(/(?:^|\s)\*\s+/);
  const items = parts
    .slice(1)
    .map((part) => part.trim())
    .filter(Boolean);

  if (items.length === 0) return [{ type: "paragraph", text: paragraph }];

  const lead = parts[0].trim();
  const blocks = lead ? [{ type: "paragraph", text: lead }] : [];
  blocks.push({ type: "list", items });
  return blocks;
}

/**
 * Neo4jVector's `from_existing_graph` prefixes every chunk with the property
 * name it embedded ("text: ..."), which is plumbing noise to a reader.
 */
export function cleanChunk(chunk) {
  return String(chunk ?? "")
    .trim()
    .replace(/^text:\s*/i, "");
}

/**
 * Splits `**bold**` and `*italic*` runs out of a string so they render as
 * <strong>/<em> instead of leaking literal asterisks (the LLM writes both
 * markdown-style; only ** was ever handled, so a lone *word* passed through
 * as-is).
 */
export function parseInline(text) {
  return String(text)
    .split(/(\*\*[^*]+\*\*|\*[^*]+\*)/g)
    .filter(Boolean)
    .map((part) => {
      if (part.startsWith("**") && part.endsWith("**")) {
        return { style: "bold", text: part.slice(2, -2) };
      }
      if (part.startsWith("*") && part.endsWith("*")) {
        return { style: "italic", text: part.slice(1, -1) };
      }
      return { style: null, text: part };
    });
}
