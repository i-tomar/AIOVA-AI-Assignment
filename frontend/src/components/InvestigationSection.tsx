import { evidenceGrounded } from "../grounding"
import { FISH_CATEGORIES } from "../format"
import { hasPendingFacts } from "../record"
import { useAppDispatch, useAppSelector } from "../store/hooks"
import { addBlank, confirmItem, confirmTracked, removeItem, updateItem, updateTracked } from "../store/investigationSlice"
import type { FishItem, TrackedKey, WhyStep } from "../types"
import { Fishbone } from "./Fishbone"
import { Badge, Field, Section } from "./ui"

const METHOD_KEYS: TrackedKey[] = ["method", "method_notes", "problem_statement"]

export function InvestigationSection() {
  const dispatch = useAppDispatch()
  const record = useAppSelector((state) => state.investigation.record)
  const highlighted = useAppSelector((state) => state.investigation.highlighted)
  const reviewer = record.prepared_by.value.trim() || "qualified reviewer"
  const onChange = (path: TrackedKey, value: string) => dispatch(updateTracked({ path, value }))
  const onConfirm = (path: TrackedKey) => dispatch(confirmTracked({ paths: [path] }))
  const source = record.source.raw_text
  const other = record.fishbone.filter((item) => !FISH_CATEGORIES.includes(item.category as (typeof FISH_CATEGORIES)[number]))

  return (
    <Section
      id="investigation"
      index="05"
      title="Investigation"
      lede="5 Whys follows one causal chain. The fishbone checks the six manufacturing categories so a single chain does not hide a second failure."
      onAccept={hasPendingFacts(record, METHOD_KEYS) ? () => dispatch(confirmTracked({ paths: METHOD_KEYS })) : undefined}
    >
      <Field
        label="Method"
        path="method"
        tracked={record.method}
        highlighted={highlighted.includes("method")}
        onChange={onChange}
        onConfirm={onConfirm}
      />
      <Field
        label="Why this method"
        path="method_notes"
        tracked={record.method_notes}
        multiline
        rows={3}
        highlighted={highlighted.includes("method_notes")}
        onChange={onChange}
        onConfirm={onConfirm}
      />
      <Field
        label="Problem statement"
        path="problem_statement"
        tracked={record.problem_statement}
        multiline
        rows={2}
        highlighted={highlighted.includes("problem_statement")}
        onChange={onChange}
        onConfirm={onConfirm}
      />

      <div className="block-head">
        <h3>Investigation team</h3>
        <button type="button" className="text-btn" onClick={() => dispatch(addBlank({ collection: "team" }))}>
          Add a person
        </button>
      </div>
      {record.team.length === 0 && <p className="hint">Only people named in the source should appear here.</p>}
      <div className="stack">
        {record.team.map((member) => (
          <div key={member.id} className={`card compact ${highlighted.includes("team") ? "is-fresh" : ""}`}>
            <div className="grid-3">
              <label>
                Name
                <input
                  value={member.name}
                  onChange={(event) =>
                    dispatch(updateItem({ collection: "team", id: member.id, patch: { name: event.target.value } }))
                  }
                />
              </label>
              <label>
                Role
                <input
                  value={member.role}
                  onChange={(event) =>
                    dispatch(updateItem({ collection: "team", id: member.id, patch: { role: event.target.value } }))
                  }
                />
              </label>
              <label>
                Department
                <input
                  value={member.department}
                  onChange={(event) =>
                    dispatch(
                      updateItem({ collection: "team", id: member.id, patch: { department: event.target.value } }),
                    )
                  }
                />
              </label>
            </div>
            <div className="card-actions">
              {member.origin === "ai" && !member.confirmed && <Badge tone="ai">AI extracted</Badge>}
              <button type="button" className="text-btn" onClick={() => dispatch(removeItem({ collection: "team", id: member.id }))}>
                Remove
              </button>
            </div>
          </div>
        ))}
      </div>

      <div className="block-head">
        <h3>5 Whys</h3>
        <button type="button" className="text-btn" onClick={() => dispatch(addBlank({ collection: "whys" }))}>
          Add a why
        </button>
      </div>
      {record.whys.length === 0 && (
        <p className="hint">The why-chain is drafted from the source. Add or remove steps after you review it.</p>
      )}
      <ol className="whys">
        {record.whys.map((step, index) => (
          <WhyCard
            key={step.id}
            step={step}
            index={index}
            fresh={highlighted.includes(`why:${step.id}`)}
            grounded={evidenceGrounded(step.evidence, source)}
            onPatch={(patch) => dispatch(updateItem({ collection: "whys", id: step.id, patch }))}
            onConfirm={() =>
              dispatch(confirmItem({ collection: "whys", id: step.id, confirmed: !step.confirmed, by: reviewer }))
            }
            onRemove={() => dispatch(removeItem({ collection: "whys", id: step.id }))}
          />
        ))}
      </ol>

      <div className="block-head">
        <h3>Fishbone — 6M</h3>
        <button type="button" className="text-btn" onClick={() => dispatch(addBlank({ collection: "fishbone" }))}>
          Add a cause
        </button>
      </div>
      <Fishbone items={record.fishbone} problem={record.problem_statement.value} />
      {FISH_CATEGORIES.map((category) => {
        const rows = record.fishbone.filter((item) => item.category === category)
        if (rows.length === 0) return null
        return (
          <FishGroup
            key={category}
            category={category}
            rows={rows}
            highlighted={highlighted}
            source={source}
            reviewer={reviewer}
          />
        )
      })}
      {other.length > 0 && (
        <FishGroup category="Other" rows={other} highlighted={highlighted} source={source} reviewer={reviewer} />
      )}
    </Section>
  )
}

function WhyCard({
  step,
  index,
  fresh,
  grounded,
  onPatch,
  onConfirm,
  onRemove,
}: {
  step: WhyStep
  index: number
  fresh: boolean
  grounded: boolean
  onPatch: (patch: Record<string, string | boolean>) => void
  onConfirm: () => void
  onRemove: () => void
}) {
  const canConfirm = step.evidence.trim().length > 0
  return (
    <li className={`card ${fresh ? "is-fresh" : ""}`} data-ai-fresh={fresh ? "true" : undefined}>
      <div className="why-layout">
        <span className="why-index">{index + 1}</span>
        <div>
          <input
            aria-label={`Why ${index + 1} question`}
            value={step.question}
            onChange={(event) => onPatch({ question: event.target.value, confirmed: false })}
          />
          <textarea
            aria-label={`Why ${index + 1} answer`}
            rows={3}
            value={step.answer}
            onChange={(event) => onPatch({ answer: event.target.value, confirmed: false })}
          />
          <label className="sub">
            Evidence
            <input
              value={step.evidence}
              placeholder="Fact from the source"
              onChange={(event) => onPatch({ evidence: event.target.value, confirmed: false })}
            />
          </label>
          <div className="card-actions">
            {step.origin === "ai" && !step.confirmed && <Badge tone="ai">AI suggested</Badge>}
            {step.confirmed && <Badge tone="ok">Confirmed</Badge>}
            {step.evidence.trim() &&
              (grounded ? <Badge tone="ok">In source</Badge> : <Badge tone="warn">Not in source</Badge>)}
            <button type="button" className="text-btn" disabled={!canConfirm && !step.confirmed} onClick={onConfirm}>
              {step.confirmed ? "Confirmed" : "Confirm"}
            </button>
            <button type="button" className="text-btn" onClick={onRemove}>
              Remove
            </button>
          </div>
          {!canConfirm && <p className="hint">Add an evidence note before confirming this step.</p>}
        </div>
      </div>
    </li>
  )
}

function FishGroup({
  category,
  rows,
  highlighted,
  source,
  reviewer,
}: {
  category: string
  rows: FishItem[]
  highlighted: string[]
  source: string
  reviewer: string
}) {
  const dispatch = useAppDispatch()
  return (
    <div className="fish-group">
      <h4>{category}</h4>
      {rows.map((item) => {
        const grounded = evidenceGrounded(item.evidence, source)
        const fresh = highlighted.includes(`fish:${item.id}`)
        return (
          <article key={item.id} className={`card ${fresh ? "is-fresh" : ""}`} data-ai-fresh={fresh ? "true" : undefined}>
            <textarea
              aria-label={`${category} cause`}
              rows={2}
              value={item.cause}
              onChange={(event) =>
                dispatch(
                  updateItem({
                    collection: "fishbone",
                    id: item.id,
                    patch: { cause: event.target.value, confirmed: false },
                  }),
                )
              }
            />
            <label className="sub">
              Evidence
              <input
                value={item.evidence}
                onChange={(event) =>
                  dispatch(
                    updateItem({
                      collection: "fishbone",
                      id: item.id,
                      patch: { evidence: event.target.value, confirmed: false },
                    }),
                  )
                }
              />
            </label>
            <div className="card-actions">
              <label className="check">
                <input
                  type="checkbox"
                  checked={item.plausible}
                  onChange={(event) =>
                    dispatch(
                      updateItem({ collection: "fishbone", id: item.id, patch: { plausible: event.target.checked } }),
                    )
                  }
                />
                Still plausible
              </label>
              <select
                aria-label="Category"
                value={item.category}
                onChange={(event) =>
                  dispatch(updateItem({ collection: "fishbone", id: item.id, patch: { category: event.target.value } }))
                }
              >
                {FISH_CATEGORIES.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
              {item.origin === "ai" && !item.confirmed && <Badge tone="ai">AI suggested</Badge>}
              {item.confirmed && <Badge tone="ok">Confirmed</Badge>}
              {item.evidence.trim() &&
                (grounded ? <Badge tone="ok">In source</Badge> : <Badge tone="warn">Not in source</Badge>)}
              <button
                type="button"
                className="text-btn"
                disabled={!item.evidence.trim() && !item.confirmed}
                onClick={() =>
                  dispatch(
                    confirmItem({ collection: "fishbone", id: item.id, confirmed: !item.confirmed, by: reviewer }),
                  )
                }
              >
                {item.confirmed ? "Confirmed" : "Confirm"}
              </button>
              <button type="button" className="text-btn" onClick={() => dispatch(removeItem({ collection: "fishbone", id: item.id }))}>
                Remove
              </button>
            </div>
          </article>
        )
      })}
    </div>
  )
}
