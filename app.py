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
    
    try:
        response = requests.post(GROK_API_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except Exception as e:
        return f"Error: {str(e)} - Retry or check connection/key."

# Streamlit UI
st.title("Marketplace Selling Assistant")
st.markdown("Welcome! This app helps with any items—select category for tailored results. Safety tip: Meet in public, cash only.")

tab1, tab2 = st.tabs(["Generate Listing", "Generate Response"])

with tab1:
    category = st.selectbox("Item Category", ["Baby/Toddler", "Vehicles", "Equipment", "Clothing", "Electronics", "Furniture", "Other"])
    condition = st.selectbox("Item Condition", ["New", "Like New", "Good", "Fair"])
    location = st.text_input("Your Location (e.g., Seattle, WA)")
    details = st.text_area("Additional Details (e.g., VIN, model #, specs)", height=100)
    is_bundle = st.checkbox("This is a bundle/lot (e.g., multiple items)")
    uploaded_files = st.file_uploader("Upload 2-3 Photos per Item", accept_multiple_files=True, type=["jpg", "png"])

    if st.button("Generate Listing") and uploaded_files:
        image_paths = []
        for uploaded_file in uploaded_files:
            with open(uploaded_file.name, "wb") as f:
                f.write(uploaded_file.getbuffer())
            image_paths.append(uploaded_file.name)
        
        # Combined prompt: Generalized, with request for links in price section, clean formatting
        bundle_str = " (bundle/lot of items)" if is_bundle else ""
        combined_prompt = f"Analyze these photos of a used {category} item{bundle_str} in {condition} condition. Details: {details}. Output in this exact format: Title: [short title]\nDescription: [appealing description]\nPrice: [clean price range e.g. $X-Y with explanation, include 2-3 direct links to sources like eBay/Craigslist listings]. First, generate the title and description highlighting features and suitability. Then, research average sold prices for similar new/used items in {location} and suggest a competitive range."
        combined_output = call_grok(combined_prompt, images=image_paths, use_search=True)
        
        # Improved parsing: Use keywords, extract links, clean garbled text
        combined_output = combined_output.replace("−", "-")  # Fix common encoding issues
        if "Title:" in combined_output and "Description:" in combined_output and "Price:" in combined_output:
            parts = combined_output.split("Title:")[1].split("Description:")
            item_name = parts[0].strip()
            desc_parts = parts[1].split("Price:")
            description = desc_parts[0].strip()
            price_suggestion = desc_parts[1].strip() if len(desc_parts) > 1 else "Error: No price info"
            # Extract links (assume in price text, e.g., http...)
            links = [word for word in price_suggestion.split() if word.startswith("http")]
        else:
            item_name = "Item"
            description = combined_output
            price_suggestion = "Error: Incomplete response - try better photos or details"
            links = []
        
        st.subheader("Suggested Title")
        st.write(item_name)
        
        st.subheader("Description")
        st.write(description)
        
        st.subheader("Price Suggestion")
        st.write(price_suggestion)
        
        if links:
            st.subheader("Source Links for Further Research")
            for link in links:
                st.markdown(f"[View Source]({link})")
        
        st.success("Copy to Marketplace! (One API call used)")
        if "Error" in price_suggestion:
            if st.button("Retry Generation"):
                st.rerun()

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
        response_prompt = f"Buyer: '{buyer_message}'. Availability: '{availability_str}'. Locations: '{preferred_locations}'. Suggest 2-3 polite responses, suggesting times/locations if relevant. Always include safety tips: Meet in public, cash only, keep comms in app."
        suggested_responses = call_grok(response_prompt)  # No search/images, cheaper
        
        st.subheader("Suggested Responses")
        st.write(suggested_responses)
        
        st.success("Copy and paste back!")
