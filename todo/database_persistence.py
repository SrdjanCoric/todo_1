import psycopg2
import psycopg2.extras
import logging
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class DatabasePersistence:
    def __init__(self):
        if os.environ.get('FLASK_ENV') == 'production':
            self.connection = psycopg2.connect(os.environ['DATABASE_URL'])
            self._setup_schema()
        else:
            self.connection = psycopg2.connect(dbname="todos")
            self._setup_schema()

    def all_lists(self):
        with self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            cur.execute("SELECT * FROM lists")
            result = cur.fetchall()
            lists = [dict(result) for result in result]
            for lst in lists:
                todos = self._find_todos_for_list(lst['id'])
                lst.setdefault('todos', todos)
            return lists

    def find_list(self, list_id):
        with self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            query = "SELECT * FROM lists WHERE id = %s"
            cur.execute(query, (list_id,))
            logger.info(f"Executing query: {query} with list_id: {list_id}")
            lst = dict(cur.fetchone())
            #highlight
            todos = self._find_todos_for_list(list_id)
            lst.setdefault('todos', todos)
            #endhighlight
            return lst

    def create_new_list(self, name):
        with self.connection.cursor() as cur:
            query = "INSERT INTO lists (name) VALUES (%s)"
            cur.execute(query, (name,))
            logger.info(f"Executing query: {query} with name: {name}")
            self.connection.commit()

    def update_list_name(self, list_id, new_name):
        with self.connection.cursor() as cur:
            query = "UPDATE lists SET name = %s WHERE id = %s"
            cur.execute(query, (new_name, list_id,))
            logger.info(f"Executing query: {query} with new_name: {new_name} and id: {list_id}")
            self.connection.commit()

    def delete_list(self, list_id):
        with self.connection.cursor() as cur:
            query1 = "DELETE FROM todos WHERE list_id = %s"
            query2 = "DELETE FROM lists WHERE id = %s"
            cur.execute(query1, (list_id,))
            logger.info(f"Executing query: {query1} with list_id: {list_id}")
            cur.execute(query2, (list_id,))
            logger.info(f"Executing query: {query2} with id: {list_id}")
            self.connection.commit()

    def create_new_todo(self, list_id, todo_name):
        with self.connection.cursor() as cur:
            query = "INSERT INTO todos (list_id, name) VALUES(%s, %s)"
            cur.execute(query, (list_id, todo_name,))
            logger.info(f"Executing query: {query} with list_id: {list_id} and name: {todo_name}")
            self.connection.commit()

    def delete_todo_from_list(self, list_id, todo_id):
        with self.connection.cursor() as cur:
            query = "DELETE FROM todos WHERE id = %s AND list_id = %s"
            cur.execute(query, (todo_id, list_id,))
            logger.info(f"Executing query: {query} with todo_id: {todo_id} and list_id: {list_id}")
            self.connection.commit()

    def update_todo_status(self, list_id, todo_id, new_status):
        with self.connection.cursor() as cur:
            query = "UPDATE todos SET completed = %s WHERE id = %s AND list_id = %s"
            cur.execute(query, (new_status, todo_id, list_id,))
            logger.info(f"Executing query: {query} with new_status: {new_status}, todo_id: {todo_id} and list_id: {list_id}")
            self.connection.commit()

    def mark_all_todos_as_completed(self, list_id):
        with self.connection.cursor() as cur:
            query = "UPDATE todos SET completed = True WHERE list_id = %s "
            cur.execute(query, (list_id,))
            logger.info(f"Executing query: {query} with list_id: {list_id}")
            self.connection.commit()

    def _find_todos_for_list(self, list_id):
        with self.connection.cursor(cursor_factory=psycopg2.extras.DictCursor) as cur:
            query = "SELECT * FROM todos WHERE list_id = %s"
            cur.execute(query, (list_id,))
            logger.info(f"Executing query: {query} with list_id: {list_id}")
            return cur.fetchall()

    def _setup_schema(self):
        with self.connection.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'lists';
            """)
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    CREATE TABLE lists (
                        id serial PRIMARY KEY,
                        name text NOT NULL UNIQUE
    );
                """)

            cur.execute("""
                SELECT COUNT(*)
                FROM information_schema.tables
                WHERE table_schema = 'public' AND table_name = 'todos';
            """)
            if cur.fetchone()[0] == 0:
                cur.execute("""
                    CREATE TABLE todos (
                        id serial PRIMARY KEY,
                        name text NOT NULL,
                        completed boolean NOT NULL DEFAULT false,
                        list_id integer NOT NULL REFERENCES lists (id)
                    );
                """)

            self.connection.commit()