import contextlib, copy, io, json, os, re, shutil, tempfile, time, unittest

import postman2pp as p

OAUTH = {'type': 'oauth2', 'oauth2': [
    {'key': 'authUrl', 'value': '{{auth_url}}'},
    {'key': 'accessTokenUrl', 'value': '{{access_token_url}}'},
    {'key': 'scope', 'value': '{{scopes}}'}]}
ENV = {'values': [
    {'key': 'auth_url', 'value': 'https://identity.example.com/connect/authorize', 'enabled': True},
    {'key': 'access_token_url', 'value': 'https://identity.example.com/connect/token', 'enabled': True},
    {'key': 'scopes', 'value': 'core.read', 'enabled': True},
    {'key': 'clientId', 'value': 'test-client-guid-from-postman', 'enabled': True}]}


def request(name, method, raw, query=None, variable=None, body=None, responses=None):
    return {'name': name, 'response': responses or [], 'request': {
        'method': method, 'header': [{'key': 'Accept', 'value': 'application/json'}],
        'url': {'raw': raw, 'query': query or [], 'variable': variable or []},
        **({'body': {'mode': 'raw', 'raw': body}} if body else {})}}


COLLECTION = {
    'info': {'name': 'Test API', 'description': '<p>Test &amp; demo API</p>'},
    'auth': OAUTH,
    'variable': [{'key': 'base_url', 'value': 'https://api.example.com'}],
    'item': [
        {'name': 'Documentation', 'item': []},
        {'name': 'Clients', 'item': [
            request('List clients.', 'GET',
                    '{{base_url}}/core/v1/clients?Code=<string>&Code=<string>&PageSize=<integer>&OfficeId=<uuid>',
                    query=[{'key': 'Code', 'value': '<string>'}, {'key': 'Code', 'value': '<string>'},
                           {'key': 'PageSize', 'value': '<integer>', 'description': 'Records per page'},
                           {'key': 'OfficeId', 'value': '<uuid>',
                            'description': {'content': '<p>(Required) Office to list</p>'}}],
                    responses=[{'code': 200, 'status': 'OK', 'body': '{"records": [{"clientID": "<uuid>"}]}'},
                               {'code': 404, 'status': 'Not Found', 'body': '{"title": "Not Found"}'}]),
            request('Get client (minimal)', 'GET', '{{base_url}}/core/v1/clients/:id',
                    variable=[{'key': 'id', 'value': '<uuid>',
                               'description': {'content': '<p>(Required) Client ID</p>'}}]),
            request('Get client notes', 'GET', '{{base_url}}/core/v1/clients/{{clientId}}/notes',
                    responses=[{'code': 200, 'status': 'OK', 'body': '{"notes": []}'}]),
            request('Create client', 'POST', '{{base_url}}/core/v1/clients',
                    body='{\n  "inactive": "<boolean>", // comment\n  "website": "https://example.com",\n'
                         '  "code": "C-{{suffix}}"\n}',
                    responses=[{'code': 201, 'status': 'Created', 'body': '{"id": "<uuid>"}'}]),
            request('Delete client', 'DELETE', '{{base_url}}/core/v1/clients/:id',
                    variable=[{'key': 'id', 'value': '<uuid>'}],
                    responses=[{'code': 200, 'status': 'OK', 'body': ''}]),
            request('Duplicate of list', 'GET', '{{base_url}}/core/v1/clients'),
        ]},
        {'name': 'Documents', 'item': [
            request('PUT file bytes', 'PUT', '{{upload_url}} (the url from the upload-session response)'),
        ]},
    ]}


def run_main(collection, env=ENV, extra=()):
    """(exit code, stdout, stderr, spec, apiProperties); spec and props are None when nothing was written."""
    with tempfile.TemporaryDirectory() as tmp:
        col_path, env_path, out = (os.path.join(tmp, n) for n in ('col.json', 'env.json', 'out'))
        with open(col_path, 'w') as f: json.dump(collection, f)
        with open(env_path, 'w') as f: json.dump(env, f)
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = p.main([col_path, '--title', 'Test', '--env', env_path, '--out', out, *extra])
        spec = props = None
        if os.path.exists(os.path.join(out, 'apiDefinition.swagger.json')):
            with open(os.path.join(out, 'apiDefinition.swagger.json')) as f: spec = json.load(f)
            with open(os.path.join(out, 'apiProperties.json')) as f: props = json.load(f)
    return code, stdout.getvalue(), stderr.getvalue(), spec, props


class Labels(unittest.TestCase):
    def test_labels(self):
        cases = {'clientID': 'Client ID', 'ABN': 'ABN', 'URLPath': 'URL Path', 'tax_file_number': 'Tax File Number',
                 'externalId': 'External ID', 'clientIDs': 'Client IDs', 'id': 'ID', 'PageSize': 'Page Size',
                 'addressLine1': 'Address Line1', 'dateOfBirth': 'Date of Birth'}
        for name, expected in cases.items():
            self.assertEqual(p.label(name), expected, name)

    def test_summaries_follow_microsoft_string_guidance(self):
        self.assertEqual(p.summary_text('Create a Client Entity.'), 'Create a Client Entity')
        self.assertEqual(p.summary_text('List documents (minimal)'), 'List documents - minimal')
        self.assertEqual(p.summary_text('Create/update a job'), 'Create or update a job')
        long = p.summary_text('Get ' + 'very ' * 30 + 'long name')
        self.assertLessEqual(len(long), 80)
        self.assertTrue(long[-1].isalnum())


class Text(unittest.TestCase):
    def test_html_is_stripped_but_literal_angle_brackets_survive(self):
        self.assertEqual(p.text('<p>Amount &lt; 100</p>'), 'Amount < 100')
        self.assertEqual(p.text('amount < 100 and > 5'), 'amount < 100 and > 5')

    def test_markdown_is_flattened(self):
        self.assertEqual(p.text('## Scopes\n**Read** see [docs](https://x.com) and `core.read`'),
                         'Scopes Read see docs (https://x.com) and core.read')


class ParseJsonLoose(unittest.TestCase):
    def test_url_inside_string_survives_comment_stripping(self):
        self.assertEqual(p.parse_json_loose('{"u": "https://x.com/a"} // note'), {'u': 'https://x.com/a'})

    def test_variables(self):
        self.assertEqual(p.parse_json_loose('{"a": "pre-{{y}}", "b": {{x}}, "c": "{{z}}"}'),
                         {'a': 'pre-PLACEHOLDER', 'b': 'PLACEHOLDER', 'c': 'PLACEHOLDER'})

    def test_block_comment_and_escaped_quote(self):
        self.assertEqual(p.parse_json_loose('{/* x */ "a": "say \\"hi\\" // not a comment"}'),
                         {'a': 'say "hi" // not a comment'})


class InferSchema(unittest.TestCase):
    def test_placeholders_are_typed(self):
        props = p.infer_schema({'on': '<boolean>', 'id': '<uuid>', 'n': '<integer>', 'when': '<dateTime>'})['properties']
        self.assertEqual(props['on']['type'], 'boolean')
        self.assertEqual(props['id']['format'], 'uuid')
        self.assertEqual(props['n']['type'], 'integer')
        self.assertEqual(props['when']['format'], 'date-time')

    def test_dates(self):
        self.assertEqual(p.infer_schema('2024-06-07T00:00:00Z')['format'], 'date-time')
        self.assertEqual(p.infer_schema('2024-06-07T00:00:00.123+10:00')['format'], 'date-time')
        self.assertEqual(p.infer_schema('2024-06-07')['format'], 'date')

    def test_long_non_date_string_is_not_slow(self):
        # guards against a backtracking date-time pattern (was ~0.2 s at 8,000 chars); bound is generous for CI
        start = time.time()
        p.infer_schema('2024-01-01T' + '1' * 20000 + 'x')
        self.assertLess(time.time() - start, 1.0)


class EndToEnd(unittest.TestCase):
    def test_collection(self):
        code, output, _, spec, props = run_main(COLLECTION)
        self.assertEqual(code, 0, output)
        if 'valid Swagger 2.0' not in output and 'not validated' not in output: self.fail(output)
        self.assertEqual(spec['host'], 'api.example.com')
        self.assertEqual(spec['info']['description'], 'Test custom connector')

        get_list = spec['paths']['/core/v1/clients']['get']
        self.assertEqual(get_list['summary'], 'List clients')
        params = {x['name']: x for x in get_list['parameters']}
        self.assertEqual(params['Code']['type'], 'array')
        self.assertEqual(params['Code']['collectionFormat'], 'multi')
        self.assertEqual(params['PageSize']['type'], 'integer')
        self.assertEqual(params['PageSize']['x-ms-summary'], 'Page Size')
        self.assertEqual(params['PageSize']['description'], 'Records per page')
        self.assertFalse(params['PageSize']['required'])
        self.assertTrue(params['OfficeId']['required'])                  # "(Required)" in the description
        self.assertEqual(params['OfficeId']['description'], 'Office to list')

        get_one = spec['paths']['/core/v1/clients/{id}']['get']
        self.assertEqual(get_one['summary'], 'Get client - minimal')
        path_param = get_one['parameters'][0]
        self.assertEqual((path_param['format'], path_param['x-ms-summary'], path_param['description']),
                         ('uuid', 'ID', 'Client ID'))

        # environment test values must not be baked into paths
        self.assertIn('/core/v1/clients/{clientId}/notes', spec['paths'])
        self.assertNotIn('test-client-guid-from-postman', json.dumps(spec))

        body = spec['paths']['/core/v1/clients']['post']['parameters'][0]['schema']['properties']
        self.assertEqual(body['inactive']['type'], 'boolean')
        self.assertIn('website', body)

        # only one response per operation carries a schema, and never 'default'
        for ops in spec['paths'].values():
            for op in ops.values():
                self.assertNotIn('schema', op['responses']['default'])
                self.assertLessEqual(sum('schema' in r for r in op['responses'].values()), 1, op['operationId'])
        self.assertNotIn('schema', get_list['responses']['404'])
        self.assertNotIn('schema', spec['paths']['/core/v1/clients/{id}']['delete']['responses']['200'])
        self.assertNotIn('definitions', spec)

        self.assertIn('skipped "Duplicate of list"', output)
        self.assertIn('skipped "PUT file bytes"', output)
        self.assertIn('"Get client (minimal)" has no usable example success response', output)
        self.assertNotIn('"Delete client" has no', output)
        self.assertEqual([t['name'] for t in spec['tags']], ['Clients'])   # empty folders dropped

        oauth = props['properties']['connectionParameters']['token']['oAuthSettings']
        self.assertEqual(oauth['redirectMode'], 'GlobalPerConnector')
        self.assertNotIn('redirectUrl', oauth)
        self.assertEqual(oauth['scopes'], ['core.read', 'x-api', 'offline_access'])

    def test_description_option(self):
        _, _, _, spec, _ = run_main(COLLECTION, extra=['--description', 'Work with Active clients and jobs'])
        self.assertEqual(spec['info']['description'], 'Work with Active clients and jobs')

    def test_documenter_format(self):
        col = copy.deepcopy(COLLECTION)
        col['auth'] = {'type': 'oauth2', 'oauth2': {'basicConfig': [], 'advancedConfig': OAUTH['oauth2']}}
        for folder in col['item']:
            for it in folder['item']:
                url = it['request']['url']
                it['request']['url'], it['request']['urlObject'] = url['raw'], url
        code, output, _, spec, _ = run_main(col)
        self.assertEqual(code, 0, output)
        self.assertEqual(spec['paths']['/core/v1/clients']['get']['parameters'][0]['type'], 'array')

    def test_hyphenated_path_variable_is_valid(self):
        col = {'auth': COLLECTION['auth'], 'item': [
            request('Get client', 'GET', 'https://api.example.com/clients/{{client-id}}',
                    responses=[{'code': 200, 'status': 'OK', 'body': '{"id": "<uuid>"}'}])]}
        code, output, _, spec, _ = run_main(col)
        self.assertEqual(code, 0, output)
        self.assertEqual(spec['paths']['/clients/{client-id}']['get']['parameters'][0]['name'], 'client-id')

    def test_undefined_auth_variables_stop_the_run(self):
        code, _, stderr, spec, _ = run_main(COLLECTION, env={'values': []})
        self.assertEqual(code, 1)
        self.assertIn('auth_url', stderr)
        self.assertIsNone(spec)

    def test_http_auth_urls_are_rejected(self):
        env = copy.deepcopy(ENV)
        env['values'][1]['value'] = 'http://identity.example.com/connect/token'
        code, _, stderr, _, _ = run_main(COLLECTION, env=env)
        self.assertEqual(code, 1)
        self.assertIn('must use https', stderr)

    def test_unknown_host_stops_the_run(self):
        col = copy.deepcopy(COLLECTION)
        col['variable'] = []   # {{base_url}} no longer resolves, so no request has an absolute URL
        code, _, stderr, _, _ = run_main(col)
        self.assertEqual(code, 1)
        self.assertIn('--host', stderr)
        code, output, _, spec, _ = run_main(col, extra=['--host', 'api.example.com'])
        self.assertEqual((code, spec['host']), (0, 'api.example.com'), output)


def mini(*requests):
    """Collection with resolved OAuth settings and the given requests, for focused end-to-end tests."""
    return {'auth': {'type': 'oauth2', 'oauth2': [
        {'key': 'authUrl', 'value': 'https://identity.example.com/connect/authorize'},
        {'key': 'accessTokenUrl', 'value': 'https://identity.example.com/connect/token'}]},
        'item': list(requests)}


OK_RESPONSE = [{'code': 200, 'status': 'OK', 'body': '{"id": "<uuid>"}'}]


class RequestHandling(unittest.TestCase):
    def test_requests_on_another_host_are_skipped(self):
        code, output, _, spec, _ = run_main(mini(
            request('A', 'GET', 'https://api.example.com/a', responses=OK_RESPONSE),
            request('B', 'GET', 'https://other.example.org/b', responses=OK_RESPONSE)))
        self.assertEqual(code, 0, output)
        self.assertEqual(list(spec['paths']), ['/a'])
        self.assertIn('skipped "B": its host other.example.org differs from the API host api.example.com', output)

    def test_host_override_does_not_skip_the_collections_requests(self):
        code, output, _, spec, _ = run_main(mini(request('A', 'GET', 'https://api.example.com/a',
                                                         responses=OK_RESPONSE)),
                                            extra=['--host', 'sandbox.example.com'])
        self.assertEqual((code, spec['host'], list(spec['paths'])), (0, 'sandbox.example.com', ['/a']), output)

    def test_query_is_parsed_from_a_plain_string_url(self):
        col = mini({'name': 'List', 'response': OK_RESPONSE, 'request': {
            'method': 'GET', 'url': 'https://api.example.com/list?Page=<integer>&Search=<string>'}})
        _, _, _, spec, _ = run_main(col)
        params = {x['name']: x for x in spec['paths']['/list']['get']['parameters']}
        self.assertEqual((params['Page']['type'], params['Search']['type']), ('integer', 'string'))

    def test_paths_differing_only_in_case_are_skipped(self):
        code, output, _, spec, _ = run_main(mini(
            request('A', 'GET', 'https://api.example.com/Items', responses=OK_RESPONSE),
            request('B', 'POST', 'https://api.example.com/items', responses=OK_RESPONSE)))
        self.assertEqual(list(spec['paths']), ['/Items'])
        self.assertIn('differs only in case from /Items', output)

    def test_body_on_a_get_is_dropped_with_a_warning(self):
        code, output, _, spec, _ = run_main(mini(
            request('Search', 'GET', 'https://api.example.com/s', body='{"q": "x"}', responses=OK_RESPONSE)))
        self.assertFalse(any(x['in'] == 'body' for x in spec['paths']['/s']['get']['parameters']))
        self.assertIn('"Search": dropped the request body of a GET request', output)

    def test_active_api_search_and_page_size_limits(self):
        _, _, _, spec, _ = run_main(mini(
            request('List', 'GET', 'https://api.example.com/jobs?Search=<string>&PageSize=<integer>',
                    query=[{'key': 'Search', 'value': '<string>'}, {'key': 'PageSize', 'value': '<integer>'}],
                    responses=OK_RESPONSE),
            request('List detailed', 'GET', 'https://api.example.com/jobs/detailed?PageSize=<integer>',
                    query=[{'key': 'PageSize', 'value': '<integer>'}], responses=OK_RESPONSE)))
        listed = {x['name']: x for x in spec['paths']['/jobs']['get']['parameters']}
        self.assertEqual(listed['Search']['maxLength'], 64)
        self.assertNotIn('maximum', listed['PageSize'])           # only /detailed is documented as capped
        detailed = spec['paths']['/jobs/detailed']['get']['parameters'][0]
        self.assertEqual((detailed['minimum'], detailed['maximum']), (1, 100))


class Output(unittest.TestCase):
    def test_api_properties_shape(self):
        _, _, _, _, props = run_main(COLLECTION)
        token = props['properties']['connectionParameters']['token']
        self.assertEqual(token['type'], 'oauthSetting')
        self.assertEqual(token['oAuthSettings']['identityProvider'], 'oauth2')
        self.assertEqual(token['oAuthSettings']['customParameters']['tokenUrl']['value'],
                         'https://identity.example.com/connect/token')
        self.assertEqual(props['properties']['iconBrandColor'], '#007EE5')

    def test_long_title_is_warned_about(self):
        _, output, _, _, _ = run_main(COLLECTION, extra=['--title', 'Business Fitness Active API Connector'])
        self.assertIn('--title is 37 characters', output)

    def test_default_output_folder_is_connector(self):
        with tempfile.TemporaryDirectory() as tmp:
            col_path, env_path = os.path.join(tmp, 'col.json'), os.path.join(tmp, 'env.json')
            with open(col_path, 'w') as f: json.dump(COLLECTION, f)
            with open(env_path, 'w') as f: json.dump(ENV, f)
            cwd = os.getcwd()
            try:
                os.chdir(tmp)
                with contextlib.redirect_stdout(io.StringIO()):
                    self.assertEqual(p.main([col_path, '--title', 'Test', '--env', env_path]), 0)
                self.assertTrue(os.path.exists(os.path.join(tmp, 'connector', 'apiDefinition.swagger.json')))
            finally:
                os.chdir(cwd)

    def test_failed_validation_leaves_output_folder_unchanged(self):
        original = p.validate
        p.validate = lambda spec: (False, 'VALIDATION FAILED: simulated')
        try:
            code, output, stderr, spec, _ = run_main(COLLECTION)
        finally:
            p.validate = original
        failed_dir = re.search(r'output is in (\S+) for inspection', stderr).group(1)
        self.addCleanup(shutil.rmtree, failed_dir, ignore_errors=True)
        self.assertEqual(code, 1)
        self.assertIsNone(spec)                                   # --out was not written
        self.assertTrue(os.path.exists(os.path.join(failed_dir, 'apiDefinition.swagger.json')))
        self.assertIn('VALIDATION FAILED: simulated', stderr)
        self.assertNotIn('ERROR', output)                         # errors go to stderr only

    def test_large_definition_falls_back_to_compact_json(self):
        original = p.MAX_DEFINITION_BYTES
        compact = len(json.dumps(run_main(COLLECTION)[3], separators=(',', ':'), ensure_ascii=False).encode())
        p.MAX_DEFINITION_BYTES = compact + 10                     # indented is over the limit, compact is under
        try:
            code, output, _, spec, _ = run_main(COLLECTION)
        finally:
            p.MAX_DEFINITION_BYTES = original
        self.assertEqual(code, 0, output)
        self.assertIn('written without indentation', output)
        self.assertIsNotNone(spec)


if __name__ == '__main__':
    unittest.main()
