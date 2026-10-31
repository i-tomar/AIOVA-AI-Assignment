import { FISH_CATEGORIES } from "../format"
import type { FishItem } from "../types"

const TOP = [
  { category: "Man", x: 190 },
  { category: "Machine", x: 400 },
  { category: "Method", x: 610 },
] as const

const BOTTOM = [
  { category: "Material", x: 190 },
  { category: "Measurement", x: 400 },
  { category: "Environment", x: 610 },
] as const

const COLOR: Record<string, string> = {
  Man: "#8c4a3a",
  Machine: "#1f4e5f",
  Method: "#3d4f2e",
  Material: "#6b5424",
  Measurement: "#3d3e6b",
  Environment: "#1e5c52",
}

export function Fishbone({ items, problem }: { items: FishItem[]; problem: string }) {
  return (
    <div className="fish-chart">
      <svg viewBox="0 0 980 520" role="img" aria-label="Ishikawa diagram of the six investigation categories">
        <line x1="70" y1="260" x2="800" y2="260" stroke="#1b1914" strokeWidth="3" />
        <polygon points="800,236 860,260 800,284" fill="#0f5e57" />
        {TOP.map((bone) => (
          <Bone key={bone.category} category={bone.category} x={bone.x} upward items={items} />
        ))}
        {BOTTOM.map((bone) => (
          <Bone key={bone.category} category={bone.category} x={bone.x} upward={false} items={items} />
        ))}
        <rect x="868" y="188" width="100" height="144" rx="8" fill="#0f5e57" />
        {wrap(problem || "Problem", 16)
          .slice(0, 6)
          .map((line, index) => (
            <text key={line + index} x="918" y={214 + index * 16} textAnchor="middle" fill="#fbf7f0" fontSize="11">
              {line}
            </text>
          ))}
      </svg>
      <ul className="fish-legend">
        {FISH_CATEGORIES.map((category) => (
          <li key={category}>
            <span style={{ background: COLOR[category] }} />
            {category}
          </li>
        ))}
      </ul>
    </div>
  )
}

function Bone({
  category,
  x,
  upward,
  items,
}: {
  category: string
  x: number
  upward: boolean
  items: FishItem[]
}) {
  const y2 = upward ? 78 : 442
  const causes = items.filter((item) => item.category === category).slice(0, 3)
  const color = COLOR[category] ?? "#1b1914"
  return (
    <g>
      <line x1={x} y1="260" x2={x - 80} y2={y2} stroke={color} strokeWidth="2" />
      <text x={x - 86} y={upward ? 64 : 462} textAnchor="end" fill={color} fontSize="13" fontWeight="600">
        {category}
      </text>
      {causes.map((cause, index) => (
        <text
          key={cause.id}
          x={x - 70}
          y={(upward ? 96 : 400) + (upward ? 1 : -1) * index * 16}
          fill={cause.plausible ? "#1b1914" : "#8a8175"}
          fontSize="11"
          opacity={cause.plausible ? 1 : 0.55}
        >
          {clip(cause.cause, 42)}
        </text>
      ))}
      {causes.length === 0 && (
        <text x={x - 70} y={upward ? 110 : 400} fill="#8a8175" fontSize="11">
          None proposed
        </text>
      )}
    </g>
  )
}

function clip(value: string, length: number): string {
  const text = value.trim() || "—"
  return text.length > length ? `${text.slice(0, length - 1)}…` : text
}

function wrap(value: string, width: number): string[] {
  const words = value.trim().split(/\s+/).filter(Boolean)
  if (words.length === 0) return ["Problem"]
  const lines: string[] = []
  let current = ""
  for (const word of words) {
    const next = current ? `${current} ${word}` : word
    if (next.length > width && current) {
      lines.push(current)
      current = word
    } else {
      current = next
    }
  }
  if (current) lines.push(current)
  return lines
}
