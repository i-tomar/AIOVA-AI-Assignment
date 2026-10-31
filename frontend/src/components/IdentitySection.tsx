import { hasPendingFacts } from "../record"
import { useAppDispatch, useAppSelector } from "../store/hooks"
import { confirmTracked, updateTracked } from "../store/investigationSlice"
import type { TrackedKey } from "../types"
import { Field, Section } from "./ui"

const IDENTITY: TrackedKey[] = [
  "deviation_number",
  "title",
  "occurred_at",
  "detected_at",
  "site",
  "area",
  "equipment",
]
const PRODUCT: TrackedKey[] = ["product_name", "batch_lot", "process_stage", "batch_disposition"]
const NARRATIVE: TrackedKey[] = ["description", "immediate_actions"]
const IMPACT: TrackedKey[] = [
  "impact_product_quality",
  "impact_patient_safety",
  "impact_regulatory",
  "severity",
  "severity_rationale",
]

const SEVERITY_OPTIONS = [
  { value: "critical", label: "Critical" },
  { value: "major", label: "Major" },
  { value: "minor", label: "Minor" },
  { value: "unknown", label: "Not yet classified" },
]

export function IdentitySections() {
  const dispatch = useAppDispatch()
  const record = useAppSelector((state) => state.investigation.record)
  const highlighted = useAppSelector((state) => state.investigation.highlighted)
  const onChange = (path: TrackedKey, value: string) => dispatch(updateTracked({ path, value }))
  const onConfirm = (path: TrackedKey) => dispatch(confirmTracked({ paths: [path] }))
  const accept = (paths: TrackedKey[]) => dispatch(confirmTracked({ paths }))
  const fresh = (path: TrackedKey) => highlighted.includes(path)
  return (
    <>
      <Section
        id="identity"
        index="01"
        title="Identification"
        lede="Where and when the deviation happened. Accept a fact once you have checked it against the source."
        onAccept={hasPendingFacts(record, IDENTITY) ? () => accept(IDENTITY) : undefined}
      >
        <div className="grid-2">
          <Field label="Deviation number" path="deviation_number" tracked={record.deviation_number} highlighted={fresh("deviation_number")} onChange={onChange} onConfirm={onConfirm} />
          <Field label="Title" path="title" tracked={record.title} highlighted={fresh("title")} onChange={onChange} onConfirm={onConfirm} />
          <Field label="Occurred" path="occurred_at" tracked={record.occurred_at} hint="Date and time the event happened, as written in the source." highlighted={fresh("occurred_at")} onChange={onChange} onConfirm={onConfirm} />
          <Field label="Detected" path="detected_at" tracked={record.detected_at} highlighted={fresh("detected_at")} onChange={onChange} onConfirm={onConfirm} />
          <Field label="Site" path="site" tracked={record.site} highlighted={fresh("site")} onChange={onChange} onConfirm={onConfirm} />
          <Field label="Area" path="area" tracked={record.area} highlighted={fresh("area")} onChange={onChange} onConfirm={onConfirm} />
        </div>
        <Field label="Equipment" path="equipment" tracked={record.equipment} multiline rows={2} highlighted={fresh("equipment")} onChange={onChange} onConfirm={onConfirm} />
      </Section>

      <Section
        id="product"
        index="02"
        title="Product and process"
        lede="The API, the batch, and the stage that was running."
        onAccept={hasPendingFacts(record, PRODUCT) ? () => accept(PRODUCT) : undefined}
      >
        <div className="grid-2">
          <Field label="Product" path="product_name" tracked={record.product_name} highlighted={fresh("product_name")} onChange={onChange} onConfirm={onConfirm} />
          <Field label="Batch / lot" path="batch_lot" tracked={record.batch_lot} highlighted={fresh("batch_lot")} onChange={onChange} onConfirm={onConfirm} />
          <Field label="Process stage" path="process_stage" tracked={record.process_stage} highlighted={fresh("process_stage")} onChange={onChange} onConfirm={onConfirm} />
          <Field label="Batch disposition" path="batch_disposition" tracked={record.batch_disposition} hint="Quarantine, hold, reject, or still to be decided." highlighted={fresh("batch_disposition")} onChange={onChange} onConfirm={onConfirm} />
        </div>
      </Section>

      <Section
        id="narrative"
        index="03"
        title="What happened"
        lede="The event itself, then the containment already taken. Corrective and preventive actions come later."
        onAccept={hasPendingFacts(record, NARRATIVE) ? () => accept(NARRATIVE) : undefined}
      >
        <Field label="Description" path="description" tracked={record.description} multiline rows={6} highlighted={fresh("description")} onChange={onChange} onConfirm={onConfirm} />
        <Field label="Immediate actions" path="immediate_actions" tracked={record.immediate_actions} multiline rows={4} hint="Containment already done: quarantine, equipment tagged out, samples pulled." highlighted={fresh("immediate_actions")} onChange={onChange} onConfirm={onConfirm} />
      </Section>

      <Section
        id="impact"
        index="04"
        title="Impact and classification"
        lede="Critical means patient exposure, a released failing batch, or a data-integrity failure that undermines disposition. Major is a contained specification or process failure. Minor is procedural, with no product impact."
        onAccept={hasPendingFacts(record, IMPACT) ? () => accept(IMPACT) : undefined}
      >
        <Field label="Product quality" path="impact_product_quality" tracked={record.impact_product_quality} multiline highlighted={fresh("impact_product_quality")} onChange={onChange} onConfirm={onConfirm} />
        <Field label="Patient safety" path="impact_patient_safety" tracked={record.impact_patient_safety} multiline highlighted={fresh("impact_patient_safety")} onChange={onChange} onConfirm={onConfirm} />
        <Field label="Regulatory" path="impact_regulatory" tracked={record.impact_regulatory} multiline highlighted={fresh("impact_regulatory")} onChange={onChange} onConfirm={onConfirm} />
        <div className="grid-2">
          <Field label="Classification" path="severity" tracked={record.severity} options={SEVERITY_OPTIONS} highlighted={fresh("severity")} onChange={onChange} onConfirm={onConfirm} />
          <Field label="Why this class" path="severity_rationale" tracked={record.severity_rationale} multiline rows={3} highlighted={fresh("severity_rationale")} onChange={onChange} onConfirm={onConfirm} />
        </div>
      </Section>
    </>
  )
}
