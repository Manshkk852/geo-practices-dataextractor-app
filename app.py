import streamlit as st
import fitz  # PyMuPDF
import pandas as pd
import io

# Title of the app
st.title("Geospatial Practices Extractor")

# Instructions
st.write("Upload one or more PDF reports to extract geospatial practices and download the results as an Excel file.")

# File uploader
uploaded_files = st.file_uploader("Upload PDF files", type=["pdf"], accept_multiple_files=True)

# Function to extract geospatial practices from text
def extract_practices(text):
    keywords = [
        'nsdi', 'geodetic', 'gnss', 'geoportal', 'lidar', 'uav', 'satellite',
        'mapping', 'height system', 'geospatial', 'coordinate system', 'geoid',
        'cadastral', 'spatial data', 'infrastructure', 'gravity', 'reference frame'
    ]
    practices = []
    lines = text.split('\n')
    for line in lines:
        line_lower = line.lower()
        if any(keyword in line_lower for keyword in keywords):
            practices.append(line.strip())
    return practices

# Process files and extract data
if uploaded_files:
    data = []
    for file in uploaded_files:
        doc = fitz.open(stream=file.read(), filetype="pdf")
        full_text = ""
        for page in doc:
            full_text += page.get_text()
        doc.close()

        practices = extract_practices(full_text)
        for practice in practices:
            data.append({
                "File Name": file.name,
                "Extracted Practice": practice
            })

    # Create DataFrame
    df = pd.DataFrame(data)

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
