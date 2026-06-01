# coffy/tests/test_sql1.py
# author

import unittest
import tempfile
import os

from coffy.sql import init, close, Model, Integer, Real, Text, Blob, raw


class TestORMModule(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Define models locally so tests do not depend on any example models
        class User(Model):
            __tablename__ = "users"
            id = Integer(primary_key=True, nullable=False)
            name = Text(nullable=False)
            age = Integer()
            occupation = Text()
            city = Text()

        class Post(Model):
            __tablename__ = "posts"
            id = Integer(primary_key=True, nullable=False)
            user_id = Integer(nullable=False)
            title = Text(nullable=False)
            body = Text()

        class Product(Model):
            __tablename__ = "products"
            id = Integer(primary_key=True, nullable=False)
            name = Text(nullable=False, default="unknown")
            price = Real(nullable=False)
            blob = Blob()  # unused, just to exercise ddl

        cls.User = User
        cls.Post = Post
        cls.Product = Product

    def setUp(self):
        self.temp_db_path = tempfile.NamedTemporaryFile(
            delete=False, suffix=".sqlite"
        ).name
        init(self.temp_db_path)
        # clean create
        self.User.objects.drop_table()
        self.Post.objects.drop_table()
        self.Product.objects.drop_table()
        self.User.objects.create_table()
        self.Post.objects.create_table()
        self.Product.objects.create_table()

        # seed
        self.User.objects.insert(
            id=1, name="Neel", age=22, occupation="RA", city="West Lafayette"
        )
        self.User.objects.insert(
            id=2, name="Tanaya", age=24, occupation="Engineer", city="Indianapolis"
        )
        self.User.objects.bulk_insert(
            [
                {
                    "id": 3,
                    "name": "Alice",
                    "age": 30,
                    "occupation": "Wonderland",
                    "city": "Wonderland",
                },
                {
                    "id": 4,
                    "name": "Bob",
                    "age": 25,
                    "occupation": "Engineer",
                    "city": None,
                },
                {
                    "id": 5,
                    "name": "Charlie",
                    "age": 35,
                    "occupation": "Electrician",
                    "city": "New York",
                },
            ]
        )
        self.Post.objects.bulk_insert(
            [
                {"id": 10, "user_id": 1, "title": "Hello", "body": "First post"},
                {"id": 11, "user_id": 2, "title": "On Engineering", "body": "Notes"},
                {"id": 12, "user_id": 5, "title": "Wires", "body": "Sparks"},
            ]
        )
        self.Product.objects.bulk_insert(
            [
                {"id": 1, "name": "wire", "price": 1.5},
                {"id": 2, "name": "bolt", "price": 0.5},
                {"id": 3, "name": "nut", "price": 0.75},
                {"id": 4, "price": 2.0},  # default name
            ]
        )

    def tearDown(self):
        close()
        os.remove(self.temp_db_path)

    def test_crud_round_trip(self):
        # create
        new_id = self.User.objects.insert(
            id=9, name="Zed", age=28, occupation="Dev", city="NYC"
        )
        self.assertEqual(new_id, 9)

        # read
        row = self.User.objects.get(id=9)
        self.assertEqual(row["name"], "Zed")

        # update
        n = self.User.objects.update([("id", "=", 9)], city="Brooklyn", age=29)
        self.assertEqual(n, 1)
        row = self.User.objects.get(id=9)
        self.assertEqual((row["city"], row["age"]), ("Brooklyn", 29))

        # delete
        n = self.User.objects.delete([("id", "=", 9)])
        self.assertEqual(n, 1)
        self.assertIsNone(self.User.objects.get(id=9))

    def test_bulk_insert_and_count(self):
        added = self.User.objects.bulk_insert(
            [
                {"id": 20, "name": "Mira"},
                {"id": 21, "name": "Ravi", "age": 31},
            ]
        )
        self.assertEqual(added, 2)
        res = raw("SELECT COUNT(*) AS c FROM users WHERE id IN (?,?)", [20, 21])
        self.assertEqual(res[0]["c"], 2)

    def test_where_nested_and_or_in_isnull(self):
        q = (
            self.User.objects.query()
            .select("id", "name")
            .where(
                (
                    [("age", ">", 21), ("city", "IS NOT", None)],
                    "OR",
                    ("name", "IN", ["Alice", "Nobody"]),
                )
            )
            .order_by("id ASC")
        )
        data = q.all().as_list()
        names = [r["name"] for r in data]
        self.assertIn("Alice", names)
        self.assertIn("Tanaya", names)
        self.assertNotIn("Bob", names)

    def test_order_by_limit_offset_and_qualified(self):
        res = (
            self.User.objects.query()
            .select("users.id", "users.name")
            .order_by("users.id DESC")
            .limit(2, offset=1)
            .all()
        )
        ids = [r["id"] for r in res.as_list()]
        self.assertEqual(len(ids), 2)
        self.assertTrue(ids[0] > ids[1])

    def test_join_basic(self):
        res = (
            self.User.objects.query()
            .select("users.id", "users.name", "posts.title")
            .join("posts", on="users.id = posts.user_id")
            .order_by("users.id ASC")
            .all()
        )
        rows = res.as_list()
        self.assertEqual(rows[0]["name"], "Neel")
        self.assertEqual(rows[0]["title"], "Hello")
        self.assertEqual(rows[1]["name"], "Tanaya")

    def test_group_by_having(self):
        res = (
            self.User.objects.query()
            .select("city", "COUNT(*) AS cnt", "AVG(age) AS avg_age")
            .group_by("city")
            .having([("cnt", ">", 1)])
            .order_by("cnt DESC")
            .all()
        )
        rows = res.as_list()
        # only cities with more than one user
        self.assertTrue(all(r["cnt"] > 1 for r in rows))

    def test_aggregate_shortcut(self):
        agg = self.User.objects.query().aggregate(
            total="COUNT(*)", avg_age="AVG(age)", max_age="MAX(age)"
        )
        self.assertIn("total", agg)
        self.assertTrue(agg["total"] >= 5)
        self.assertGreaterEqual(agg["max_age"], agg["avg_age"])

    def test_first_none_when_empty(self):
        row = self.User.objects.query().where([("name", "=", "__nope__")]).first()
        self.assertIsNone(row)

    def test_get_eq_filters(self):
        row = self.User.objects.get(name="Alice", age=30)
        self.assertEqual(row["id"], 3)

    def test_identifier_validation_blocks_injection(self):
        # invalid identifier in order_by should raise
        with self.assertRaises(ValueError):
            self.User.objects.query().order_by("users.id; DROP TABLE users").all()
        with self.assertRaises(ValueError):
            self.User.objects.query().group_by("users.id, -- comment").all()

    def test_value_parameterization_blocks_injection(self):
        # put an injection string as a value, table should survive
        inj = "x'); DROP TABLE users; --"
        self.User.objects.insert(id=99, name=inj)
        # still queryable
        res = raw("SELECT COUNT(*) AS c FROM users WHERE id=99")
        self.assertEqual(res[0]["c"], 1)
        # users still exists
        res2 = raw("SELECT COUNT(*) AS c FROM users")
        self.assertGreater(res2[0]["c"], 0)

    def test_join_type_validation(self):
        with self.assertRaises(ValueError):
            self.User.objects.query().join(
                "posts", on="users.id = posts.user_id", kind="CROSS"
            ).all()

    def test_cte_via_raw(self):
        res = raw(
            "WITH older AS (SELECT * FROM users WHERE age > ?) "
            "SELECT id, name FROM older WHERE city IS NOT NULL ORDER BY id",
            [25],
        )
        names = [r["name"] for r in res.as_list()]
        self.assertIn("Alice", names)
        self.assertIn("Charlie", names)
        self.assertNotIn("Bob", names)

    def test_defaults_and_not_null(self):
        # product id 4 had no name provided, should use default "unknown"
        row = raw("SELECT name, price FROM products WHERE id=4")[0]
        self.assertEqual(row["name"], "unknown")
        self.assertEqual(row["price"], 2.0)
        # inserting NULL into not null field should fail
        with self.assertRaises(Exception):
            self.Product.objects.insert(id=5, name=None, price=1.0)

    def test_drop_and_recreate(self):
        self.Post.objects.drop_table()
        # table should be gone
        with self.assertRaises(Exception):
            raw("SELECT COUNT(*) AS c FROM posts")
        # recreate
        self.Post.objects.create_table()
        res = raw("SELECT COUNT(*) AS c FROM posts")
        self.assertEqual(res[0]["c"], 0)

    def test_blob_column_exists_in_schema(self):
        # ensure schema created cleanly
        cols = raw("PRAGMA table_info(products)")
        names = [r["name"] for r in cols.as_list()]
        self.assertIn("blob", names)

    def test_limit_without_offset(self):
        rows = (
            self.User.objects.query()
            .select("id")
            .order_by("id ASC")
            .limit(1)
            .all()
            .as_list()
        )
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["id"], 1)

    def test_with_cte_orm_method(self):
        # Use Query.with_cte() to filter older users via a CTE
        res = (
            self.User.objects.query()
            .with_cte("older", "SELECT * FROM users WHERE age > ?", [25])
            .select("id", "name")
            .where([("id", "IN", [3, 5])])
            .order_by("id ASC")
            .all()
            .as_list()
        )
        names = [r["name"] for r in res]
        self.assertIn("Alice", names)
        self.assertIn("Charlie", names)
        self.assertNotIn("Neel", names)

    def test_left_join(self):
        # LEFT JOIN includes users with no posts (Bob, id=4, has no post)
        res = (
            self.User.objects.query()
            .select("users.id", "users.name", "posts.title")
            .join("posts", on="users.id = posts.user_id", kind="LEFT")
            .order_by("users.id ASC")
            .all()
            .as_list()
        )
        ids_in_result = [r["id"] for r in res]
        # Bob (id=4) appears in a LEFT JOIN even without a matching post
        self.assertIn(4, ids_in_result)

    def test_update_no_match_returns_zero(self):
        n = self.User.objects.update([("id", "=", 9999)], city="Nowhere")
        self.assertEqual(n, 0)

    def test_delete_no_match_returns_zero(self):
        n = self.User.objects.delete([("id", "=", 9999)])
        self.assertEqual(n, 0)

    def test_to_sqldict_utility(self):
        from coffy.sql import to_sqldict

        plain = [{"id": 1, "name": "X"}, {"id": 2, "name": "Y"}]
        sd = to_sqldict(plain)
        self.assertEqual(sd.as_list(), plain)
        self.assertEqual(sd[0]["name"], "X")


print("SQL ORM tests:")

unittest.TextTestRunner().run(
    unittest.TestLoader().loadTestsFromTestCase(TestORMModule)
)
