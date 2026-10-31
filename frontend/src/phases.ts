export const ANALYZE_PHASES = [
  { id: "ingest", label: "Read the file" },
  { id: "prepare_source", label: "Prepare the source" },
  { id: "extract_fields", label: "Extract the deviation" },
  { id: "investigate", label: "5 Whys and fishbone" },
  { id: "identify_causes", label: "Root causes" },
  { id: "evidence_gaps", label: "Evidence gaps" },
  { id: "recommend_capa", label: "CAPA proposals" },
  { id: "assemble", label: "Fill the record" },
] as const
