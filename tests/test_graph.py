# coffy/graph/graph_tests.py
# author: nsarathy

import json
import os

import tempfile
import unittest

from coffy.graph import GraphDB


class TestGraphDB(unittest.TestCase):

    def setUp(self):
        self.temp_path = tempfile.NamedTemporaryFile(delete=False, suffix=".json").name
        self.db = GraphDB(path=self.temp_path)
        self.db.add_node("A", labels="Person", name="Alice", age=30)
        self.db.add_node("B", labels="Person", name="Bob", age=25)
        self.db.add_node("C", labels="Person", name="Carol", age=40)
        self.db.add_relationship("A", "B", rel_type="KNOWS", since=2010)
        self.db.add_relationship("B", "C", rel_type="KNOWS", since=2015)

        # Create directed graph
        self.temp_path_directed = tempfile.NamedTemporaryFile(
            delete=False, suffix="_directed.json"
        ).name
        self.directed_db = GraphDB(directed=True, path=self.temp_path_directed)
        self.directed_db.add_node("A")
        self.directed_db.add_node("B")
        self.directed_db.add_node("C")
        self.directed_db.add_relationship("A", "B", _type="KNOWS")
        self.directed_db.add_relationship("B", "C", _type="KNOWS")

    def tearDown(self):
        os.remove(self.temp_path)

    def test_add_and_get_node(self):
        self.db.add_node("D", labels="Person", name="Dan")
        node = self.db.get_node("D")
        self.assertEqual(node["name"], "Dan")

    def test_remove_node(self):
        self.db.remove_node("C")
        self.assertFalse(self.db.has_node("C"))

    def test_remove_node_by_label(self):
        self.db.add_nodes(
            [
                {"id": "D", "_labels": ["Penguin"], "name": "Dan", "age": 30},
                {"id": "E", "_labels": ["Penguin"], "name": "Eve", "age": 25},
                {"id": "F", "_labels": ["Fish"], "name": "Fido", "age": 5},
            ]
        )
        self.db.remove_nodes_by_label("Penguin")
        self.db.remove_nodes_by_label("NonExistentLabel")  # Should not raise error
        self.assertFalse(self.db.has_node("D"))
        self.assertFalse(self.db.has_node("E"))
        self.assertTrue(self.db.has_node("F"))

    def test_add_and_get_relationship(self):
        rel = self.db.get_relationship("A", "B")
        self.assertEqual(rel["_type"], "KNOWS")

    def test_update_node(self):
        self.db.update_node("A", age=35, city="Wonderland")
        node = self.db.get_node("A")
        self.assertEqual(node["age"], 35)
        self.assertEqual(node["city"], "Wonderland")

    def test_update_relationship(self):
        self.db.update_relationship("A", "B", since=2020, weight=0.8)
        rel = self.db.get_relationship("A", "B")
        self.assertEqual(rel["since"], 2020)
        self.assertEqual(rel["weight"], 0.8)

    def test_set_node_update(self):
        self.db.set_node("A", name="Alicia", mood="happy")
        node = self.db.get_node("A")
        self.assertEqual(node["name"], "Alicia")
        self.assertEqual(node["mood"], "happy")

    def test_set_node_add(self):
        self.db.set_node("Z", labels="Robot", name="Zeta", age=5)
        self.assertTrue(self.db.has_node("Z"))
        node = self.db.get_node("Z")
        self.assertEqual(node["name"], "Zeta")
        self.assertEqual(node["age"], 5)
        self.assertIn("Robot", node["_labels"])

    def test_remove_relationship(self):
        self.db.remove_relationship("A", "B")
        self.assertFalse(self.db.has_relationship("A", "B"))

    def test_remove_relationships_by_type(self):
        self.db.add_relationship("A", "C", rel_type="KNOWS OF", since=2010)
        self.assertEqual(self.db.count_relationships_by_type("KNOWS"), 2)
        self.assertEqual(self.db.count_relationships_by_type("KNOWS OF"), 1)
        self.db.remove_relationships_by_type("KNOWS")
        self.assertEqual(self.db.count_relationships_by_type("KNOWS"), 0)
        self.assertEqual(self.db.count_relationships_by_type("KNOWS OF"), 1)

    def test_find_nodes_basic(self):
        results = self.db.find_nodes(name="Alice")
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Alice")

    def test_find_nodes_logic_or(self):
        results = self.db.find_nodes(_logic="or", name="Alice", age={"gt": 35})
        names = {r["name"] for r in results}
        self.assertIn("Alice", names)
        self.assertIn("Carol", names)

    def test_find_nodes_logic_not(self):
        results = self.db.find_nodes(_logic="not", age={"lt": 35})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["name"], "Carol")

    def test_find_nodes_doc_examples(self):
        # OR example: older than 30 OR named 'Alice'
        results_or = self.db.find_nodes(
            label="Person", _logic="or", age={"gt": 30}, name="Alice"
        )
        names_or = {r["name"] for r in results_or}
        self.assertIn("Alice", names_or)
        self.assertIn("Carol", names_or)
        self.assertNotIn("Bob", names_or)

        # NOT example: NOT under 25
        results_not = self.db.find_nodes(label="Person", _logic="not", age={"lt": 25})
        self.assertEqual(
            len(results_not), 3
        )  # Since Alice (30), Bob (25), Carol (40) are all NOT < 25

    def test_find_by_label(self):
        results = self.db.find_by_label("Person")
        self.assertEqual(len(results), 3)

    def test_find_relationships_type_and_filter(self):
        results = self.db.find_relationships(rel_type="KNOWS", since={"gte": 2011})
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["target"], "C")

    def test_project_node_fields(self):
        result = self.db.project_node("A", fields=["name"])
        self.assertEqual(result, {"name": "Alice"})

    def test_project_relationship_fields(self):
        result = self.db.project_relationship("A", "B", fields=["since"])
        self.assertEqual(result, {"since": 2010})

    def test_match_node_path(self):
        pattern = [{"rel_type": "KNOWS", "node": {"name": "Bob"}}]
        paths = self.db.match_node_path(start={"name": "Alice"}, pattern=pattern)
        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0][0]["name"], "Alice")
        self.assertEqual(paths[0][1]["name"], "Bob")

    def test_match_full_path(self):
        pattern = [
            {"rel_type": "KNOWS", "node": {"name": "Bob"}},
            {"rel_type": "KNOWS", "node": {"name": "Carol"}},
        ]
        results = self.db.match_full_path(start={"name": "Alice"}, pattern=pattern)
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["nodes"][2]["name"], "Carol")
        self.assertEqual(results[0]["relationships"][0]["type"], "KNOWS")

    def test_match_path_structured(self):
        pattern = [{"rel_type": "KNOWS", "node": {"name": "Bob"}}]
        result = self.db.match_path_structured(start={"name": "Alice"}, pattern=pattern)
        self.assertEqual(len(result), 1)
        path = result[0]["path"]
        self.assertEqual(path[0]["node"]["name"], "Alice")
        self.assertEqual(path[1]["relationship"]["type"], "KNOWS")
        self.assertEqual(path[2]["node"]["name"], "Bob")

    def test_save_and_load(self):
        self.db.save()
        new_db = GraphDB(path=self.temp_path)
        self.assertTrue(new_db.has_node("A"))
        self.assertTrue(new_db.has_relationship("A", "B"))

    def test_save_query_result(self):
        result = self.db.find_nodes(name="Alice")
        temp_result_path = self.temp_path.replace(".json", "_result.json")
        self.db.save_query_result(result, path=temp_result_path)
        with open(temp_result_path) as f:
            loaded = json.load(f)
        self.assertEqual(loaded[0]["name"], "Alice")
        os.remove(temp_result_path)

    def test_graph_aggregations(self):
        # Structural aggregations
        self.assertEqual(self.db.count_nodes(), 3)
        self.assertEqual(self.db.count_relationships(), 2)

        # Degree distribution: A (1), B (2), C (1)
        self.assertAlmostEqual(self.db.avg_degree(), 1.33, delta=0.01)
        self.assertEqual(self.db.min_degree(), 1)
        self.assertEqual(self.db.max_degree(), 2)

    def test_graph_aggregations_with_filtering(self):
        self.db.add_relationship("A", "C", rel_type="KNOWS OF", since=2018)
        self.assertEqual(self.db.count_relationships_by_type("KNOWS"), 2)
        self.assertEqual(self.db.count_relationships_by_type("KNOWS OF"), 1)
        self.assertEqual(self.db.count_relationships_by_type("DOESNT KNOW"), 0)
        self.db.add_nodes(
            [
                {"id": "DO", "_labels": ["Orangutan"], "name": "Dan", "age": 30},
                {"id": "EO", "_labels": ["Orangutan"], "name": "Eve", "age": 25},
                {"id": "FO", "_labels": ["Shark"], "name": "Fido", "age": 5},
            ]
        )
        self.assertEqual(self.db.count_nodes_by_label("Orangutan"), 2)
        self.assertEqual(self.db.count_nodes_by_label("Shark"), 1)
        self.assertEqual(self.db.count_nodes_by_label("NonExistentLabel"), 0)

    def test_graph_result_aggregates(self):
        res = self.db.find_nodes(label="Person", fields=["name", "age"])
        self.assertEqual(res.count(), 3)
        self.assertEqual(res.sum("age"), 95)
        self.assertEqual(res.avg("age"), 95 / 3)
        self.assertEqual(res.min("age"), 25)
        self.assertEqual(res.max("age"), 40)
        self.assertEqual(res.first()["name"], "Alice")

    def test_total_degree_undirected(self):
        # A-B, B-C → degrees: A(1), B(2), C(1) → total = 4
        self.assertEqual(self.db.total_degree(), 4)

    def test_directed_degrees(self):
        # Degrees:
        # in-degrees: A(0), B(1), C(1)
        # out-degrees: A(1), B(1), C(0)

        self.assertEqual(self.directed_db.total_in_degree(), 2)
        self.assertEqual(self.directed_db.avg_in_degree(), 2 / 3)
        self.assertEqual(self.directed_db.min_in_degree(), 0)
        self.assertEqual(self.directed_db.max_in_degree(), 1)

        self.assertEqual(self.directed_db.total_out_degree(), 2)
        self.assertEqual(self.directed_db.avg_out_degree(), 2 / 3)
        self.assertEqual(self.directed_db.min_out_degree(), 0)
        self.assertEqual(self.directed_db.max_out_degree(), 1)

    def test_directed_degree_errors_on_undirected(self):
        with self.assertRaises(ValueError):
            self.db.total_in_degree()
        with self.assertRaises(ValueError):
            self.db.avg_out_degree()

    def test_degree(self):
        self.assertEqual(self.db.degree("A"), 1)
        self.assertEqual(self.db.degree("B"), 2)

    def test_neighbors(self):
        neighbors = self.db.neighbors("B")
        self.assertIn("A", neighbors)
        self.assertIn("C", neighbors)

    def test_nodes_export(self):
        nodes = self.db.nodes()
        ids = [n["id"] for n in nodes]
        self.assertIn("A", ids)
        self.assertIn("B", ids)
        self.assertIn("C", ids)

    def test_relationships_export(self):
        rels = self.db.relationships()
        rel_pairs = [(r["source"], r["target"]) for r in rels]
        self.assertIn(("A", "B"), rel_pairs)
        self.assertIn(("B", "C"), rel_pairs)

    def test_to_dict(self):
        graph_dict = self.db.to_dict()
        self.assertIn("nodes", graph_dict)
        self.assertIn("relationships", graph_dict)
        self.assertEqual(len(graph_dict["nodes"]), 3)
        self.assertEqual(len(graph_dict["relationships"]), 2)

    def test_load_empty_file(self):
        empty_path = self.temp_path.replace(".json", "_empty.json")
        with open(empty_path, "w", encoding="utf-8") as f:
            f.write("")  # empty file
        db2 = GraphDB(path=empty_path)
        self.assertEqual(db2.count_nodes(), 0)
        os.remove(empty_path)

    def test_load_malformed_json(self):
        bad_path = self.temp_path.replace(".json", "_bad.json")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write("{ not: valid }")
        with self.assertRaises(json.JSONDecodeError):
            GraphDB(path=bad_path)
        os.remove(bad_path)

    def test_find_nodes_with_limit(self):
        results = self.db.find_nodes(label="Person", limit=2)
        self.assertEqual(len(results), 2)

    def test_find_nodes_with_offset(self):
        results = self.db.find_nodes(label="Person", offset=10)
        self.assertEqual(len(results), 0)

    def test_find_nodes_limit_and_offset(self):
        all_results = self.db.find_nodes(label="Person").as_list()
        sliced = self.db.find_nodes(label="Person", offset=1, limit=1).as_list()
        self.assertEqual(sliced[0], all_results[1])

    def test_find_relationships_with_limit(self):
        results = self.db.find_relationships(rel_type="KNOWS", limit=1)
        self.assertEqual(len(results), 1)

    def test_find_by_label_with_limit_offset(self):
        results = self.db.find_by_label("Person", limit=1, offset=2)
        self.assertEqual(len(results), 1)

    def test_find_by_relationship_type_with_offset_out_of_range(self):
        results = self.db.find_by_relationship_type("KNOWS", offset=10)
        self.assertEqual(len(results), 0)

    def test_clear(self):
        self.db.clear()
        self.assertEqual(self.db.count_nodes(), 0)
        self.assertEqual(self.db.count_relationships(), 0)


print("Graph tests:")
unittest.TextTestRunner().run(unittest.TestLoader().loadTestsFromTestCase(TestGraphDB))
