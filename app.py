import streamlit as st
import requests
import os
from dotenv import load_dotenv
import base64  # For encoding images

load_dotenv()  # Load .env file with GROK_API_KEY

GROK_API_URL = "https://api.x.ai/v1/chat/completions"
API_KEY = os.getenv("GROK_API_KEY")

def encode_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode('utf-8')

def call_grok(prompt, images=None, use_search=False):
    messages = [{"role": "user", "content": prompt}]
    
    if images:
        image_contents = []
        for img in images:
            base64_image = encode_image(img)
            image_contents.append({
                "type": "image_url",
                "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}
            })
        messages[0]["content"] = [{"type": "text", "text": prompt}] + image_contents
    
    payload = {
        "model": "grok-4-1-fast-non-reasoning",  # Low-cost model
        "messages": messages,
        "temperature": 0.7,
        "max_tokens": 300  # Reduced for cost savings
    }
    
    if use_search:
        payload["search_parameters"] = {"mode": "on"}
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    response = requests.post(GROK_API_URL, json=payload, headers=headers)
    if response.status_code == 200:
        return response.json()["choices"][0]["message"]["content"]
    else:
        return f"Error: {response.text}"

# Streamlit UI
st.title("Marketplace Selling Assistant")

tab1, tab2 = st.tabs(["Generate Listing", "Generate Response"])

with tab1:
    condition = st.selectbox("Item Condition", ["New", "Like New", "Good", "Fair"])
    location = st.text_input("Your Location (e.g., Seattle, WA)")
    uploaded_files = st.file_uploader("Upload 2-3 Photos", accept_multiple_files=True, type=["jpg", "png"])

    if st.button("Generate Listing") and uploaded_files:
        image_paths = []
        for uploaded_file in uploaded_files:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            image_paths.append(uploaded_file.name)
        
        # Combined prompt: Description + prices in one call
        combined_prompt = f"Analyze these photos of a used baby/toddler item in {condition} condition. First, generate a short appealing Facebook Marketplace title and description (highlight features, age suitability). Then, research average sold prices for similar used items in {location} and suggest a competitive price range."
        combined_output = call_grok(combined_prompt, images=image_paths, use_search=True)
        
        # Parse output (assume structured response)
        lines = combined_output.split("\n")
        item_name = lines[0] if lines else "Item"
        description = "\n".join(lines[1:lines.index("Price:") if "Price:" in lines else len(lines)]) if lines else "Error"
        price_suggestion = "\n".join(lines[lines.index("Price:") + 1:] if "Price:" in lines else []) or "Error"
        
        st.subheader("Suggested Title")
        st.write(item_name)
        
        st.subheader("Description")
        st.write(description)
        
        st.subheader("Price Suggestion")
        st.write(price_suggestion)
        
        st.success("Copy to Marketplace! (One API call used)")

with tab2:
    buyer_message = st.text_area("Paste Buyer Message Here", height=100)
    
    # Structured availability with checkboxes and custom inputs
    st.subheader("Availability")
    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    availability_dict = {}
    for day in days:
        st.write(f"**{day}**")
        cols = st.columns(4)
        with cols[0]:
            morning = st.checkbox("Morning (8am-12pm)", key=f"{day}_morning")
        with cols[1]:
            afternoon = st.checkbox("Afternoon (12pm-5pm)", key=f"{day}_afternoon")
        with cols[2]:
            evening = st.checkbox("Evening (5pm-9pm)", key=f"{day}_evening")
        with cols[3]:
            custom_time = st.text_input("Custom (e.g., 4-4:30pm)", key=f"{day}_custom", label_visibility="collapsed")
        
        # Collect selections
        slots = []
        if morning: slots.append("Morning")
        if afternoon: slots.append("Afternoon")
        if evening: slots.append("Evening")
        if custom_time: slots.append(f"Custom: {custom_time}")
        if slots:
            availability_dict[day] = ", ".join(slots)
    
    # Format availability string
    availability_str = "; ".join([f"{day}: {slots}" for day, slots in availability_dict.items()]) or "No specific availability set"
    
    preferred_locations = st.text_area("Preferred Meeting Locations (e.g., Local park, Mall)", height=100)
    
    if st.button("Generate Response") and buyer_message:
        response_prompt = f"Buyer: '{buyer_message}'. Availability: '{availability_str}'. Locations: '{preferred_locations}'. Suggest 2-3 polite responses, suggesting times/locations if relevant."
        suggested_responses = call_grok(response_prompt)  # No search/images, cheaper
        
        st.subheader("Suggested Responses")
        st.write(suggested_responses)
        
        st.success("Copy and paste back!")
