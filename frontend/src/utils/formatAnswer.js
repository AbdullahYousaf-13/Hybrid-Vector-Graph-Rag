/**
 * Turns the model's markdown-style answer into blocks: headings (`## x` or a
 * line that is only `**x**`), bullet lists (`-`, `*`), numbered lists (`1.`),
 * and paragraphs (consecutive plain lines, split by blank lines).
 */
export function parseAnswer(raw) {
  const blocks = [];
  let paragraph = [];

  const flushParagraph = () => {
    if (paragraph.length) blocks.push({ type: "paragraph", text: paragraph.join(" ") });
    paragraph = [];
  };

  const addItem = (ordered, text, number) => {
    const last = blocks[blocks.length - 1];
    if (last?.type === "list" && last.ordered === ordered) {
      last.items.push(text);
    } else {
      blocks.push({ type: "list", ordered, start: number ?? 1, items: [text] });
    }
  };

  for (const rawLine of String(raw ?? "").split(/\r?\n/)) {
    const line = rawLine.trim();
    let match;

    if (!line) {
      flushParagraph();
    } else if ((match = line.match(/^#{1,6}\s+(.+)$/))) {
      flushParagraph();
      blocks.push({ type: "heading", text: stripBold(match[1]) });
    } else if ((match = line.match(/^\*\*([^*]+)\*\*:?$/))) {
      flushParagraph();
      blocks.push({ type: "heading", text: match[1] });
    } else if ((match = line.match(/^[-*•]\s+(.+)$/))) {
      flushParagraph();
      addItem(false, match[1]);
    } else if ((match = line.match(/^(\d+)[.)]\s+(.+)$/))) {
      flushParagraph();
      addItem(true, match[2], Number(match[1]));
    } else {
      paragraph.push(line);
    }
  }
  flushParagraph();
  return blocks;
}

function stripBold(text) {
  return text.replace(/^\*\*(.+)\*\*$/, "$1");
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
