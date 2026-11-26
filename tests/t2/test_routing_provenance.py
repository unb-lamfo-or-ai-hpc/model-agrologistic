"""Routing lineage failure controls, without native solvers or a live cache."""

import copy
import importlib.util
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location('review_t2', ROOT/'scripts/t2/reconcile_inputs.py')
T2 = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(T2)


class RoutingProvenance(unittest.TestCase):
    def setUp(self):
        self.group = dict(source='osrm', dataset_id='immutable-route', profile='driving',
                          data_version='v1', service='table', schema_version=1,
                          annotations=['distance', 'duration'], records=7)
        self.asset = dict(population=215, workbook_sha256='a'*64,
                          distance_provenance=dict(provider='osrm', dataset_id='immutable-route',
                                                   profile='driving', osrm_data_versions=['v1']))

    def test_frozen_match_does_not_certify_live_source(self):
        result = T2.review_routing_provenance([self.group], [self.asset], {'215': 'a'*64})
        self.assertEqual(result['cache_records_reviewed'], 7)
        self.assertFalse(result['source_consistency_certified'])
        self.assertFalse(result['current_server_verified'])

    def test_each_routing_identity_component_is_required(self):
        for field in ('source', 'dataset_id', 'profile', 'data_version', 'service',
                      'schema_version', 'annotations'):
            group = copy.deepcopy(self.group)
            group[field] = [] if field == 'annotations' else 'different'
            with self.subTest(field=field), self.assertRaises(ValueError):
                T2.review_routing_provenance([group], [self.asset], {'215': 'a'*64})

    def test_equal_distances_cannot_override_workbook_hash(self):
        with self.assertRaisesRegex(ValueError, 'SHA differs'):
            T2.review_routing_provenance([self.group], [self.asset], {'215': 'b'*64})

    def test_missing_and_ambiguous_manifest_entries_rejected(self):
        for assets in ([], [self.asset, self.asset]):
            with self.assertRaises(ValueError):
                T2.review_routing_provenance([self.group], assets, {'215': 'a'*64})

    def test_second_routing_version_cannot_hide_behind_first(self):
        second = dict(self.group, dataset_id='different-map')
        with self.assertRaises(ValueError):
            T2.review_routing_provenance([self.group, second], [self.asset], {'215': 'a'*64})

    def test_empty_review_and_missing_dataset_rejected(self):
        for groups, hashes in (([], {'215': 'a'*64}), ([self.group], {})):
            with self.assertRaises(ValueError):
                T2.review_routing_provenance(groups, [self.asset], hashes)
        self.asset['distance_provenance']['dataset_id'] = None
        with self.assertRaises(ValueError):
            T2.review_routing_provenance([self.group], [self.asset], {'215': 'a'*64})

    def test_t2_and_t3_ci_paths_survive_reconciliation(self):
        spec = importlib.util.spec_from_file_location(
            'routing_scope', ROOT/'scripts/effective_ci_scope.py'
        )
        scope = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(scope)
        paths = ['tests/t2/test_routing_provenance.py', 'scripts/t2/reconcile_inputs.py',
                 'scripts/prepare_mvp3_t3.py', 'tests/test_mvp3_preparation.py',
                 'experiments/proposals/mvp3_t3_staged_design_20261124.json']
        self.assertTrue(scope.classify(paths)['data_only'])
        self.assertFalse(scope.classify(paths+['src/logic/optimization_gurobipy.py'])['data_only'])


if __name__ == '__main__':
    unittest.main()
