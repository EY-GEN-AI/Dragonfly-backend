#from langchain.schema import HumanMessage
#from sahdev.pgvector.pgvector import PG_VectorStore
from ..sahdev.pgvector.pgvector import PG_VectorStore
# from sqlalchemy import create_engine
import os
import warnings
from ..sahdev.openai import OpenAI_Chat
# from ..sahdev.openai import OpenAI_Chat
from openai import AzureOpenAI
#from sahdev.pgvector.pgvector import PG_VectorStore 
#from backend.sahdev.pgvector.pgvector import PG_VectorStore
from urllib3.exceptions import InsecureRequestWarning  # Import the specific warning

warnings.filterwarnings("ignore", category=UserWarning, message=".*langchain.*")
warnings.filterwarnings("ignore", category=InsecureRequestWarning)

client = AzureOpenAI(
    api_key = os.getenv("AZURE_API_KEY"),      
    api_version=os.getenv("AZURE_API_VERSION"),    
    azure_endpoint= os.getenv("AZURE_API_BASE")      
)



class MySahdev(PG_VectorStore, OpenAI_Chat):
    def __init__(self, config=None):
        if config is None:
            config = {}

        connection_string = config.get("connection_string", os.getenv('POSTGRES_URL'))

        PG_VectorStore.__init__(self, config={"connection_string": connection_string})


        OpenAI_Chat.__init__(self, client=client, config=config) # Make sure to put your AzureOpenAI client here# Make sure to put your AzureOpenAI client here

sd = MySahdev(config={'model': 'gpt-4'})
# Create a singleton instance
sd = MySahdev()
sd.connect_to_mssql(odbc_conn_str=os.getenv("MSSQL_URL"))
print("Sahdev setup sucessful")
#sd.execute_query_with_retries("hello")
#sd.generate_sql("How many orders are delayed due to material unavailability")