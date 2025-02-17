r"""

# Nomenclature

| Prefix | Definition | Examples |
| --- | --- | --- |
| `sd.get_` | Fetch some data | [`sd.get_related_ddl(...)`][Sahdev.base.base.SahdevBase.get_related_ddl] |
| `sd.add_` | Adds something to the retrieval layer | [`sd.add_question_sql(...)`][Sahdev.base.base.SahdevBase.add_question_sql] <br> [`sd.add_ddl(...)`][Sahdev.base.base.SahdevBase.add_ddl] |
| `sd.generate_` | Generates something using AI based on the information in the model | [`sd.generate_sql(...)`][Sahdev.base.base.SahdevBase.generate_sql] <br> [`sd.generate_explanation()`][Sahdev.base.base.SahdevBase.generate_explanation] |
| `sd.run_` | Runs code (SQL) | [`sd.run_sql`][Sahdev.base.base.SahdevBase.run_sql] |
| `sd.remove_` | Removes something from the retrieval layer | [`sd.remove_training_data`][Sahdev.base.base.SahdevBase.remove_training_data] |
| `sd.connect_` | Connects to a database | [`sd.connect_to_snowflake(...)`][Sahdev.base.base.SahdevBase.connect_to_snowflake] |
| `sd.update_` | Updates something | N/A -- unused |
| `sd.set_` | Sets something | N/A -- unused  |

# Open-Source and Extending

Sahdev.AI is open-source and extensible. If you'd like to use Sahdev without the servers, see an example [here](https://Sahdev.ai/docs/postgres-ollama-chromadb/).

The following is an example of where various functions are implemented in the codebase when using the default "local" version of Sahdev. `Sahdev.base.SahdevBase` is the base class which provides a `Sahdev.base.SahdevBase.ask` and `Sahdev.base.SahdevBase.train` function. Those rely on abstract methods which are implemented in the subclasses `Sahdev.openai_chat.OpenAI_Chat` and `Sahdev.chromadb_vector.ChromaDB_VectorStore`. `Sahdev.openai_chat.OpenAI_Chat` uses the OpenAI API to generate SQL and Plotly code. `Sahdev.chromadb_vector.ChromaDB_VectorStore` uses ChromaDB to store training data and generate embeddings.

If you want to use Sahdev with other LLMs or databases, you can create your own subclass of `Sahdev.base.SahdevBase` and implement the abstract methods.

```mermaid
flowchart
    subgraph SahdevBase
        ask
        train
    end

    subgraph OpenAI_Chat
        get_sql_prompt
        submit_prompt
        generate_question
        generate_plotly_code
    end

    subgraph ChromaDB_VectorStore
        generate_embedding
        add_question_sql
        add_ddl
        add_documentation
        get_similar_question_sql
        get_related_ddl
        get_related_documentation
    end
```

"""

import json
import os
import re
import sqlite3
import traceback
from abc import ABC, abstractmethod
from typing import List, Tuple, Union
from urllib.parse import urlparse

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Result
from datetime import datetime

import pandas as pd
import requests



from ..exceptions import DependencyError, ImproperlyConfigured, ValidationError
from ..types import TrainingPlan, TrainingPlanItem
from ..utils import validate_config_path
# from ..cachepg import CacheManager

class SahdevBase(ABC):
    def __init__(self, config=None):
        if config is None:
            config = {}

        self.config = config
        self.run_sql_is_set = False
        self.static_documentation = ""
        self.dialect = self.config.get("dialect", "SQL")
        self.language = self.config.get("language", None)
        self.max_tokens = self.config.get("max_tokens", 14000)

    def log(self, message: str, title: str = "Info"):
        print(f"{title}: {message}")

    def _response_language(self) -> str:
        if self.language is None:
            return ""

        return f"Respond in the {self.language} language."

    def generate_sql(self, question: str,context_str:str ,allow_llm_to_see_data=False, **kwargs) -> str:

        if self.config is not None:
            initial_prompt = self.config.get("initial_prompt", None)
        else:
            initial_prompt = None
        question_sql_list = self.get_similar_question_sql(question, **kwargs)
        ddl_list = self.get_related_ddl(question, **kwargs)
        doc_list = self.get_related_documentation(question, **kwargs)
        rel_list=self.get_related_relations(question, **kwargs)
        prompt = self.get_sql_prompt(
            initial_prompt=initial_prompt,
            question=question,
            context_str=context_str,
            question_sql_list=question_sql_list,
            ddl_list=ddl_list,
            doc_list=doc_list,
            rel_list=rel_list,
            **kwargs,
        )


        # Iterate through each item in the list
        for item in question_sql_list:
            # Check if the current item's question matches the input question
            if item['question'] == question:
                # If a match is found, return the corresponding sql value
                self.log(title="Question matched",message="Returning the SQL")

                return item['sql']
        self.log(title="Question not matched",message="continuing with RAG")

        self.log(title="SQL Prompt", message=prompt)
        #self.log(title="The prompt type is",message=type(prompt))

        llm_response = self.submit_prompt(prompt, **kwargs)
        self.log(title="LLM Response", message=llm_response)

        if 'intermediate_sql' in llm_response:
            if not allow_llm_to_see_data:
                return "The LLM is not allowed to see the data in your database. Your question requires database introspection to generate the necessary SQL. Please set allow_llm_to_see_data=True to enable this."

            if allow_llm_to_see_data:
                intermediate_sql = self.extract_sql(llm_response)

                try:
                    self.log(title="Running Intermediate SQL", message=intermediate_sql)
                    df = self.run_sql(intermediate_sql)

                    prompt = self.get_sql_prompt(
                        initial_prompt=initial_prompt,
                        context_str=context_str,
                        question=question,
                        question_sql_list=question_sql_list,
                        ddl_list=ddl_list,
                        doc_list=doc_list,
                        rel_list=rel_list+[f"The following is a pandas DataFrame with the results of the intermediate SQL query {intermediate_sql}: \n" + df.to_markdown()],
                        **kwargs,
                    )
                    self.log(title="Final SQL Prompt", message=prompt)
                    self.log(title="The prompt type is",message=type(prompt))
                    llm_response = self.submit_prompt(prompt, **kwargs)
                    self.log(title="LLM Response", message=llm_response)
                except Exception as e:
                    return f"Error running intermediate SQL: {e}"


        return self.extract_sql(llm_response)
    
    
    def return_sql(self,prompt, **kwargs):
        llm_response = self.submit_prompt(prompt, **kwargs)
        self.log(title="LLM Response", message=llm_response)
        return self.extract_sql(llm_response)
                



    from typing import Tuple, Optional
    import pandas as pd




    def execute_query_with_retries(self, question: str,context_str:str, max_retries: int = 3) -> Tuple[Optional[str], Optional[pd.DataFrame], str]:
        """
        Attempts to generate and execute an SQL query for the given question with retry logic.
        Returns the SQL query, result DataFrame, and a message.
        """
        sql = ''
        df = None
        error_message = ''  # Initialize to ensure it's available in case of exceptions

        
            
        for attempt in range(max_retries):
            try:
                # Generate SQL
                if attempt == 0:
                    sql = self.generate_sql(question=question,context_str=context_str)
                else:
                    # For retries, include the previous SQL and error in the prompt
                    prompt = f"""
                    Your previous SQL query for the question "{question}" failed with the following error:
                    {error_message}
                    
                    The failing query was:
                    {sql}
                   
                    Please provide a corrected SQL query that addresses this error. Note - but if the user is greeting you, for example, saying "hi" or something similar, respond to them politely without generating SQL.
                    """
                    sql = self.generate_sql(question=prompt,context_str=context_str)
                
                # Execute SQL
                df = self.run_sql(sql)
                
                # Check if df is a valid DataFrame
                if not isinstance(df, pd.DataFrame):
                    raise TypeError(f"Expected a pandas DataFrame, but got {type(df).__name__}")
                
                # Check if df is empty
                if df.empty:
                    return sql, df, "🌟 No Data Found 🌟\n Maybe it’s a fresh start for this combination! 🕊️ .\n If you think something’s amiss, try refining your query or let us know. 😊"


                
                return sql, df, "Query Executed Sucessfully"
            
            except Exception as e:
                error_message = str(e)
                print(f"Attempt {attempt + 1} failed. Error: {error_message}")

        # All retries failed, generate a fallback response
        fallback_response = self.generate_fallback_response(question, error_message,context_str)
        return sql, df, fallback_response

    def generate_fallback_response(self, question: str, last_error: str,context_str: str) -> str:
        """
        Generates a fallback response when SQL generation or execution fails.
        """
        prompt = f"""
        I couldn't generate a valid SQL query to answer your question: "{question}". 
        However, here's some general advice or information related to your query. If you are greeting me or asking a generic question, let me know, and I'll respond accordingly.

        Could you please narrow down your question into a more specific SQL-related query? This will help me provide a more accurate response.
        Some additional knowledge for you-
        You are 'Maddy', an AI assistant created by EY India GEN AI Engineers. Your primary focus is on:
        1. Supply chain analysis and optimization
        2. Root cause analysis (RCA)
        3. Predictive quality analysis (PQA)
        4. Data summarization and forecasting
        5. Machine learning insights

        Always maintain a professional tone while being helpful and precise in your responses.
        Focus on providing actionable insights and clear explanations.
        

        """
        resp = self.client.chat.completions.create(
            model='gpt-4',
            messages=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ]
        )
        return resp.choices[0].message.content





    

    def extract_sql(self, llm_response: str) -> str:
        """
        Example:
        ```python
        sd.extract_sql("Here's the SQL query in a code block: ```sql\nSELECT * FROM customers\n```")
        ```

        Extracts the SQL query from the LLM response. This is useful in case the LLM response contains other information besides the SQL query.
        Override this function if your LLM responses need custom extraction logic.

        Args:
            llm_response (str): The LLM response.

        Returns:
            str: The extracted SQL query.
        """

        # If the llm_response contains a CTE (with clause), extract the last sql between WITH and ;
        sqls = re.findall(r"\bWITH\b .*?;", llm_response, re.DOTALL)
        if sqls:
            sql = sqls[-1]
            self.log(title="Extracted SQL", message=f"{sql}")
            return sql

        # If the llm_response is not markdown formatted, extract last sql by finding select and ; in the response
        sqls = re.findall(r"SELECT.*?;", llm_response, re.DOTALL)
        if sqls:
            sql = sqls[-1]
            self.log(title="Extracted SQL", message=f"{sql}")
            return sql

        # If the llm_response contains a markdown code block, with or without the sql tag, extract the last sql from it
        sqls = re.findall(r"```sql\n(.*)```", llm_response, re.DOTALL)
        if sqls:
            sql = sqls[-1]
            self.log(title="Extracted SQL", message=f"{sql}")
            return sql

        sqls = re.findall(r"```(.*)```", llm_response, re.DOTALL)
        if sqls:
            sql = sqls[-1]
            self.log(title="Extracted SQL", message=f"{sql}")
            return sql

        return llm_response




    def generate_rewritten_question(self, last_question: str, new_question: str, **kwargs) -> str:
        """
        **Example:**
        ```python
        rewritten_question = sd.generate_rewritten_question("Who are the top 5 customers by sales?", "Show me their email addresses")
        ```

        Generate a rewritten question by combining the last question and the new question if they are related. If the new question is self-contained and not related to the last question, return the new question.

        Args:
            last_question (str): The previous question that was asked.
            new_question (str): The new question to be combined with the last question.
            **kwargs: Additional keyword arguments.

        Returns:
            str: The combined question if related, otherwise the new question.
        """
        if last_question is None:
            return new_question

        prompt = [
            self.system_message("Your goal is to combine a sequence of questions into a singular question if they are related. If the second question does not relate to the first question and is fully self-contained, return the second question. Return just the new combined question with no additional explanations. The question should theoretically be answerable with a single SQL statement."),
            self.user_message("First question: " + last_question + "\nSecond question: " + new_question),
        ]

        return self.submit_prompt(prompt=prompt, **kwargs)

    def generate_followup_questions(
        self, question: str, sql: str, df: pd.DataFrame, n_questions: int = 5, **kwargs
    ) -> list:
        """
        **Example:**
        ```python
        sd.generate_followup_questions("What are the top 10 customers by sales?", sql, df)
        ```

        Generate a list of followup questions that you can ask Sahdev.AI.

        Args:
            question (str): The question that was asked.
            sql (str): The LLM-generated SQL query.
            df (pd.DataFrame): The results of the SQL query.
            n_questions (int): Number of follow-up questions to generate.

        Returns:
            list: A list of followup questions that you can ask Sahdev.AI.
        """

        message_log = [
            self.system_message(
                f"You are a helpful data assistant. The user asked the question: '{question}'\n\nThe SQL query for this question was: {sql}\n\nThe following is a pandas DataFrame with the results of the query: \n{df.to_markdown()}\n\n"
            ),
            self.user_message(
                f"Generate a list of {n_questions} followup questions that the user might ask about this data. Respond with a list of questions, one per line. Do not answer with any explanations -- just the questions. Remember that there should be an unambiguous SQL query that can be generated from the question. Prefer questions that are answerable outside of the context of this conversation. Prefer questions that are slight modifications of the SQL query that was generated that allow digging deeper into the data. Each question will be turned into a button that the user can click to generate a new SQL query so don't use 'example' type questions. Each question must have a one-to-one correspondence with an instantiated SQL query." +
                self._response_language()
            ),
        ]

        llm_response = self.submit_prompt(message_log, **kwargs)

        numbers_removed = re.sub(r"^\d+\.\s*", "", llm_response, flags=re.MULTILINE)
        return numbers_removed.split("\n")

    def generate_questions(self, **kwargs) -> List[str]:
        """
        **Example:**
        ```python
        sd.generate_questions()
        ```

        Generate a list of questions that you can ask Sahdev.AI.
        """
        question_sql = self.get_similar_question_sql(question="", **kwargs)

        return [q["question"] for q in question_sql]

    





    # ----------------- Use Any Embeddings API ----------------- #
    @abstractmethod
    def generate_embedding(self, data: str, **kwargs) -> List[float]:
        pass

    # ----------------- Use Any Database to Store and Retrieve Context ----------------- #
    @abstractmethod
    def get_similar_question_sql(self, question: str, **kwargs) -> list:
        """
        This method is used to get similar questions and their corresponding SQL statements.

        Args:
            question (str): The question to get similar questions and their corresponding SQL statements for.

        Returns:
            list: A list of similar questions and their corresponding SQL statements.
        """
        pass
    @abstractmethod
    def get_related_relations(self,question:str, **kwargs) -> list:
        pass

    @abstractmethod
    def get_related_ddl(self, question: str, **kwargs) -> list:
        """
        This method is used to get related DDL statements to a question.

        Args:
            question (str): The question to get related DDL statements for.

        Returns:
            list: A list of related DDL statements.
        """
        pass

    @abstractmethod
    def get_related_documentation(self, question: str, **kwargs) -> list:
        """
        This method is used to get related documentation to a question.

        Args:
            question (str): The question to get related documentation for.

        Returns:
            list: A list of related documentation.
        """
        pass

    @abstractmethod
    def add_question_sql(self, question: str, sql: str, **kwargs) -> str:
        """
        This method is used to add a question and its corresponding SQL query to the training data.

        Args:
            question (str): The question to add.
            sql (str): The SQL query to add.

        Returns:
            str: The ID of the training data that was added.
        """
        pass

    @abstractmethod
    def add_relations(self, relations:str, **kwargs) ->str:
        pass

    @abstractmethod
    def add_ddl(self, ddl: str, **kwargs) -> str:
        """
        This method is used to add a DDL statement to the training data.

        Args:
            ddl (str): The DDL statement to add.

        Returns:
            str: The ID of the training data that was added.
        """
        pass

    @abstractmethod
    def add_documentation(self, documentation: str, **kwargs) -> str:
        """
        This method is used to add documentation to the training data.

        Args:
            documentation (str): The documentation to add.

        Returns:
            str: The ID of the training data that was added.
        """
        pass

    @abstractmethod
    def get_training_data(self, **kwargs) -> pd.DataFrame:
        """
        Example:
        ```python
        sd.get_training_data()
        ```

        This method is used to get all the training data from the retrieval layer.

        Returns:
            pd.DataFrame: The training data.
        """
        pass

    @abstractmethod
    def remove_training_data(self, id: str, **kwargs) -> bool:
        """
        Example:
        ```python
        sd.remove_training_data(id="123-ddl")
        ```

        This method is used to remove training data from the retrieval layer.

        Args:
            id (str): The ID of the training data to remove.

        Returns:
            bool: True if the training data was removed, False otherwise.
        """
        pass

    # ----------------- Use Any Language Model API ----------------- #

    @abstractmethod
    def system_message(self, message: str) -> any:
        pass

    @abstractmethod
    def user_message(self, message: str) -> any:
        pass

    @abstractmethod
    def assistant_message(self, message: str) -> any:
        pass

    def str_to_approx_token_count(self, string: str) -> int:
        return len(string) / 4
    
    def add_context_to_prompt(
        self,
        initial_prompt: str,
        context_str:str,
        max_tokens: int = 14000,
    ) -> str:
        
        initial_prompt += "\n===Previous Chatbot Conversations \n\n"

        initial_prompt+=f"{context_str}\n\n"

        return initial_prompt

    def add_ddl_to_prompt(
        self, initial_prompt: str, ddl_list: list[str], max_tokens: int = 14000
    ) -> str:
        if len(ddl_list) > 0:
            initial_prompt += "\n===Tables \n"

            for ddl in ddl_list:
                if (
                    self.str_to_approx_token_count(initial_prompt)
                    + self.str_to_approx_token_count(ddl)
                    < max_tokens
                ):
                    initial_prompt += f"{ddl}\n\n"

        return initial_prompt

    def add_documentation_to_prompt(
        self,
        initial_prompt: str,
        documentation_list: list[str],
        max_tokens: int = 14000,
    ) -> str:
        if len(documentation_list) > 0:
            initial_prompt += "\n===Additional Context \n\n"

            for documentation in documentation_list:
                if (
                    self.str_to_approx_token_count(initial_prompt)
                    + self.str_to_approx_token_count(documentation)
                    < max_tokens
                ):
                    initial_prompt += f"{documentation}\n\n"

        return initial_prompt
    
    def add_relations_to_prompt(
        self,
        initial_prompt: str,
        relations_list: list[str],
        max_tokens: int = 14000,
    ) -> str:
        if len(relations_list) > 0:
            initial_prompt += "\n=== The relationship between the tables \n\n"

            for relations in relations_list:
                if (
                    self.str_to_approx_token_count(initial_prompt)
                    + self.str_to_approx_token_count(relations)
                    < max_tokens
                ):
                    initial_prompt += f"{relations}\n\n"

        return initial_prompt
    


    def add_sql_to_prompt(
        self, initial_prompt: str, sql_list: list[str], max_tokens: int = 14000
    ) -> str:
        if len(sql_list) > 0:
            initial_prompt += "\n===Question-SQL Pairs\n\n"

            for question in sql_list:
                if (
                    self.str_to_approx_token_count(initial_prompt)
                    + self.str_to_approx_token_count(question["sql"])
                    < max_tokens
                ):
                    initial_prompt += f"{question['question']}\n{question['sql']}\n\n"

        return initial_prompt
    



    def get_sql_prompt(
        self,
        initial_prompt : str,
        context_str:str,
        question: str,
        question_sql_list: list,
        ddl_list: list,
        doc_list: list,
        rel_list :list,
        **kwargs,
    ):
        """
        Example:
        ```python
        sd.get_sql_prompt(
            question="What are the top 10 customers by sales?",
            question_sql_list=[{"question": "What are the top 10 customers by sales?", "sql": "SELECT * FROM customers ORDER BY sales DESC LIMIT 10"}],
            ddl_list=["CREATE TABLE customers (id INT, name TEXT, sales DECIMAL)"],
            doc_list=["The customers table contains information about customers and their sales."],
        )

        ```

        This method is used to generate a prompt for the LLM to generate SQL.

        Args:
            question (str): The question to generate SQL for.
            question_sql_list (list): A list of questions and their corresponding SQL statements.
            ddl_list (list): A list of DDL statements.
            doc_list (list): A list of documentation.

        Returns:
            any: The prompt for the LLM to generate SQL.
        """

        if initial_prompt is None:
            initial_prompt = f"""You are a {self.dialect} expert. " + \
            "Generate a SQL query to answer the question based strictly on the provided **CONTEXT** (DDL(Tables), Additional context(Documentations), Relations between the tables and Question SQL pairs ) and **HISTORY** (Previous Questions Context). First, determine if the question is a **follow-up** (build on prior queries) or a **new question** (standalone query), and craft the query accordingly. Ensure your response adheres to the **response guidelines**
           """

        initial_prompt += (
            f"\n\n Previous Questions Context : ****PREVIOUS 3 QUESTIONS ASKED BY USER and SQL queries are**** \n {context_str} =========="
        )

        initial_prompt += (
            f"\n\n  ======**OVERALLN CONTEXT FOR SQL QUERY (given below) : **======="
        )


            ###Histpory addition#####
        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, ddl_list, max_tokens=self.max_tokens
        )



        if self.static_documentation != "":
            doc_list.append(self.static_documentation)

        initial_prompt = self.add_documentation_to_prompt(
            initial_prompt, doc_list, max_tokens=self.max_tokens
        )

        initial_prompt = self.add_relations_to_prompt(
            initial_prompt,rel_list, max_tokens=self.max_tokens
        )

        # initial_prompt += (
        #     "===Response Guidelines \n"
        #     "1. If the provided context is sufficient, please generate a valid SQL query without any explanations for the question. Also donot make any ambiguous queries, always crosscheck if the query which are made are valid according to the asked question or not. If you need further clarification on question, you can refer to the previously asked questions and thier SQL given below these guidelines\n"
        #     "2. If the provided context is almost sufficient but requires knowledge of a specific string in a particular column, Please refer the recent conversation history which is given below after these instructions \n"
        #     "3. If the provided context is insufficient, please check if the question is based on the recent conversation history given below and weather the users wanted to ask a followup question on already asked questions or not  \n"
        #     "4. Please use the most relevant table(s). \n"
        #     "5. If the question has been asked and answered before, please repeat the answer exactly as it was given before. \n"
        #     f"6. Ensure that the output SQL is {self.dialect}-compliant and executable, and free of syntax errors. \n"
        # )

#             1. **Follow-Up vs. New Question**:
#             - First, determine if the current question is a **follow-up** to a previous query in the **HISTORY**.
#             - If it is a follow-up, modify or extend the previous query to accommodate the new requirements while maintaining the logic of the earlier query.
#             - If it is a new question, generate a standalone SQL query based on the given **CONTEXT**.

#             2. **Adherence to History**:
#             - Use the results or logic of the previous query (if applicable) as the basis for updates in the follow-up question.
#             - For example, if a new column or condition is requested, update the prior query rather than creating a new one from scratch.

#             3. **Optimization and Accuracy**:
#             - Ensure all queries are syntactically correct, optimized for performance, and address potential edge cases (e.g., null values or mismatched joins).

#             Now, based on the **CONTEXT** and **HISTORY**, intelligently determine whether the question is a follow-up or a new question, adapt the SQL query accordingly, and provide the updated result.

        initial_prompt += (
            "===Response Guidelines \n"
            "1. If the provided context is sufficient, please generate a valid SQL query without any explanations for the question. \n"
            "2. If the provided context is almost sufficient but requires knowledge of a specific string in a particular column, please generate an intermediate SQL query to find the distinct strings in that column. Prepend the query with a comment saying intermediate_sql \n"
            "3. If the provided context is insufficient, please explain why it can't be generated. \n"
            "4. Use the 'Previous Questions Context' to resolve ambiguity or infer missing details in the current question. For example:\n"
            "   - If the current question refers to 'this' or 'that,' resolve it based on the last question.\n"
            "   - If the current question logically follows the last question, generate the SQL for the combined intent. \n"
            "5. Prioritize 'Previous Questions Context' over retrieved similar questions/SQL pairs when there is any ambiguity or when the current question explicitly builds on the previous question. \n"
            "6. Use retrieved similar questions/SQL pairs only when they are more relevant and explicitly match the current question without requiring inference from 'Previous Questions Context.' \n"
            "7. Please use the most relevant table(s). \n"
            "8. If the question has been asked and answered before, please repeat the answer exactly as it was given before. \n"
            f"9. Ensure that the output SQL is {self.dialect}-compliant and executable, and free of syntax errors. \n"
        )
        
        
        
        
        message_log = [self.system_message(initial_prompt)]

        for example in question_sql_list:
            if example is None:
                print("example is None")
            else:
                if example is not None and "question" in example and "sql" in example:
                    message_log.append(self.user_message(example["question"]))
                    message_log.append(self.assistant_message(example["sql"]))

        message_log.append(self.user_message(question))

        return message_log

    def get_followup_questions_prompt(
        self,
        question: str,
        question_sql_list: list,
        ddl_list: list,
        doc_list: list,
        rel_list:list,
        **kwargs,
    ) -> list:
        initial_prompt = f"The user initially asked the question: '{question}': \n\n"

        initial_prompt = self.add_ddl_to_prompt(
            initial_prompt, ddl_list, max_tokens=self.max_tokens
        )

        initial_prompt = self.add_documentation_to_prompt(
            initial_prompt, doc_list, max_tokens=self.max_tokens
        )

        initial_prompt = self.add_sql_to_prompt(
            initial_prompt, question_sql_list, max_tokens=self.max_tokens
        )

        initial_prompt = self.add_relations_to_prompt(
            initial_prompt,rel_list,max_tokens=self.max_tokens
        )

        message_log = [self.system_message(initial_prompt)]
        message_log.append(
            self.user_message(
                "Generate a list of followup questions that the user might ask about this data. Respond with a list of questions, one per line. Do not answer with any explanations -- just the questions."
            )
        )

        return message_log

    @abstractmethod
    def submit_prompt(self, prompt, **kwargs) -> str:
        """
        Example:
        ```python
        sd.submit_prompt(
            [
                sd.system_message("The user will give you SQL and you will try to guess what the business question this query is answering. Return just the question without any additional explanation. Do not reference the table name in the question."),
                sd.user_message("What are the top 10 customers by sales?"),
            ]
        )
        ```

        This method is used to submit a prompt to the LLM.

        Args:
            prompt (any): The prompt to submit to the LLM.

        Returns:
            str: The response from the LLM.
        """
        pass

    def generate_question(self, sql: str, **kwargs) -> str:
        response = self.submit_prompt(
            [
                self.system_message(
                    "The user will give you SQL and you will try to guess what the business question this query is answering. Return just the question without any additional explanation. Do not reference the table name in the question."
                ),
                self.user_message(sql),
            ],
            **kwargs,
        )

        return response

    def _extract_python_code(self, markdown_string: str) -> str:
        # Regex pattern to match Python code blocks
        pattern = r"```[\w\s]*python\n([\s\S]*?)```|```([\s\S]*?)```"

        # Find all matches in the markdown string
        matches = re.findall(pattern, markdown_string, re.IGNORECASE)

        # Extract the Python code from the matches
        python_code = []
        for match in matches:
            python = match[0] if match[0] else match[1]
            python_code.append(python.strip())

        if len(python_code) == 0:
            return markdown_string

        return python_code[0]


    
    def connect_to_mssql(self, odbc_conn_str: str, **kwargs):
        """
        Connect to a Microsoft SQL Server database. This is just a helper function to set [`sd.run_sql`][Sahdev.base.base.SahdevBase.run_sql]

        Args:
            odbc_conn_str (str): The ODBC connection string.

        Returns:
            None
        """
        try:
            import pyodbc
        except ImportError:
            raise DependencyError(
                "You need to install required dependencies to execute this method,"
                " run command: pip install pyodbc"
            )

        try:
            import sqlalchemy as sa
            from sqlalchemy.engine import URL
        except ImportError:
            raise DependencyError(
                "You need to install required dependencies to execute this method,"
                " run command: pip install sqlalchemy"
            )

        connection_url = URL.create(
            "mssql+pyodbc", query={"odbc_connect": odbc_conn_str}
        )

        from sqlalchemy import create_engine

        engine = create_engine(connection_url, **kwargs)

        def run_sql_mssql(sql: str):
            # Execute the SQL statement and return the result as a pandas DataFrame
            with engine.begin() as conn:
                df = pd.read_sql_query(sa.text(sql), conn)
                conn.close()
                return df

            raise Exception("Couldn't run sql")

        self.dialect = "Microsoft SQL Server / SSMS"
        self.run_sql = run_sql_mssql
        self.run_sql_is_set = True
    

    def run_sql(self, sql: str, **kwargs) -> pd.DataFrame:
        """
        Example:
        ```python
        sd.run_sql("SELECT * FROM my_table")
        ```

        Run a SQL query on the connected database.

        Args:
            sql (str): The SQL query to run.

        Returns:
            pd.DataFrame: The results of the SQL query.
        """
        raise Exception(
            "You need to connect to a database first by running sd.connect_to_snowflake(), sd.connect_to_postgres(), similar function, or manually set sd.run_sql"
        )