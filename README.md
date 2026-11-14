# Documentation claim auditor

An offline static audit tool comparing documentation promises with recognized source calls. It parses source without executing it, uses only the standard library, and requires CPython 3.9 or newer. It makes no network calls and writes no reports or project files.

## Installation and usage

```sh
python3 -m pip install .
delivery-note-extraction-claim-audit audit .
delivery-note-extraction-claim-audit audit . --json --verbose --ignore build --ignore dist --fail-on medium
python3 -m delivery_note_extraction_claim_audit audit .
delivery-note-extraction-claim-audit --version
python3 -m unittest discover
```

The repository defaults to the current directory. Ignore prefixes are repeatable relative paths, matched by path component. The threshold accepts high or medium in lowercase. Exit 0 means PASS at the selected threshold; exit 2 means findings at that threshold; exit 1 means usage or I/O error. Default high allows a medium finding. JSON includes verdict, findings with rule, severity, message and locations, and production and test evidence. Verbose text includes evidence locations.

## Matching rules

Root README.md and Markdown files with a docs path component are scanned. Backtick and tilde fences with up to three leading spaces are excluded; inline code counts. Paragraphs split on blank lines. Normalization lowercases, expands contractions, replaces hyphens with spaces and collapses whitespace. Exact word-boundary matches prefer longest phrases with alphabetical ties. Denial spans are removed before positive matching. Each family emits at most one finding.

Source is parsed with AST, never executed. Symlinked files and directories are excluded. Files under fixtures, docs and examples supply no evidence. Tests count separately. Invalid syntax supplies no evidence. Each route must occur within a single module. Local function, method and class definitions shadow matching route names. Assignment, annotated assignment and context-manager bindings shadow imported names. Generic attributes allow any base; bare calls require an imported recognized name. A positive promise without source fails, while a denial without source passes. Dead code counts; untraced alias chains are missed; this is static pattern matching rather than semantic judgement. Denial handling depends on the exact denial vocabulary.

## Reference data

All checked vocabulary and rule identifiers are quoted below, outside audited prose.

```text
delivery note extraction
extract delivery notes
extracts delivery notes
extracting delivery notes
extract delivery note
extracts delivery note
extracting delivery note
delivery note parsing
delivery note parser
parse delivery notes
parses delivery notes
parse delivery note
parses delivery note
delivery note scanning
delivery note scanner
scan delivery notes
scans delivery notes
scan delivery note
scans delivery note
delivery docket extraction
extract delivery dockets
extracts delivery dockets
extracting delivery dockets
extract delivery docket
extracts delivery docket
extracting delivery docket
delivery docket parsing
delivery docket parser
parse delivery dockets
parses delivery dockets
parse delivery docket
parses delivery docket
delivery docket scanning
delivery docket scanner
scan delivery dockets
scans delivery dockets
scan delivery docket
scans delivery docket
docket extraction
extract dockets
extracts dockets
extracting dockets
extract docket
extracts docket
extracting docket
docket parsing
docket parser
parse dockets
parses dockets
parse docket
no delivery note extraction
does not extract delivery notes
does not extract delivery note
does not support delivery note extraction
without delivery note extraction
no delivery docket extraction
does not extract delivery dockets
does not extract delivery docket
does not support delivery docket extraction
without delivery docket extraction
no delivery note parser
does not parse delivery notes
does not parse delivery note
no delivery note scanner
does not scan delivery notes
does not scan delivery note
no docket extraction
does not extract dockets
does not extract docket
without docket extraction
no docket parser
does not parse dockets
does not parse docket
delivery note extraction not supported

documented-delivery-note-extraction-claim-false HIGH (MEDIUM for test-only evidence)
documented-no-delivery-note-extraction-claim-false HIGH

Generic names:
extract_delivery_note
extract_delivery_notes
parse_delivery_note
parse_delivery_notes
extract_delivery_docket
parse_delivery_docket
extract_docket
parse_docket
extract_delivery_note_data
parse_delivery_note_data
delivery_note_extraction
delivery_note_extractor
delivery_note_parser
docket_extraction
docket_extractor
docket_parser
extract_delivery_note_info
parse_delivery_note_info
delivery_note_scan
delivery_note_scanner
scan_delivery_note
scan_delivery_notes
extract_docket_data
parse_docket_data
```

## Evidence and honest limitations

The following technical reference describes recognized calls and known matching hazards. These quoted examples describe the checked feature rather than capabilities of this auditor.

```text

- The bare phrases "delivery note extraction" / "extract delivery
  note" / "extract delivery notes" are deliberately
  DELIVERYNOTEEXTRACTION phrases: in document-tool docs they almost
  always name delivery note extraction. But "delivery note" can
  also name a delivery note the tool merely stores, displays, or
  manages (a delivery note archive, a delivery note template
  library) without extracting fields from a delivery note
  document: a doc that means storing, displaying, or templating
  delivery notes, not extracting fields from them, is a false
  positive; the tool flags the claim, only the code decides.
- "delivery note parsing" / "delivery note parser" are deliberately
  phrases: a doc can say "delivery note parser" about a tool that
  only renders a delivery note as formatted text, or a "delivery
  note parser" that is really a keyword highlighter over plain
  text. The tool flags the claim; only the code decides.
- "delivery note scanning" / "scan delivery note(s)" are
  deliberately phrases: "scanning" a delivery note can mean merely
  photographing it or OCRing it into raw text, with no structured
  field extraction. The tool flags the claim; only the code decides.
- "delivery docket extraction" / "extract delivery docket(s)" /
  "delivery docket parsing" / "delivery docket parser" are
  deliberately phrases: a delivery docket is the same document as
  a delivery note under a different name. A doc that merely
  mentions delivery dockets as document types it stores is a false
  positive; the tool flags the claim, only the code decides.
- "docket extraction" / "extract docket(s)" / "docket parsing" /
  "docket parser" are deliberately phrases: "docket" also means a
  court docket or a meeting agenda in other domains. A doc that
  means a different "docket" is a false positive; the tool flags
  the claim, only the code decides.
- "delivery note data extraction" / "extract delivery note data" /
  "delivery note field extraction" are deliberately phrases: a doc
  can mean extracting plain text from a delivery note, not
  structured fields. The tool flags the claim; only the code
  decides.
- DeliveryNoteV1 v1.2 carries exactly seven fields
  (customer_address, customer_name, delivery_date,
  delivery_number, supplier_address, supplier_name,
  total_amount): it has NO line items, NO quantities, and NO tax
  split. A tool that extracts delivery note line items or tax
  breakdowns does so through some other route; this family checks
  for the DeliveryNoteV1 call, not for line-item fields. 
- A generic `extract_delivery_note(` / `parse_delivery_note(` /
  `extract_docket(` call can name a string parser for text the user
  typed in rather than a document extractor: the tool counts the
  call, the claim plus the code decide — and a subprocess call
  invoking an external CLI is NOT evidence by design, so a thin
  wrapper that only calls subprocess fails.
- Mindee `parse` with DeliveryNoteV1 counts as evidence:
  DeliveryNoteV1 exists in mindee 4.x (4.22.0 wheel inspected
  2026-11-14). The tool detects the call in source, not whether
  the call succeeds against a current API version. Say so in the
  README.
- Mindee `parse` with DeliveryNoteV1 is a 4.x-only fingerprint:
  mindee 5.4.0 removed the off-the-shelf delivery note product
  (wheel inspected 2026-11-14 — no delivery_note product
  directory; zero "DeliveryNote" hits anywhere in the wheel).
  Code written against mindee 5.x cannot use this route.
  
- Mindee `parse` with InvoiceV4 / ReceiptV5 / PassportV1 /
  FinancialDocumentV1 / BankCheckV1 / BankAccountDetailsV2 /
  PayslipV2 / PayslipV3 / HealthcareCardV1 / BusinessCardV1 /
  CustomV1 / GeneratedV1 / BillOfLadingV1 / ResumeV1 is NOT
  detected: those are other document types, and mindee 5.x has no
  delivery note product at all. 
- Mindee `parse` with BillOfLadingV1 is NOT detected: a bill of
  lading is a different document from a delivery note. 
- Azure `begin_analyze_document` with ANY model id is NOT
  detected: Azure Document Intelligence has no delivery note
  model (the Learn v4.0 GA page contains zero hits for "delivery
  note", verified 2026-11-14). 
- Veryfi calls of ANY kind are NOT detected: veryfi has no delivery
  note method (5.1.0 wheel inspected 2026-11-14 — the word
  "delivery" does not appear anywhere in the wheel), and its
  document APIs post to a generic documents endpoint shared across
  document types. 
- Google Document AI `process_document` / `batch_process_documents`
  with ANY processor is NOT detected: Document AI has no delivery
  note processor (the processors list page contains zero hits
  for "Delivery Note", verified 2026-11-14). 
- Eden AI universal-ai calls with ANY model id are NOT detected:
  Eden AI documents no delivery-note parser model. Say so in the
  README.
- LlamaParse calls are NOT detected: its delivery note OCR is a
  generative parsing API with no fixed static fingerprint naming
  delivery notes. 
- Nanonets / Docsumo / ABBYY Vantage / Rossum / Klippa / Parseur /
  Extend calls are NOT detected: opaque model / skill / queue /
  template / workflow IDs, or a generic upload endpoint with the
  document type configured outside the call — no fixed fingerprint.
  
- Textract `analyze_document` / `analyze_expense` /
  `start_document_analysis` / `get_expense_analysis` are NOT
  detected: generic document and expense analysis are not
  delivery note extraction, and Textract has no delivery note
  operation. 
- A hand-rolled extraction from OCR text (`re.search` /
  `re.findall` on extracted text plus manual field assembly, no
  listed call) is NOT detected: the tool requires a listed call.
  
- The mindee CLI, the veryfi CLI, and any other external delivery
  note tool invoked through subprocess are NOT detected:
  subprocess calls invoking an external CLI are NOT evidence by
  design. 
- Azure Document Intelligence, Mindee, and Veryfi are cloud APIs:
  the tool detects the client call in source, not whether
  credentials are configured or the call succeeds. Say so in the
  README.
- "extract delivery note text" / "extract text from delivery note"
  claims are NOT in the phrase lists: extracting plain text
  from a delivery note is text extraction, not delivery note
  field extraction. 
- "delivery note template" / "delivery note form" claims are NOT
  in the phrase lists: templating or form-filling a delivery note
  is creating one, not extracting fields from one. Say so in the
  README.
- "delivery note tracking" / "delivery note status" claims are
  NOT in the phrase lists: tracking a shipment by its delivery
  note number is downstream of extraction, not extraction
  itself. 
- "proof of delivery extraction" / "packing list extraction" /
  "goods received note extraction" claims are NOT in the phrase
  lists: proofs of delivery, packing lists, and goods received
  notes are different documents from delivery notes. Say so in the
  README.
- "air waybill extraction" / "air waybill parsing" claims are NOT
  in the phrase lists: an air waybill is a different document from
  a delivery note. 
- Invoice extraction claims ("extract invoices", "invoice
  extraction"), receipt extraction claims ("extract receipts",
  "receipt extraction"), ID document extraction claims ("extract
  passports", "passport extraction"), bank check extraction claims
  ("extract bank checks", "check extraction"), bank statement
  extraction claims ("extract bank statements", "statement
  extraction"), tax form extraction claims ("extract tax forms",
  "extract w2 forms", "1099 extraction"), pay stub extraction
  claims ("extract pay stubs", "payslip extraction"), health
  insurance card extraction claims ("extract health insurance
  cards", "health insurance card extraction"), business card
  extraction claims ("extract business cards", "business card
  extraction"), credit card extraction claims ("extract credit
  cards", "credit card extraction"), contract extraction claims
  ("extract contracts", "contract extraction"), mortgage
  extraction claims ("extract mortgages", "mortgage extraction"),
  resume extraction claims ("extract resumes", "resume
  extraction"), and bill of lading extraction claims ("extract
  bills of lading", "bill of lading extraction") are NOT in the
  phrase lists: this family covers delivery notes only. 
- As with every family: static pattern matching, not semantic
  judgement; dead code counts; alias chains the tracer cannot follow
  are missed; exact phrases only, not semantics; denial handling
  depends on the denial phrase list; each route must sit in a single
  module.



mindee Client construction + parse call passing DeliveryNoteV1 (Name
exactly DeliveryNoteV1, or Attribute with attr exactly DeliveryNoteV1 such
as product.DeliveryNoteV1 / mindee.product.DeliveryNoteV1 /
mindee.v1.product.DeliveryNoteV1) as any argument; import gate
mindee. DeliveryNoteV1 exists in mindee 4.x only (4.22.0 wheel
inspected 2026-11-14: mindee/product/delivery_note/delivery_note_v1.py
defines class DeliveryNoteV1(Inference), endpoint_name
"delivery_notes", endpoint_version "1", exported as
mindee.product.DeliveryNoteV1; its document is "Delivery note API
version 1.2" with fields customer_address, customer_name,
delivery_date, delivery_number, supplier_address, supplier_name,
total_amount — no line items, no quantities, no tax split); mindee
5.4.0 removed it (wheel inspected 2026-11-14: no delivery_note
product directory under mindee/v1/product; zero "DeliveryNote" hits
anywhere in the wheel; the only "delivery" hits in any 5.4.0 .py
file are docstrings in invoice_v4_document.py and
carte_grise_v1_document.py). The tool detects the call in source,
not the installed SDK version. A parse call passing any other product
(InvoiceV4, ReceiptV5, PassportV1, FinancialDocumentV1,
BankCheckV1, BankAccountDetailsV2, PayslipV2, PayslipV3,
HealthcareCardV1, BusinessCardV1, CustomV1, GeneratedV1,
BillOfLadingV1, ResumeV1, or any other) is NOT evidence.

## veryfi names (implementation MUST match exactly)

NO veryfi route: veryfi has no delivery note method in the Python SDK.
The 5.1.0 wheel, inspected 2026-11-14, contains zero hits for
"delivery" across all .py files, so a veryfi call of ANY kind is
NOT evidence. A call to the non-existent
process_delivery_note_document / process_delivery_note_document_url counts as
nothing. A raw HTTP call to
"https://api.veryfi.com/api/v8/partner/documents" is NOT evidence
either: it is Veryfi's generic documents endpoint, shared by
receipts, invoices, and other documents alike.

## azure names (implementation MUST match exactly)

NO azure route: Azure Document Intelligence has no delivery note model.
The Microsoft Learn v4.0 (GA) page, opened and searched
2026-11-14, contains zero hits for "delivery note". A
begin_analyze_document call with ANY model id is NOT evidence.

## google document ai names (implementation MUST match exactly)

NO Google Document AI route: the Document AI processors list page,
opened and searched 2026-11-14, contains zero hits for
"Delivery Note" — there is no delivery note processor, so a
process_document call with ANY processor is NOT evidence.

## eden ai / llamaparse / nanonets / docsumo / other vendor names (implementation MUST match exactly)

NO Eden AI route: Eden AI documents no delivery-note parser
model, so a universal-ai call with ANY model id is NOT evidence.
NO LlamaParse route: LlamaParse markets delivery note OCR, but
its generative parsing API has no fixed static fingerprint naming
delivery notes. NO Nanonets route: Nanonets document calls carry
an opaque model_id in the URL path (no fixed fingerprint — the
model id is user-configured, not a delivery note product). NO
Docsumo route: Docsumo uploads go to a generic endpoint with the
document type configured in the dashboard, not in the call. NO
ABBYY Vantage / Rossum / Klippa / Parseur / Extend route: opaque
skill / queue / template / workflow IDs. NO Textract route:
Textract has no delivery note operation. NO mindee v2 extraction
API route: configurable model id, no fixed fingerprint.


```
