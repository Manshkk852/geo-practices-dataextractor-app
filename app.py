import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import io
import textwrap
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# --- UI HEADER ---
st.title("Geospatial Practices Extractor (Full Coverage Mode)")
st.write("""
Upload one or more PDF reports and click **'Extract Practices'** to analyze and download the results.  
This version uses *section-by-section extraction* to capture **all** practices in a single run.
""")

# File uploader
uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

# --- Helper: chunk text ---
def chunk_text(text, max_chars=9000, overlap=500):
    """Split text into overlapping chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = min(start + max_chars, len(text))
        chunks.append(text[start:end])
        start = end - overlap  # overlap for context continuity
        if start < 0:
            break
    return chunks

# --- Extraction function ---
def extract_practices_with_openai(text, index):
    prompt = f"""
You are an expert in analyzing development and environmental project documents.

From the following section of a report, extract **all possible geospatial practices**, 
even if they are uncertain, small-scale, or only partially described.

For this task:
- Be *comprehensive* and *inclusive*: list everything that might qualify.
- Look for mentions of geospatial, mapping, GIS, remote sensing, spatial databases, or digital tools.
- Also search for or near keywords like: adoption, project, new, achievements, introduce, developed, implemented, upgraded, plan, modernize, establish.
- If any practice seems related, list it.

For **each distinct practice**, output with the following structure:

[index number].
- **Practice Title:** A short, clear title (5–12 words)
- **Country:** [country mentioned or "Unknown"]
- **Partner/Organization:** [organization(s) involved or "N/A"]
- **Theme:** [choose one: Energy | Natural Resource Management | Connectivity | Disaster Risk Management | Climate Change Mitigation | Social Development | Spatial Governance | Agriculture | Urban Planning]
- **Practice Description:** [concise paragraph explaining what was done, developed, or planned and what technology/data was used]
- **Supporting Quote:** [short direct quote from this section supporting this practice]

List **all** relevant practices found in this section.  
Do not summarize; output each one in the above structure.

Text section:
{text}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# --- Main processing ---
if uploaded_files:
    if st.button("Extract Practices"):
        all_practices = []
        index = 1

        with st.spinner("Analyzing PDFs section by section... please wait."):
            for file in uploaded_files:
                # Read PDF
                doc = fitz.open(stream=file.read(), filetype="pdf")
                full_text = ""
                for page in doc:
                    full_text += page.get_text("text")
                doc.close()

                # Chunk text
                chunks = chunk_text(full_text)

                for chunk in chunks:
                    extracted_text = extract_practices_with_openai(chunk, index)

                    # Parse structured response
                    current_practice = {"File Name": file.name}
                    for line in extracted_text.split("\n"):
                        line = line.strip()
                        if line.startswith("- **Practice Title:**"):
                            current_practice["Practice Title"] = line.replace("- **Practice Title:**", "").strip()
                        elif line.startswith("- **Country:**"):
                            current_practice["Country"] = line.replace("- **Country:**", "").strip()
                        elif line.startswith("- **Partner/Organization:**"):
                            current_practice["Partner/Organization"] = line.replace("- **Partner/Organization:**", "").strip()
                        elif line.startswith("- **Theme:**"):
                            current_practice["Theme"] = line.replace("- **Theme:**", "").strip()
                        elif line.startswith("- **Practice Description:**"):
                            current_practice["Practice Description"] = line.replace("- **Practice Description:**", "").strip()
                        elif line.startswith("- **Supporting Quote:**"):
                            current_practice["Supporting Quote"] = line.replace("- **Supporting Quote:**", "").strip()
                        elif line.startswith("[") and current_practice.get("Practice Title"):
                            all_practices.append(current_practice)
                            index += 1
                            current_practice = {"File Name": file.name}
                    if current_practice.get("Practice Title"):
                        all_practices.append(current_practice)
                        index += 1

        # Convert to DataFrame
        df = pd.DataFrame(all_practices)

        # Deduplicate similar entries
        if not df.empty:
            df.drop_duplicates(subset=["Practice Title", "Supporting Quote"], inplace=True)

        # Display results
        st.subheader("Extracted Geospatial Practices (Comprehensive List)")
        st.dataframe(df)

        # Export to Excel
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Practices')

        st.download_button(
            label="Download Excel File",
            data=output.getvalue(),
            file_name="geospatial_practices_fullcoverage.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Please upload one or more PDF files to begin.")

