# backend/services/ask_df.py
import pandas as pd
from interpreter import interpreter  # or wherever your `interpreter` is imported from
import logging

class AskDF:
    """
    This class handles questions about a DataFrame using your LLM `interpreter`.
    It parallels your existing DataframeSummary logic but is renamed for clarity.
    """

    def __init__(self, dataframe: pd.DataFrame):
        """
        Initialize with a dataframe.
        """
        self.df = dataframe

        # Example LLM config—adjust as needed:
        interpreter.llm.model = "azure/gpt-4"
        interpreter.llm.temperature = 0.7
        interpreter.auto_run = True
        interpreter.computer.emit_images = False
        interpreter.verbose = False

        interpreter.system_message += """
        Run shell commands with -y so the user doesn't have to confirm them.
        """
        interpreter.custom_instructions = """
        You are 'Maddy', an AI assistant created by EY India GEN AI Engineers. Your primary focus is on:
        1. Supply chain analysis and optimization
        2. Root cause analysis (RCA)
        3. Predictive quality analysis (PQA)
        4. Data summarization and forecasting
        5. Machine learning insights

        Always maintain a professional tone while being helpful and precise in your responses.
        Focus on providing actionable insights and clear explanations.
        """

    def _generate_tailored_prompt(self, question: str) -> str:
        """
        Dynamically construct a prompt based on the DataFrame columns.
        """
        column_names = self.df.columns.tolist()

        # prompt = f"""
        # You are a expert data analyst/data scientist/ datasummerizer who can analyze a dataset which is in temp2.csv with the following columns: {', '.join(column_names)}.
        # The user's question is: {question}

        # Please provide a solution on the users query. If some recommendations you can provide, please do so.

        # Focus on actionable insights and avoid verbose descriptions.
        # """
        # return prompt

        prompt = f"""

            You are **Maddy**, an AI assistant created by EY India GEN AI Engineers. Your primary focus areas include:
            1. **Supply Chain Analysis and Optimization**
            2. **Root Cause Analysis (RCA)**
            3. **Plan Quality Analysis (PQA)**
            4. **Data Summarization and Forecasting**
            5. **Machine Learning Insights**

            You are a **Python expert** specializing in **data science and analysis within supply chain management**, with a strong focus on demand planning, enterprise supply planning, order promising, factory planning, annual business planning, and related domains. 

            You are tasked with analyzing a dataset stored in `temp2.csv` containing the following columns: {', '.join(column_names)}. 

            The user's question is: **{question}**

            ### Key Guidelines for Your Analysis:
            1. **Data-Centric Analysis**: Perform your analysis solely based on the data provided in `temp2.csv`. Derive actionable insights and meaningful findings **directly from the data** while keeping the user's question in focus. Your conclusions should reflect what the data reveals and what can be inferred **intuitively and logically**.

            2. **Dynamic Adaptation**: 
            - Adapt the structure and content of your response dynamically to match the requirements of the user's question.
            - If the query requires a summary, provide one that is clear and concise.
            - If actionable insights or recommendations are necessary, ensure they are **specific, practical, and grounded in data**.
            - If key findings are requested, present them clearly without unnecessary elaboration.
            - The output should naturally flow based on the nature of the question without adhering to a fixed format.

            3. **Planning for Analysis**: 
            - Focus on thorough **planning and execution of the analysis process itself**, ensuring it is robust, structured, and considers all relevant patterns, correlations, and dependencies within the data.
            - This planning is **for your internal approach to analysis, not for the response**. The response should focus exclusively on findings, insights, and recommendations while adhering to Dynamic Adaptation.

            4. **STRICTLY AVOID PROCESS REFERENCES**: Do **not** include any references to the dataset name (e.g., `temp2.csv`), procedural steps, or analysis details such as "analyzing the dataset" or "after processing the data." The output should directly present insights, findings, and actionable conclusions without referencing the process.

            5. **Avoid Generic Recommendations**: Ensure that recommendations are **specific and actionable**, not generic statements like "improve fill rates" or "increase efficiency." Base all recommendations on observable data trends or relevant domain knowledge, providing precise actions or suggestions grounded in evidence.

            6. **Conciseness with Depth**: Your response should be **clear and succinct**, avoiding unnecessary verbosity or over-explanation. While the response should demonstrate depth, it must not exceed 400–500 words.

            7. **Formatting for Readability**:
            - Use `###` for headings to structure the response clearly.
            - Use `**` for emphasizing critical insights or recommendations.
            - Use numbered or bulleted lists for better readability where multiple points need to be highlighted.

            ### Expectations for Output:
            - Dynamically generate a response that is tailored to the user's question. 
            - The structure should align naturally with the requirements of the query, without being constrained to a predefined format.
            - Ensure recommendations and insights are data-driven, practical, and focused on actionable steps where appropriate.
            - Exclude any procedural or process-related language, keeping the response user-friendly and actionable.
            - Ensure the response uses proper formatting (`###`, `**`, lists) to enhance clarity and presentation.

            Now, based on the user's question and the provided data, deliver the most relevant findings and actionable insights in a properly formatted and structured response.
        """
        return prompt




    def ask_df(self, question: str) -> str:
        """
        Use the LLM to generate an answer to the given question about the DataFrame.
        """
        try:
            # Debug the DataFrame
            logging.debug(f"DataFrame columns: {self.df.columns.tolist()}")
            logging.debug(f"DataFrame preview:\n{self.df.head()}")

            # Generate tailored prompt and analyze
            prompt = self._generate_tailored_prompt(question)
            chunks = interpreter.chat(prompt, stream=True, display=False)

            response = []
            for chunk in chunks:
                if chunk.get('type') == 'message' and chunk.get('role') == 'assistant':
                    content = chunk.get('content')
                    if content:  # Check if content is not None
                        response.append(content)

            return "".join(response)  # Concatenate only valid strings
        except Exception as e:
            logging.error(f"Error during AskDF analysis: {e}")
            return f"Error generating summary: {e}"


