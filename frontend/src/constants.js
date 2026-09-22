import {
  BookOpen,
  Layers,
  Network,
  PawPrint,
  PencilLine,
  ScanSearch,
  ScrollText,
  Users,
  Wand2,
} from "lucide-react";

/**
 * Retrieval modes exposed by the backend. Tailwind class strings are written
 * out in full (never interpolated) so the compiler can see them.
 */
export const MODES = [
  {
    id: "vector",
    label: "Vector",
    tagline: "Semantic search over the book text",
    blurb: "Embeds the question, pulls the closest passages from the books, and answers from those.",
    icon: ScanSearch,
    card: "border-ravenclaw/60 bg-ravenclaw/5 ring-1 ring-ravenclaw/25",
    iconWrap: "bg-ravenclaw/10 text-ravenclaw",
    accentText: "text-ravenclaw",
    badge: "border-ravenclaw/30 bg-ravenclaw/10 text-ravenclaw",
  },
  {
    id: "graph",
    label: "Graph",
    tagline: "Structured queries over the knowledge graph",
    blurb: "Writes Cypher against the Neo4j graph — best for relationships and precise facts.",
    icon: Network,
    card: "border-slytherin/60 bg-slytherin/5 ring-1 ring-slytherin/25",
    iconWrap: "bg-slytherin/10 text-slytherin",
    accentText: "text-slytherin",
    badge: "border-slytherin/30 bg-slytherin/10 text-slytherin",
  },
  {
    id: "hybrid",
    label: "Hybrid",
    tagline: "Both paths, reconciled into one answer",
    blurb: "Runs vector and graph retrieval, then reconciles the two answers. Costs up to 3 requests.",
    icon: Layers,
    card: "border-gryffindor/60 bg-gryffindor/5 ring-1 ring-gryffindor/25",
    iconWrap: "bg-gryffindor/10 text-gryffindor",
    accentText: "text-gryffindor",
    badge: "border-gryffindor/30 bg-gryffindor/10 text-gryffindor",
  },
];

export const DEFAULT_MODE = "hybrid";

/**
 * "Ask Away" carries no presets — it is the free-form path and the default tab.
 * Every preset question below was verified against this backend.
 */
export const CATEGORIES = [
  {
    id: "ask-away",
    label: "Ask Away",
    icon: PencilLine,
    hint: "No suggestions here — ask anything about the books below.",
    questions: [],
  },
  {
    id: "characters",
    label: "Characters",
    icon: Users,
    questions: [
      { text: "Who is Albus Dumbledore?", mode: "vector" },
      { text: "Who is Severus Snape?", mode: "vector" },
      { text: "Who is Hermione Granger?", mode: "vector" },
      { text: "Who is Ron Weasley?", mode: "vector" },
      { text: "Who are Harry Potter's friends?", mode: "graph" },
      { text: "Who is Draco Malfoy's father?", mode: "graph" },
      { text: "Who is Albus Dumbledore's brother?", mode: "graph" },
      { text: "Who is Sirius Black to Harry Potter?", mode: "hybrid" },
      { text: "Who is Severus Snape loyal to?", mode: "hybrid" },
      { text: "Who are the Dursleys to Harry Potter?", mode: "hybrid" },
    ],
  },
  {
    id: "spells-items",
    label: "Spells & Items",
    icon: Wand2,
    questions: [
      { text: "What does Polyjuice Potion do?", mode: "vector" },
      { text: "What does the Patronus charm do?", mode: "vector" },
      { text: "What is a Horcrux?", mode: "vector" },
      { text: "What is the Sorcerer's Stone?", mode: "vector" },
      { text: "What does Albus Dumbledore own?", mode: "graph" },
      { text: "Who created the Marauder's Map?", mode: "graph" },
      { text: "Who owns the Elder Wand?", mode: "graph" },
      { text: "What is the Elder Wand and who has owned it?", mode: "hybrid" },
      { text: "Who made the Marauder's Map and what does it do?", mode: "hybrid" },
      { text: "Who owns the Invisibility Cloak and what does it do?", mode: "hybrid" },
    ],
  },
  {
    id: "creatures",
    label: "Magical Creatures",
    icon: PawPrint,
    questions: [
      { text: "What is a hippogriff?", mode: "vector" },
      { text: "What is a dementor?", mode: "vector" },
      { text: "What is a house-elf?", mode: "vector" },
      { text: "What is a phoenix?", mode: "vector" },
      { text: "Who is Hedwig's owner?", mode: "graph" },
      { text: "Who owns Crookshanks?", mode: "graph" },
      { text: "Who killed the basilisk?", mode: "graph" },
      { text: "What is Fawkes and who does he belong to?", mode: "hybrid" },
      { text: "What is a basilisk and who killed it?", mode: "hybrid" },
      { text: "What is Scabbers and who owns him?", mode: "hybrid" },
    ],
  },
  {
    id: "history",
    label: "History",
    icon: ScrollText,
    questions: [
      { text: "Who founded Hogwarts?", mode: "vector" },
      { text: "How did Harry's parents die?", mode: "vector" },
      { text: "What happened to Cedric Diggory?", mode: "vector" },
      { text: "What happened at the Triwizard Tournament?", mode: "vector" },
      { text: "Who is the head of Gryffindor?", mode: "graph" },
      { text: "Who works at Hogwarts?", mode: "graph" },
      { text: "Who is a member of the Ministry of Magic?", mode: "graph" },
      { text: "What is the Order of the Phoenix and who belongs to it?", mode: "hybrid" },
      { text: "Who leads Hogwarts and what is it?", mode: "hybrid" },
      { text: "What is the Chamber of Secrets and who opened it?", mode: "hybrid" },
    ],
  },
];

export const CORPUS_ICON = BookOpen;

/** Backend guardrail: questions over 300 characters are rejected with a 400. */
export const MAX_QUESTION_LENGTH = 300;
