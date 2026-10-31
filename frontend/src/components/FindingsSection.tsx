import { evidenceGrounded } from "../grounding"
import { CAPA_STATUS_LABEL, CONFIDENCE_LABEL, FISH_CATEGORIES, causeBadge } from "../format"
import { useAppDispatch, useAppSelector } from "../store/hooks"
import {
  addBlank,
  confirmItem,
  markApproved,
  markReturned,
  patchApproval,
  removeItem,
  setStatus,
  updateItem,
} from "../store/investigationSlice"
import type { Cause, ItemCollection } from "../types"
import { Badge, Section } from "./ui"

const CATEGORIES = [...FISH_CATEGORIES, "Other"]

export function FindingsSections() {
  const dispatch = useAppDispatch()
  const record = useAppSelector((state) => state.investigation.record)
  const highlighted = useAppSelector((state) => state.investigation.highlighted)
  const reviewer = record.prepared_by.value.trim() || record.approval.reviewer_name.trim() || "qualified reviewer"
  const canApprove = record.approval.reviewer_name.trim().length > 0 && record.approval.acknowledged_ai_review
  const openCauses = record.root_causes.filter((cause) => !(cause.confirmed && cause.evidence.trim())).length

  return (
    <>
      <Section
        id="causes"
        index="06"
        title="Root causes and contributing factors"
        lede="A suggestion is not an established cause. Confirm it only when the evidence note is something you accept. The source check looks for that note in the uploaded document; you may still confirm evidence that came from an interview or a record outside the file."
      >
        <p className="callout">
          {openCauses === 0 && record.root_causes.length > 0
            ? "Every root-cause line has been confirmed or none were proposed."
            : `${openCauses} root-cause ${openCauses === 1 ? "hypothesis remains" : "hypotheses remain"} unconfirmed.`}
        </p>
        <CauseColumn
          title="Probable root causes"
          collection="root_causes"
          items={record.root_causes}
          highlighted={highlighted}
          source={record.source.raw_text}
          reviewer={reviewer}
          freshPrefix="cause"
        />
        <CauseColumn
          title="Contributing factors"
          collection="contributing_factors"
          items={record.contributing_factors}
          highlighted={highlighted}
          source={record.source.raw_text}
          reviewer={reviewer}
          freshPrefix="factor"
        />
      </Section>

      <Section
        id="gaps"
        index="07"
        title="Evidence still missing"
        lede="What a qualified investigator would collect before disposing of the batch or closing the cause."
      >
        <div className="block-head">
          <h3>Gaps</h3>
          <button type="button" className="text-btn" onClick={() => dispatch(addBlank({ collection: "gaps" }))}>
            Add a gap
          </button>
        </div>
        {record.gaps.length === 0 && <p className="hint">No gaps have been listed.</p>}
        <div className="stack">
          {record.gaps.map((gap) => {
            const fresh = highlighted.includes(`gap:${gap.id}`)
            return (
              <article key={gap.id} className={`card ${fresh ? "is-fresh" : ""} ${gap.resolved ? "resolved" : ""}`} data-ai-fresh={fresh ? "true" : undefined}>
                <input
                  aria-label="Gap topic"
                  value={gap.topic}
                  onChange={(event) =>
                    dispatch(updateItem({ collection: "gaps", id: gap.id, patch: { topic: event.target.value } }))
                  }
                />
                <textarea
                  aria-label="Why this gap matters"
                  rows={2}
                  value={gap.why_it_matters}
                  onChange={(event) =>
                    dispatch(
                      updateItem({ collection: "gaps", id: gap.id, patch: { why_it_matters: event.target.value } }),
                    )
                  }
                />
                <label className="sub">
                  Where to get it
                  <input
                    value={gap.suggested_source}
                    onChange={(event) =>
                      dispatch(
                        updateItem({
                          collection: "gaps",
                          id: gap.id,
                          patch: { suggested_source: event.target.value },
                        }),
                      )
                    }
                  />
                </label>
                <div className="card-actions">
                  {gap.origin === "ai" && <Badge tone="ai">AI suggested</Badge>}
                  <label className="check">
                    <input
                      type="checkbox"
                      checked={gap.resolved}
                      onChange={(event) =>
                        dispatch(updateItem({ collection: "gaps", id: gap.id, patch: { resolved: event.target.checked } }))
                      }
                    />
                    Resolved
                  </label>
                  <button type="button" className="text-btn" onClick={() => dispatch(removeItem({ collection: "gaps", id: gap.id }))}>
                    Remove
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      </Section>

      <Section
        id="capa"
        index="08"
        title="CAPA"
        lede="Corrective action deals with this event. Preventive action changes the system so the next batch does not repeat it. A proposal stays marked until you accept it."
      >
        <div className="block-head">
          <h3>Actions</h3>
          <button type="button" className="text-btn" onClick={() => dispatch(addBlank({ collection: "capas" }))}>
            Add a CAPA
          </button>
        </div>
        {record.capas.length === 0 && <p className="hint">No actions have been proposed.</p>}
        <div className="stack">
          {record.capas.map((capa) => {
            const fresh = highlighted.includes(`capa:${capa.id}`)
            return (
              <article key={capa.id} className={`card ${fresh ? "is-fresh" : ""}`} data-ai-fresh={fresh ? "true" : undefined}>
                <div className="card-actions">
                  <select
                    aria-label="CAPA type"
                    value={capa.capa_type}
                    onChange={(event) =>
                      dispatch(updateItem({ collection: "capas", id: capa.id, patch: { capa_type: event.target.value } }))
                    }
                  >
                    <option value="corrective">Corrective</option>
                    <option value="preventive">Preventive</option>
                  </select>
                  <select
                    aria-label="CAPA status"
                    value={capa.status}
                    onChange={(event) =>
                      dispatch(updateItem({ collection: "capas", id: capa.id, patch: { status: event.target.value } }))
                    }
                  >
                    {Object.entries(CAPA_STATUS_LABEL).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                  {capa.ai_suggested && !capa.confirmed && <Badge tone="ai">AI suggested</Badge>}
                  {capa.confirmed && <Badge tone="ok">Accepted</Badge>}
                </div>
                <label className="sub">
                  Action
                  <textarea
                    rows={3}
                    value={capa.description}
                    onChange={(event) =>
                      dispatch(
                        updateItem({ collection: "capas", id: capa.id, patch: { description: event.target.value } }),
                      )
                    }
                  />
                </label>
                <label className="sub">
                  Rationale
                  <textarea
                    rows={2}
                    value={capa.rationale}
                    onChange={(event) =>
                      dispatch(updateItem({ collection: "capas", id: capa.id, patch: { rationale: event.target.value } }))
                    }
                  />
                </label>
                <div className="grid-2">
                  <label className="sub">
                    Owner role
                    <input
                      value={capa.owner}
                      onChange={(event) =>
                        dispatch(updateItem({ collection: "capas", id: capa.id, patch: { owner: event.target.value } }))
                      }
                    />
                  </label>
                  <label className="sub">
                    Due date
                    <input
                      type="date"
                      value={capa.due_date}
                      onChange={(event) =>
                        dispatch(updateItem({ collection: "capas", id: capa.id, patch: { due_date: event.target.value } }))
                      }
                    />
                  </label>
                </div>
                <label className="sub">
                  Effectiveness check
                  <textarea
                    rows={2}
                    value={capa.effectiveness_check}
                    onChange={(event) =>
                      dispatch(
                        updateItem({
                          collection: "capas",
                          id: capa.id,
                          patch: { effectiveness_check: event.target.value },
                        }),
                      )
                    }
                  />
                </label>
                <div className="card-actions">
                  <button
                    type="button"
                    className="text-btn"
                    onClick={() =>
                      dispatch(confirmItem({ collection: "capas", id: capa.id, confirmed: !capa.confirmed, by: reviewer }))
                    }
                  >
                    {capa.confirmed ? "Accepted" : "Accept proposal"}
                  </button>
                  <button type="button" className="text-btn" onClick={() => dispatch(removeItem({ collection: "capas", id: capa.id }))}>
                    Remove
                  </button>
                </div>
              </article>
            )
          })}
        </div>
      </Section>

      <Section
        id="approval"
        index="09"
        title="QA review"
        lede="Approval means a named reviewer has looked at the suggestions. It does not turn an unconfirmed hypothesis into an established root cause."
      >
        <div className="grid-2">
          <label className="sub">
            Reviewer name
            <input
              value={record.approval.reviewer_name}
              onChange={(event) => dispatch(patchApproval({ reviewer_name: event.target.value }))}
            />
          </label>
          <label className="sub">
            Role
            <input
              value={record.approval.reviewer_role}
              onChange={(event) => dispatch(patchApproval({ reviewer_role: event.target.value }))}
            />
          </label>
        </div>
        <label className="sub">
          Review comment
          <textarea
            rows={3}
            value={record.approval.comment}
            onChange={(event) => dispatch(patchApproval({ comment: event.target.value }))}
          />
        </label>
        <label className="check acknowledge">
          <input
            type="checkbox"
            checked={record.approval.acknowledged_ai_review}
            onChange={(event) => {
              dispatch(patchApproval({ acknowledged_ai_review: event.target.checked }))
              if (!event.target.checked && record.status === "approved") dispatch(setStatus("pending_qa"))
            }}
          />
          <span>
            I have reviewed every AI suggestion. Unconfirmed items are not established root causes, and I am
            authorised to sign this investigation.
          </span>
        </label>
        <div className="card-actions">
          <button type="button" className="primary" disabled={!canApprove} onClick={() => dispatch(markApproved())}>
            Approve and sign
          </button>
          <button type="button" className="quiet" onClick={() => dispatch(markReturned())}>
            Return to investigation
          </button>
        </div>
        {!canApprove && (
          <p className="hint">Enter the reviewer name and acknowledge the AI review before signing.</p>
        )}
        {record.approval.signed_at && (
          <p className="hint">
            Signed {new Date(record.approval.signed_at).toLocaleString()} by {record.approval.reviewer_name}. Save to
            record the signature if you have just approved.
          </p>
        )}
        {record.status === "approved" && !record.approval.signed_at && (
          <p className="hint">Save the investigation to record the signature time.</p>
        )}
      </Section>
    </>
  )
}

function CauseColumn({
  title,
  collection,
  items,
  highlighted,
  source,
  reviewer,
  freshPrefix,
}: {
  title: string
  collection: ItemCollection
  items: Cause[]
  highlighted: string[]
  source: string
  reviewer: string
  freshPrefix: string
}) {
  const dispatch = useAppDispatch()
  return (
    <div className="cause-column">
      <div className="block-head">
        <h3>{title}</h3>
        <button type="button" className="text-btn" onClick={() => dispatch(addBlank({ collection }))}>
          Add
        </button>
      </div>
      {items.length === 0 && <p className="hint">None listed.</p>}
      <div className="stack">
        {items.map((cause) => {
          const fresh = highlighted.includes(`${freshPrefix}:${cause.id}`)
          const grounded = evidenceGrounded(cause.evidence, source)
          const badge = causeBadge(cause)
          return (
            <article key={cause.id} className={`card ${fresh ? "is-fresh" : ""}`} data-ai-fresh={fresh ? "true" : undefined}>
              <div className="card-actions">
                <select
                  aria-label="Category"
                  value={cause.category}
                  onChange={(event) =>
                    dispatch(updateItem({ collection, id: cause.id, patch: { category: event.target.value } }))
                  }
                >
                  {CATEGORIES.map((name) => (
                    <option key={name} value={name}>
                      {name}
                    </option>
                  ))}
                </select>
                <select
                  aria-label="Confidence"
                  value={cause.confidence}
                  onChange={(event) =>
                    dispatch(updateItem({ collection, id: cause.id, patch: { confidence: event.target.value } }))
                  }
                >
                  {Object.entries(CONFIDENCE_LABEL).map(([value, label]) => (
                    <option key={value} value={value}>
                      {label}
                    </option>
                  ))}
                </select>
                <Badge tone={badge.tone}>{badge.label}</Badge>
                {cause.evidence.trim() &&
                  (grounded ? <Badge tone="ok">In source</Badge> : <Badge tone="warn">Not in source</Badge>)}
              </div>
              <textarea
                aria-label="Cause statement"
                rows={3}
                value={cause.statement}
                onChange={(event) =>
                  dispatch(
                    updateItem({
                      collection,
                      id: cause.id,
                      patch: { statement: event.target.value, confirmed: false },
                    }),
                  )
                }
              />
              <label className="sub">
                Evidence
                <textarea
                  rows={2}
                  value={cause.evidence}
                  onChange={(event) =>
                    dispatch(
                      updateItem({
                        collection,
                        id: cause.id,
                        patch: { evidence: event.target.value, confirmed: false },
                      }),
                    )
                  }
                />
              </label>
              {cause.confirmed && cause.ai_suggested && (
                <p className="hint">Proposed by the assistant{cause.confirmed_by ? `, confirmed by ${cause.confirmed_by}` : ""}.</p>
              )}
              <div className="card-actions">
                <button
                  type="button"
                  className="text-btn"
                  disabled={!cause.evidence.trim() && !cause.confirmed}
                  onClick={() =>
                    dispatch(confirmItem({ collection, id: cause.id, confirmed: !cause.confirmed, by: reviewer }))
                  }
                >
                  {cause.confirmed ? "Confirmed" : "Confirm as established"}
                </button>
                <button type="button" className="text-btn" onClick={() => dispatch(removeItem({ collection, id: cause.id }))}>
                  Remove
                </button>
              </div>
              {!cause.evidence.trim() && (
                <p className="hint">Add an evidence note before confirming this as an established cause.</p>
              )}
            </article>
          )
        })}
      </div>
    </div>
  )
}
