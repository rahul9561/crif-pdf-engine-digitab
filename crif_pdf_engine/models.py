"""Tolerant Pydantic v2 models for the Digitap CRIF "B2C-REPORT" JSON.

Design rules:
* Unknown keys are ignored; every field is optional with a safe default.
* Scalars are coerced to ``str`` (``None`` -> ``""``, ``0`` -> ``"0"``).
* Lists accept ``None`` (-> ``[]``) or a single object (-> ``[obj]``), a common
  artefact of XML->JSON conversion.
* Nested objects accept ``None`` / ``""`` (-> defaults).
JSON keys are UPPER-KEBAB (``ACCT-NUMBER``); fields are snake_case (``acct_number``).
"""

from __future__ import annotations

from typing import Annotated, Any, TypeVar

from pydantic import BaseModel, BeforeValidator, ConfigDict, Field


def _alias(name: str) -> str:
    return name.upper().replace("_", "-")


def _to_str(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Y" if value else "N"
    if isinstance(value, (dict, list)):
        return ""
    return str(value)


def _to_list(value: Any) -> list:
    if value is None or value == "":
        return []
    if isinstance(value, dict):
        return [value]
    if isinstance(value, (list, tuple)):
        return [v for v in value if v is not None]
    return []


def _to_obj(value: Any) -> Any:
    return {} if value is None or value == "" or isinstance(value, (str, list)) else value


Str = Annotated[str, BeforeValidator(_to_str)]
T = TypeVar("T")
List = Annotated[list[T], BeforeValidator(_to_list)]


class _Model(BaseModel):
    model_config = ConfigDict(
        extra="ignore", populate_by_name=True, alias_generator=_alias, frozen=True
    )


def obj(model: type[BaseModel]):
    """Field for a nested object that may be missing or null."""
    return Field(default_factory=model)


# --------------------------------------------------------------------------- #
# HEADER-SEGMENT
# --------------------------------------------------------------------------- #
class HeaderSegment(_Model):
    date_of_request: Str = ""
    prepared_for: Str = ""
    prepared_for_id: Str = ""
    date_of_issue: Str = ""
    report_id: Str = ""
    batch_id: Str = ""
    status: Str = ""
    product_type: Str = ""
    product_ver: Str = ""


# --------------------------------------------------------------------------- #
# REQUEST-DATA
# --------------------------------------------------------------------------- #
class Dob(_Model):
    dob_dt: Str = ""
    age: Str = ""
    age_as_on: Str = ""


class TypedValue(_Model):
    type: Str = ""
    value: Str = ""


class Address(_Model):
    type: Str = ""
    addresstext: Str = ""
    city: Str = ""
    locality: Str = ""
    state: Str = ""
    pin: Str = ""
    country: Str = ""


class Email(_Model):
    email: Str = ""


class ApplicantSegment(_Model):
    first_name: Str = ""
    middle_name: Str = ""
    last_name: Str = ""
    gender: Str = ""
    applicant_id: Str = ""
    dob: Annotated[Dob, BeforeValidator(_to_obj)] = obj(Dob)
    ids: List[TypedValue] = []
    addresses: List[Address] = []
    phones: List[TypedValue] = []
    emails: List[Email] = []
    account_number: Str = ""


class RequestData(_Model):
    applicant_segment: Annotated[ApplicantSegment, BeforeValidator(_to_obj)] = obj(
        ApplicantSegment
    )


# --------------------------------------------------------------------------- #
# STANDARD-DATA
# --------------------------------------------------------------------------- #
class Variation(_Model):
    value: Str = ""
    reported_dt: Str = ""
    first_reported_dt: Str = ""
    loan_type_assoc: Str = ""
    source_indicator: Str = ""


class VariationGroup(_Model):
    type: Str = ""
    variation: List[Variation] = []


class Demogs(_Model):
    variations: List[VariationGroup] = []


class EmploymentDetail(_Model):
    occupation: Str = ""
    first_reported_dt: Str = ""
    last_reported_dt: Str = ""
    acct_type: Str = ""
    source_indicator: Str = ""


class EmploymentWrapper(_Model):
    employment_detail: Annotated[EmploymentDetail, BeforeValidator(_to_obj)] = obj(
        EmploymentDetail
    )


class History(_Model):
    name: Str = ""
    dates: Str = ""
    values: Str = ""


class SecurityDetail(_Model):
    security_type: Str = ""
    owner_name: Str = ""
    security_valuation: Str = ""
    date_of_valuation: Str = ""


class Tradeline(_Model):
    acct_number: Str = ""
    credit_grantor: Str = ""
    credit_grantor_group: Str = ""
    credit_grantor_type: Str = ""
    acct_type: Str = ""
    reported_dt: Str = ""
    ownership_type: Str = ""
    account_status: Str = ""
    closed_dt: Str = ""
    disbursed_amt: Str = ""
    disbursed_dt: Str = ""
    installment_amt: Str = ""
    credit_limit: Str = ""
    cash_limit: Str = ""
    current_bal: Str = ""
    installment_frequency: Str = ""
    original_term: Str = ""
    term_to_maturity: Str = ""
    repayment_tenure: Str = ""
    interest_rate: Str = ""
    actual_payment: Str = ""
    last_payment_dt: Str = ""
    overdue_amt: Str = ""
    write_off_amt: Str = ""
    principal_write_off_amt: Str = ""
    settlement_amt: Str = ""
    obligation: Str = ""
    history: List[History] = []
    account_remarks: Str = ""
    security_status: Str = ""
    acct_in_dispute: Str = ""
    suit_filed_wilful_default_status: Str = ""
    written_off_settled_status: Str = ""
    write_off_dt: Str = ""
    security_details: List[SecurityDetail] = []
    suit_filed_dt: Str = ""
    last_paid_amount: Str = ""
    occupation: Str = ""
    income_frequency: Str = ""
    income_amount: Str = ""


class Inquiry(_Model):
    """Shape not present in the sample (always ``[]``); keys per CRIF spec."""

    model_config = ConfigDict(extra="allow")

    member_name: Str = ""
    lender_name: Str = ""
    inquiry_date: Str = ""
    purpose: Str = ""
    ownership_type: Str = ""
    amount: Str = ""
    remark: Str = ""


class ScoreFactor(_Model):
    type: Str = ""
    desc: Str = ""


class Score(_Model):
    name: Str = ""
    version: Str = ""
    value: Str = ""
    description: Str = ""
    factors: List[ScoreFactor] = []


class StandardData(_Model):
    demogs: Annotated[Demogs, BeforeValidator(_to_obj)] = obj(Demogs)
    employment_details: List[EmploymentWrapper] = []
    tradelines: List[Tradeline] = []
    inquiry_history: List[Inquiry] = []
    score: List[Score] = []


# --------------------------------------------------------------------------- #
# ACCOUNTS-SUMMARY / TRENDS
# --------------------------------------------------------------------------- #
class AccountsSummaryBlock(_Model):
    number_of_accounts: Str = ""
    active_accounts: Str = ""
    overdue_accounts: Str = ""
    secured_accounts: Str = ""
    unsecured_accounts: Str = ""
    untagged_accounts: Str = ""
    total_current_balance: Str = ""
    current_balance_secured: Str = ""
    current_balance_unsecured: Str = ""
    total_sanctioned_amt: Str = ""
    total_disbursed_amt: Str = ""
    total_amt_overdue: Str = ""


class MfiSummary(_Model):
    number_of_accounts: Str = ""
    active_accounts: Str = ""
    overdue_accounts: Str = ""
    closed_accounts: Str = ""
    no_of_other_mfis: Str = ""
    no_of_own_mfis: Str = ""
    total_own_current_balance: Str = ""
    total_own_installment_amt: Str = ""
    total_own_disbursed_amt: Str = ""
    total_own_overdue_amt: Str = ""
    total_other_current_balance: Str = ""
    total_other_installment_amt: Str = ""
    total_other_disbursed_amt: Str = ""
    total_other_overdue_amt: Str = ""
    max_worst_delinquency: Str = ""


class Attribute(_Model):
    attr_name: Str = ""
    attr_value: Str = ""


class AccountsSummary(_Model):
    primary_accounts_summary: Annotated[
        AccountsSummaryBlock, BeforeValidator(_to_obj)
    ] = obj(AccountsSummaryBlock)
    secondary_accounts_summary: Annotated[
        AccountsSummaryBlock, BeforeValidator(_to_obj)
    ] = obj(AccountsSummaryBlock)
    mfi_group_accounts_summary: Annotated[MfiSummary, BeforeValidator(_to_obj)] = obj(
        MfiSummary
    )
    additional_summary: List[Attribute] = []
    perform_attributes: List[Attribute] = []


class Trends(_Model):
    name: Str = ""
    dates: Str = ""
    values: Str = ""
    description: Str = ""


class ReportData(_Model):
    standard_data: Annotated[StandardData, BeforeValidator(_to_obj)] = obj(StandardData)
    accounts_summary: Annotated[AccountsSummary, BeforeValidator(_to_obj)] = obj(
        AccountsSummary
    )
    trends: Annotated[Trends, BeforeValidator(_to_obj)] = obj(Trends)


class B2CReport(_Model):
    header_segment: Annotated[HeaderSegment, BeforeValidator(_to_obj)] = obj(HeaderSegment)
    request_data: Annotated[RequestData, BeforeValidator(_to_obj)] = obj(RequestData)
    report_data: Annotated[ReportData, BeforeValidator(_to_obj)] = obj(ReportData)
