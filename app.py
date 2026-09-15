import streamlit as st
from openlibrary import verify_book

st.set_page_config(page_title="What Should I Read Next?", layout="centered")
st.title("What Should I Read Next?")
st.caption("Enter 1-5 books you've enjoyed. Author is optional.")

# --- session state setup ---
# num_rows tracks how many book input rows are currently visible
if "num_rows" not in st.session_state:
    st.session_state.num_rows = 1

# --- render input rows ---
with st.form("book_input_form"):
    col_title, col_author = st.columns(2)
    col_title.markdown("**Book Title**")
    col_author.markdown("**Author** (optional)")

    for i in range(st.session_state.num_rows):
        title_placeholder = "Book Title" if i == 0 else "Book Title (optional)"
        col_title.text_input(
            title_placeholder, key=f"title_{i}", label_visibility="collapsed"
        )
        col_author.text_input(
            "Author", key=f"author_{i}", label_visibility="collapsed"
        )

    col1, col2 = st.columns([1, 1])
    add_row = col1.form_submit_button("+ Add another book")
    submitted = col2.form_submit_button("Submit", type="primary")

# --- handle "+ Add another book" ---
if add_row and st.session_state.num_rows < 5:
    st.session_state.num_rows += 1
    st.rerun()

# --- handle Submit ---
if submitted and not add_row:
    # Collect and validate inputs:
    # - Row 1: title is required to count
    # - Rows 2-5: title optional; author only used if title present
    books_input = []
    for i in range(st.session_state.num_rows):
        title = st.session_state.get(f"title_{i}", "").strip()
        author = st.session_state.get(f"author_{i}", "").strip()

        if i == 0 and not title:
            st.error("Please enter at least one book title (Row 1).")
            st.stop()

        if title:  # only include rows where a title was actually entered
            books_input.append({"title": title, "author": author or None})

    if not books_input:
        st.error("Please enter at least one book title.")
        st.stop()

    st.subheader("Verifying your books...")
    verified_books = []
    for entry in books_input:
        with st.spinner(f"Looking up '{entry['title']}'..."):
            result = verify_book(entry["title"], entry["author"])
        verified_books.append(result)

    # --- display verification results ---
    for entry, result in zip(books_input, verified_books):
        if result["status"] == "found":
            book = result["book"]
            cols = st.columns([1, 4])
            if book.get("cover_url"):
                cols[0].image(book["cover_url"], width=80)
            cols[1].markdown(f"**{book['title']}** by {book['author']}")
            cols[1].caption(f"OLID: {book['olid']} | ISBN: {book.get('isbn', 'N/A')}")
        elif result["status"] == "ambiguous":
            st.warning(f"'{entry['title']}' matched multiple books. Did you mean:")
            for candidate in result["candidates"]:
                st.write(f"- {candidate['title']} by {candidate['author']}")
        else:
            st.error(f"Could not find a book matching '{entry['title']}'. "
                      f"Please check the spelling or try a different title.")

    # Stash verified books in session_state so later days (candidate
    # generation, etc.) can access them without re-running verification.
    st.session_state.verified_books = verified_books