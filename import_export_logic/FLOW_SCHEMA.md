# Rainn Flow Package Schema (flow_definition_v1)

_Added in iteration: 4_

This document defines the portable JSON format for exporting and importing
Rainn flows without any run data. The schema is intentionally minimal and
privacy-first.

## Schema version

`schema_version`: `"rainn.flow.v1"`

## Root object

```json
{
  "schema_version": "rainn.flow.v1",
  "exported_at": "2026-02-03T12:34:56Z",
  "flow": {
    "agent_name": "Invoice Compliance (Visual + Summary)",
    "ai_model": "llama3.1:8b",
    "task_title": "invoice_compliance_visual_text",
    "task_description": "Invoice compliance pipeline with both visual risk chart and written summary.",
    "primer_text": "You are a compliance analyst. Be strict, accurate, and concise.",
    "stages": [
      {
        "order": 1,
        "name": "extract",
        "description": "Extract supplier, invoice number, dates, totals, and line items."
      },
      {
        "order": 2,
        "name": "validate",
        "description": "Check for missing fields, inconsistent totals, and date/payment issues."
      },
      {
        "order": 3,
        "name": "graph",
        "description": "Visualise key risks and totals as a chart (JSON chart spec).",
        "output_format": "graph"
      },
      {
        "order": 4,
        "name": "output",
        "description": "Provide a concise compliance summary and next steps."
      }
    ]
  },
  "source": "rainn",
  "notes": "Optional notes from the exporter."
}
```

## Required fields

- `schema_version` (string): `"rainn.flow.v1"`
- `exported_at` (string, ISO datetime)
- `flow` (object)
  - `agent_name` (string)
  - `ai_model` (string)
  - `task_title` (string)
  - `task_description` (string)
  - `primer_text` (string, optional if empty)
  - `stages` (array, non-empty)
    - `order` (int)
    - `name` (string)
    - `description` (string)
    - `output_format` (string, optional: `graph|csv|json|text`)

## Explicitly excluded (privacy-first)

- TaskInstance / TaskStageInstance
- Input files or file contents
- Artifacts or output_descriptor.json
- Run IDs or runtime logs

## Notes

Flows are reusable definitions only. Runs remain ephemeral in Rainn.
