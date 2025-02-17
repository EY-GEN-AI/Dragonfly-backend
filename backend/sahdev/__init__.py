import dataclasses
import json
import os
from dataclasses import dataclass
from typing import Callable, List, Tuple, Union

import pandas as pd
import requests

from .exceptions import (
    OTPCodeError,
    ValidationError,
)
from .types import (
    ApiKey,
    Status,
    TrainingData,
    UserEmail,
    UserOTP,
)
from .utils import sanitize_model_name, validate_config_path

api_key: Union[str, None] = None  # API key for Vanna.AI

fig_as_img: bool = False  # Whether or not to return Plotly figures as images

run_sql: Union[
    Callable[[str], pd.DataFrame], None
] = None  # Function to convert SQL to a Pandas DataFrame
"""
**Example**
```python
vn.run_sql = lambda sql: pd.read_sql(sql, engine)
```

Set the SQL to DataFrame function for Vanna.AI. This is used in the [`vn.ask(...)`][vanna.ask] function.
Instead of setting this directly you can also use [`vn.connect_to_snowflake(...)`][vanna.connect_to_snowflake] to set this.

"""

__org: Union[str, None] = None  # Organization name for Vanna.AI

_unauthenticated_endpoint = "https://ask.vanna.ai/unauthenticated_rpc"

def error_deprecation():
    raise Exception("""
Please switch to the following method for initializing Vanna:

from vanna.remote import VannaDefault

api_key = # Your API key from https://vanna.ai/account/profile 
vanna_model_name = # Your model name from https://vanna.ai/account/profile
                    
vn = VannaDefault(model=vanna_model_name, api_key=api_key)
""")

def __unauthenticated_rpc_call(method, params):
    headers = {
        "Content-Type": "application/json",
    }
    data = {"method": method, "params": [__dataclass_to_dict(obj) for obj in params]}

    response = requests.post(
        _unauthenticated_endpoint, headers=headers, data=json.dumps(data)
    )
    return response.json()



def __dataclass_to_dict(obj):
    return dataclasses.asdict(obj)







def create_model(model: str, db_type: str) -> bool:
    error_deprecation()


def add_user_to_model(model: str, email: str, is_admin: bool) -> bool:
    error_deprecation()


def update_model_visibility(public: bool) -> bool:
    error_deprecation()


def set_model(model: str):
    error_deprecation()


def add_sql(
    question: str, sql: str, tag: Union[str, None] = "Manually Trained"
) -> bool:
    error_deprecation()


def add_ddl(ddl: str) -> bool:
    error_deprecation()


def add_documentation(documentation: str) -> bool:
    error_deprecation()





def flag_sql_for_review(
    question: str, sql: Union[str, None] = None, error_msg: Union[str, None] = None
) -> bool:
    error_deprecation()


def remove_sql(question: str) -> bool:
    error_deprecation()


def remove_training_data(id: str) -> bool:
    error_deprecation()


def generate_sql(question: str) -> str:
    error_deprecation()


def get_related_training_data(question: str) -> TrainingData:
    error_deprecation()


def generate_meta(question: str) -> str:
    error_deprecation()


def generate_followup_questions(question: str, df: pd.DataFrame) -> List[str]:
    error_deprecation()


def generate_questions() -> List[str]:
    error_deprecation()



def get_results(cs, default_database: str, sql: str) -> pd.DataFrame:
    error_deprecation()


def generate_explanation(sql: str) -> str:
    error_deprecation()


def generate_question(sql: str) -> str:
    error_deprecation()


def get_all_questions() -> pd.DataFrame:
    error_deprecation()


def get_training_data() -> pd.DataFrame:
    error_deprecation()


def connect_to_sqlite(url: str):
    error_deprecation()




def connect_to_postgres(
    host: str = None,
    dbname: str = None,
    user: str = None,
    password: str = None,
    port: int = None,
):
    error_deprecation()


def connect_to_bigquery(cred_file_path: str = None, project_id: str = None):
    error_deprecation()

def connect_to_duckdb(url: str="memory", init_sql: str = None):
    error_deprecation()