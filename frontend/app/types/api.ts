/**
 * Contratos compartidos con la API.
 *
 * Antes cada página redeclaraba estos tipos por su cuenta, así que un cambio
 * en la respuesta del backend obligaba a corregir cuatro archivos y era fácil
 * que uno quedara desactualizado sin que TypeScript lo notara.
 */

export type TokenPair = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
};

export type Registration = {
  user_id: string;
  verification_token?: string | null;
  message: string;
};

export type User = {
  id: string;
  status: string;
  locale: string;
  timezone: string;
  /** Códigos de rol, para mostrar quién es la usuaria. */
  roles: string[];
  /** Códigos de permiso: los mismos que verifica el backend. */
  permissions: string[];
};

export type BusinessStage =
  | 'IDEA'
  | 'STARTUP'
  | 'OPERATING'
  | 'GROWING'
  | 'PAUSED';

export type Business = {
  id: string;
  name: string;
  stage: BusinessStage;
  activity: string;
  department_code?: string | null;
  municipality?: string | null;
  status: string;
};

export type MovementType = 'INCOME' | 'EXPENSE' | 'COST' | 'TRANSFER';

export type Category = {
  id: string;
  code: string;
  name: string;
  movement_type: MovementType;
};

export type Movement = {
  id: string;
  business_id?: string | null;
  category_id: string;
  movement_type: MovementType;
  scope: string;
  counter_scope?: string | null;
  amount: string;
  currency: string;
  occurred_on: string;
  note?: string | null;
};

export type Summary = {
  income: string;
  outflow: string;
  balance: string;
};

export type Citation = {
  source_version_id: string;
  source_chunk_id: string;
  institution: string;
  title: string;
  url: string;
  version_or_date?: string | null;
  consulted_at: string;
};

export type AssistantAnswer = {
  answer: string;
  citations: Citation[];
  warning?: string | null;
  abstained: boolean;
  trace_id: string;
};

export type ConsentPurpose = 'ACCOUNT' | 'AUDIO' | 'RESEARCH' | 'SECONDARY_USE';

export type ConsentStatus = {
  purpose_code: ConsentPurpose;
  name: string;
  is_required: boolean;
  withdrawal_effect: string;
  /** `null` mientras la usuaria no haya decidido nunca sobre esta finalidad. */
  decision: 'GRANTED' | 'WITHDRAWN' | null;
  version: string | null;
  decided_at: string | null;
  allowed: boolean;
};

export type Publisher = {
  id: string;
  code: string;
  name: string;
  official_domain?: string | null;
  country_code: string;
};

export type SourceStatus = 'DRAFT' | 'IN_REVIEW' | 'PUBLISHED' | 'RETIRED';

export type Source = {
  id: string;
  publisher_id: string;
  publisher_name: string;
  title: string;
  canonical_url: string;
  jurisdiction: string;
  topic: string;
  license_name?: string | null;
  status: SourceStatus;
};

export type SourceVersion = {
  id: string;
  source_id: string;
  version_label: string;
  publication_date?: string | null;
  consulted_at: string;
  valid_from?: string | null;
  valid_to?: string | null;
  content_hash: string;
  storage_key: string;
  status: string;
  chunk_count: number;
};

export type SourceChunk = {
  id: string;
  source_version_id: string;
  chunk_number: number;
  heading?: string | null;
  content: string;
  page_number?: number | null;
  token_count: number;
};

export type AuditEvent = {
  id: string;
  /** Nunca llega el identificador real de quien actuó. */
  actor_pseudonym: string;
  action: string;
  object_type: string;
  object_id?: string | null;
  result: 'SUCCESS' | 'DENIED' | 'FAILED';
  occurred_at: string;
  correlation_id: string;
  integrity_hash: string;
};
