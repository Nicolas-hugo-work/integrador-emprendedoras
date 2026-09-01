from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, model_validator

from app import domain_rules


class ContactRegistration(BaseModel):
    contact_type: Literal["EMAIL", "PHONE"]
    value: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)
    accept_account_terms: bool


class VerifyContactRequest(BaseModel):
    token: str = Field(min_length=32, max_length=200)


class LoginRequest(BaseModel):
    contact: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=12, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=32, max_length=200)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RegistrationResult(BaseModel):
    user_id: str
    verification_token: str | None = None
    message: str


class UserView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str
    locale: str
    timezone: str
    #: Códigos de rol, para mostrar quién es la usuaria.
    roles: list[str] = Field(default_factory=list)
    #: Códigos de permiso, los mismos que verifica `assert_permission`. La
    #: interfaz se condiciona por capacidad y no por un rol adivinado.
    permissions: list[str] = Field(default_factory=list)


class BusinessCreate(BaseModel):
    name: str = Field(min_length=2, max_length=180)
    stage: Literal["IDEA", "STARTUP", "OPERATING", "GROWING", "PAUSED"]
    activity: str = Field(min_length=2, max_length=180)
    department_code: str | None = Field(default=None, max_length=8)
    municipality: str | None = Field(default=None, max_length=120)


class BusinessView(BusinessCreate):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: str


class FinancialMovementCreate(BaseModel):
    business_id: str | None = None
    category_id: str
    movement_type: Literal["INCOME", "EXPENSE", "COST", "TRANSFER"]
    scope: Literal["BUSINESS", "HOUSEHOLD"]
    counter_scope: Literal["BUSINESS", "HOUSEHOLD"] | None = None
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="BOB", pattern=r"^[A-Z]{3}$")
    occurred_on: date
    note: str | None = Field(default=None, max_length=2000)

    @model_validator(mode="after")
    def validate_transfer(self) -> "FinancialMovementCreate":
        domain_rules.validate_transfer(self.movement_type, self.scope, self.counter_scope)
        return self


class FinancialMovementView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    business_id: str | None
    category_id: str
    movement_type: str
    scope: str
    counter_scope: str | None
    amount: Decimal
    currency: str
    occurred_on: date
    note: str | None = None


class CostItemCreate(BaseModel):
    business_id: str
    name: str = Field(min_length=1, max_length=180)
    cost_type: Literal["FIXED", "VARIABLE"]
    amount: Decimal = Field(gt=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="BOB", pattern=r"^[A-Z]{3}$")
    unit: str = Field(min_length=1, max_length=40)
    periodicity: str = Field(min_length=1, max_length=32)
    quantity_base: Decimal = Field(default=Decimal("1"), gt=0, max_digits=14, decimal_places=4)
    notes: str | None = Field(default=None, max_length=2000)


class ConversationCreate(BaseModel):
    business_id: str | None = None
    title: str | None = Field(default=None, max_length=180)
    topic_code: str | None = Field(default=None, max_length=64)


class ConversationView(BaseModel):
    id: str
    business_id: str | None
    title: str | None
    topic_code: str | None
    status: str
    updated_at: datetime


class PricingScenarioCreate(BaseModel):
    business_id: str
    product_name: str = Field(min_length=1, max_length=180)
    units: Decimal = Field(gt=0, max_digits=14, decimal_places=4)
    margin_percent: Decimal = Field(ge=0, le=1000, max_digits=8, decimal_places=4)
    cost_item_ids: list[str] = Field(min_length=1)
    currency: str = Field(default="BOB", pattern=r"^[A-Z]{3}$")


class Citation(BaseModel):
    source_version_id: str
    source_chunk_id: str
    institution: str
    title: str
    url: HttpUrl
    version_or_date: str | None
    consulted_at: datetime


class AssistantQueryRequest(BaseModel):
    conversation_id: str | None = None
    business_id: str | None = None
    message: str = Field(min_length=1, max_length=8000)


class AssistantQueryResponse(BaseModel):
    answer: str
    citations: list[Citation]
    warning: str | None
    abstained: bool
    trace_id: str

    @model_validator(mode="after")
    def normative_answer_requires_evidence(self) -> "AssistantQueryResponse":
        if not self.abstained and self.warning and not self.citations:
            raise ValueError("Una respuesta advertida no puede omitir citas salvo abstención")
        return self


class ConsentDecision(BaseModel):
    purpose_code: Literal["ACCOUNT", "AUDIO", "RESEARCH", "SECONDARY_USE"]
    version: str
    decision: Literal["GRANTED", "WITHDRAWN"]


class FeedbackCreate(BaseModel):
    message_id: str
    feedback_type: Literal["USEFUL", "ERROR", "OUTDATED_SOURCE"]
    comment: str | None = Field(default=None, max_length=2000)


class SourceVersionCreate(BaseModel):
    source_id: str
    version_label: str = Field(min_length=1, max_length=120)
    publication_date: date | None = None
    valid_from: date | None = None
    valid_to: date | None = None
    content_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    storage_key: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_validity(self) -> "SourceVersionCreate":
        if self.valid_from and self.valid_to and self.valid_to < self.valid_from:
            raise ValueError("valid_to no puede ser anterior a valid_from")
        return self


class SourceCreate(BaseModel):
    publisher_id: str
    title: str = Field(min_length=2, max_length=500)
    canonical_url: HttpUrl
    jurisdiction: str = Field(default="Bolivia", max_length=120)
    topic: str = Field(min_length=2, max_length=120)
    license_name: str | None = Field(default=None, max_length=180)


class SourceChunkCreate(BaseModel):
    source_version_id: str
    chunk_number: int = Field(gt=0)
    heading: str | None = Field(default=None, max_length=500)
    content: str = Field(min_length=20)
    page_number: int | None = Field(default=None, gt=0)
    token_count: int = Field(gt=0)


class PublisherView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    code: str
    name: str
    official_domain: str | None
    country_code: str


class SourceView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    publisher_id: str
    publisher_name: str
    title: str
    canonical_url: str
    jurisdiction: str
    topic: str
    license_name: str | None
    status: str


class SourceVersionView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_id: str
    version_label: str
    publication_date: date | None
    consulted_at: datetime
    valid_from: date | None
    valid_to: date | None
    content_hash: str
    storage_key: str
    status: str
    #: Permite a la interfaz saber si la versión puede publicarse: publicar sin
    #: fragmentos responde 409.
    chunk_count: int


class SourceChunkView(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_version_id: str
    chunk_number: int
    heading: str | None
    content: str
    page_number: int | None
    token_count: int


class RetireRequest(BaseModel):
    reason: str = Field(min_length=5, max_length=500)


class DeleteAccountRequest(BaseModel):
    confirmation: Literal["ELIMINAR MI CUENTA"]
