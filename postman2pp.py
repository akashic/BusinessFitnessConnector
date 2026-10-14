#!/usr/bin/env python3
"""
postman2pp.py - Convert a Postman collection into a Power Platform custom-connector
definition (Swagger 2.0) + apiProperties.json, using the same conventions as the
BGL SF360 connector (x-ms-summary, tags from folders, operationIds from request
names, body/response schemas inferred from examples).

Accepts a Postman "Export > Collection v2.1" file, or the JSON behind a Postman
Documenter site (e.g. https://development.businessfitness.com/api/collections/<owner>/<id>).

Usage:
  python3 postman2pp.py collection.json --title "Business Fitness Active" \
      --env environment.json [--host api.example.com] [--out ./connector]

Exit code is non-zero if the auth config is incomplete or insecure, no API host
is known, or the output fails validation or is too large; --out is then left
unchanged and the failed output goes to a temporary folder. Errors go to stderr.
Review the generated YAML before deploying - inferred schemas are only as good as
the examples in the collection - and run `paconn validate` for Power Platform's
own rules.
"""
import argparse, html, json, os, re, sys, tempfile
from collections import Counter, OrderedDict
from urllib.parse import parse_qsl

import yaml

MAX_DEFINITION_BYTES = 1024 * 1024   # Power Platform rejects definitions of 1 MB or more
MAX_SUMMARY_CHARS = 80               # Microsoft's connector string guidance
MAX_TITLE_CHARS = 30                 # Microsoft's connector string guidance
OUTPUT_FILES = ('apiDefinition.swagger.yaml', 'apiDefinition.swagger.json', 'apiProperties.json')
UNTYPED = {'type': 'object'}         # schema used when no example can be inferred; copy it, don't share it
FETCH_METHODS = ('get', 'head')      # no body allowed (BodyOrFormDataParameterInFetchOperationNotAllowed)

# Business Fitness Active API limits from its collection docs ("Searching", "Pagination")
SEARCH_MAX_LENGTH = 64           # "The search field is typically restricted to 64 characters"
DETAILED_PAGE_SIZE_MAX = 100     # max PageSize on /detailed endpoints

HTML_TAGS = ('a|b|blockquote|br|code|div|em|h[1-6]|hr|i|img|li|ol|p|pre|span|strong|sub|sup|'
             'table|tbody|td|th|thead|tr|u|ul')
HTML_TAG_RE = re.compile(rf'</?(?:{HTML_TAGS})\b[^<>]*>', re.IGNORECASE)
REQUIRED_PREFIX_RE = re.compile(r'^\(Required\)\s*', re.IGNORECASE)


class ConfigError(Exception):
    """Input that would produce a connector which can't work; main() reports it and exits 1."""

# Postman Documenter writes example values as typed placeholders, e.g. "<uuid>" or "<boolean>"
PLACEHOLDER_TYPES = {
    'string': {'type': 'string'},
    'uuid': {'type': 'string', 'format': 'uuid'},
    'integer': {'type': 'integer'},
    'long': {'type': 'integer', 'format': 'int64'},
    'number': {'type': 'number'},
    'double': {'type': 'number', 'format': 'double'},
    'boolean': {'type': 'boolean'},
    'date': {'type': 'string', 'format': 'date'},
    'dateTime': {'type': 'string', 'format': 'date-time'},
}
DATE_RE = re.compile(r'\d{4}-\d{2}-\d{2}')
DATETIME_RE = re.compile(r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:?\d{2})?')

ACRONYMS = {'abn', 'acn', 'api', 'bas', 'csv', 'gst', 'id', 'pdf', 'tfn', 'uri', 'url', 'utc'}
MINOR_WORDS = {'a', 'an', 'and', 'as', 'at', 'by', 'for', 'in', 'of', 'on', 'or', 'the', 'to'}


def slug(s):
    s = re.sub(r'[^A-Za-z0-9]+', ' ', s).strip().title().replace(' ', '')
    return s or 'Op'


def label(name):
    """Title Case display label for x-ms-summary: clientID -> Client ID, URLPath -> URL Path."""
    words = re.findall(r'[A-Z]{2,}s(?![a-z])|[A-Z]+(?=[A-Z][a-z])|[A-Z]?[a-z]+\d*|[A-Z]+\d*|\d+', name)
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if lw in ACRONYMS: w = w.upper()
        elif lw.endswith('s') and lw[:-1] in ACRONYMS: w = lw[:-1].upper() + 's'
        elif len(w) > 1 and w.isupper(): pass
        elif i and lw in MINOR_WORDS: w = lw
        else: w = w[0].upper() + w[1:]
        out.append(w)
    return ' '.join(out) or name


def text(desc, limit=1000):
    """Plain text from a Postman description (string or {content: ...}, HTML or markdown)."""
    if isinstance(desc, dict): desc = desc.get('content')
    if not isinstance(desc, str): return ''
    s = html.unescape(HTML_TAG_RE.sub(' ', desc))   # only real tags, so "a < b > c" survives
    s = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'\1 (\2)', s)   # markdown link -> "text (url)"
    s = re.sub(r'(\*\*|__|`)', '', s)
    s = re.sub(r'^\s*#+\s*', '', s, flags=re.MULTILINE)
    s = re.sub(r'\s+', ' ', s).strip()
    if len(s) > limit: s = s[:limit - 1].rsplit(' ', 1)[0] + '…'
    return s


def summary_text(name):
    """Operation summary per Microsoft's guidance: no '/', at most 80 chars, ends alphanumeric."""
    s = re.sub(r'\s*/\s*', ' or ', name.strip())
    s = re.sub(r'\s*\(([^()]*)\)\s*$', r' - \1', s)   # "List documents (minimal)" -> "List documents - minimal"
    if len(s) > MAX_SUMMARY_CHARS: s = s[:MAX_SUMMARY_CHARS].rsplit(' ', 1)[0]
    return re.sub(r'[^A-Za-z0-9]+$', '', s) or name


def placeholder_schema(v):
    m = re.fullmatch(r'<(\w+)>', v.strip()) if isinstance(v, str) else None
    return dict(PLACEHOLDER_TYPES[m.group(1)]) if m and m.group(1) in PLACEHOLDER_TYPES else None


def infer_schema(v, depth=0):
    if depth > 8: return dict(UNTYPED)
    if isinstance(v, bool): return {'type': 'boolean'}
    if isinstance(v, int): return {'type': 'integer'}
    if isinstance(v, float): return {'type': 'number'}
    if isinstance(v, str):
        typed = placeholder_schema(v)
        if typed: return typed
        if DATE_RE.fullmatch(v): return {'type': 'string', 'format': 'date'}
        if DATETIME_RE.fullmatch(v): return {'type': 'string', 'format': 'date-time'}
        return {'type': 'string'}
    if v is None: return {'type': 'string'}
    if isinstance(v, list):
        return {'type': 'array', 'items': infer_schema(v[0], depth + 1) if v else dict(UNTYPED)}
    if isinstance(v, dict):
        props = OrderedDict()
        for k, val in v.items():
            if not re.fullmatch(r'[A-Za-z0-9_\-.]+', k): continue
            p = infer_schema(val, depth + 1)
            p['x-ms-summary'] = label(k)
            props[k] = p
        return {'type': 'object', 'properties': props}
    return {'type': 'string'}


def parse_json_loose(raw):
    """Parse a Postman example body: {{vars}} become strings, // and /* */ comments are dropped."""
    if not raw: return None
    out, i, n, in_str = [], 0, len(raw), False
    while i < n:
        if raw.startswith('{{', i) and raw.find('}}', i + 2) != -1:
            out.append('PLACEHOLDER' if in_str else '"PLACEHOLDER"')
            i = raw.find('}}', i + 2) + 2
        elif in_str:
            if raw[i] == '\\': out.append(raw[i:i + 2]); i += 2; continue
            if raw[i] == '"': in_str = False
            out.append(raw[i]); i += 1
        elif raw.startswith('//', i):
            end = raw.find('\n', i)
            i = n if end == -1 else end
        elif raw.startswith('/*', i):
            end = raw.find('*/', i + 2)
            i = n if end == -1 else end + 2
        else:
            if raw[i] == '"': in_str = True
            out.append(raw[i]); i += 1
    try: return json.loads(''.join(out))
    except ValueError: return None


def resolve(s, env, leading_only=False):
    """Substitute {{vars}} from env. leading_only resolves just a URL's {{base_url}}-style prefix,
    so test values in the environment never get baked into path segments."""
    if not isinstance(s, str): return s
    pattern = r'^\{\{([^}]+)\}\}' if leading_only else r'\{\{([^}]+)\}\}'
    return re.sub(pattern, lambda m: env.get(m.group(1).strip(), m.group(0)), s)


def load_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def auth_config(auth, kind):
    """Key/value settings of an auth block. v2.1 exports use a list; Documenter JSON nests them."""
    cfg = auth.get(kind) or []
    if isinstance(cfg, dict): cfg = (cfg.get('basicConfig') or []) + (cfg.get('advancedConfig') or [])
    return {x['key']: x.get('value') for x in cfg if 'key' in x}


def all_auth(col):
    """Every auth block in the collection: collection level first, then folders and requests."""
    found = [col.get('auth')]
    def walk(items):
        for it in items:
            found.append(it.get('auth'))
            if 'item' in it: walk(it['item'])
            else: found.append((it.get('request') or {}).get('auth'))
    walk(col.get('item', []))
    return [a for a in found if a and a.get('type') not in (None, 'noauth')]


def build_security(col, env, extra_scopes):
    auths = all_auth(col)
    auth = auths[0] if auths else {}
    atype = auth.get('type')
    secdefs, security, conn_params = {}, [], {}
    if atype == 'oauth2':
        cfg = {k: resolve(v, env) for k, v in auth_config(auth, 'oauth2').items()}
        scopes = []   # union of every folder's / request's scopes, plus the ones the API always needs
        for a in auths:
            if a.get('type') == 'oauth2':
                scopes += (resolve(auth_config(a, 'oauth2').get('scope'), env) or '').split()
        scopes = list(OrderedDict.fromkeys(scopes + extra_scopes)) or ['default']
        auth_url = cfg.get('authUrl') or 'https://CHANGE_ME/authorize'
        token_url = cfg.get('accessTokenUrl') or 'https://CHANGE_ME/token'
        secdefs['oauth2_auth'] = {'type': 'oauth2', 'flow': 'accessCode', 'authorizationUrl': auth_url,
                                  'tokenUrl': token_url, 'scopes': {s: s for s in scopes}}
        security = [{'oauth2_auth': scopes}]
        conn_params = {'token': {'type': 'oauthSetting', 'oAuthSettings': {
            'identityProvider': 'oauth2', 'clientId': 'YOUR_CLIENT_ID', 'scopes': scopes,
            'redirectMode': 'GlobalPerConnector',
            'properties': {'IsFirstParty': 'False', 'IsOnbehalfofLoginSupported': False},
            'customParameters': {'authorizationUrl': {'value': auth_url}, 'tokenUrl': {'value': token_url},
                                 'refreshUrl': {'value': token_url}}}}}
    elif atype == 'apikey':
        hdr = auth_config(auth, 'apikey').get('key') or 'x-api-key'
        secdefs['api_key'] = {'type': 'apiKey', 'in': 'header', 'name': hdr}
        security = [{'api_key': []}]
        conn_params = {'api_key': {'type': 'securestring', 'uiDefinition': {
            'displayName': hdr, 'description': f'The {hdr} for this API', 'tooltip': f'Provide your {hdr}',
            'constraints': {'tabIndex': 2, 'clearText': False, 'required': 'true'}}}}
    else:  # bearer / unknown -> treat token as API key "Bearer <token>"
        secdefs['api_key'] = {'type': 'apiKey', 'in': 'header', 'name': 'Authorization'}
        security = [{'api_key': []}]
        conn_params = {'api_key': {'type': 'securestring', 'uiDefinition': {
            'displayName': 'Bearer token', 'description': 'Enter: Bearer <access token>',
            'tooltip': 'Bearer <token>', 'constraints': {'tabIndex': 2, 'clearText': False, 'required': 'true'}}}}

    unresolved = sorted(set(re.findall(r'\{\{([^}]+)\}\}', json.dumps(secdefs))))
    if unresolved:
        raise ConfigError(f'auth settings use undefined variables: {", ".join(unresolved)}. '
                          'Define them in the collection or pass --env with an environment that does.')
    if atype == 'oauth2':
        insecure = [u for u in (auth_url, token_url) if not u.lower().startswith('https://')]
        if insecure:
            raise ConfigError(f'OAuth URLs must use https: {", ".join(insecure)}')
    return secdefs, security, conn_params


def request_url(req):
    """(raw URL, structured URL) - Documenter JSON keeps the structured form in urlObject.
    A plain-string URL with no structured form gets its query parsed from the raw string."""
    url = req.get('url')
    raw = url if isinstance(url, str) else (url or {}).get('raw', '')
    obj = url if isinstance(url, dict) else req.get('urlObject') or {}
    if 'query' not in obj and '?' in raw:
        query = raw.split('?', 1)[1].split('#')[0]
        obj = {**obj, 'query': [{'key': k, 'value': v} for k, v in parse_qsl(query, keep_blank_values=True)]}
    return raw, obj


def typed_param(name, location, example, description, required=False, array=False):
    """Parameter typed from a "<type>" placeholder. A "(Required)" description prefix marks it required."""
    if REQUIRED_PREFIX_RE.match(description):
        required, description = True, REQUIRED_PREFIX_RE.sub('', description)
    p = OrderedDict(name=name, **{'in': location}, required=required)
    schema = placeholder_schema(example) or {'type': 'string'}
    if array: p.update(type='array', items=schema, collectionFormat='multi')
    else: p.update(schema)
    p['x-ms-summary'] = label(name)
    if description: p['description'] = description
    return p


def build_operation(it, req, method, path, url, folder, opid, warnings):
    name = it['name'].strip()
    op = OrderedDict(operationId=opid, summary=summary_text(name))
    desc = text(req.get('description') or it.get('description'))
    if desc and desc.rstrip('.') != op['summary']: op['description'] = desc
    op['tags'] = [folder or 'General']
    op['parameters'] = []

    path_vars = {v.get('key'): v for v in url.get('variable') or []}
    for pv in re.findall(r'\{([A-Za-z_][A-Za-z0-9_.\-]*)\}', path):
        var = path_vars.get(pv, {})
        p = typed_param(pv, 'path', var.get('value'), text(var.get('description'), 300), required=True)
        p['x-ms-url-encoding'] = 'single'
        op['parameters'].append(p)

    query = [q for q in url.get('query') or [] if not q.get('disabled') and q.get('key')]
    repeats = Counter(q['key'] for q in query)   # a repeated key means the API takes a list
    for q in query:
        if any(p['name'] == q['key'] and p['in'] == 'query' for p in op['parameters']): continue
        op['parameters'].append(typed_param(q['key'], 'query', q.get('value'), text(q.get('description'), 300),
                                            array=repeats[q['key']] > 1))
    for p in op['parameters']:
        if p['in'] != 'query' or p['type'] == 'array': continue
        if p['name'].lower() == 'search' and p['type'] == 'string': p['maxLength'] = SEARCH_MAX_LENGTH
        if p['name'].lower() == 'pagesize' and p['type'] == 'integer' and path.endswith('/detailed'):
            p['minimum'], p['maximum'] = 1, DETAILED_PAGE_SIZE_MAX

    for h in req.get('header') or []:
        k = h.get('key', '').lower()
        if h.get('disabled') or k in ('authorization', 'content-type', 'accept'): continue
        op['parameters'].append({'name': h['key'], 'in': 'header', 'required': False, 'type': 'string',
                                 'x-ms-summary': label(h['key']), 'x-ms-visibility': 'advanced'})

    body = req.get('body') or {}
    mode = body.get('mode')
    content = body.get(mode) if mode else None   # raw: str; formdata/urlencoded: list; file/graphql: dict
    if isinstance(content, str): content = content.strip()
    if content and method in FETCH_METHODS:
        warnings.append(f'"{name}": dropped the request body of a {method.upper()} request; Power Platform '
                        "doesn't allow a body on fetch operations (BodyOrFormDataParameterInFetchOperationNotAllowed)")
    elif content and mode == 'raw':
        parsed = parse_json_loose(content)
        op['parameters'].append({'name': 'body', 'in': 'body', 'required': True,
                                 'schema': infer_schema(parsed) if parsed is not None else dict(UNTYPED)})
    elif content and mode == 'formdata':
        op['consumes'] = ['multipart/form-data']
        for f in content:
            op['parameters'].append({'name': f['key'], 'in': 'formData', 'required': True,
                                     'type': 'file' if f.get('type') == 'file' else 'string',
                                     'x-ms-summary': label(f['key'])})
    elif content:
        warnings.append(f'"{name}": its {mode} request body isn\'t converted; add the parameters by hand')

    # Only the first success response carries a schema: the designer uses just one, and Power Platform's
    # validator flags schemas on 'default' (DefaultResponseHasSchema) or on several responses
    # (OperationHasManyResponsesWithSchema). Error responses are listed for documentation only.
    responses = OrderedDict()
    for r in it.get('response') or []:
        code = str(r.get('code') or 200)
        if code in responses: continue
        responses[code] = {'description': r.get('status') or ('OK' if code.startswith('2') else 'Error')}
        if code.startswith('2') and not any('schema' in x for x in responses.values()):
            example = (r.get('body') or '').strip()
            if example:
                parsed = parse_json_loose(example)
                responses[code]['schema'] = infer_schema(parsed) if parsed is not None else dict(UNTYPED)
    if not any(c.startswith('2') for c in responses):
        responses['200'] = {'description': 'OK', 'schema': dict(UNTYPED)}
    if method != 'delete' and all(r.get('schema') in (None, UNTYPED) for r in responses.values()):
        warnings.append(f'"{name}" has no usable example success response, so its output is untyped; '
                        'add a response schema by hand')
    responses['default'] = {'description': 'Error'}
    op['responses'] = responses
    return op


def build_paths(col, env):
    paths, tags, seen_ids, warnings = OrderedDict(), [], set(), []
    path_case = {}       # lower-cased path -> path as first seen; Power Platform rejects case-only differences
    host_guess = None    # the collection's own API host: the first absolute URL's host

    def walk(items, folder):
        nonlocal host_guess
        for it in items:
            if 'item' in it:
                tag = it['name'].strip()
                if tag not in tags: tags.append(tag)
                walk(it['item'], tag)
                continue
            req = it.get('request')
            if not req: continue
            name = it['name'].strip()
            raw, url = request_url(req)
            raw = resolve(raw, env, leading_only=True)
            m = re.match(r'https?://([^/]+)(/[^?#]*)?', raw)
            if m:
                host_guess = host_guess or m.group(1)
                if m.group(1).lower() != host_guess.lower():
                    # a connector has one host; this request would otherwise be sent to the wrong server
                    warnings.append(f'skipped "{name}": its host {m.group(1)} differs from the API host {host_guess}')
                    continue
                path = m.group(2) or '/'
            else:
                path = re.sub(r'^\{\{[^}]+\}\}', '', raw).split('?')[0]
                if raw.startswith('{{') and not re.fullmatch(r'(/[^\s#]*)?', path):
                    # e.g. "{{upload_url}} (the url from ...)": a URL returned at runtime, not an API path
                    warnings.append(f'skipped "{name}": URL {raw!r} is not a path on the API host')
                    continue
                path = path or '/'
                if not path.startswith('/'): path = '/' + path
            path = re.sub(r'(?<=/):([A-Za-z_][A-Za-z0-9_.\-]*)', r'{\1}', path)
            path = re.sub(r'\{\{([^}]+)\}\}', r'{\1}', path)
            method = (req.get('method') or 'GET').lower()
            if path_case.setdefault(path.lower(), path) != path:
                warnings.append(f'skipped "{name}": {path} differs only in case from {path_case[path.lower()]}, '
                                'which Power Platform rejects (PathRedefined)')
                continue
            existing = paths.get(path, {}).get(method)
            if existing:
                warnings.append(f'skipped "{name}": {method.upper()} {path} is already defined by '
                                f'"{existing["summary"]}"')
                continue
            opid = base = slug(name)
            n = 2
            while opid in seen_ids:
                opid = f'{base}{n}'
                n += 1
            seen_ids.add(opid)
            paths.setdefault(path, OrderedDict())[method] = build_operation(it, req, method, path, url, folder,
                                                                            opid, warnings)

    walk(col.get('item', []), None)
    used = {o['tags'][0] for ops in paths.values() for o in ops.values()}
    tags = [t for t in tags if t in used] + (['General'] if 'General' in used else [])
    return paths, tags, host_guess, warnings


def build_spec(a, paths, tags, host, secdefs, security):
    return OrderedDict([
        ('swagger', '2.0'),
        ('info', {'title': a.title, 'version': '1.0.0',
                  'description': a.description or f'{a.title} custom connector'}),
        ('host', host), ('basePath', a.base_path), ('schemes', ['https']),
        ('consumes', ['application/json']), ('produces', ['application/json']),
        ('securityDefinitions', secdefs), ('security', security),
        ('tags', [{'name': t} for t in tags]),
        ('paths', paths),
        ('x-ms-connector-metadata', [{'propertyName': 'Website', 'propertyValue': a.website},
                                     {'propertyName': 'Privacy policy', 'propertyValue': a.privacy_url},
                                     {'propertyName': 'Categories', 'propertyValue': 'Finance'}])])


def validate(spec):
    """(ok, message); ok is None when the validator isn't installed."""
    try:
        from openapi_spec_validator import validate as validate_spec
    except ImportError:
        return None, 'not validated: pip install -r requirements.txt'
    try:
        validate_spec(json.loads(json.dumps(spec)))
    except Exception as e:
        return False, f'VALIDATION FAILED: {e}'
    return True, 'valid Swagger 2.0'


def write_outputs(out, spec, definition, props):
    class Dumper(yaml.SafeDumper): pass
    Dumper.add_representer(OrderedDict, lambda d, data: d.represent_dict(data.items()))
    os.makedirs(out, exist_ok=True)
    yaml_file, json_file, props_file = (os.path.join(out, f) for f in OUTPUT_FILES)
    with open(yaml_file, 'w', encoding='utf-8') as f:
        yaml.dump(spec, f, Dumper=Dumper, sort_keys=False, width=120, allow_unicode=True)
    with open(json_file, 'w', encoding='utf-8') as f:
        f.write(definition)
    with open(props_file, 'w', encoding='utf-8') as f:
        json.dump(props, f, indent=2)


def main(argv=None):
    ap = argparse.ArgumentParser(description='Convert a Postman collection into a Power Platform custom connector.')
    ap.add_argument('collection')
    ap.add_argument('--title', required=True)
    ap.add_argument('--description', help='connector description shown in Power Platform')
    ap.add_argument('--host')
    ap.add_argument('--base-path', default='/')
    ap.add_argument('--env')
    ap.add_argument('--out', default='connector', help='output folder, written only if generation succeeds')
    ap.add_argument('--publisher', default='YOUR_ORG')
    ap.add_argument('--extra-scopes', default='x-api offline_access',
                    help='OAuth scopes always requested (Active API needs x-api; offline_access gives refresh tokens)')
    ap.add_argument('--website', default='https://CHANGE_ME')
    ap.add_argument('--privacy-url', default='https://CHANGE_ME')
    ap.add_argument('--brand-color', default='#007EE5')
    a = ap.parse_args(argv)

    col = load_json(a.collection)
    env = {v['key']: v.get('value', '') for v in col.get('variable', [])}
    if a.env:
        env.update({v['key']: v.get('value', '') for v in load_json(a.env).get('values', []) if v.get('enabled', True)})

    try:
        secdefs, security, conn_params = build_security(col, env, a.extra_scopes.split())
        paths, tags, host_guess, warnings = build_paths(col, env)
        host = a.host or host_guess
        if not host:
            raise ConfigError('no request has an absolute URL, so the API host is unknown; pass --host')
    except ConfigError as e:
        print(f'ERROR: {e}', file=sys.stderr)
        return 1
    spec = build_spec(a, paths, tags, host, secdefs, security)
    props = {'properties': {'connectionParameters': conn_params, 'iconBrandColor': a.brand_color,
                            'capabilities': [], 'publisher': a.publisher}}

    definition = json.dumps(spec, indent=2, ensure_ascii=False)
    if len(definition.encode('utf-8')) >= MAX_DEFINITION_BYTES:   # indentation alone can push it over
        definition = json.dumps(spec, separators=(',', ':'), ensure_ascii=False)
        print('NOTE: apiDefinition.swagger.json written without indentation to stay under 1 MB')
    errors = []
    ok, message = validate(spec)
    if ok is False: errors.append(message)
    size = len(definition.encode('utf-8'))
    if size >= MAX_DEFINITION_BYTES:
        errors.append(f'apiDefinition.swagger.json is {size:,} bytes; Power Platform requires less than 1 MB')

    # a failed run must not leave a broken definition where `pac connector create` will pick it up
    out = tempfile.mkdtemp(prefix='postman2pp-failed-') if errors else a.out
    write_outputs(out, spec, definition, props)

    n = sum(len(ops) for ops in paths.values())
    print(f'{n} operations across {len(paths)} paths -> {out}  [{"validation failed" if ok is False else message}]')
    for w in warnings: print(f'WARNING: {w}')
    if len(a.title) > MAX_TITLE_CHARS:
        print(f'WARNING: --title is {len(a.title)} characters; Microsoft allows at most {MAX_TITLE_CHARS}')
    if 'CHANGE_ME' in a.website + a.privacy_url: print('WARNING: pass --website and --privacy-url for connector metadata')
    for e in errors: print(f'ERROR: {e}', file=sys.stderr)
    if errors:
        print(f'ERROR: {a.out} was not changed; the failed output is in {out} for inspection', file=sys.stderr)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
