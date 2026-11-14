"""Regression and fixed vocabulary oracle tests."""
import ast
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from delivery_note_extraction_claim_audit import phrases
from delivery_note_extraction_claim_audit.audit import audit, source_evidence, claims
from delivery_note_extraction_claim_audit.__main__ import main

EXPECTED_POS = ('delivery note extraction', 'extract delivery notes', 'extracts delivery notes', 'extracting delivery notes', 'extract delivery note', 'extracts delivery note', 'extracting delivery note', 'delivery note parsing', 'delivery note parser', 'parse delivery notes', 'parses delivery notes', 'parse delivery note', 'parses delivery note', 'delivery note scanning', 'delivery note scanner', 'scan delivery notes', 'scans delivery notes', 'scan delivery note', 'scans delivery note', 'delivery docket extraction', 'extract delivery dockets', 'extracts delivery dockets', 'extracting delivery dockets', 'extract delivery docket', 'extracts delivery docket', 'extracting delivery docket', 'delivery docket parsing', 'delivery docket parser', 'parse delivery dockets', 'parses delivery dockets', 'parse delivery docket', 'parses delivery docket', 'delivery docket scanning', 'delivery docket scanner', 'scan delivery dockets', 'scans delivery dockets', 'scan delivery docket', 'scans delivery docket', 'docket extraction', 'extract dockets', 'extracts dockets', 'extracting dockets', 'extract docket', 'extracts docket', 'extracting docket', 'docket parsing', 'docket parser', 'parse dockets', 'parses dockets', 'parse docket')
EXPECTED_NEG = ('no delivery note extraction', 'does not extract delivery notes', 'does not extract delivery note', 'does not support delivery note extraction', 'without delivery note extraction', 'no delivery docket extraction', 'does not extract delivery dockets', 'does not extract delivery docket', 'does not support delivery docket extraction', 'without delivery docket extraction', 'no delivery note parser', 'does not parse delivery notes', 'does not parse delivery note', 'no delivery note scanner', 'does not scan delivery notes', 'does not scan delivery note', 'no docket extraction', 'does not extract dockets', 'does not extract docket', 'without docket extraction', 'no docket parser', 'does not parse dockets', 'does not parse docket', 'delivery note extraction not supported')
EXPECTED_NAMES = ('extract_delivery_note', 'extract_delivery_notes', 'parse_delivery_note', 'parse_delivery_notes', 'extract_delivery_docket', 'parse_delivery_docket', 'extract_docket', 'parse_docket', 'extract_delivery_note_data', 'parse_delivery_note_data', 'delivery_note_extraction', 'delivery_note_extractor', 'delivery_note_parser', 'docket_extraction', 'docket_extractor', 'docket_parser', 'extract_delivery_note_info', 'parse_delivery_note_info', 'delivery_note_scan', 'delivery_note_scanner', 'scan_delivery_note', 'scan_delivery_notes', 'extract_docket_data', 'parse_docket_data')

POS_RULE = 'documented-delivery-note-extraction-claim-false'
NEG_RULE = 'documented-no-delivery-note-extraction-claim-false'
GOOD = 'import mindee\nc = mindee.Client()\nc.parse(product.DeliveryNoteV1, document)'


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def put(self, name, text):
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding='utf-8')
        return path

    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            try:
                code = main(list(args))
            except SystemExit as error:
                code = error.code
        return code, out.getvalue(), err.getvalue()

    def test_phrase_oracle(self):
        tree = ast.parse(Path(phrases.__file__).read_text())
        data = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body
                if isinstance(n, ast.Assign)}
        self.assertEqual(data['DELIVERYNOTEEXTRACTION'], EXPECTED_POS)
        self.assertEqual(data['NODELIVERYNOTEEXTRACTION'], EXPECTED_NEG)
        self.assertEqual(data['GENERIC_NAMES'], EXPECTED_NAMES)
        self.assertEqual(len(set(EXPECTED_POS)), 50)
        self.assertEqual(len(set(EXPECTED_NEG)), 24)
        self.assertEqual(len(set(EXPECTED_NAMES)), 24)

    def test_good_pass(self):
        self.put('README.md', 'We extract delivery notes.')
        self.put('main.py', GOOD)
        self.assertEqual(self.run_cli('audit', str(self.root))[0], 0)
        self.assertEqual(audit(self.root)['findings'], [])

    def test_bad_high(self):
        self.put('README.md', 'delivery note extraction')
        self.put('main.py', 'import mindee')
        code, out, err = self.run_cli('audit', str(self.root), '--json')
        self.assertEqual(code, 2)
        report = json.loads(out)
        self.assertEqual(report['verdict'], 'FAIL')
        self.assertEqual(report['findings'][0]['rule'], POS_RULE)
        self.assertEqual(report['findings'][0]['severity'], 'HIGH')
        self.assertTrue(report['findings'][0]['message'])
        self.assertEqual(report['findings'][0]['locations'][0]['path'], 'README.md')
        self.assertEqual(err, '')

    def test_test_only_medium(self):
        self.put('README.md', 'delivery note extraction')
        self.put('tests/route.py', GOOD)
        report = audit(self.root)
        self.assertEqual(report['findings'][0]['severity'], 'MEDIUM')
        self.assertEqual(report['findings'][0]['rule'], POS_RULE)
        self.assertEqual(self.run_cli('audit', str(self.root))[0], 0)
        self.assertEqual(self.run_cli('audit', str(self.root), '--fail-on', 'medium')[0], 2)

    def test_denial_high(self):
        self.put('README.md', 'does not extract delivery notes')
        self.put('main.py', GOOD)
        report = audit(self.root)
        self.assertEqual(len(report['findings']), 1)
        self.assertEqual(report['findings'][0]['rule'], NEG_RULE)
        self.assertEqual(report['findings'][0]['severity'], 'HIGH')
        self.assertEqual(self.run_cli('audit', str(self.root))[0], 2)

    def test_no_claim(self):
        self.put('README.md', 'A neutral project.')
        self.put('main.py', GOOD)
        self.assertEqual(audit(self.root)['findings'], [])

    def test_no_source_positive(self):
        self.put('README.md', 'delivery note extraction')
        self.assertEqual(audit(self.root)['findings'][0]['severity'], 'HIGH')

    def test_no_source_denial(self):
        self.put('README.md', 'no delivery note extraction')
        self.assertEqual(audit(self.root)['findings'], [])

    def test_fences(self):
        for opening, closing in [('```sh', '```'), ('   ~~~~text', '   ~~~~'), ('````', '````')]:
            with self.subTest(opening=opening):
                self.assertEqual(claims(opening+'\ndelivery note extraction\n'+closing), ([], []))
        self.assertEqual(claims('~~~\n```\ndelivery note extraction\n~~~'), ([], []))
        self.assertEqual(claims('```\ndelivery note extraction'), ([], []))

    def test_inline_counts(self):
        self.put('README.md', '`delivery note extraction`')
        self.assertEqual(audit(self.root)['verdict'], 'FAIL')

    def test_normalization_and_boundaries(self):
        self.assertTrue(claims('DELIVERY-NOTE\nEXTRACTION')[0])
        self.assertEqual(claims("doesn't extract delivery notes")[0], [])
        self.assertTrue(claims("doesn't extract delivery notes")[1])
        self.assertEqual(claims('xdelivery note extractionx'), ([], []))
        self.assertEqual(claims('delivery note\n\nextraction'), ([], []))
        self.assertEqual(claims('extract delivery notes')[0][0]['phrase'], 'extract delivery notes')
        pos, neg = claims('does not extract delivery notes; we extract dockets')
        self.assertEqual([p['phrase'] for p in pos], ['extract dockets'])
        self.assertEqual([p['phrase'] for p in neg], ['does not extract delivery notes'])

    def test_one_finding_per_family(self):
        self.put('README.md', 'extract delivery notes\n\nextract delivery dockets')
        self.put('docs/guide.md', 'delivery note extraction')
        report = audit(self.root)
        self.assertEqual(len(report['findings']), 1)
        self.assertEqual(len(report['findings'][0]['locations']), 3)

    def test_docs_selection(self):
        self.put('other.md', 'delivery note extraction')
        self.assertEqual(audit(self.root)['findings'], [])
        self.put('nested/docs/guide.md', 'delivery note extraction')
        self.assertEqual(audit(self.root)['verdict'], 'FAIL')

    def test_split_modules(self):
        self.put('README.md', 'delivery note extraction')
        self.put('client.py', 'import mindee\nc=mindee.Client()')
        self.put('parse.py', 'import mindee\nc.parse(product.DeliveryNoteV1)')
        self.assertEqual(audit(self.root)['verdict'], 'FAIL')

    def test_ignore_prefix_components(self):
        self.put('README.md', 'delivery note extraction')
        self.put('src/route.py', GOOD)
        self.assertEqual(audit(self.root, ['src'])['verdict'], 'FAIL')
        self.assertEqual(audit(self.root, ['sr'])['verdict'], 'PASS')
        self.assertEqual(audit(self.root, ['README.md'])['findings'], [])
        self.assertEqual(self.run_cli('audit', str(self.root), '--ignore', 'src', '--ignore', 'README.md')[0], 0)

    def test_symlinks(self):
        self.put('README.md', 'delivery note extraction')
        external = tempfile.TemporaryDirectory()
        self.addCleanup(external.cleanup)
        path = Path(external.name)
        (path/'route.py').write_text(GOOD)
        (path/'claim.md').write_text('delivery note extraction')
        (self.root/'route.py').symlink_to(path/'route.py')
        (self.root/'linked').symlink_to(path, target_is_directory=True)
        self.assertEqual(audit(self.root)['production_evidence'], [])
        (self.root/'docs').mkdir()
        (self.root/'docs/claim.md').symlink_to(path/'claim.md')
        self.assertEqual(len(audit(self.root)['findings'][0]['locations']), 1)

    def test_bad_usage_and_io(self):
        for args in [[], ['wat'], ['audit', '--wat'], ['audit', '--fail-on', 'HIGH'],
                     ['audit', '--ignore', 'a', 'b', 'c'], ['audit', str(self.root/'absent')],
                     ['audit', str(self.root), '--ignore', '../outside']]:
            with self.subTest(args=args):
                self.assertEqual(self.run_cli(*args)[0], 1)
        self.put('README.md', 'x')
        self.assertEqual(self.run_cli('audit', str(self.root/'README.md'))[0], 1)
        self.put('README.md', 'x').write_bytes(b'\xff')
        self.assertEqual(self.run_cli('audit', str(self.root))[0], 1)

    def test_verbose_and_default_root(self):
        self.put('README.md', 'extract dockets')
        self.put('route.py', GOOD)
        code, out, _ = self.run_cli('audit', str(self.root), '--verbose')
        self.assertEqual(code, 0)
        self.assertIn('production_evidence: route.py:', out)
        previous = Path.cwd()
        try:
            os.chdir(self.root)
            self.assertEqual(self.run_cli('audit')[0], 0)
        finally:
            os.chdir(previous)

    def test_version_and_module_entry(self):
        self.assertEqual(self.run_cli('--version')[:2], (0, '0.1.0\n'))
        process = subprocess.run([sys.executable, '-m', 'delivery_note_extraction_claim_audit', '--version'],
                                 capture_output=True, text=True)
        self.assertEqual((process.returncode, process.stdout), (0, '0.1.0\n'))

    def test_console_entry_declared(self):
        # On installed wheels metadata supplies the equivalent entry-point check.
        from importlib import metadata
        try:
            entries = metadata.distribution('delivery-note-extraction-claim-audit').entry_points
            self.assertTrue(any(e.name == 'delivery-note-extraction-claim-audit' and
                                e.value == 'delivery_note_extraction_claim_audit.__main__:main' for e in entries))
        except metadata.PackageNotFoundError:
            project = Path(__file__).resolve().parents[1]/'pyproject.toml'
            self.assertIn('delivery-note-extraction-claim-audit = "delivery_note_extraction_claim_audit.__main__:main"', project.read_text())

    def test_readme_self_audit(self):
        readme = Path(__file__).resolve().parents[1]/'README.md'
        if readme.exists():
            self.assertEqual(claims(readme.read_text()), ([], []))


def evidence_test(code, expected):
    def test(self):
        self.assertEqual(bool(source_evidence(code)), expected, code)
    return test


# Every recognized generic attribute and imported alias is exercised independently.
for index, name in enumerate(EXPECTED_NAMES):
    setattr(AuditTests, 'test_generic_attribute_%02d' % index, evidence_test('x.'+name+'(document)', True))
    setattr(AuditTests, 'test_generic_import_%02d' % index, evidence_test('from vendor import '+name+' as f\nf(document)', True))
    setattr(AuditTests, 'test_generic_bare_%02d' % index, evidence_test(name+'(document)', False))
    setattr(AuditTests, 'test_generic_shadow_%02d' % index, evidence_test('def '+name+'(x): pass\nx.'+name+'(doc)', False))

MIND_EVIDENCE = [
    GOOD,
    'from mindee import Client\nfrom mindee.product import DeliveryNoteV1\nClient()\nc.parse(DeliveryNoteV1, doc)',
    'import mindee\nmindee.Client()\nc.parse(mindee.product.DeliveryNoteV1, doc)',
    'import mindee\nmindee.Client()\nc.parse(product_class=mindee.v1.product.DeliveryNoteV1)',
    'from mindee import Client as C\nC()\nc.parse(product_class=product.DeliveryNoteV1)',
    'import mindee.product\nmindee.Client()\nc.parse(doc, product.DeliveryNoteV1)',
    'import mindee\nc: object = mindee.Client()\nc.parse(product.DeliveryNoteV1)',
    'import mindee\nwith mindee.Client() as c:\n c.parse(product.DeliveryNoteV1)',
    'import mindee\nasync def f():\n async with mindee.Client() as c:\n  c.parse(product.DeliveryNoteV1)',
]
for index, code in enumerate(MIND_EVIDENCE):
    setattr(AuditTests, 'test_mindee_route_%02d' % index, evidence_test(code, True))

NOT_EVIDENCE = [
    'import mindee', 'import veryfi', 'import azure.ai.documentintelligence',
    'import azure.ai.formrecognizer', 'import google.cloud.documentai', 'import boto3',
    'import mindee\nmindee.Client()', 'import mindee\nc.parse(product.DeliveryNoteV1)',
    'c.parse(product.DeliveryNoteV1)\nx.Client()',
    'from azure.ai.documentintelligence import DocumentIntelligenceClient\nc=DocumentIntelligenceClient()',
    'import veryfi\nveryfi.Client()',
    'import requests\nrequests.post("https://api.veryfi.com/api/v8/partner/documents")',
    'import google.cloud.documentai\nc.process_document(processor="opaque")',
    'import google.cloud.documentai\nc.batch_process_documents(processor="opaque")',
    'import edenai\nc.universal_ai(model="ocr/invoice_parser/affinda")',
    'import edenai\nc.universal_ai(model="ocr/resume_parser/affinda")',
    'import edenai\nc.universal_ai(model="ocr/delivery_note/vendor")',
    'from llama_parse import LlamaParse\nLlamaParse().load_data("note.pdf")',
    'import nanonets\nc.ocr(model_id="opaque")', 'import docsumo\nc.upload(document_type="opaque")',
    'import mindee\nc.enqueue_and_get_inference(model_id="opaque")',
    'import re\nfields={"delivery_number": re.search("Number: (.*)", text)}',
    'text.split("delivery note")',
    'import subprocess\nsubprocess.run(["mindee", "parse", "DeliveryNoteV1"])',
    'import subprocess\nsubprocess.run(["veryfi", "document"])',
    '# x.extract_delivery_note(doc)\ns="delivery note extraction"',
    'x.extract_delivery_note', 'def broken(:\n x.extract_delivery_note()',
    'from vendor import extract_delivery_note\nextract_delivery_note = other\nextract_delivery_note(doc)',
    'from vendor import extract_delivery_note\nextract_delivery_note: object = other\nextract_delivery_note(doc)',
    'from vendor import extract_delivery_note\nwith context() as extract_delivery_note:\n extract_delivery_note(doc)',
    'from vendor import extract_delivery_note\nasync def f():\n async with context() as extract_delivery_note:\n  extract_delivery_note(doc)',
    'from mindee import Client\nClient = other\nClient()\nc.parse(product.DeliveryNoteV1)',
    'import mindee\nwith context() as mindee:\n mindee.Client()\n c.parse(product.DeliveryNoteV1)',
    'import mindee\nclass Client: pass\nmindee.Client()\nc.parse(product.DeliveryNoteV1)',
    'import mindee\ndef parse(): pass\nmindee.Client()\nc.parse(product.DeliveryNoteV1)',
    'import mindee\nclass DeliveryNoteV1: pass\nmindee.Client()\nc.parse(DeliveryNoteV1)',
    'class X:\n def extract_delivery_note(self): pass\nx.extract_delivery_note(doc)',
    'class extract_delivery_note: pass\nx.extract_delivery_note(doc)',
]
for product in ['InvoiceV4', 'ReceiptV5', 'PassportV1', 'FinancialDocumentV1', 'BankCheckV1',
                'BankAccountDetailsV2', 'PayslipV2', 'PayslipV3', 'HealthcareCardV1', 'BusinessCardV1',
                'CustomV1', 'GeneratedV1', 'BillOfLadingV1', 'ResumeV1', 'TypeDeliveryNoteV1', 'Other']:
    NOT_EVIDENCE.append('import mindee\nmindee.Client()\nc.parse(product.'+product+')')
for model in ['invoice', 'receipt', 'layout', 'read', 'idDocument', 'check.us', 'tax.us',
              'bankStatement.us', 'payStub.us', 'healthInsuranceCard.us', 'businessCard',
              'creditCard', 'contract', 'mortgage.us.1003', 'deliveryNote', 'arbitrary']:
    NOT_EVIDENCE.append('import azure.ai.documentintelligence\nc.begin_analyze_document("prebuilt-'+model+'", doc)')
for method in ['process_any_document', 'process_any_document_url', 'process_document', 'process_document_url',
               'process_w2_document', 'process_w9_document', 'process_w8_document', 'process_check',
               'process_check_url', 'process_check_with_remittance', 'process_check_with_remittance_url',
               'process_bank_statement_document', 'process_bank_statement_document_url',
               'process_bussines_card_document', 'process_bussines_card_document_url', 'classify_document',
               'get_business_cards', 'get_business_card', 'delete_business_card',
               'process_delivery_note_document', 'process_delivery_note_document_url']:
    NOT_EVIDENCE.append('import veryfi\nc=veryfi.Client()\nc.'+method+'(doc)')
for vendor, methods in [
    ('textract', ['analyze_document', 'analyze_expense', 'start_document_analysis', 'get_expense_analysis']),
    ('pdfplumber', ['extract_text', 'extract_table', 'extract_tables', 'find_table', 'find_tables']),
    ('fitz', ['extract_text', 'find_tables']), ('pypdf', ['extract_text']), ('PyPDF2', ['extract_text']),
    ('pdfminer', ['extract_text']), ('pytesseract', ['image_to_string']), ('pandas', ['read_csv', 'read_excel']),
    ('camelot', ['read_pdf']), ('tabula', ['read_pdf', 'convert_into']),
    ('abbyy', ['extract']), ('rossum', ['upload']), ('klippa', ['parse']), ('parseur', ['upload']), ('extend', ['extract'])]:
    for method in methods:
        NOT_EVIDENCE.append('import '+vendor+'\n'+vendor+'.'+method+'(doc)')
for index, code in enumerate(NOT_EVIDENCE):
    setattr(AuditTests, 'test_not_evidence_%03d' % index, evidence_test(code, False))


def path_test(path, test_only):
    def test(self):
        self.put('README.md', 'delivery note extraction')
        self.put(path, GOOD)
        report = audit(self.root)
        self.assertEqual(report['production_evidence'], [])
        self.assertEqual(bool(report['test_evidence']), test_only)
        self.assertEqual(report['findings'][0]['severity'], 'MEDIUM' if test_only else 'HIGH')
    return test


for index, path in enumerate(['fixtures/a.py', 'docs/a.py', 'examples/a.py', 'nested/fixtures/a.py',
                              'tests/a.py', 'nested/tests/a.py', 'test_route.py', 'route_test.py']):
    setattr(AuditTests, 'test_path_exclusion_%02d' % index, path_test(path, index >= 4))

for index, phrase in enumerate(EXPECTED_POS):
    def positive_test(self, phrase=phrase):
        positive, negative = claims(phrase)
        self.assertEqual([p['phrase'] for p in positive], [phrase])
        self.assertEqual(negative, [])
    setattr(AuditTests, 'test_positive_phrase_%02d' % index, positive_test)
for index, phrase in enumerate(EXPECTED_NEG):
    def negative_test(self, phrase=phrase):
        positive, negative = claims(phrase)
        self.assertEqual(positive, [])
        self.assertEqual([p['phrase'] for p in negative], [phrase])
    setattr(AuditTests, 'test_negative_phrase_%02d' % index, negative_test)


if __name__ == '__main__':
    unittest.main()
