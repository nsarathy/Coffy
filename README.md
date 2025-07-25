# ☕ Coffy

[![PyPI version](https://img.shields.io/pypi/v/coffy)](https://pypi.org/project/coffy/)

**Coffy** is a lightweight embedded database engine for Python, designed for local-first apps, scripts, and tools. It includes:

- `coffy.nosql`: A simple JSON-backed NoSQL engine with a fluent, chainable query interface  
- `coffy.graph`: An graph engine built on `networkx` with advanced filtering and logic-based querying  
- `coffy.sql`: A wrapper over `SQLite` for executing raw SQL  

---
## Latest Updates
- Added projection and dot-notation support for nested fields in NoSQL queries. Expanded logic chaining (`_and`, `_or`, `_not`) with improved test and better query semantics.
- GraphDB now supports saving query results, fixed relationship type serialization, and added more robust unit coverage.
- Unit tests added to test NoSQL and Graph database features.
- Documentation Updated.

---

## 🔧 Install

```bash
pip install coffy
```

---

## 📂 Modules

### `coffy.nosql`

- Embedded NoSQL document store with a fluent, chainable query API
- Supports nested fields, logical filters, aggregations, projections, and joins
- Built for local usage with optional persistence; minimal setup, fast iteration

📄 [NoSQL Documentation →](https://github.com/nsarathy/Coffy/blob/main/Documentation/NOSQL_DOCS.md)

---

### `coffy.graph`

- Lightweight, file-backed graph database using `networkx` under the hood
- Supports pattern matching, label/type filtering, logical conditions, and projections
- Query results can be saved, updated, or transformed; ideal for local, schema-flexible graph data

📄 [Graph Documentation →](https://github.com/nsarathy/Coffy/blob/main/Documentation/GRAPH_DOCS.md)

---

### `coffy.sql`

- SQLite-backed engine with raw SQL query support  
- Outputs as readable tables or exportable lists  
- Uses in-memory DB by default, or json-based if initialized with a path  

📄 [SQL Documentation →](https://github.com/nsarathy/Coffy/blob/main/Documentation/SQL_DOCS.md)

---

## 🧪 Example

```python
from coffy.nosql import db

users = db("users", path="users.json")
users.add({"id": 1, "name": "Neel"})
print(users.where("name").eq("Neel").first())
```

```python
from coffy.graph import GraphDB

g = GraphDB(directed=True)
g.add_nodes([{"id": 1, "name": "Neel"}, {"id": 2, "name": "Tanaya"}])
g.add_relationships([{"source": 1, "target": 2, "type": "friend"}])
print(g.find_relationships(type="friend"))
```

```python
from coffy.sql import init, query

init("app.db")
query("CREATE TABLE test (id INT, name TEXT)")
query("INSERT INTO test VALUES (1, 'Neel')")
print(query("SELECT * FROM test"))
```

---

## 📄 License

MIT © 2025 nsarathy