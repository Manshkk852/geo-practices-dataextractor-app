import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import io
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# Title
st.title("Geospatial Practices Extractor")

# Instructions
st.write("""
Upload one or more PDF reports and press **'Extract Practices'** 
to analyze and download results as an Excel file.
""")

# File uploader
uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

# Function to extract geospatial practices using GPT
def extract_practices_with_openai(text, index):
    prompt = f"""
You are an expert in analyzing development and environmental project documents.

From the following report text, extract **geospatial practices** and organize each one into the following fields:

[index number]. 
- **Country:** [country mentioned or "Unknown"]
- **Partner/Organization:** [organization(s) involved or "N/A"]
- **Theme:** [choose one: Energy | Natural Resource Management | Connectivity | Disaster Risk Management | Climate Change Mitigation | Social Development]
- **Practice Description:** [clear description of what was done and what geospatial or remote sensing technology was used]
- **Supporting Quote:** [direct short quote or excerpt from the report text supporting this practice]

Return the results in plain text, one block per practice, starting with index {index}.

Text:
{text}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # better reasoning and cost-efficient
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# Process button to control execution
if uploaded_files:
    if st.button("Extract Practices"):
        all_practices = []
        index = 1

        with st.spinner("Extracting practices using OpenAI... Please wait."):
            for file in uploaded_files:
                # Read PDF
                doc = fitz.open(stream=file.read(), filetype="pdf")
                full_text = ""
                for page in doc:
                    full_text += page.get_text()
                doc.close()

                # Extract with GPT
                extracted_text = extract_practices_with_openai(full_text, index)

                # Parse GPT output into structured data
                current_practice = {"File Name": file.name}
                for line in extracted_text.split("\n"):
                    line = line.strip()
                    if line.startswith("- **Country:**"):
                        current_practice["Country"] = line.replace("- **Country:**", "").strip()
                    elif line.startswith("- **Partner/Organization:**"):
                        current_practice["Partner/Organization"] = line.replace("- **Partner/Organization:**", "").strip()
                    elif line.startswith("- **Theme:**"):
                        current_practice["Theme"] = line.replace("- **Theme:**", "").strip()
                    elif line.startswith("- **Practice Description:**"):
                        current_practice["Practice Description"] = line.replace("- **Practice Description:**", "").strip()
                    elif line.startswith("- **Supporting Quote:**"):
                        current_practice["Supporting Quote"] = line.replace("- **Supporting Quote:**", "").strip()
                    elif line.startswith("[") and current_practice.get("Country"):
                        all_practices.append(current_practice)
                        index += 1
                        current_practice = {"File Name": file.name}
                # Append last one
                if current_practice.get("Country"):
                    all_practices.append(current_practice)
                    index += 1

        # Create DataFrame
        df = pd.DataFrame(all_practices)

        # Display
        st.subheader("Extracted Geospatial Practices")
        st.dataframe(df)

        # Download Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Practices')

        st.download_button(
            label="Download Excel File",
            data=output.getvalue(),
            file_name="geospatial_practices_structured.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Please upload one or more PDF files to begin.")
