import streamlit as st
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import matplotlib.pyplot as plt
import mplcursors
import pandas as pd

from streamlit import set_page_config


# Update the Streamlit app configuration
st.set_page_config(
    page_title="MAP-AMR Kenya prospective surveillance",
    page_icon="🇰🇪",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Crafted by the MAP-AMR team. ",
        'Get help': None,
        'Report a bug': None,
    }
)

hide_streamlit_style = """
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    </style>
    """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
    
# Hide the "Made with Streamlit" footer
st.markdown('<style>footer{visibility:hidden;}</style>', unsafe_allow_html=True)


# Set up Streamlit title
st.title('MAP-AMR, Prospective Surveillance')

# Load the credentials from the secrets
credentials = ServiceAccountCredentials.from_json_keyfile_dict(
    st.secrets["gcp_service_account"],
    scopes=["https://www.googleapis.com/auth/spreadsheets"],
)

# Connect to Google Sheets API
gc = gspread.authorize(credentials)

# Open the Google Sheet
sheet_url = st.secrets["private_gsheets_url"]
sheet = gc.open_by_url(sheet_url)

# Get the sheet names and titles dynamically
sheet_names = [worksheet.title for worksheet in sheet.worksheets()]
graph_titles = [sheet_name + " trends" for sheet_name in sheet_names]

# Separate sheet names into different sections
positives_sheets = sheet_names[:3]
environmental_audits_sheets = sheet_names[3:8]
hand_hygiene_audits_sheets = sheet_names[8:]

# Create the multiselect navbar with sections
with st.sidebar:
    st.sidebar.write("### Positive Isolates Epicurves")
    selected_positives = st.sidebar.multiselect("", positives_sheets)

    st.sidebar.write("### Environmental Audits")
    selected_environmental_audits = st.sidebar.multiselect("", environmental_audits_sheets)

    st.sidebar.write("### Hand Hygiene Audits")
    selected_hand_hygiene_audits = st.sidebar.multiselect("", hand_hygiene_audits_sheets)

# Combine the selected sheets from different sections
selected_sheets = selected_positives + selected_environmental_audits + selected_hand_hygiene_audits

# Get the "Totals" worksheet
totals_worksheet = sheet.get_worksheet(sheet_names.index("Totals"))

# Extract the data from the "Totals" worksheet
def get_totals_data():
    totals_data = totals_worksheet.get_all_values()
    totals_header = totals_data[0]
    totals_rows = totals_data[1:]
    return pd.DataFrame(totals_rows, columns=totals_header)

totals_df = get_totals_data()

# Define a function to apply background colors to cells based on conditions
def apply_background_color(val):
    color_mapping = {
        'Date': 'lightblue',
        'KNH': 'lightgreen',
        'YNH': 'lightpink',
        'NSIRH': 'lightyellow'
    }
    return f'background-color: {color_mapping.get(val, "")}'

# Apply the background color to the DataFrame
styled_totals_df = totals_df.style.applymap(apply_background_color)

# Display the summary tabs using the data from the "Totals" worksheet
with st.container():
    st.markdown("## Summary")
    st.write("Total Patients Screened:")
    st.dataframe(styled_totals_df, width=800)

# Define the sheets that should have 'Number of patients' on y-axis
number_of_patients_sheets = positives_sheets[:3]

# Check if at least two graphs are selected
if len(selected_sheets) >= 2:
    # Display the graphs side by side
    st.write("## Selected graphs")
    st.write("Displaying selected graphs side by side:")
    st.write("")

    # Create a grid layout for the plots
    num_graphs = len(selected_sheets)
    num_cols = 2
    num_rows = (num_graphs + num_cols - 1) // num_cols
    fig, axs = plt.subplots(num_rows, num_cols, figsize=(12, 6 * num_rows), squeeze=False)

    # Iterate over selected sheets
    for i, selected_sheet in enumerate(selected_sheets):
        # Calculate the subplot indices
        row_idx = i // num_cols
        col_idx = i % num_cols

        # Get the index of the selected sheet
        selected_index = sheet_names.index(selected_sheet)

        # Get the selected sheet in the workbook
        worksheet = sheet.get_worksheet(selected_index)

        # Extract the data from the sheet
        data = worksheet.get_all_values()
        header = data[0]
        rows = data[1:]

        # Convert the data to a pandas DataFrame
        df = pd.DataFrame(rows, columns=header)

        # Identify the first column dynamically
        first_column = df.columns[0]

        # Convert numeric columns to numeric data types (if they exist)
        numeric_columns = []
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
                numeric_columns.append(col)
            except ValueError:
                pass

        if numeric_columns:
            # Plot the graph in the respective subplot
            ax = axs[row_idx, col_idx]
            bars = df.plot(x=first_column, y=numeric_columns, kind='bar', ax=ax)
            ax.set_xlabel(first_column)

            # Update y-axis label based on the selected_sheet
            if selected_sheet in number_of_patients_sheets:
                ax.set_ylabel('Number of patients')
            else:
                ax.set_ylabel('Percentage score')

            ax.set_title(selected_sheet)

            # Add labels to the bars (excluding bars with value 0)
            for container in bars.containers:
                for bar in container:
                    height = bar.get_height()
                    if height != 0:
                        ax.annotate(f'{height:.0f}', xy=(bar.get_x() + bar.get_width() / 2, height),
                                    xytext=(0, 3), textcoords='offset points',
                                    ha='center', va='bottom')

            # Add hover values using mplcursors
            cursor = mplcursors.cursor(hover=True)
            cursor.connect("add", lambda sel: sel.annotation.set_text(sel.target.y))

    # Adjust the spacing between subplots
    plt.subplots_adjust(wspace=0.3, hspace=0.4)

    # Display the plots
    st.pyplot(fig)

else:
    # Less than two graphs selected
    st.write("## Graph Display")
    st.write("On the top left, click on '>' to open the side panel. \
            Please select at least two graphs to display side by side.")
