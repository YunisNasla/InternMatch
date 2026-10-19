export type Option = { code: string; label: string }

export type Meta = {
  industries: Option[]
  role_type_groups: { group: string; role_types: Option[] }[]
  work_arrangements: Option[]
  terms: string[]
  last_ingest: string | null
}
