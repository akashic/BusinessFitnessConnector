import contextlib, io, json, os, sys, tempfile, time, unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import postman2pp as p

OAUTH = {'type': 'oauth2', 'oauth2': [
    {'key': 'authUrl', 'value': '{{auth_url}}'},
    {'key': 'accessTokenUrl', 'value': '{{access_token_url}}'},
    {'key': 'scope', 'value': '{{scopes}}'}]}
ENV = {'values': [
    {'key': 'auth_url', 'value': 'https://identity.example.com/connect/authorize', 'enabled': True},
    {'key': 'access_token_url', 'value': 'https://identity.example.com/connect/token', 'enabled': True},
    {'key': 'scopes', 'value': 'core.read', 'enabled': True}]}


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
            request('List clients', 'GET', '{{base_url}}/core/v1/clients?Code=<string>&Code=<string>&PageSize=<integer>',
                    query=[{'key': 'Code', 'value': '<string>'}, {'key': 'Code', 'value': '<string>'},
                           {'key': 'PageSize', 'value': '<integer>', 'description': 'Records per page'}],
                    responses=[{'code': 200, 'status': 'OK', 'body': '{"records": [{"clientID": "<uuid>"}]}'},
                               {'code': 404, 'status': 'Not Found', 'body': '{"title": "Not Found"}'}]),
            request('Get client', 'GET', '{{base_url}}/core/v1/clients/:id',
                    variable=[{'key': 'id', 'value': '<uuid>', 'description': {'content': '<p>Client ID</p>'}}]),
            request('Create client', 'POST', '{{base_url}}/core/v1/clients',
                    body='{\n  "inactive": "<boolean>", // comment\n  "website": "https://example.com",\n'
                         '  "code": "C-{{suffix}}"\n}'),
            request('Duplicate of list', 'GET', '{{base_url}}/core/v1/clients'),
        ]},
        {'name': 'Documents', 'item': [
            request('PUT file bytes', 'PUT', '{{upload_url}} (the url from the upload-session response)'),
        ]},
    ]}


class Labels(unittest.TestCase):
    def test_labels(self):
        cases = {'clientID': 'Client ID', 'ABN': 'ABN', 'URLPath': 'URL Path', 'tax_file_number': 'Tax File Number',
                 'externalId': 'External ID', 'clientIDs': 'Client IDs', 'id': 'ID', 'PageSize': 'Page Size',
                 'addressLine1': 'Address Line1', 'dateOfBirth': 'Date of Birth'}
        for name, expected in cases.items():
            self.assertEqual(p.label(name), expected, name)


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

    def test_long_non_date_string_is_fast(self):
        start = time.time()
        p.infer_schema('2024-01-01T' + '1' * 20000 + 'x')
        self.assertLess(time.time() - start, 0.1)


class EndToEnd(unittest.TestCase):
    def run_main(self, collection, env=ENV, extra=()):
        with tempfile.TemporaryDirectory() as tmp:
            col_path, env_path, out = (os.path.join(tmp, n) for n in ('col.json', 'env.json', 'out'))
            with open(col_path, 'w') as f: json.dump(collection, f)
            with open(env_path, 'w') as f: json.dump(env, f)
            stdout = io.StringIO()
            with contextlib.redirect_stdout(stdout):
                code = p.main([col_path, '--title', 'Test', '--env', env_path, '--out', out, *extra])
            with open(os.path.join(out, 'apiDefinition.swagger.json')) as f: spec = json.load(f)
            with open(os.path.join(out, 'apiProperties.json')) as f: props = json.load(f)
        return code, stdout.getvalue(), spec, props

    def test_collection(self):
        code, output, spec, props = self.run_main(COLLECTION)
        self.assertEqual(code, 0, output)
        if 'valid Swagger 2.0' not in output and 'not validated' not in output: self.fail(output)
        self.assertEqual(spec['host'], 'api.example.com')
        self.assertEqual(spec['info']['description'], 'Test & demo API')

        params = {x['name']: x for x in spec['paths']['/core/v1/clients']['get']['parameters']}
        self.assertEqual(params['Code']['type'], 'array')
        self.assertEqual(params['Code']['collectionFormat'], 'multi')
        self.assertEqual(params['PageSize']['type'], 'integer')
        self.assertEqual(params['PageSize']['x-ms-summary'], 'Page Size')
        self.assertEqual(params['PageSize']['description'], 'Records per page')

        path_param = spec['paths']['/core/v1/clients/{id}']['get']['parameters'][0]
        self.assertEqual((path_param['format'], path_param['x-ms-summary'], path_param['description']),
                         ('uuid', 'ID', 'Client ID'))

        body = spec['paths']['/core/v1/clients']['post']['parameters'][0]['schema']['properties']
        self.assertEqual(body['inactive']['type'], 'boolean')
        self.assertIn('website', body)

        responses = spec['paths']['/core/v1/clients']['get']['responses']
        self.assertEqual(responses['404']['schema'], {'$ref': '#/definitions/Error'})
        self.assertIn('traceId', spec['definitions']['Error']['properties'])

        self.assertIn('skipped "Duplicate of list"', output)
        self.assertIn('skipped "PUT file bytes"', output)
        self.assertEqual(len(spec['paths']), 2)
        self.assertEqual([t['name'] for t in spec['tags']], ['Clients'])   # empty folders dropped

        oauth = props['properties']['connectionParameters']['token']['oAuthSettings']
        self.assertEqual(oauth['redirectMode'], 'GlobalPerConnector')
        self.assertNotIn('redirectUrl', oauth)
        self.assertEqual(oauth['scopes'], ['core.read', 'x-api', 'offline_access'])

    def test_documenter_format(self):
        col = json.loads(json.dumps(COLLECTION))
        col['auth'] = {'type': 'oauth2', 'oauth2': {'basicConfig': [], 'advancedConfig': OAUTH['oauth2']}}
        for folder in col['item']:
            for it in folder['item']:
                url = it['request']['url']
                it['request']['url'], it['request']['urlObject'] = url['raw'], url
        code, output, spec, _ = self.run_main(col)
        self.assertEqual(code, 0, output)
        self.assertEqual(spec['paths']['/core/v1/clients']['get']['parameters'][0]['type'], 'array')

    def test_undefined_auth_variables_stop_the_run(self):
        with self.assertRaises(SystemExit) as cm:
            self.run_main(COLLECTION, env={'values': []})
        self.assertIn('auth_url', str(cm.exception.code))


if __name__ == '__main__':
    unittest.main()
