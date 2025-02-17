# dataframe_summary.py

import pandas as pd
from interpreter import interpreter  # Assuming `generate_response` is your LLM interaction function.

class DataframeSummary:

    #interpreter_summary=OpenInterpreter()
    def custom_code_output_sender(content):
        # Print output to the console only
        output = f"Code output:\n{content}\n\n"
        print(output)  # Send to console
        return output  # Prevent browser rendering

    def __init__(self, dataframe: pd.DataFrame):
        """
        Initialize with a dataframe.    
        """


        self.df = dataframe
        self.column_names = dataframe.columns.tolist()
        #interpreter=OpenInterpreter()
        interpreter.llm.model = "azure/gpt-4"
       # interpreter.code_output_sender
        interpreter.llm.temperature=0.7
        interpreter.auto_run=True
        interpreter.computer.emit_images=False
        interpreter.verbose=False





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

    def generate_tailored_prompt(self,question:str) -> str:
        """
        Construct the tailored prompt based on the dataframe columns.
        """
        column_names = self.df.columns.tolist()
        tailored_prompt = (f"""
                        You are a steel manufacturing data analyst. You have a dataset named temp.csv containing columns: {', '.join(column_names)}.
                        The user's question is: {question}
 
                        Internal Analysis Guidelines (not to be shown in output):
                        - Identify specific metrics needed for the question
                        - Map relevant columns to the analysis objectives
                        - Progress from basic patterns to detailed insights
                        - Consider user's intentions and sentiment
 
                        Present your response in this exact format:
 
                        KEY FINDINGS:
                        - [3-4 bullet points with specific numeric insights]
                        - Each bullet must include concrete numbers and their business impact
 
                        RECOMMENDED ACTIONS:
                        - [3-4 bullet points with specific actions]
                        - Each recommendation must link directly to the findings above
 
                        SUMMARY:
                        A concise paragraph (max 100 words) that addresses:
                        - The main numeric takeaway
                        - Business impact
                        - Answer to user's specific question
                        - Potential efficiency improvement
 
                        Total response must not exceed 200 words. Each bullet point should be data-driven and include specific numbers. Focus on actionable manufacturing insights rather than statistical descriptions.
                        """)
        
        return tailored_prompt
    

    def generate_summary(self, question: str) -> str:
        """
        Generate the summary using the LLM and tailored prompt.
        """
        # Generate the prompt
        prompt = self.generate_tailored_prompt(question)

        # Prepare messages for the LLM
        # messages = [
        #     {"role": "system", "content": "You are a helpful assistant."},
        #     {"role": "user", "content": prompt}  # User's input
        # ]

        try:
            # Debugging: Ensure messages structure is correct
            # print("Debug: Messages being sent to interpreter:", messages)

            # Call the interpreter with the messages
            # summary = interpreter.chat(messages, display=False)
            ms=[]

            for chunk in interpreter.chat(prompt, stream=True, display=False):
    # Filter out chunks with 'html' or 'image' formats
                #if chunk.get('format') not in ['html', 'image'] and chunk.get('role') in ['assistant'] and :
                if chunk.get('type') in['message'] and chunk.get('role') in ['assistant']:
                    content = chunk.get('content')
                    if content:  # Ensure content is not None or empty
                        ms.append(str(content))
            
            # Join the collected content and print as a single message
            output_message = "".join(ms)
            print(output_message)
            return output_message
            #compiled_content=''
            #for chunk in interpreter.chat(prompt, stream=True, display=False):


                # content=chunk.get('content')
                # if(content):
                #     ms.append(content)
                # if chunk.get('format') not in ['html','image']:

                #     ms.append(chunk)
                #     if chunk.get('')
                #     compiled_content += chunk.get('content','')
                # #print(chunk)
            # output_message="".join(ms)
            # print(output_message)
            #print(ms)
            #print(compiled_content)
           


            # Debugging: Check the structure of the response
            #print("Debug: Response from interpreter:", summary)

            # Extract content if the response is valid
            # if isinstance(summary, list) and summary:
            #     # Extract the last message content
            #     content = summary[-1].get('content', 'No content found')
            #     return content
            # else:
            #     return "Error: Unexpected response structure from interpreter."
        except Exception as e:
            # Debugging: Log exception details
            print("Debug: Exception encountered:", e)

            # Return a detailed error message for debugging
            return f"Error generating summary: {e}"








    # def generate_summary(self, question:str) -> str:
    #     """
    #     Generate the summary using the LLM and tailored prompt.
    #     """
        
    #     prompt = self.generate_tailored_prompt(question)
    #     messages = [
    #                 {"role": "system", "content": "You are a helpful assistant."},
    #                 {"role": "user", "content": prompt}  # User's input
    #                 ]
        
    #     try:
    #         #summary = interpreter.chat(prompt,display=False)
    #         summary = interpreter.chat(messages)  # Replace with your actual LLM function.
    #         content = summary[-1].get('content', 'No content found')
    #         return content
    #     except Exception as e:

    #         return f"Error generating summary: {e}"


# # Trigger function
# def main(dataframe: pd.DataFrame):
#     """
#     Trigger function to be called when a dataframe is generated.
#     """
#     summarizer = DataframeSummary(dataframe)
#     summary = summarizer.generate_summary()
#     #print("Summary:\n", summary)



