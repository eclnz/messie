"""Fixture corpus of office, business and administrative documents.

Each topic maps to six (filename_stem, body_text) pairs of fictional prose. The
documents inside a topic deliberately reuse the same domain nouns over and over
("invoice", "payment", "billed"; "premium", "adjuster", "claim") because one of
the embedding backends under test matches surface words rather than meanings, so
shared vocabulary is what makes a topic cluster. Vocabulary is kept disjoint
between topics so that clusters stay separable. All names, numbers and addresses
are invented placeholders.
"""

from __future__ import annotations

TOPICS: dict[str, list[tuple[str, str]]] = {
    "tax_return": [
        (
            "2023_tax_return_federal",
            "Federal tax return for the 2023 filing year, prepared for submission to the "
            "revenue service. Total taxable income, withheld income tax and estimated "
            "quarterly tax payments are reconciled on the return. Deductions claimed "
            "include charitable contributions, self employment expenses and depreciation. "
            "The taxpayer elects itemised deductions rather than the standard deduction "
            "because the itemised total exceeds the threshold. A taxable capital gain from "
            "the disposal of shares is reported on the supplementary gains schedule. The "
            "computed tax liability, less credits and prior withholding, results in a "
            "refund due from the revenue service. The taxpayer declares that the return is "
            "complete and correct, signs the declaration page and retains supporting "
            "receipts for the statutory record retention period required by tax law.",
        ),
        (
            "tax_return_2022_amended",
            "Amended tax return for the 2022 tax year, superseding the original return "
            "filed with the revenue service. The amendment corrects understated taxable "
            "income and adds a deduction for professional subscriptions that was omitted "
            "from the first filing. Revised taxable income increases the assessed tax "
            "liability, and the taxpayer remits the additional tax together with statutory "
            "interest calculated from the original due date. Withholding figures and "
            "credits carried forward are restated. The revenue service is asked to apply "
            "the corrected figures to the taxpayer account and to issue a revised notice "
            "of assessment. Supporting schedules for income, deductions and allowable "
            "expenses accompany the amended tax return as required.",
        ),
        (
            "Self Assessment Tax Computation",
            "Self assessment tax computation summarising taxable income, allowances and "
            "the final tax liability for the year. Employment income, dividend income and "
            "rental income are aggregated before personal allowance is applied. Allowable "
            "expenses and pension contributions reduce taxable income, and the resulting "
            "tax is banded across the basic and higher rate thresholds. Tax already "
            "deducted at source is credited against the computed liability. The balance of "
            "tax payable and the first payment on account toward next year are shown "
            "separately. The taxpayer should file the return with the revenue service "
            "before the statutory deadline to avoid late filing penalties and interest "
            "charges on unpaid tax.",
        ),
        (
            "quarterly_estimated_tax_worksheet",
            "Worksheet for computing quarterly estimated tax payments where income is not "
            "subject to withholding. Projected taxable income for the tax year is "
            "annualised, reduced by expected deductions, and multiplied by the applicable "
            "marginal tax rates to estimate the annual tax liability. One quarter of the "
            "estimated liability is remitted to the revenue service each period. Safe "
            "harbour rules based on the prior year tax return are described, allowing the "
            "taxpayer to avoid an underpayment penalty by paying a set percentage of last "
            "year assessed tax. Records of each estimated tax payment, including "
            "confirmation references, should be retained and reconciled against the final "
            "annual return.",
        ),
        (
            "tax-deduction-summary-2021",
            "Summary of deductions claimed on the 2021 tax return, organised by category "
            "for the revenue service. Home office deduction, mileage deduction, equipment "
            "depreciation and charitable contributions are itemised with supporting "
            "totals. Each deduction reduces taxable income and therefore the assessed tax "
            "liability for the tax year. Non deductible personal expenditure has been "
            "excluded from the computation. The summary notes which deductions are subject "
            "to statutory limits and which may be carried forward to a later tax year. "
            "Receipts, logbooks and invoices evidencing every deduction are filed with the "
            "return in case the revenue service opens an enquiry into the taxpayer "
            "filing.",
        ),
        (
            "revenue_service_assessment_notice",
            "Notice of assessment issued by the revenue service following review of the "
            "filed tax return. The notice confirms assessed taxable income, total "
            "deductions allowed, tax credits applied and the final tax liability for the "
            "tax year. One claimed deduction was reduced because supporting evidence was "
            "not supplied, increasing taxable income slightly above the figure on the "
            "return. The resulting tax underpayment, plus interest, is payable by the date "
            "stated. The taxpayer may object to the assessment in writing within the "
            "objection period, attaching evidence for the disallowed deduction. Future "
            "returns should reflect the revised treatment to prevent repeated adjustments "
            "to assessed tax.",
        ),
    ],
    "client_invoices": [
        (
            "invoice_1043_northwind_studio",
            "Invoice number 1043 issued to Northwind Studio for design services delivered "
            "during the billing period. The invoice itemises billable hours at the agreed "
            "hourly rate, a fixed fee for the brand guidelines deliverable, and reimbursed "
            "printing costs. Subtotal, sales tax and the invoice total payable are shown "
            "at the foot of the billing table. Payment terms are net thirty days from the "
            "invoice date, payable by bank transfer to the account details printed below. "
            "Late payment attracts interest at the stated monthly rate. Please quote the "
            "invoice number on the remittance advice so the payment can be matched against "
            "the outstanding balance on the client account.",
        ),
        (
            "Invoice 1044 - Blue Harbour Ltd",
            "Invoice 1044 billed to Blue Harbour Ltd covering consultancy work performed "
            "this month. Each line item lists the task, the quantity of billable days and "
            "the daily rate charged. A discount agreed under the retainer is applied "
            "before tax, and the resulting invoice total is payable within fourteen days. "
            "The client purchase order number is quoted for accounts payable matching. "
            "Two previous invoices remain unpaid and are listed on the attached statement "
            "of account. The billing contact is asked to release payment for all "
            "outstanding invoices together. Remittance should reference the invoice "
            "numbers so payments can be allocated correctly against each billed amount.",
        ),
        (
            "overdue_invoice_reminder_1021",
            "Payment reminder regarding invoice 1021, which is now overdue by more than "
            "thirty days. The invoice was issued for services billed in the prior quarter "
            "and remains unpaid on the client account. A copy of the original invoice, "
            "together with the itemised billing breakdown and the agreed payment terms, is "
            "attached for convenience. Please arrange payment of the outstanding invoice "
            "total by bank transfer within seven days. If payment has already been sent, "
            "kindly forward the remittance advice so the invoice can be marked as paid. "
            "Continued non payment will result in late payment interest being added and "
            "further billing being suspended until the account is settled.",
        ),
        (
            "client_billing_statement_q3",
            "Client billing statement for the third quarter listing every invoice issued, "
            "each payment received and the closing balance outstanding. Invoices are shown "
            "in date order with invoice number, billed amount, tax charged and payment "
            "status. Credit notes issued against two disputed invoices are deducted from "
            "the billed total. Payments allocated during the quarter are matched to the "
            "corresponding invoice numbers. The statement closes with an aged balance "
            "analysis separating current invoices from those overdue by thirty, sixty and "
            "ninety days. The client is asked to confirm the statement and to settle all "
            "overdue invoice balances by the payment date shown.",
        ),
        (
            "proforma-invoice-greenfield",
            "Proforma invoice prepared for Greenfield Catering ahead of work commencing. "
            "The document sets out the proposed billing lines, unit prices and the "
            "estimated invoice total including sales tax, but is not yet a demand for "
            "payment. Once the client approves the scope, a numbered commercial invoice "
            "will be issued and payment terms will begin from that invoice date. A fifty "
            "percent deposit is billed in advance and the remaining balance is invoiced on "
            "delivery. Bank details for payment and the billing address of record are "
            "included. Any change to the billed quantities will be reflected in a revised "
            "proforma invoice before issue.",
        ),
        (
            "recurring_invoice_schedule_2024",
            "Schedule of recurring invoices to be raised for retainer clients during 2024. "
            "For each client the schedule shows the invoice issue date, the fixed monthly "
            "amount billed, the applicable tax rate and the payment due date. Invoices are "
            "generated automatically on the first working day of the month and emailed to "
            "the client billing contact. Payments received by direct debit are reconciled "
            "against the invoice number within two working days. Where a retainer is "
            "paused, no invoice is raised for that month and the billing schedule resumes "
            "the following period. Unpaid recurring invoices are escalated to the credit "
            "control process after the payment terms expire.",
        ),
    ],
    "employment_contract": [
        (
            "Employment Contract - Signed",
            "Contract of employment between the company and the employee setting out the "
            "agreed terms and conditions of employment. The employee is engaged in the "
            "role described in the schedule, reporting to the line manager named there. "
            "Annual salary is payable monthly in arrears and reviewed each year. Normal "
            "working hours, annual leave entitlement, sick pay and pension enrolment are "
            "specified. The probationary period runs for six months, during which either "
            "party may terminate on shorter notice. Thereafter the notice period stated in "
            "the contract applies. The employee agrees to confidentiality obligations and "
            "to the restrictive covenants in the appendix. Both parties sign the contract "
            "to confirm acceptance of these terms of employment.",
        ),
        (
            "offer_letter_senior_analyst",
            "Letter of offer for the post of senior analyst, subject to satisfactory "
            "references and right to work checks. The offer confirms the starting annual "
            "salary, the discretionary bonus scheme, the employer pension contribution and "
            "the holiday entitlement for the employment year. The employee will be based "
            "at the head office with hybrid working by agreement with the line manager. "
            "Employment commences on the start date stated and is subject to a six month "
            "probationary period. A full contract of employment setting out notice "
            "periods, confidentiality duties and company policies accompanies this letter. "
            "The candidate is asked to sign and return a copy of the offer to accept the "
            "terms of employment.",
        ),
        (
            "staff_handbook_terms_and_conditions",
            "Staff handbook describing the terms and conditions that apply to all "
            "employees alongside the individual contract of employment. Sections cover "
            "working hours and overtime, annual leave booking, sickness absence reporting, "
            "family leave entitlements and the pension scheme. The disciplinary procedure "
            "and grievance procedure set out the stages, the right to be accompanied and "
            "the appeal route. Policies on equal opportunity, harassment and acceptable "
            "use of company systems form part of the employment relationship. Where the "
            "handbook conflicts with the signed employment contract, the contract prevails. "
            "Employees confirm each year that they have read the handbook and understand "
            "their obligations as an employee.",
        ),
        (
            "notice-of-resignation-letter",
            "Formal letter of resignation from the employee to the line manager, giving "
            "the contractual notice period required by the contract of employment. The "
            "employee confirms the intended final working day and offers to assist with "
            "handover of duties during the notice period. Accrued but untaken annual leave "
            "will be paid in the final salary payment, and the employee asks for a "
            "statement of leave balance. The employee acknowledges continuing "
            "confidentiality obligations and the restrictive covenants that survive "
            "termination of employment. A reference request is expected from the future "
            "employer. The letter thanks the manager for the development opportunities "
            "provided during the period of employment with the company.",
        ),
        (
            "fixed_term_contract_maternity_cover",
            "Fixed term contract of employment for maternity cover, expiring on the return "
            "of the substantive post holder or on the end date stated, whichever is "
            "earlier. The employee performs the duties described in the role schedule "
            "under the direction of the line manager. Salary, working hours, annual leave "
            "and pension enrolment mirror the terms applying to permanent employees on the "
            "equivalent grade. The contract may be terminated early by either party giving "
            "the written notice period specified. Expiry of the fixed term is itself a "
            "termination of employment, and no redundancy entitlement arises where the "
            "contract runs its stated course. The employee signs to accept these terms.",
        ),
        (
            "contract_variation_hours_amendment",
            "Variation to the existing contract of employment reducing the employee "
            "contractual working hours from full time to four days each week. Annual "
            "salary, annual leave entitlement and the employer pension contribution are "
            "prorated accordingly from the effective date. All other terms and conditions "
            "of employment, including the notice period, confidentiality obligations and "
            "the disciplinary and grievance procedures, remain unchanged and in force. The "
            "line manager and the employee agree the revised working pattern set out in "
            "the schedule. Both parties sign this variation, which is attached to and read "
            "together with the original employment contract held on the employee personnel "
            "file.",
        ),
    ],
    "mortgage_application": [
        (
            "mortgage_application_form_complete",
            "Mortgage application for the purchase of a freehold property, submitted to the "
            "lender for underwriting. The applicants state the purchase price, the deposit "
            "contributed from savings and the loan amount requested, giving the resulting "
            "loan to value ratio. Household income, existing borrowing and monthly "
            "commitments are disclosed for affordability assessment. The applicants seek a "
            "five year fixed interest rate on a capital repayment basis over a twenty five "
            "year mortgage term. A valuation of the property will be instructed by the "
            "lender before a formal mortgage offer is issued. The applicants confirm the "
            "information given is accurate and consent to credit reference searches by the "
            "lender.",
        ),
        (
            "Mortgage Offer - Ref MX9921",
            "Formal mortgage offer issued by the lender following successful underwriting "
            "and valuation of the property. The offer states the loan amount advanced, the "
            "fixed interest rate and the period for which it applies, the mortgage term "
            "and the monthly repayment on a capital and interest basis. The reversion rate "
            "applying after the fixed period ends is shown, with an illustration of the "
            "revised repayment. Conditions of the offer include satisfactory buildings "
            "cover on the property and redemption of an existing secured loan on "
            "completion. Early repayment charges apply during the fixed rate period. The "
            "offer remains open for the validity period stated before it lapses.",
        ),
        (
            "affordability_assessment_worksheet",
            "Affordability worksheet used by the lender to test whether the applicants can "
            "sustain the mortgage repayment. Verified household income is compared against "
            "committed expenditure, existing credit balances and the stressed monthly "
            "repayment calculated at an interest rate above the offered fixed rate. The "
            "resulting income multiple and loan to value ratio are checked against lending "
            "policy for the requested loan amount and mortgage term. Deposit source is "
            "evidenced to satisfy the lender. The worksheet records the underwriting "
            "decision, any conditions attached to the mortgage offer, and the maximum "
            "borrowing the applicants could support on the property being purchased.",
        ),
        (
            "remortgage-illustration-fixed-rate",
            "Illustration prepared for applicants considering a remortgage of their "
            "existing property to a new lender. The current outstanding loan balance, the "
            "estimated property value and the resulting loan to value ratio determine the "
            "interest rate band offered. The illustration compares the present variable "
            "reversion rate against a two year and a five year fixed rate, showing the "
            "monthly repayment and total cost over the comparison period. Product fees, "
            "valuation costs and legal fees associated with the remortgage are listed. "
            "Early repayment charges on the existing mortgage are noted, since these may "
            "outweigh the saving from switching lender before the current deal expires.",
        ),
        (
            "deposit_source_of_funds_statement",
            "Statement evidencing the source of the deposit for the mortgage application, "
            "prepared for the lender underwriting team. The deposit is made up of accrued "
            "savings held for several years and a gift from a family member. A signed "
            "gifted deposit declaration confirms the gift is not repayable and that the "
            "donor retains no interest in the property. Savings account history supporting "
            "the balance accumulated is attached. The lender requires this evidence before "
            "releasing a mortgage offer because the deposit directly affects the loan to "
            "value ratio and the interest rate band applied to the requested loan amount "
            "and mortgage term.",
        ),
        (
            "property_valuation_report_lender",
            "Valuation report on the property commissioned by the lender in support of the "
            "mortgage application. The surveyor states the estimated market value, the "
            "reinstatement figure and the tenure of the property. The valuation supports "
            "the purchase price, so the requested loan amount produces the loan to value "
            "ratio assumed in the underwriting assessment. Minor defects noted do not "
            "affect suitability as security for the mortgage, though a damp investigation "
            "is recommended as a condition of the mortgage offer. The report is prepared "
            "for the lender only and does not constitute a survey for the applicants, who "
            "are advised to commission their own inspection.",
        ),
    ],
    "insurance_claim": [
        (
            "insurance_claim_form_water_damage",
            "Claim form submitted to the insurer under the household policy following "
            "escape of water from a burst pipe. The policyholder describes the incident "
            "date, the cause of loss and the rooms affected. Damaged flooring, plasterwork "
            "and furnishings are listed with estimated replacement values. Emergency "
            "plumbing costs already incurred are claimed under the policy. The policy "
            "number and the excess payable by the policyholder are stated. The insurer is "
            "asked to appoint a loss adjuster to inspect the damage and to confirm cover "
            "under the perils section of the policy wording. Photographs of the damage and "
            "the plumber report are attached in support of the claim.",
        ),
        (
            "Loss Adjuster Report - Claim 88214",
            "Report of the loss adjuster appointed by the insurer to investigate claim "
            "88214. The adjuster attended the risk address, inspected the damage and "
            "interviewed the policyholder about the circumstances of the loss. The cause "
            "is consistent with the peril insured under the policy wording, and no "
            "exclusion or breach of policy condition was identified. The adjuster verifies "
            "the schedule of damaged items, adjusts two values to reflect wear, and "
            "recommends settlement on a reinstatement basis less the policy excess. "
            "Underinsurance was considered but the declared sum insured appears adequate. "
            "The adjuster recommends the insurer accepts the claim and authorises payment "
            "of the settlement figure stated.",
        ),
        (
            "motor_claim_accident_statement",
            "Statement made by the policyholder to the motor insurer concerning a "
            "collision at a junction. The statement gives the date, time and location of "
            "the incident, road and weather conditions, and the damage sustained by the "
            "insured vehicle. Details of the third party vehicle and driver are recorded "
            "for liability purposes. The policyholder denies fault and asks the insurer to "
            "pursue recovery of the excess from the third party insurer. Cover for a "
            "courtesy vehicle under the policy is requested while repairs are carried out "
            "at an approved repairer. The claim reference, policy number and the excess "
            "applying to this claim are noted.",
        ),
        (
            "travel-insurance-claim-cancellation",
            "Claim under the travel policy for irrecoverable costs following cancellation "
            "of a trip for medical reasons. The policyholder sets out the booking dates, "
            "the reason for cancellation and the amounts not refunded by the airline and "
            "the accommodation provider. A certificate from a practitioner confirming the "
            "policyholder was unfit to travel is attached, as required by the policy "
            "wording. Receipts and booking confirmations evidence the loss claimed. The "
            "insurer is asked to settle the claim less the cancellation excess stated in "
            "the policy schedule. The policyholder confirms no other insurance covers the "
            "same loss and that no part of the amount claimed has been recovered "
            "elsewhere.",
        ),
        (
            "claim_settlement_letter_final",
            "Letter from the insurer confirming final settlement of the claim under the "
            "policy. The settlement figure represents the assessed loss agreed with the "
            "loss adjuster less the policy excess and less an allowance for betterment on "
            "two replacement items. Payment will be made to the policyholder nominated "
            "account within five working days of acceptance. Acceptance of the settlement "
            "discharges the insurer from further liability in respect of this claim, "
            "though the policy remains in force for the balance of the period of "
            "insurance. The claim will be recorded against the policyholder claims history "
            "and may affect the no claims discount applied at renewal.",
        ),
        (
            "policy_schedule_and_excess_summary",
            "Schedule of insurance issued with the policy wording, summarising the cover "
            "in force for the period of insurance. Sections of cover, the sums insured, "
            "and the excess applying to each type of claim are listed, together with "
            "endorsements that vary the standard policy terms. The policyholder is "
            "reminded to notify the insurer promptly of any claim or circumstance likely "
            "to give rise to a claim, and of any change in risk during the policy period. "
            "Failure to disclose a material fact may entitle the insurer to avoid the "
            "policy or to reduce a claim settlement. Renewal terms will be issued before "
            "the policy expiry date.",
        ),
    ],
    "board_slides": [
        (
            "board_deck_q4_strategy",
            "Board presentation for the fourth quarter covering strategy, performance and "
            "the outlook for the coming year. Opening slides summarise recurring revenue "
            "growth, gross margin and cash runway against the operating plan approved by "
            "the board. A market slide positions the company against competitors and sizes "
            "the addressable opportunity. The strategy section proposes expansion into an "
            "adjacent segment, with the headcount and capital required set out on the "
            "investment slide. Risks and mitigations are tabled for board discussion. The "
            "closing slide lists the three decisions requested of the board this quarter, "
            "including approval of the operating plan and the proposed hiring envelope for "
            "the next two quarters.",
        ),
        (
            "Board Meeting Slides - March",
            "Slide deck circulated to directors ahead of the March board meeting. The "
            "agenda slide sets out apologies, minutes of the previous meeting, matters "
            "arising and the items for decision. Performance slides chart bookings, "
            "churn and pipeline coverage against plan, with commentary from the chief "
            "executive on the variance. The operations slide reports on delivery "
            "milestones and on the hiring plan. A governance slide covers compliance "
            "training completion and the risk register review. The final slides invite the "
            "board to approve the revised budget and to note the chair succession timetable "
            "so that a recommendation can be brought to the next board meeting for "
            "decision.",
        ),
        (
            "investor_update_board_pack",
            "Board pack assembled for directors and observers, combining the presentation "
            "slides with supporting appendices. The executive summary slide highlights the "
            "quarter headline metrics, the cash position and the key strategic decision "
            "before the board. Functional slides from product, go to market and operations "
            "each report progress against the objectives agreed at the previous board "
            "meeting. Appendices contain the detailed management accounts, the hiring plan "
            "and the risk register. Directors are asked to read the pack in advance so "
            "that the meeting can focus on discussion rather than presentation. The final "
            "slide records the resolutions proposed for approval by the board.",
        ),
        (
            "strategy-offsite-presentation",
            "Presentation prepared for the leadership offsite to shape the strategy that "
            "will be taken to the board. Early slides review where the company won and "
            "lost in the last year and what the data says about customer segments. The "
            "middle section frames three strategic options, each with a slide setting out "
            "the thesis, the required investment and the expected return. A decision slide "
            "compares the options against agreed criteria. Closing slides propose the "
            "recommended strategy, the operating plan implications and the milestones that "
            "would be reported to the board each quarter. Facilitation notes accompany each "
            "slide for the session leads.",
        ),
        (
            "quarterly_business_review_slides",
            "Quarterly business review slides for the leadership team and board observers. "
            "The scorecard slide tracks the quarter objectives with a status for each, "
            "followed by slides analysing revenue by segment, retention cohorts and "
            "acquisition efficiency. A delivery slide reviews roadmap commitments met and "
            "missed, with root causes. The people slide reports headcount, attrition and "
            "hiring against the plan. Each functional lead presents one slide of lessons "
            "learned and one slide of commitments for next quarter. The closing slides "
            "consolidate the asks of the board and the resourcing decisions needed before "
            "the next quarterly review.",
        ),
        (
            "board_slides_annual_plan_2025",
            "Annual plan presentation to the board for the 2025 financial year. The "
            "opening slides recap performance against the prior year plan and set the "
            "context for the targets proposed. Revenue, margin and cash slides present the "
            "base case with sensitivity slides for an upside and a downside scenario. The "
            "investment slide allocates spend across product, go to market and platform, "
            "and the headcount slide shows the hiring profile by quarter. Governance "
            "slides cover the risk register, compliance and the audit timetable. The final "
            "slide asks the board to approve the plan, the capital allocation and the "
            "executive objectives for the year.",
        ),
    ],
    "medical_records": [
        (
            "discharge_summary_ward_b",
            "Discharge summary prepared for the patient general practitioner following an "
            "inpatient admission. The patient was admitted with shortness of breath and "
            "chest discomfort. On examination the patient was afebrile with mildly raised "
            "respiratory rate; observations and blood results are recorded in the notes. "
            "The working diagnosis was a lower respiratory tract infection treated with a "
            "course of antibiotics and supplemental oxygen. Symptoms resolved and the "
            "patient was mobilised safely by the physiotherapy team. Discharge medication "
            "and dosage are listed, with advice to complete the antibiotic course. A "
            "follow up appointment in the respiratory clinic is arranged in six weeks, and "
            "the patient was advised to seek review if symptoms recur.",
        ),
        (
            "Clinic Letter - Cardiology Follow Up",
            "Clinic letter documenting the cardiology follow up consultation. The patient "
            "reports improved exercise tolerance since the last review and no further "
            "episodes of palpitation. Examination found a regular pulse, normal heart "
            "sounds and no peripheral oedema. The electrocardiogram recorded in clinic was "
            "unremarkable, and recent blood results including renal function are within "
            "the reference range. Current medication is continued at the same dose, with "
            "counselling given on symptoms that should prompt urgent review. Lifestyle "
            "advice on activity and diet was reinforced. The patient will be reviewed in "
            "the clinic in twelve months, or sooner if symptoms change; a copy of this "
            "letter is sent to the patient and the general practitioner.",
        ),
        (
            "patient_referral_dermatology",
            "Referral letter asking the dermatology clinic to review a patient with a "
            "changing pigmented skin lesion on the upper back. The patient first noticed "
            "the lesion eight months ago and reports recent change in border and colour. "
            "There is no bleeding and no associated symptoms. Relevant history includes "
            "childhood sunburn and a family history of skin cancer; current medication and "
            "allergies are listed in the notes. Examination findings and a clinical "
            "photograph are attached. The referral is made under the urgent suspected "
            "cancer pathway so the patient is seen promptly. The general practitioner "
            "would be grateful for assessment, dermoscopy and any treatment the clinic "
            "considers appropriate.",
        ),
        (
            "immunisation-record-child",
            "Immunisation record held for a paediatric patient, listing each vaccine "
            "administered with the date, the dose number and the site of administration. "
            "The primary course was completed on schedule and the preschool booster was "
            "given at the clinic appointment recorded. No adverse reaction was observed "
            "beyond mild local soreness, which settled without treatment. The patient "
            "allergy status and relevant medical history are noted. The record identifies "
            "one outstanding vaccine and the age at which it becomes due, and the parent "
            "has been advised to book the clinic appointment. A copy of the record is held "
            "in the patient notes and shared with the general practitioner and the school "
            "health team.",
        ),
        (
            "laboratory_results_blood_panel",
            "Laboratory report for a routine blood panel requested by the clinic. Full "
            "blood count, renal profile, liver enzymes, thyroid function and glucose were "
            "analysed on the sample taken at the patient appointment. Most results fall "
            "within the reference range printed alongside each value. Haemoglobin is "
            "marginally below range and ferritin is low, consistent with mild iron "
            "deficiency; the clinician is advised to correlate with the patient symptoms "
            "and clinical history. Liver enzymes and renal function are normal. A repeat "
            "sample in three months is suggested to monitor the trend. The report is filed "
            "in the patient notes and a copy sent to the requesting clinician for "
            "review.",
        ),
        (
            "operation_note_day_surgery",
            "Operation note recorded after a day case procedure carried out under local "
            "anaesthetic. The patient consented to the procedure after discussion of "
            "benefits, risks and alternatives, and the consent form is filed in the "
            "patient notes. The surgeon describes the approach, the findings at operation "
            "and the closure technique used. Estimated blood loss was minimal and no "
            "complication occurred during the procedure. Postoperative instructions cover "
            "wound care, analgesia, activity restriction and the signs of infection that "
            "should prompt the patient to contact the clinic. The patient was discharged "
            "the same day with a nurse review arranged in one week for wound inspection "
            "and suture removal.",
        ),
    ],
    "school_reports": [
        (
            "year_9_report_autumn_term",
            "End of autumn term report for a pupil in Year 9, prepared by the form tutor "
            "and subject teachers. Attainment grades and effort grades are given for each "
            "subject alongside a short comment from the teacher. The pupil has made strong "
            "progress in mathematics and science, contributing confidently in lessons and "
            "completing homework to a good standard. Literacy targets set in the previous "
            "term have been met. The pupil should aim to revise more systematically before "
            "assessments and to take a fuller part in class discussion in humanities. "
            "Attendance and punctuality are excellent. Parents are invited to discuss this "
            "report with the form tutor at the parents evening next term.",
        ),
        (
            "Pupil Progress Report - Summer",
            "Summer term progress report describing the pupil attainment, effort and "
            "attitude to learning across the curriculum. Teachers report that the pupil "
            "reads widely, writes with increasing accuracy and responds well to feedback "
            "in lessons. Numeracy has improved since the spring assessment, though "
            "problem solving remains a target for next year. The pupil participates in "
            "school clubs and has represented the school at the regional tournament. "
            "Homework is generally completed on time, and the teacher encourages more "
            "independent revision ahead of end of year examinations. Attendance is above "
            "the school average. The class teacher looks forward to meeting parents at the "
            "summer parents evening to discuss targets.",
        ),
        (
            "parents_evening_summary_notes",
            "Summary of the discussion held with parents at the parents evening, recorded "
            "by the form tutor. Subject teachers reported on the pupil attainment and "
            "effort in each lesson, highlighting strong classwork in art and steady "
            "progress in languages. Parents raised concerns about homework organisation, "
            "and the tutor agreed to review the planner weekly with the pupil. Targets "
            "were agreed for the coming term covering revision routines, classroom "
            "contribution and reading at home. The school will report progress against "
            "these targets in the next written report. Parents were reminded of the school "
            "attendance policy and of the dates for forthcoming assessments and the school "
            "trip.",
        ),
        (
            "primary-school-annual-report",
            "Annual report for a primary pupil, covering attainment and personal "
            "development across the school year. The class teacher notes that the pupil "
            "reads fluently for pleasure, writes imaginative stories and uses mathematical "
            "vocabulary accurately in lessons. Progress in phonics assessment was above "
            "expectation. The pupil is kind towards classmates, takes responsibility in "
            "the classroom and joins in enthusiastically with physical education. Targets "
            "for next year include neater handwriting and greater independence when "
            "checking written work. Attendance for the year is recorded with authorised "
            "and unauthorised absence shown separately. Parents are welcome to discuss the "
            "report with the class teacher before the end of term.",
        ),
        (
            "gcse_predicted_grades_sheet",
            "Sheet of predicted examination grades issued to pupils and parents ahead of "
            "the option and sixth form application process. For each subject the teacher "
            "records the current working grade, the predicted final grade and the target "
            "grade derived from prior attainment data. Commentary identifies the pupils "
            "whose coursework or revision needs attention before the mock examinations. "
            "Pupils are reminded that predicted grades reflect classwork, homework and "
            "assessment performance to date and can change with sustained effort. The "
            "school will review predictions after the mock examination results and will "
            "report any revision to parents. Subject teachers are available at the "
            "parents evening to discuss individual targets.",
        ),
        (
            "attendance_and_behaviour_record",
            "School record of a pupil attendance and behaviour for the academic year. "
            "Attendance is expressed as a percentage of possible sessions, with authorised "
            "absence for illness shown separately from unauthorised absence. Late marks "
            "are recorded by term. The behaviour log lists merits awarded by teachers for "
            "classwork, helpfulness and effort in lessons, together with two recorded "
            "incidents and the restorative action taken by the form tutor. The pastoral "
            "lead notes that the pupil responded well and has had no further incident "
            "since. Parents are informed of the attendance expectation and of the support "
            "the school can offer to improve punctuality before the next report.",
        ),
    ],
    "rental_lease": [
        (
            "tenancy_agreement_flat_4b",
            "Assured shorthold tenancy agreement between the landlord and the tenant for "
            "the furnished flat described in the particulars. The tenancy runs for a fixed "
            "term of twelve months from the commencement date, after which it continues "
            "monthly until ended by notice. Rent is payable monthly in advance by standing "
            "order on the day stated. A tenancy deposit equal to five weeks rent is taken "
            "and protected in a government approved scheme. The tenant covenants to keep "
            "the premises in good condition, not to sublet, and to permit the landlord "
            "access on reasonable notice for inspection or repair. The landlord covenants "
            "to keep the structure and installations in repair throughout the tenancy.",
        ),
        (
            "Lease Renewal Letter - Unit 12",
            "Letter offering the tenant a renewal of the tenancy for a further fixed term "
            "at the premises. The landlord proposes a new twelve month term commencing on "
            "expiry of the current tenancy, with rent increased to the amount stated in "
            "line with comparable local rents. All other covenants in the existing tenancy "
            "agreement would continue unchanged, including the repairing obligations and "
            "the restriction on subletting. The tenancy deposit already protected will be "
            "carried over to the renewed term. If the tenant does not wish to renew, the "
            "tenant should give written notice before the expiry date so the landlord can "
            "arrange a check out inspection of the premises.",
        ),
        (
            "inventory_and_check_in_report",
            "Inventory and condition report prepared at check in, recording the state of "
            "the premises and the contents at the start of the tenancy. Each room is "
            "listed with the fixtures, furnishings, decorative condition and meter "
            "readings noted. Keys handed to the tenant are recorded. Existing marks and "
            "wear are photographed so that they are not attributed to the tenant at check "
            "out. The tenant has seven days to comment on the inventory before it is "
            "treated as agreed. At the end of the tenancy the premises will be compared "
            "against this report, and any damage beyond fair wear and tear may be deducted "
            "from the protected tenancy deposit by the landlord.",
        ),
        (
            "notice-to-quit-landlord",
            "Notice served by the landlord on the tenant requiring possession of the "
            "premises at the end of the notice period prescribed by statute. The notice "
            "states the address of the premises, the date on which possession is required "
            "and the ground relied upon under the tenancy legislation. The tenant remains "
            "liable for rent and for the covenants in the tenancy agreement until "
            "possession is given up. The landlord will arrange a check out inspection "
            "against the inventory and will return the tenancy deposit less any agreed "
            "deduction. The notice explains that the tenant need not leave before a court "
            "order is made and that free housing advice is available.",
        ),
        (
            "commercial_lease_retail_unit",
            "Lease of a retail unit granted by the landlord to the tenant for a term of "
            "five years, with a tenant break clause at the third anniversary. Rent is "
            "payable quarterly in advance, subject to review at the third year on an open "
            "market basis. The tenant covenants to use the premises only for the permitted "
            "retail use, to keep the demised premises in repair and decorated, and to "
            "contribute a service charge toward the upkeep of the common parts. Assignment "
            "and subletting of the whole require landlord consent, not to be unreasonably "
            "withheld. The tenant holds a rent deposit as security and must yield up the "
            "premises in repair at the end of the term.",
        ),
        (
            "rent_increase_notice_annual",
            "Notice informing the tenant of a proposed rent increase taking effect at the "
            "start of the next rental period. The notice sets out the current rent, the "
            "proposed rent and the date from which the new amount becomes payable under "
            "the tenancy. The landlord explains that the revised figure reflects local "
            "market rents for comparable premises and increased costs of maintaining the "
            "property. All other terms of the tenancy agreement remain unchanged, "
            "including the length of the notice period and the repairing covenants. The "
            "tenant may refer the proposed rent to the tribunal before the effective date "
            "if the tenant considers the increase to exceed the market level.",
        ),
    ],
    "conference_talk": [
        (
            "conference_talk_abstract_submission",
            "Abstract submitted to the programme committee for a forty minute conference "
            "talk. The session proposes a practical account of how a small team rebuilt "
            "its deployment pipeline, aimed at an intermediate audience of practitioners. "
            "The talk opens with the problem, walks through three approaches the team "
            "tried, and closes with measured outcomes and the lessons that generalise. "
            "Attendees will leave with a checklist they can apply the following week. The "
            "speaker has presented at three previous conferences and can supply recordings "
            "on request. The abstract lists the track, the preferred session length, the "
            "speaker biography and the audio visual requirements for the conference "
            "venue.",
        ),
        (
            "Keynote Speaker Notes - Day 1",
            "Speaker notes for the opening keynote of the conference, timed for thirty "
            "five minutes with five minutes of audience questions. The notes mark where to "
            "pause, where to advance the slide and which stories to tell if the session "
            "runs ahead of time. The opening anecdote establishes the theme, the middle "
            "section develops three arguments with evidence, and the close returns to the "
            "opening image and issues a call to action for attendees. Reminders cover "
            "microphone checks with the audio visual team, speaking pace, and how to "
            "handle questions from the floor. A shortened version of the talk is noted in "
            "case the conference schedule slips.",
        ),
        (
            "call_for_papers_workshop_track",
            "Call for papers inviting submissions to the workshop track of the annual "
            "conference. The programme committee seeks talks, tutorials and lightning "
            "sessions from practitioners and researchers, with a strong preference for "
            "sessions that give attendees something to take away. Submissions should "
            "include an abstract, an outline of the session, the intended audience level "
            "and a short speaker biography. Review is double blind and the committee will "
            "notify speakers of acceptance by the date given. Accepted speakers receive a "
            "conference pass and a contribution toward travel. Questions about the track, "
            "the session formats or the audio visual setup should be sent to the programme "
            "chair.",
        ),
        (
            "talk-slides-lightning-session",
            "Slide outline for a lightning session of five minutes at the conference. "
            "Because the session is short, the talk carries one idea: a single technique "
            "the speaker wants every attendee to try. The opening slide poses a question "
            "the audience will recognise, three slides demonstrate the technique with live "
            "examples, and the final slide gives the link to the repository and the "
            "speaker contact for questions afterwards. Speaker notes remind the presenter "
            "to rehearse aloud twice, to avoid dense slides that the back of the room "
            "cannot read, and to confirm screen resolution with the audio visual crew "
            "before the session begins.",
        ),
        (
            "session_feedback_summary_attendees",
            "Summary of attendee feedback collected after the conference session. "
            "Respondents rated the talk highly for clarity and relevance, and many "
            "commented that the live demonstration was the most useful part of the "
            "session. Several attendees asked for a slower pace in the middle segment and "
            "for the slides to be published after the conference. Two respondents wanted "
            "more depth than the session length allowed and suggested the speaker propose "
            "a longer workshop next year. The programme committee notes the room was at "
            "capacity and recommends scheduling this talk in a larger auditorium if the "
            "speaker returns to a future conference.",
        ),
        (
            "speaker_briefing_pack_2025",
            "Briefing pack sent to every confirmed conference speaker. It confirms the "
            "session title, the track, the room and the start time, and asks speakers to "
            "arrive fifteen minutes early for a microphone and laptop check with the audio "
            "visual team. Guidance covers slide aspect ratio, readable font sizes, the "
            "recording consent form and the code of conduct that applies to all sessions. "
            "Speakers are asked to leave time for audience questions and to repeat each "
            "question for the recording. Travel, accommodation and the speaker dinner are "
            "detailed, along with the contact for the programme chair on the day of the "
            "conference.",
        ),
    ],
    "meeting_minutes": [
        (
            "minutes_committee_meeting_may",
            "Minutes of the committee meeting held in May. Present, apologies and the "
            "chair are recorded at the head of the minutes. The minutes of the previous "
            "meeting were approved as an accurate record and signed by the chair. Matters "
            "arising covered the outstanding action on the car park lighting, which the "
            "secretary agreed to chase. The treasurer reported on the balance held and the "
            "committee noted the report. Under any other business, a member raised the "
            "notice period for circulating papers, and the committee resolved that papers "
            "be circulated seven days ahead. Actions were assigned with owners and "
            "deadlines. The date of the next meeting was agreed before the chair closed "
            "the meeting.",
        ),
        (
            "Minutes - Annual General Meeting",
            "Minutes of the annual general meeting, recorded by the secretary. The chair "
            "opened the meeting, confirmed a quorum was present and noted apologies "
            "received. The minutes of the last annual general meeting were approved "
            "without amendment. The chair delivered the annual report and members asked "
            "questions from the floor, which are summarised in these minutes. Elections to "
            "the committee were held and the results declared by the returning officer. "
            "Two resolutions were put to the meeting; both were carried on a show of "
            "hands, with the voting recorded. The secretary noted the actions arising and "
            "the chair thanked members before declaring the meeting closed.",
        ),
        (
            "project_standup_notes_week_12",
            "Notes taken at the weekly project meeting in week twelve. Attendees are "
            "listed and apologies noted. Each workstream lead reported progress since the "
            "last meeting, flagged blockers and confirmed the actions carried forward. The "
            "chair recorded that the integration action from the previous meeting remains "
            "open and reassigned it with a firm deadline. Discussion covered the revised "
            "milestone dates, and the meeting agreed to escalate the resourcing question "
            "to the steering group. Any other business included a request to move the "
            "recurring meeting slot. Actions, owners and due dates are tabulated at the "
            "foot of these notes for circulation before the next meeting.",
        ),
        (
            "steering-group-minutes-october",
            "Minutes of the steering group meeting in October. The chair welcomed a new "
            "member and confirmed the agenda circulated in advance. The minutes of the "
            "previous meeting were agreed subject to one amendment to the attendance list. "
            "Matters arising were reviewed against the action log, with three actions "
            "closed and two carried forward. The group considered the escalation from the "
            "project meeting and resolved to approve additional resource, recording the "
            "decision in these minutes. Risks were reviewed and the register updated. "
            "Under any other business the secretary reminded members of the reporting "
            "deadline. The chair confirmed the date and venue of the next meeting.",
        ),
        (
            "action_log_from_previous_meeting",
            "Action log maintained by the secretary and circulated with the minutes of "
            "each meeting. Every action records the meeting at which it was raised, a "
            "description of what was agreed, the owner and the due date. Completed actions "
            "are marked closed with the date and remain visible for one further meeting "
            "before being archived. Open actions are reviewed under matters arising at the "
            "start of each meeting, and owners are asked to report progress to the chair. "
            "Where an action can no longer be delivered, the meeting must formally agree "
            "to withdraw it and the minutes record the reason. The log is attached to the "
            "agenda for every meeting.",
        ),
        (
            "agenda_and_minutes_residents_meeting",
            "Agenda and draft minutes for the residents meeting. The agenda lists "
            "apologies, approval of the previous minutes, matters arising, the treasurer "
            "report, grounds maintenance, and any other business. The draft minutes record "
            "that residents discussed the maintenance schedule at length and agreed by "
            "majority to obtain three further quotations before the next meeting. An "
            "action was recorded for the secretary to write to the managing agent. A "
            "resident asked that future agendas be posted on the noticeboard a week before "
            "each meeting, and the chair agreed. The draft minutes will be circulated for "
            "correction and formally approved at the following residents meeting.",
        ),
    ],
}

EXTENSIONS: dict[str, tuple[str, ...]] = {
    "tax_return": ("pdf", "xlsx", "docx"),
    "client_invoices": ("pdf", "xlsx", "docx", "odt"),
    "employment_contract": ("docx", "pdf", "rtf"),
    "mortgage_application": ("pdf", "docx", "xlsx"),
    "insurance_claim": ("pdf", "docx", "rtf", "txt"),
    "board_slides": ("pptx", "pdf"),
    "medical_records": ("pdf", "docx", "rtf"),
    "school_reports": ("pdf", "docx", "odt"),
    "rental_lease": ("pdf", "docx", "rtf", "odt"),
    "conference_talk": ("pptx", "pdf", "docx", "txt"),
    "meeting_minutes": ("docx", "pdf", "odt", "txt"),
}
