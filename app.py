import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import io
import openai

# Title of the app
st.title("Geospatial Practices Extractor")

# Instructions
st.write("Upload one or more PDF reports to extract geospatial practices and download the results as an Excel file.")

# Input for OpenAI API key
api_key = st.text_input("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", type="password")

# File uploader
uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

# Function to extract geospatial practices using OpenAI
def extract_practices_with_openai(text, index):
    prompt = f"""Extract geospatial practices from the following text and format each practice as:
[index number]. [Country name] - [Associated organization or N/A if non] - [Practice theme: energy, natural resource management, connectivity, disaster risk management, climate change mitigation or social development] - [Description of practice and technology used]

Text:
{text}

Start with index {index}.
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.7
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# Process files and extract data
if uploaded_files and api_key:
    openai.api_key = api_key
    all_practices = []
    index = 1

    for file in uploaded_files:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        extracted_text = extract_practices_with_openai(full_text, index)
        for line in extracted_text.split("\n"):
            if line.strip():
                all_practices.append({
                    "File Name": file.name,
                    "Extracted Practice": line.strip()
                })
                index += 1

    # Create DataFrame
    df = pd.DataFrame(all_practices)

    # Show extracted data
    st.subheader("Extracted Geospatial Practices")
    st.dataframe(df)

    # Provide download link for Excel
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Practices')
    st.download_button(
        label="Download Excel File",
        data=output.getvalue(),
        file_name="geospatial_practices.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )