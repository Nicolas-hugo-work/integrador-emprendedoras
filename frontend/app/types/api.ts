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
