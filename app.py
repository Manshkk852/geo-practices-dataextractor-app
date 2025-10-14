import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import io
from openai import OpenAI

# Initialize OpenAI client
client = OpenAI(api_key=st.secrets["openai"]["api_key"])

# --- UI HEADER ---
st.title("Geospatial Practices Extractor (Full Coverage Mode)")
st.write("""
Upload one or more PDF reports and click **'Extract Practices'** to analyze and download the results.  
This version uses *section-by-section extraction* to capture **all** practices in one run.
""")

# File uploader
uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)


# --- Helper: chunk text safely ---
def chunk_text(text, max_chars=8000, overlap=500):
    """Split text into overlapping chunks without infinite loop risk."""
    chunks = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + max_chars, length)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == length:
            break
        start = end - overlap if end - overlap > start else end
    return chunks


# --- Function: Extract practices ---
def extract_practices_with_openai(text, index):
    prompt = f"""
You are an expert analyzing development and environmental reports.

From the text below, extract **ALL potential geospatial practices**, being liberal in what you consider a practice. 
Include mentions of mapping, GIS, remote sensing, spatial data, SDI, digital tools, portals, visualization systems, etc.

Also scan near keywords such as: adoption, action, project, new, introduce, achievement, developed, implemented, upgrade, plan, modernize.

For each distinct practice, provide the following fields clearly labeled:

[index number].
- **Practice Title:** A short, clear title (5–12 words)
- **Country:** [country mentioned or "Unknown"]
- **Partner/Organization:** [organization(s) involved or "N/A"]
- **Theme:** [choose one: Energy | Natural Resource Management | Connectivity | Disaster Risk Management | Climate Change Mitigation | Social Development | Spatial Governance | Agriculture | Urban Planning]
- **Practice Description:** [concise description of the activity and technology]
- **Supporting Quote:** [short direct quote from text supporting the practice]

List all practices found in this text section.
Text section:
{text}
"""
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.6,
            max_tokens=1500
        )
        return response.choices[0].message.content if response.choices else ""
    except Exception as e:
        return f"Error: {e}"


# --- Main process ---
if uploaded_files:
    if st.button("Extract Practices"):
        all_practices = []
        index = 1

        with st.spinner("Extracting practices from uploaded PDFs..."):
            for file in uploaded_files:
                try:
                    # Read PDF text
                    file_bytes = file.read()
                    doc = fitz.open(stream=file_bytes, filetype="pdf")
                    full_text = ""
                    for page in doc:
                        full_text += page.get_text("text") or ""
                    doc.close()

                    if not full_text.strip():
                        st.warning(f"No readable text found in {file.name}. Skipping.")
                        continue

                    # Split into chunks
                    chunks = chunk_text(full_text)
                    st.write(f"Processing **{file.name}** — {len(chunks)} sections detected.")

                    # Process each chunk
                    for i, chunk in enumerate(chunks):
                        extracted_text = extract_practices_with_openai(chunk, index)
                        if not extracted_text or "Error:" in extracted_text:
                            continue

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

                        # Append last one if valid
                        if current_practice.get("Practice Title"):
                            all_practices.append(current_practice)
                            index += 1

                        st.text(f"→ Processed chunk {i + 1}/{len(chunks)}")

                except Exception as e:
                    st.error(f"Error reading {file.name}: {e}")
                    continue

        # Create DataFrame
        if not all_practices:
            st.error("No practices were extracted from any file. Try adjusting the text or verifying PDFs.")
        else:
            df = pd.DataFrame(all_practices)
            df.drop_duplicates(subset=["Practice Title", "Supporting Quote"], inplace=True, ignore_index=True)

            st.subheader("Extracted Geospatial Practices (Comprehensive List)")
            st.dataframe(df)

            # Download Excel
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
