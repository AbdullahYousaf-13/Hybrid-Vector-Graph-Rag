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

export function cleanChunk(chunk) {
  return String(chunk ?? "")
    .trim()
    .replace(/^text:\s*/i, "");
}

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
