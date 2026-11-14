"""Read-only Markdown and AST analysis; audited source is never executed."""
import ast
import os
from pathlib import Path
import re

from .phrases import DELIVERYNOTEEXTRACTION, NODELIVERYNOTEEXTRACTION, GENERIC_NAMES


def normalize(text):
    return ' '.join(text.lower().replace("n't", ' not').replace('-', ' ').split())


def _pattern(phrases):
    return re.compile(r'\b(?:' + '|'.join(re.escape(p) for p in
                      sorted(phrases, key=lambda p: (-len(p), p))) + r')\b')


_POS = _pattern(DELIVERYNOTEEXTRACTION)
_NEG = _pattern(NODELIVERYNOTEEXTRACTION)


def claims(text):
    """Return positive and negative normalized phrase matches with line numbers."""
    lines = []
    fence = None
    for line in text.splitlines():
        opening = re.match(r'^ {0,3}(`{3,}|~{3,})(.*)$', line)
        if fence:
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) +
                            '{' + str(fence[1]) + r',}\s*', line):
                fence = None
            lines.append('')
        elif opening:
            fence = (opening[1][0], len(opening[1]))
            lines.append('')
        else:
            lines.append(line)
    positive, negative = [], []
    start, paragraph = 1, []
    for number, line in enumerate(lines + [''], 1):
        if line.strip():
            if not paragraph:
                start = number
            paragraph.append(line)
        elif paragraph:
            text = normalize(' '.join(paragraph))
            negative.extend({'line': start, 'phrase': m[0]} for m in _NEG.finditer(text))
            text = _NEG.sub(lambda m: ' ' * len(m[0]), text)
            positive.extend({'line': start, 'phrase': m[0]} for m in _POS.finditer(text))
            paragraph = []
    return positive, negative


def source_evidence(text):
    """Recognize only the two specified routes within one module."""
    try:
        tree = ast.parse(text)
    except (SyntaxError, ValueError):
        return []
    nodes = list(ast.walk(tree))
    imports = {}
    mindee_import = False
    definitions = {n.name for n in nodes if isinstance(
        n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
    bound = set()
    for node in nodes:
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports[alias.asname or alias.name.split('.')[0]] = alias.name if alias.asname else alias.name.split('.')[0]
                mindee_import |= alias.name.split('.')[0] == 'mindee'
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ''
            mindee_import |= module.split('.')[0] == 'mindee' and node.level == 0
            for alias in node.names:
                imports[alias.asname or alias.name] = module + '.' + alias.name
        targets = []
        if isinstance(node, ast.Assign):
            targets = node.targets
        elif isinstance(node, ast.AnnAssign):
            targets = [node.target]
        elif isinstance(node, (ast.With, ast.AsyncWith)):
            targets = [item.optional_vars for item in node.items if item.optional_vars]
        for target in targets:
            bound.update(n.id for n in ast.walk(target) if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store))
    shadow = bound | definitions

    def imported(name):
        return imports.get(name, '') if name not in shadow else ''

    def allowed_attribute(node):
        # A base may be bound (clients normally are); local route definitions
        # and rebinding an imported root invalidate that route through the root.
        base = node.value
        while isinstance(base, ast.Attribute):
            base = base.value
        return (node.attr not in definitions and
                not (isinstance(base, ast.Name) and
                     (base.id in definitions or (base.id in imports and base.id in bound))))

    client, parse, evidence = [], [], []
    for node in nodes:
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if isinstance(func, ast.Attribute):
            if not allowed_attribute(func):
                continue
            if func.attr in GENERIC_NAMES:
                evidence.append({'line': node.lineno, 'route': 'generic'})
            if (func.attr == 'Client' and isinstance(func.value, ast.Name)
                    and func.value.id == 'mindee' and 'Client' not in definitions):
                client.append(node.lineno)
            if func.attr == 'parse' and 'parse' not in definitions:
                args = node.args + [k.value for k in node.keywords]
                if any((isinstance(a, ast.Name) and a.id == 'DeliveryNoteV1' and a.id not in shadow) or
                       (isinstance(a, ast.Attribute) and a.attr == 'DeliveryNoteV1' and
                        allowed_attribute(a)) for a in args):
                    parse.append(node.lineno)
        elif isinstance(func, ast.Name):
            resolved = imported(func.id)
            if resolved.rsplit('.', 1)[-1] in GENERIC_NAMES and resolved.rsplit('.', 1)[-1] not in definitions:
                evidence.append({'line': node.lineno, 'route': 'generic'})
            if resolved == 'mindee.Client' and 'Client' not in definitions:
                client.append(node.lineno)
    if mindee_import and client and parse:
        evidence.append({'line': min(parse), 'route': 'mindee', 'client_line': min(client)})
    return sorted(evidence, key=lambda item: (item['line'], item['route']))


def audit(root, ignore=(), fail_on='high'):
    root = Path(root)
    if root.is_symlink() or not root.is_dir():
        raise OSError('root must be a readable, non-symlink directory')
    prefixes = []
    for prefix in ignore:
        path = Path(prefix)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('ignore prefixes must be relative paths without ..')
        prefixes.append(path.parts)

    def ignored(parts):
        return any(parts[:len(p)] == p for p in prefixes)

    positive, negative, production, tests = [], [], [], []

    def onerror(error):
        raise error

    for directory, dirs, files in os.walk(root, followlinks=False, onerror=onerror):
        base = Path(directory)
        dirs[:] = sorted(d for d in dirs if not (base / d).is_symlink()
                         and not ignored((base / d).relative_to(root).parts))
        for name in sorted(files):
            path = base / name
            relative = path.relative_to(root)
            parts = relative.parts
            if path.is_symlink() or ignored(parts):
                continue
            is_doc = relative.as_posix() == 'README.md' or (path.suffix == '.md' and 'docs' in parts[:-1])
            if is_doc:
                pos, neg = claims(path.read_text(encoding='utf-8'))
                positive.extend(dict(item, path=relative.as_posix()) for item in pos)
                negative.extend(dict(item, path=relative.as_posix()) for item in neg)
            if path.suffix != '.py' or set(parts[:-1]) & {'fixtures', 'docs', 'examples'}:
                continue
            found = source_evidence(path.read_text(encoding='utf-8'))
            target = tests if ('tests' in parts[:-1] or name.startswith('test_') or name.endswith('_test.py')) else production
            target.extend(dict(item, path=relative.as_posix()) for item in found)
    findings = []
    if positive and not production:
        findings.append({'rule': 'documented-delivery-note-extraction-claim-false',
                         'severity': 'MEDIUM' if tests else 'HIGH',
                         'message': 'The documented capability has only test evidence.' if tests else 'The documented capability has no production evidence.',
                         'locations': positive})
    if negative and production:
        findings.append({'rule': 'documented-no-delivery-note-extraction-claim-false',
                         'severity': 'HIGH', 'message': 'The documented denial contradicts production evidence.',
                         'locations': negative})
    failed = any(f['severity'] == 'HIGH' or fail_on == 'medium' for f in findings)
    return {'verdict': 'FAIL' if failed else 'PASS', 'findings': findings,
            'production_evidence': production, 'test_evidence': tests}
