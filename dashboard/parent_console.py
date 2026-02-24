import streamlit as st
import sqlite3
import pandas as pd
import os
import sys
import json

# Add root to sys.path
root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
sys.path.append(root_dir)

from core.utils.priority_memory import priority_memory

# Database Path
DB_PATH = os.path.join(root_dir, "data", "mimi_interactions.db")

st.set_page_config(page_title="Mimi Parent Console", layout="wide")

st.title("👨‍🏫 Mimi Parent Control Console")
st.markdown("Monitor conversations and fine-tune Mimi's intelligence.")

def get_interactions():
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM interactions ORDER BY timestamp DESC", conn)
    conn.close()
    return df

# Tabbed Layout
tab1, tab2 = st.tabs(["📊 Activity Log", "🧠 Training & Priority Memory"])

with tab1:
    st.header("Activity Log")
    df = get_interactions()
    
    if df.empty:
        st.info("No interactions logged yet.")
    else:
        # Display the log
        for index, row in df.iterrows():
            with st.expander(f"[{row['timestamp']}] {row['user_id']}: {row['user_input'][:50]}..."):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**Student Input:**")
                    st.info(row['user_input'])
                    st.write("**Intent Detected:**", row['intent'])
                with col2:
                    st.write("**Mimi's Response:**")
                    st.success(row['agent_output'])
                
                # Edit & Train Button
                st.write("---")
                st.subheader("Edit & Train (Human-in-the-Loop)")
                new_answer = st.text_area("Correct the answer or provide a 'Golden Response':", value=row['agent_output'], key=f"edit_{row['id']}")
                if st.button("Save as Priority Memory", key=f"btn_{row['id']}"):
                    priority_memory.add_golden_answer(
                        question=row['user_input'],
                        answer=new_answer,
                        metadata={"origin_interaction_id": row['id'], "edited_by": "parent"}
                    )
                    st.balloons()
                    st.success("Golden Answer saved! Mimi will now use this response for similar questions.")

with tab2:
    st.header("Priority Memory (Golden Answers)")
    st.write("These answers take precedence over LLM-generated content.")
    
    # Priority Memory View (Reading from JSON fallback or Chroma - for MVP we check the JSON/metadata)
    # Since we can't easily iterate Chroma without specific IDs in some versions,
    # we can show the fallback JSON contents if it exists.
    fallback_path = os.path.join(root_dir, "data", "mimi_priority_fallback.json")
    if os.path.exists(fallback_path):
        with open(fallback_path, 'r', encoding='utf-8') as f:
            priority_data = json.load(f)
            st.table(priority_data)
    else:
        st.info("No priority memory items found yet.")

# Automatic Refresh
if st.button("Refresh Data"):
    st.rerun()
