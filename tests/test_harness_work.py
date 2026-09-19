from __future__ import annotations

import copy
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from lai_gateway.errors import GatewayError
from lai_gateway.harness_client import HarnessClient
from lai_gateway.harness_work import HarnessWorkError, run_work
from lai_gateway.local_dev_agent import LocalDevAgent

WS = 'lw-1234567890abcdef'
RUN = 'cr-1234567890abcdef'


class WorkClient:
    def __init__(self):
        self.contract = {'schema_version': 1, 'negotiated': True, 'capabilities': {
            'local_chat_work_runs': True, 'source_repository_write': False}}
        self.workspaces = {'workspaces': [{'workspace_id': WS, 'source_checkout_write': False}]}
        self.models = {'workspace_id': WS, 'models': [{'model_id': 'default', 'available': True}]}
        self.created = {'run': {'control_run_id': RUN, 'mode': 'implement', 'status': 'queued'}}
        self.events = [{'control_run_id': RUN, 'mode': 'implement', 'status': 'running',
                        'terminal': False, 'cursor': 0, 'next_cursor': 3},
                       {'control_run_id': RUN, 'mode': 'implement', 'status': 'succeeded',
                        'terminal': True, 'cursor': 3, 'next_cursor': 7}]
        self.review = {'workspace_id': WS, 'review': {
            'control_run_id': RUN, 'mode': 'implement', 'status': 'succeeded', 'terminal': True,
            'workspace': {'isolated': True, 'changed_paths': ['src/app.py'], 'diff_preview': 'SECRET'},
            'validation': {'last_result': {'status': 'pass', 'exit_code': 0}},
            'stdout': 'SECRET', 'promotion': {'secret': 'SECRET'}}}
        self.calls = []
        self.submissions = 0

    def local_chat_contract(self): return self.contract
    def local_chat_workspaces(self): return self.workspaces
    def local_chat_models(self, workspace_id): return self.models
    def create_local_chat_run(self, **kwargs):
        self.calls.append(('create', kwargs))
        self.submissions += 1
        return self.created
    def get_local_chat_events(self, run_id, cursor=0):
        self.calls.append(('poll', cursor))
        return self.events.pop(0)
    def get_local_chat_review(self, run_id, workspace_id):
        self.calls.append(('review', run_id, workspace_id))
        return self.review


class HarnessWorkTest(unittest.TestCase):
    def run_work(self, client, **kwargs):
        return run_work(client, 'implement', 'Fix the local implementation.', sleep=lambda _: None, **kwargs)

    def test_real_client_contract_cursor_and_sanitized_review(self):
        fixture = WorkClient()
        client = HarnessClient(Mock())
        # Real HarnessClient body/CSRF/query builders, with HTTP payloads from the real schema.
        def transport(method, path, body=None, **kwargs):
            if path.startswith('/v1/local-chat/contract'):
                return {**fixture.contract, 'security': {'csrf_header': 'X-LAI-CSRF', 'csrf_token': 'synthetic'}}
            if path.startswith('/v1/local-chat/workspaces'): return fixture.workspaces
            if path.startswith('/v1/local-chat/models'): return fixture.models
            if path == '/v1/local-chat/runs':
                self.assertEqual(body['model_id'], 'default')
                self.assertEqual(kwargs['extra_headers'], {'X-LAI-CSRF': 'synthetic'})
                return fixture.create_local_chat_run(**body)
            if '/events?' in path:
                return fixture.get_local_chat_events(RUN, int(path.rsplit('cursor=', 1)[1]))
            if '/review?' in path: return fixture.get_local_chat_review(RUN, WS)
            self.fail('unexpected endpoint')
        client._request_json = transport
        result = self.run_work(client)
        self.assertEqual(result['status'], 'ready')
        self.assertEqual([c[1] for c in fixture.calls if c[0] == 'poll'], [0, 3])
        self.assertEqual(fixture.submissions, 1)
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('src/app.py', json.dumps(result))
        self.assertTrue(result['review']['validation_passed'])

    def test_invalid_input_never_contacts_harness(self):
        for kwargs in ({'mode': 'plan'}, {'task': ' '}, {'task': None}, {'workspace_id': ''},
                       {'workspace_id': '../x'}, {'model_id': None}, {'max_polls': True},
                       {'timeout_seconds': float('nan')}, {'timeout_seconds': 0}):
            client = Mock()
            args = dict(mode='implement', task='Fix code') | kwargs
            with self.subTest(kwargs=kwargs), self.assertRaises(HarnessWorkError):
                run_work(client, **args)
            self.assertEqual(client.mock_calls, [])

    def test_bad_registry_and_contract_prevent_submission(self):
        for mutate in (
            lambda c: c.contract['capabilities'].update(source_repository_write=True),
            lambda c: c.workspaces.update(workspaces=[]),
            lambda c: c.workspaces['workspaces'].append({'workspace_id': 'lw-aaaaaaaaaaaaaaaa', 'source_checkout_write': False}),
            lambda c: c.workspaces['workspaces'][0].update(workspace_id='bad'),
            lambda c: c.models.update(workspace_id='lw-aaaaaaaaaaaaaaaa'),
            lambda c: c.models['models'][0].update(available=False),
        ):
            client = WorkClient(); mutate(client)
            with self.assertRaises(HarnessWorkError): self.run_work(client)
            self.assertEqual(client.submissions, 0)

    def test_unknown_workspace_and_model_fail_closed(self):
        for kwargs in ({'workspace_id': 'lw-aaaaaaaaaaaaaaaa'}, {'model_id': 'unknown'}):
            client = WorkClient()
            with self.assertRaises(HarnessWorkError): self.run_work(client, **kwargs)
            self.assertEqual(client.submissions, 0)

    def test_inconsistent_events_and_review_are_rejected(self):
        for mutate in (
            lambda c: c.created['run'].update(control_run_id='bad'),
            lambda c: c.created['run'].update(mode='fix'),
            lambda c: c.events[0].update(control_run_id='cr-aaaaaaaaaaaaaaaa'),
            lambda c: c.events[0].update(next_cursor=-1),
            lambda c: c.events[0].update(terminal=True),
            lambda c: c.events[1].update(next_cursor=2),
            lambda c: c.review.update(workspace_id='lw-aaaaaaaaaaaaaaaa'),
            lambda c: c.review['review'].update(control_run_id='cr-aaaaaaaaaaaaaaaa'),
            lambda c: c.review['review'].update(mode='fix'),
            lambda c: c.review['review'].update(status='running'),
            lambda c: c.review['review']['workspace'].update(isolated=False),
        ):
            client = WorkClient(); mutate(client)
            with self.assertRaises(HarnessWorkError): self.run_work(client)
            self.assertEqual(client.submissions, 1)

    def test_poll_and_deadline_budgets_do_not_cancel_or_resubmit(self):
        client = WorkClient()
        with self.assertRaises(HarnessWorkError): self.run_work(client, max_polls=1)
        self.assertEqual(client.submissions, 1)
        client = WorkClient()
        now = [0.0]
        def sleep(_): now[0] = 20.0
        with self.assertRaises(HarnessWorkError):
            run_work(client, 'implement', 'Fix code', timeout_seconds=10,
                     clock=lambda: now[0], sleep=sleep)
        self.assertEqual(client.submissions, 1)
        self.assertFalse(any(c[0] == 'review' for c in client.calls))

    def test_transport_failure_does_not_leak_or_retry(self):
        client = WorkClient()
        client.create_local_chat_run = Mock(side_effect=GatewayError('SECRET'))
        with self.assertRaises(HarnessWorkError) as caught: self.run_work(client)
        self.assertNotIn('SECRET', str(caught.exception))
        client.create_local_chat_run.assert_called_once()

    def test_failed_unvalidated_or_unchanged_work_cannot_claim_success(self):
        for mutate in (
            lambda c: (c.events[1].update(status='failed'), c.review['review'].update(status='failed')),
            lambda c: c.review['review']['validation'].update(last_result=None),
            lambda c: c.review['review']['workspace'].update(changed_paths=[]),
        ):
            client = WorkClient(); mutate(client)
            self.assertEqual(self.run_work(client)['status'], 'blocked')

    def test_agent_opt_in_binding_and_single_submission(self):
        with tempfile.TemporaryDirectory() as tmp:
            client = WorkClient()
            agent = LocalDevAgent(project_root=tmp, client=Mock(), harness_client=client)
            args = {'mode': 'implement', 'task': 'Fix code'}
            self.assertEqual(agent._execute_work(args)['status'], 'blocked')
            self.assertEqual(client.submissions, 0)
            agent = LocalDevAgent(project_root=tmp, client=Mock(), harness_client=client, allow_work=True)
            expected = 'lw-' + hashlib.sha256(str(Path(tmp).resolve()).encode()).hexdigest()[:16]
            client.workspaces['workspaces'][0]['workspace_id'] = expected
            client.models['workspace_id'] = expected
            client.review['workspace_id'] = expected
            with patch('lai_gateway.harness_work.time.sleep'):
                # Use no polling wait through injected coordinator; real coordinator tested above.
                with patch('lai_gateway.local_dev_agent.run_work', side_effect=lambda c, **kw: run_work(c, sleep=lambda _: None, **kw)):
                    self.assertEqual(agent._execute_work(args)['status'], 'ready')
                    self.assertEqual(agent._execute_work(args)['status'], 'blocked')
            self.assertEqual(client.submissions, 1)
            self.assertEqual(client.calls[0][1]['workspace_id'], expected)
            self.assertEqual(agent._execute_work(args | {'allow_work': True})['status'], 'blocked')

    def test_module_has_no_effect_execution_imports_or_calls(self):
        import ast
        source = Path('lai_gateway/harness_work.py').read_text()
        tree = ast.parse(source)
        forbidden = {'subprocess', 'os', 'local_chat_lifecycle', 'promote_local_chat_run', 'run_process'}
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                self.assertFalse(forbidden & {a.name for a in node.names})
            if isinstance(node, ast.Attribute): self.assertNotIn(node.attr, forbidden)


if __name__ == '__main__':
    unittest.main()
