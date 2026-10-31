/** Keep this check aligned with `backend/app/services/grounding.py`. */

const STOP = new Set([
  "that",
  "this",
  "with",
  "from",
  "were",
  "was",
  "have",
  "been",
  "into",
  "than",
  "then",
  "when",
  "where",
  "which",
  "their",
  "there",
  "about",
  "after",
  "before",
  "during",
  "because",
  "would",
  "could",
  "should",
  "other",
  "only",
  "also",
  "over",
  "under",
  "between",
  "within",
  "using",
  "used",
  "such",
  "batch",
  "result",
  "results",
])

const TOKEN = /[a-z0-9]+(?:-[a-z0-9]+)*/g
const NUMBER = /\d+(?:\.\d+)?/g

export function evidenceGrounded(evidence: string, source: string): boolean {
  const quote = evidence.trim().replace(/\s+/g, " ")
  if (quote.length < 12 || !source.trim()) return false
  const folded = source.toLowerCase()
  if (folded.includes(quote.toLowerCase())) return true
  const numbers = quote.match(NUMBER) ?? []
  if (numbers.some((number) => !folded.includes(number))) return false
  const tokens = [...quote.toLowerCase().matchAll(TOKEN)]
    .map((match) => match[0])
    .filter((token) => token.length >= 4 && !STOP.has(token))
  if (tokens.length < 3) return false
  const sourceTokens = new Set([...folded.matchAll(TOKEN)].map((match) => match[0]))
  const overlap = tokens.filter((token) => sourceTokens.has(token)).length
  return overlap >= 3 && overlap / tokens.length >= 0.45
}
