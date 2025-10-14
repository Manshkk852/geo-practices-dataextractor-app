import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import io
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# Title
st.title("Geospatial Practices Extractor (Expanded Detection)")

# Instructions
st.write("""
Upload one or more PDF reports and press **'Extract Practices'** 
to analyze and download results as an Excel file.

This version is more liberal — it captures *all potential* geospatial practices, 
even uncertain or partial ones, for manual review.
""")

# File uploader
uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

# Function to extract geospatial practices using GPT
def extract_practices_with_openai(text, index):
    prompt = f"""
You are an expert analyst extracting potential **geospatial practices** from technical and policy reports.

Be **liberal** in identifying practices — include all segments that describe:
- Use, testing, or proposal of geospatial, mapping, remote sensing, GIS, Earth observation, or data integration technologies.
- Development or modernization of spatial databases, mapping portals, SDI (spatial data infrastructure), or visualization systems (2D, 3D, or 4D).
- Actions or projects involving new data adoption, pilots, partnerships, digital tools, or platforms.
- Institutional initiatives or national efforts to use geospatial information for evidence-based decision making.

**Important:** 
If in doubt, include it. It's better to list an uncertain case than to omit a relevant one.

Also scan specifically for lines or sections containing or near the following keywords:
“adoption”, “action”, “project”, “new”, “future”, “achievements”, “introduce”, “developed”, “implemented”, “upgrade”, “plan”, “modernize”.

For **each distinct practice found**, output the following fields in the same order and formatting:

[index number].
- **Practice Title:** A short, clear title summarizing the practice (5–12 words max).
- **Country:** [country mentioned or "Unknown"]
- **Partner/Organization:** [organization(s) involved or "N/A"]
- **Theme:** [choose one: Energy | Natural Resource Management | Connectivity | Disaster Risk Management | Climate Change Mitigation | Social Development | Spatial Governance | Agriculture | Urban Planning]
- **Practice Description:** [clear, short paragraph describing what was done, developed, or planned, including what technology or data type was used]
- **Supporting Quote:** [brief direct quote or excerpt from the text supporting this practice]

Return one block per practice, starting with index {index}.

Text:
{text}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6  # Slightly exploratory
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {e}"

# Button to control execution
if uploaded_files:
    if st.button("Extract Practices"):
        all_practices = []
        index = 1

        with st.spinner("Extracting geospatial practices... This may take a few moments."):
            for file in uploaded_files:
                # Read PDF content
                doc = fitz.open(stream=file.read(), filetype="pdf")
                full_text = ""
                for page in doc:
                    full_text += page.get_text()
                doc.close()

                # Extract practices using GPT
                extracted_text = extract_practices_with_openai(full_text, index)

                # Parse GPT output into structured data
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

        # Create DataFrame
        df = pd.DataFrame(all_practices)

        # Display results
        st.subheader("Extracted Geospatial Practices (Expanded)")
        st.dataframe(df)

        # Download Excel file
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Practices')

        st.download_button(
            label="Download Excel File",
            data=output.getvalue(),
            file_name="geospatial_practices_expanded.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

else:
    st.info("Please upload one or more PDF files to begin.")
