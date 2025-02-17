import ast
import json
import uuid
import pandas as pd
from typing import List
from sqlalchemy import create_engine,text
from sqlalchemy.exc import OperationalError
from time import sleep
from langchain_community.vectorstores import PGVector
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.documents import Document
from pandas.core.api import DataFrame as DataFrame
from ...sahdev.base.base import SahdevBase


class PG_VectorStore(SahdevBase):
    def __init__(self, config=None):
        if not config or "connection_string" not in config:
            raise ValueError(
                "A valid 'config' dictionary with a 'connection_string' is required.")

        SahdevBase.__init__(self, config=config)

        self.connection_string = config["connection_string"]
        self.n_results = config.get("n_results", 3)
        self.embedding_function = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-l6-v2")
        self.ddl_vectorstore = self._initialize_vectorstore("ddl_statements")
        self.documentation_vectorstore = self._initialize_vectorstore("documentation")
        self.sql_vectorstore = self._initialize_vectorstore("question_sql_pairs")
        self.relations_vectorstore = self._initialize_vectorstore("relations")

        # Initialize the SQLAlchemy engine
        self.engine = self._create_engine_with_retries()

    def _initialize_vectorstore(self, collection_name):
        return PGVector(
            embedding_function=self.embedding_function,
            collection_name=collection_name,
            connection_string=self.connection_string,
        )

    def _create_engine_with_retries(self):
        return create_engine(
            self.connection_string,
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=28000,  # Recycle connections before idle_session_timeout
            pool_pre_ping=True,
            connect_args={
                "sslmode": "require",
                "application_name": "YourAppName"
            }
        )

    def _retry_query(self, query_func, retries=3, delay=2, *args, **kwargs):
        """
        Helper method to retry queries in case of connection issues.
        """
        for attempt in range(retries):
            try:
                return query_func(*args, **kwargs)
            except OperationalError as e:
                if attempt < retries - 1:
                    print(f"Retrying query after error: {e}. Attempt {attempt + 1}")
                    sleep(delay)  # Wait before retrying
                else:
                    raise e  # Raise exception if all retries fail

    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        question_sql_json = json.dumps(
            {"question": question, "sql": sql}, ensure_ascii=False)
        id = str(uuid.uuid4()) + "-sql"

        def add_doc():
            doc = Document(page_content=question_sql_json, metadata={"id": id})
            self.sql_vectorstore.add_documents([doc], ids=doc.metadata["id"])

        self._retry_query(add_doc)

        return id

    def add_relations(self, relations: str, **kwargs) -> str:
        id = str(uuid.uuid4()) + "-rel"

        def add_doc():
            doc = Document(page_content=relations, metadata={"id": id})
            self.relations_vectorstore.add_documents([doc], ids=doc.metadata["id"])

        self._retry_query(add_doc)
        return id

    def add_ddl(self, ddl: str, **kwargs) -> str:
        id = str(uuid.uuid4()) + "-ddl"

        def add_doc():
            doc = Document(page_content=ddl, metadata={"id": id})
            self.ddl_vectorstore.add_documents([doc], ids=doc.metadata["id"])

        self._retry_query(add_doc)
        return id

    def add_documentation(self, documentation: str, **kwargs) -> str:
        id = str(uuid.uuid4()) + "-doc"

        def add_doc():
            doc = Document(page_content=documentation, metadata={"id": id})
            self.documentation_vectorstore.add_documents([doc], ids=doc.metadata["id"])

        self._retry_query(add_doc)
        return id

    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        def fetch_similar():
            return self.sql_vectorstore.similarity_search(question, k=self.n_results)

        return [ast.literal_eval(doc.page_content) for doc in self._retry_query(fetch_similar)]

    def get_related_ddl(self, question: str, **kwargs) -> list:
        def fetch_similar():
            return self.ddl_vectorstore.similarity_search(question, k=self.n_results)

        return [doc.page_content for doc in self._retry_query(fetch_similar)]

    def get_related_documentation(self, question: str, **kwargs) -> list:
        def fetch_similar():
            return self.documentation_vectorstore.similarity_search(question, k=self.n_results)

        return [doc.page_content for doc in self._retry_query(fetch_similar)]

    def get_related_relations(self, question: str, **kwargs) -> list:
        def fetch_similar():
            return self.relations_vectorstore.similarity_search(question, k=self.n_results)

        return [doc.page_content for doc in self._retry_query(fetch_similar)]

    def get_training_data(self, **kwargs) -> DataFrame:
        query_embedding = "SELECT cmetadata, document FROM langchain_pg_embedding"

        def execute_query():
            return pd.read_sql(query_embedding, self.engine)

        df_embedding = self._retry_query(execute_query)

        processed_rows = []
        for _, row in df_embedding.iterrows():
            custom_id = row['cmetadata']['id']
            document = row['document']

            training_data_type = "relations" if custom_id[-3:] == "rel" else (
                "documentation" if custom_id[-3:] == "doc" else custom_id[-3:]
            )

            if training_data_type == 'sql':
                try:
                    doc_dict = ast.literal_eval(document)
                    question = doc_dict.get('question')
                    content = doc_dict.get('sql')
                except (ValueError, SyntaxError):
                    print(
                        f"Skipping row with custom_id {custom_id} due to parsing error.")
                    continue
            elif training_data_type in ['documentation', 'ddl', 'relations']:
                question = None
                content = document
            else:
                print(
                    f"Skipping row with custom_id {custom_id} due to unrecognized training data type.")
                continue

            processed_rows.append({
                'id': custom_id,
                'question': question,
                'content': content,
                'training_data_type': training_data_type
            })

        return pd.DataFrame(processed_rows)



                ################# without retry logic functions ###################################
    def remove_training_data(self, id: str, **kwargs) -> bool:
        # Create the database engine
        engine = create_engine(self.connection_string)

        # SQL DELETE statement
        delete_statement = text("""
            DELETE FROM langchain_pg_embedding
            WHERE cmetadata ->> 'id' = :id
        """)

        # Connect to the database and execute the delete statement
        with engine.connect() as connection:
            # Start a transaction
            with connection.begin() as transaction:
                try:
                    result = connection.execute(
                        delete_statement, {'id': id})
                    # Commit the transaction if the delete was successful
                    transaction.commit()
                    # Check if any row was deleted and return True or False accordingly
                    return result.rowcount > 0
                except Exception as e:
                    # Rollback the transaction in case of error
                    print(f"An error occurred: {e}")
                    transaction.rollback()
                    return False

    def remove_collection(self, collection_name: str) -> bool:
        engine = create_engine(self.connection_string)

        # Determine the suffix to look for based on the collection name
        suffix_map = {'ddl': 'ddl', 'sql': 'sql', 'documentation': 'doc','relations':'rel'}
        suffix = suffix_map.get(collection_name)

        if not suffix:
            print(
                "Invalid collection name. Choose from 'ddl', 'sql','documentation' or 'relations'.")
            return False

        # SQL query to delete rows based on the condition
        query = text(f"""
            DELETE FROM langchain_pg_embedding
            WHERE cmetadata->>'id' LIKE '%{suffix}'
        """)

        # Execute the deletion within a transaction block
        with engine.connect() as connection:
            with connection.begin() as transaction:
                try:
                    result = connection.execute(query)
                    transaction.commit()  # Explicitly commit the transaction
                    if result.rowcount > 0:
                        print(
                            f"Deleted {result.rowcount} rows from langchain_pg_embedding where collection is {collection_name}.")
                        return True
                    else:
                        print(
                            f"No rows deleted for collection {collection_name}.")
                        return False
                except Exception as e:
                    print(f"An error occurred: {e}")
                    transaction.rollback()  # Rollback in case of error
                    return False

    def generate_embedding(self, data: str, **kwargs) -> List[float]:
        pass



    def connect_to_db():
        retries = 3
        for attempt in range(retries):
            try:
                engine = create_engine(self.connection_string, pool_pre_ping=True)
                connection = engine.connect()
                return connection
            except OperationalError as e:
                print(f"Connection failed. Attempt {attempt + 1} of {retries}. Retrying...")
                sleep(5)
        raise Exception("Could not connect to the database after retries.")
